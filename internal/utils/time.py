from datetime import datetime


def format_timestamp(timestamp: int) -> str:
    """
    Format a timestamp ms to a human-readable string.
    :param timestamp: Timestamp in milliseconds.
    :return: Formatted date string.
    """
    if timestamp < 1000000000000:  # If timestamp is in seconds, convert to milliseconds
        timestamp *= 1000
    return datetime.utcfromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S.%f")[
        :-3
    ]  # Remove last 3 digits for milliseconds


def format_timestamp_to_UTC8(timestamp: int) -> str:
    """
    Format a timestamp ms to a human-readable string in UTC+8.
    :param timestamp: Timestamp in milliseconds.
    :return: Formatted date string in UTC+8.
    """
    if timestamp < 1000000000000:  # If timestamp is in seconds, convert to milliseconds
        timestamp *= 1000
    # Convert to UTC+8 by adding 8 hours (28800 seconds)
    timestamp += 28800000  # 8 hours in milliseconds
    return datetime.utcfromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S.%f")[
        :-3
    ]  # Remove last 3 digits for milliseconds
