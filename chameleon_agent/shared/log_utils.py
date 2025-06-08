import datetime
from colorama import Fore, Style, init

# Initialize colorama to auto-reset colors after each print
init(autoreset=True)

# Emojis for different log levels/contexts
LOG_EMOJI = {
    "INFO": "ℹ️",
    "SUCCESS": "✅",
    "WARNING": "⚠️",
    "ERROR": "❌",
    "DEBUG": "🐞",
    "ORCHESTRATOR": "🎼",
    "AGENT": "🤖",
    "DEVICE": "📱",
    "LLM": "🧠",
    "ACTION": "⚡️",
    "OBSERVATION": "👀",
    "THOUGHT": "🤔",
    "SETUP": "🛠️",
    "CLEANUP": "🧹"
}

# Color mapping
COLOR_MAP = {
    "red": Fore.RED,
    "green": Fore.GREEN,
    "yellow": Fore.YELLOW,
    "blue": Fore.BLUE,
    "magenta": Fore.MAGENTA,
    "cyan": Fore.CYAN,
    "white": Fore.WHITE,
    "default": "" # No color
}

def log_message(
    level: str,
    message: str,
    component: str = None,
    color: str = "default"
):
    """
    A standardized logging function for the Chameleon agent.

    Args:
        level (str): The level of the message (e.g., "INFO", "ERROR", "SUCCESS").
                     Also used as a key for the emoji.
        message (str): The log message content.
        component (str, optional): The name of the component logging the message.
                                   Defaults to None.
        color (str, optional): The color for the message text.
                               Defaults to "default".
    """
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    emoji = LOG_EMOJI.get(level.upper(), "➡️")
    component_prefix = f"[{component}] " if component else ""
    log_color = COLOR_MAP.get(color.lower(), "")

    print(f"{emoji} {timestamp} {component_prefix}{log_color}{message}")