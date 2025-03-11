# plugins/calculator_plugin.py
def get_functions():
    return [{
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Perform math calculations",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string"}
                },
                "required": ["expression"]
            }
        }
    }]

def handle_function_call(name, args):
    if name == "calculate":
        try:
            return eval(args["expression"])
        except:
            return "Invalid expression"