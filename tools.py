import ast
import operator
import os

import requests
from dotenv import load_dotenv

load_dotenv()

WEATHER_URL = "https://api.weatherapi.com/v1/current.json"
WEATHER_TIMEOUT_SECONDS = 10


def get_weather(city):
    """Look up current weather via WeatherAPI (https://www.weatherapi.com/docs/).

    Uses HTTPS, passes the city as a query parameter so it is URL-encoded, and
    sets a timeout so a slow upstream cannot hang the request thread.
    """
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        return "Could not get weather: WEATHER_API_KEY is not configured"
    if not isinstance(city, str) or not city.strip():
        return "Could not get weather: provide a city name"
    try:
        response = requests.get(
            WEATHER_URL,
            params={"key": api_key, "q": city.strip()},
            timeout=WEATHER_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        temp = data['current']['temp_c']
        condition = data['current']['condition']['text']
        humidity = data['current']['humidity']
        return f"Weather in {city}: {temp}°C, {condition}, Humidity: {humidity}%"
    except requests.HTTPError as e:
        # str(e) would echo the request URL, which contains the API key.
        return f"Could not get weather: upstream returned HTTP {e.response.status_code}"
    except requests.RequestException:
        return "Could not get weather: upstream request failed"
    except (KeyError, ValueError):
        return "Could not get weather: unexpected response format"


_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
MAX_EXPRESSION_LENGTH = 200


def _eval_node(node):
    """Evaluate an AST node using only + - * / and unary +/- on numbers."""
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("unsupported syntax")


def calculate(expression):
    """Evaluate a basic arithmetic expression without using eval().

    The model chooses `expression`, and the model can be steered by user input,
    so it is treated as untrusted. The previous version filtered characters and
    then called eval(); that still allowed `9**9**9`, which pins a CPU. This
    version parses the text and walks the syntax tree, permitting only numbers,
    + - * / and parentheses. Exponentiation is deliberately not supported.
    """
    if not isinstance(expression, str) or not expression.strip():
        return "Invalid — provide a math expression"
    if len(expression) > MAX_EXPRESSION_LENGTH:
        return "Invalid — expression too long"
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        return f"Result: {_eval_node(tree)}"
    except ZeroDivisionError:
        return "Could not calculate: division by zero"
    except (SyntaxError, ValueError, RecursionError, OverflowError):
        return "Invalid — only numbers and + - * / ( ) are allowed"


TOOLS = [
    {
        "name": "get_weather",
        "description": "Get current real weather for any city in the world",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name e.g. Calgary, Toronto"
                }
            },
            "required": ["city"]
        }
    },
    {
        "name": "calculate",
        "description": "Calculate any math expression e.g. 45*40",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Math expression e.g. 45*40"
                }
            },
            "required": ["expression"]
        }
    }
]