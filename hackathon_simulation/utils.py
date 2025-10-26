from __future__ import annotations

import os
from typing import Optional, Tuple


def parse_team_size(value: str) -> Tuple[int, int]:
    parts = value.split("-")
    if len(parts) != 2:
        raise ValueError("Team size must be in 'min-max' format.")
    low, high = int(parts[0]), int(parts[1])
    if low < 1 or high < low:
        raise ValueError("Invalid team size range.")
    return low, high


def ensure_parent_dir(path: Optional[str]) -> None:
    if not path:
        return
    directory = os.path.dirname(os.path.abspath(path))
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
