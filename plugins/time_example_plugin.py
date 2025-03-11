import datetime

def get_functions():
    return [{
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get current time in specified timezone",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string", "enum": ["UTC", "EST", "PST"]}
                },
                "required": ["timezone"]
            }
        }
    }]

def handle_function_call(name, arguments):
    if name == "get_current_time":
        tz = arguments.get('timezone', 'UTC')
        return "Time: " + datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S') + " timezone " + tz
    return None