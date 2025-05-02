import discord
from discord.ext import commands
import asyncio
from typing import Dict
import time
import threading

class DiscordBot(commands.Bot):
    def __init__(self, config, llm_service):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix=config.bot_config['command_prefix'],
            intents=intents,
            help_command=None
        )
        
        self.config = config
        self.llm = llm_service
        self.typing_tasks: Dict[str, asyncio.Task] = {}
        self.user_locks: Dict[str, asyncio.Lock] = {}

    async def start_typing(self, channel):
        try:
            while True:
                async with channel.typing():
                    await asyncio.sleep(4.5)
        except asyncio.CancelledError:
            pass

    async def safe_send(self, channel, content):
        print(f"Message from Bot: {content}") if self.config.full_log else None

        if len(content) < 2000:
            return await channel.send(content)
        
        # Handling long messages by splitting into parts
        parts = [content[i:i+1900] for i in range(0, len(content), 1900)]
        for part in parts:
            await channel.send(part)
            await asyncio.sleep(0.5)

    async def process_message(self, message: discord.Message):
        user_id = str(message.author.id)
        
        # Get or create a lock for the user
        lock = self.user_locks.setdefault(user_id, asyncio.Lock())
        
        async with lock:
            # Initialize typing_task to None
            typing_task = None 
            try:
                if self.config.stream_mode:
                    sent_message = None
                    current_response = ""
                    buffer = "" # Accumulate chunks between updates
                    last_update_time = 0.0 # Initialize timer
                    update_interval = 0.75  # Seconds between edits
                    edit_error_count = 0
                    max_edit_errors = 3 # Stop editing after consecutive errors

                    try:
                         # Queue for thread-safe communication between LLM thread and async loop
                         queue = asyncio.Queue()
                         loop = asyncio.get_running_loop()
                         # Event to signal when the LLM thread function has finished
                         llm_task_done = asyncio.Event() 

                         # Function to run the LLM generator in a separate thread
                         def llm_thread_target():
                             try:
                                 # Get the generator from the LLM service
                                 llm_generator = self.llm.get_response(
                                     user_id, message.content, message.author.name
                                 )
                                 # Iterate over chunks yielded by the generator
                                 for chunk in llm_generator:
                                     # Put chunk into the async queue safely from the thread
                                     future = asyncio.run_coroutine_threadsafe(queue.put(chunk), loop)
                                     future.result() # Wait for put() to complete (optional, but ensures queue doesn't grow infinitely if consumer is slow)
                                     
                                 # Signal end of stream by putting None
                                 asyncio.run_coroutine_threadsafe(queue.put(None), loop).result()
                             except Exception as e:
                                 # Handle errors during generation within the thread
                                 err_msg = f"🚨 Critical error in LLM thread: {e}"
                                 print(err_msg)
                                 # Put error message onto queue for main thread to handle
                                 asyncio.run_coroutine_threadsafe(queue.put(err_msg), loop).result()
                                 # Still signal completion after error
                                 asyncio.run_coroutine_threadsafe(queue.put(None), loop).result()
                             finally:
                                # Signal that the thread function is finished executing
                                loop.call_soon_threadsafe(llm_task_done.set)

                         # Start the LLM generation in the background thread
                         thread = threading.Thread(target=llm_thread_target, daemon=True)
                         thread.start()

                         # Consume items from the queue in the main async event loop
                         while True:
                             chunk = await queue.get()

                             # Check for end-of-stream signal
                             if chunk is None:
                                 queue.task_done() # Mark item processed
                                 break # Exit consumption loop

                             # Check if the chunk is an error message
                             if chunk.startswith(("⚠️ Error:", "🚨 Critical error:")):
                                 current_response = chunk # Display the error
                                 buffer = "" # Clear any pending buffer
                                 if sent_message:
                                     try:
                                         # Try to edit the existing message to show the error
                                         await sent_message.edit(content=current_response)
                                     except (discord.HTTPException, discord.NotFound):
                                         # If edit fails, try sending error as new message
                                         print(f"Failed to edit message with error, sending new.")
                                         await self.safe_send(message.channel, current_response)
                                 else:
                                     # If no message sent yet, send the error directly
                                     await self.safe_send(message.channel, current_response)
                                 queue.task_done()
                                 # Wait for thread cleanup before returning
                                 await llm_task_done.wait() 
                                 return # Stop processing this request

                             # Process a normal chunk
                             current_response += chunk
                             buffer += chunk
                             now = time.time()

                             # Send initial message or edit existing one
                             if not sent_message:
                                try:
                                   # Initial message send (use buffer first, then add cursor)
                                   sent_message = await message.channel.send(buffer + " ▌")
                                   current_response = buffer # Ensure current_response matches sent content
                                   buffer = "" # Clear buffer after send
                                   last_update_time = now # Start timer after first send
                                except discord.HTTPException as e:
                                     print(f"Error sending initial stream message: {e}")
                                     await message.channel.send("⚠️ Error starting stream.")
                                     # Need to signal thread to stop? For now, just break locally.
                                     break # Stop processing chunks
                             
                             # Check if update interval passed and there's new content
                             elif now - last_update_time >= update_interval and buffer:
                                 if edit_error_count < max_edit_errors:
                                     try:
                                         await sent_message.edit(content=current_response + " ▌")
                                         buffer = "" # Clear buffer on success
                                         last_update_time = now
                                         edit_error_count = 0 # Reset errors on success
                                         await asyncio.sleep(0.05) # Small yield
                                     except discord.NotFound:
                                         print("Message not found during edit (deleted?). Stopping updates.")
                                         break # Stop processing chunks
                                     except discord.HTTPException as e:
                                         edit_error_count += 1
                                         print(f"Failed to edit message ({edit_error_count}/{max_edit_errors}): {e}")
                                         # Keep buffer, will try again or use in final edit
                                         last_update_time = now # Prevent rapid retries
                                 else:
                                     # Max edit errors reached, stop trying to edit this message
                                     if buffer: # Only print warning once
                                         print("Max edit errors reached, further edits skipped.")
                                         buffer = "" # Discard buffer for this interval to prevent spam

                             queue.task_done() # Mark chunk as processed

                         # --- End of queue consumption loop ---

                         # Final edit after loop finishes to show complete response and remove cursor
                         if sent_message:
                            final_content = current_response # Contains full response now
                            if edit_error_count < max_edit_errors:
                                try:
                                     # Edit one last time to remove cursor and ensure all content is present
                                     await sent_message.edit(content=final_content)
                                except (discord.HTTPException, discord.NotFound) as e:
                                    print(f"Failed final message edit: {e}")
                                    # Optionally send remaining buffer if final edit failed
                                    # if buffer: await self.safe_send(message.channel, "..." + buffer)
                            else:
                                # If editing failed too many times, maybe send the full thing as a new message
                                print("Final edit skipped due to previous errors.")
                                # await self.safe_send(message.channel, final_content) # Alternative

                         # Wait for the background thread function to fully complete
                         await llm_task_done.wait()

                    except Exception as e:
                        # Catch errors in the main async stream handling logic
                        print(f"Error during stream processing/queue handling: {e}")
                        await message.channel.send(f"🚨 An error occurred processing the stream.")

                # --- NON-STREAMING MODE ---
                else:
                    # Start typing indicator for non-stream mode
                    typing_task = asyncio.create_task(self.start_typing(message.channel))
                    self.typing_tasks[user_id] = typing_task
                    
                    response_text = ""
                    try:
                         # Define helper to run generator and collect chunks in thread
                         def collect_chunks_target():
                             generator = self.llm.get_response(
                                 user_id, message.content, message.author.name
                             )
                             # Consume the generator completely within the thread
                             chunks = list(generator)
                             # Check if the first (and potentially only) chunk is an error
                             if chunks and chunks[0].startswith(("⚠️ Error:", "🚨 Critical error:")):
                                 return chunks[0] # Return only the error message
                             else:
                                 return "".join(chunks) # Join normal chunks

                         # Run the helper in a thread
                         response_text = await asyncio.to_thread(collect_chunks_target)
                         
                         # Send the complete response (or error) collected from the thread
                         await self.safe_send(message.channel, response_text)

                    except Exception as e:
                         print(f"Critical error processing non-stream message: {e}")
                         await message.channel.send(f"🚨 Critical error: {str(e)}")
                    finally:
                         # Always cancel typing task in non-stream mode after completion/error
                         if typing_task:
                             typing_task.cancel()
                             # Remove task from dict (handled in outer finally too, but good practice here)
                             self.typing_tasks.pop(user_id, None) 

            except Exception as e:
                # Catch-all for unexpected errors in process_message
                print(f"Outer critical error in process_message: {str(e)}")
                await message.channel.send(f"🚨 An unexpected critical error occurred.")
                
            finally:
                # Ensure typing task (if any started) is always cleaned up
                # This handles cases where errors occurred before specific finally blocks
                task = self.typing_tasks.pop(user_id, None)
                if task and not task.done():
                    task.cancel()

    async def on_ready(self):
        await self.change_presence(activity=discord.Game(name="DM me"))
        print(f"Bot {self.user} is online")

    async def on_message(self, message):
        if message.author == self.user:
            return
            
        if self.config.bot_config['only_dm'] and not isinstance(message.channel, discord.DMChannel):
            return
        
        print(f"Message from {message.author}: {message.content}") if self.config.full_log else None

        ctx = await self.get_context(message)
        if not ctx.valid:
            await self.process_message(message)
            
        await self.process_commands(message)
