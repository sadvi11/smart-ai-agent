import requests
import os
from dotenv import load_dotenv

load_dotenv()

def get_weather(city):
    api_key = os.getenv("WEATHER_API_KEY")
    url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={city}"
    try:
        response = requests.get(url)
        data = response.json()
        temp = data['current']['temp_c']
        condition = data['current']['condition']['text']
        humidity = data['current']['humidity']
        return f"Weather in {city}: {temp}°C, {condition}, Humidity: {humidity}%"
    except Exception as e:
        return f"Could not get weather: {str(e)}"


def calculate(expression):
    try:
        allowed = set('0123456789+-*/()., ')
        if all(c in allowed for c in expression):
            result = eval(expression)
            return f"Result: {result}"
        else:
            return "Invalid — only numbers and math operators allowed"
    except Exception as e:
        return f"Could not calculate: {str(e)}"


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