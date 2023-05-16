"""
This is a boilerplate pipeline 'example00'
generated using Kedro 0.18.4
"""
import time

def echo(text: str, example: str, parameters: dict) -> str:
    time.sleep(int(parameters.get("duration", 1)))
    return text