from dataclasses import dataclass, field
from typing import Tuple

@dataclass
class UIElement:
    """A dataclass to represent an interactive UI element on the screen."""
    uid: str
    bbox: Tuple[Tuple[int, int], Tuple[int, int]]
    attributes: str
    text: str = ""
    children: list = field(default_factory=list)