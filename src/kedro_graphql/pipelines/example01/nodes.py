"""
This is a boilerplate pipeline 'example01'
generated using Kedro 0.19.11
"""
import time


def uppercase(text: str) -> str:
    """Converts text to uppercase."""
    return text.upper()


def reverse(text: str) -> str:
    """Reverses the given text."""
    return text[::-1]


def append_timestamp(text: str) -> str:
    """Appends a timestamp to the text."""
    return f"{text} - {time.time()}"


def timestamped_partitions(text: str) -> dict:
    """Returns a dict with the text and a timestamp for partitioned dataset example."""
    return {"part_00": f"{text} - {time.time()}",
            "part_01": f"{text} - {time.time()}",
            "part_02": f"{text} - {time.time()}"}
