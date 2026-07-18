"""Keyboard-navigable terminal menus for scripts/cli_session.py (stdlib only). - AI generated UI for quick path validation"""
from __future__ import annotations

import sys
import termios
import tty
from typing import Optional, Sequence


def _is_interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _read_key() -> str:
    """Return 'up' | 'down' | 'enter' | 'space' | 'esc' | printable char."""
    ch = sys.stdin.read(1)
    if ch == "\x1b":
        nxt = sys.stdin.read(1)
        if nxt == "[":
            arrow = sys.stdin.read(1)
            if arrow == "A":
                return "up"
            if arrow == "B":
                return "down"
        return "esc"
    if ch in ("\r", "\n"):
        return "enter"
    if ch == " ":
        return "space"
    if ch == "\x03":
        raise KeyboardInterrupt
    return ch


def _frame(
    title: str,
    choices: Sequence[str],
    idx: int,
    *,
    checked: Optional[Sequence[bool]],
    hint: str,
) -> list[str]:
    lines = [title, f"  ({hint})"]
    for i, label in enumerate(choices):
        cursor = "›" if i == idx else " "
        if checked is None:
            lines.append(f"  {cursor} {label}")
        else:
            mark = "●" if checked[i] else "○"
            lines.append(f"  {cursor} {mark} {label}")
    return lines


def _paint(lines: list[str], *, prev_h: int) -> int:
    if prev_h:
        sys.stdout.write(f"\033[{prev_h}A")
    for line in lines:
        sys.stdout.write("\033[2K" + line + "\n")
    # Erase leftover lines if the new frame is shorter.
    for _ in range(max(0, prev_h - len(lines))):
        sys.stdout.write("\033[2K\n")
    if prev_h > len(lines):
        sys.stdout.write(f"\033[{prev_h - len(lines)}A")
    sys.stdout.flush()
    return len(lines)


def _erase(height: int) -> None:
    if height <= 0:
        return
    sys.stdout.write(f"\033[{height}A")
    for _ in range(height):
        sys.stdout.write("\033[2K\n")
    sys.stdout.write(f"\033[{height}A")
    sys.stdout.flush()


def select_one(
    title: str,
    choices: Sequence[str],
    *,
    hint: str = "↑↓ · Enter · q quit",
) -> Optional[str]:
    if not choices:
        raise ValueError("select_one requires at least one choice")
    if not _is_interactive():
        return _fallback_numbered(title, list(choices))

    idx = 0
    height = 0
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while True:
            lines = _frame(title, choices, idx, checked=None, hint=hint)
            height = _paint(lines, prev_h=height)
            key = _read_key()
            if key == "up":
                idx = (idx - 1) % len(choices)
            elif key == "down":
                idx = (idx + 1) % len(choices)
            elif key == "enter":
                _erase(height)
                print(f"  ✓ {choices[idx]}")
                return choices[idx]
            elif key in ("q", "esc"):
                _erase(height)
                return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def select_many(
    title: str,
    choices: Sequence[str],
    *,
    hint: str = "↑↓ · Space toggle · Enter · q quit",
) -> Optional[list[str]]:
    if not choices:
        raise ValueError("select_many requires at least one choice")
    if not _is_interactive():
        return _fallback_numbered(title, list(choices), multi=True)

    idx = 0
    checked = [False] * len(choices)
    height = 0
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while True:
            lines = _frame(title, choices, idx, checked=checked, hint=hint)
            height = _paint(lines, prev_h=height)
            key = _read_key()
            if key == "up":
                idx = (idx - 1) % len(choices)
            elif key == "down":
                idx = (idx + 1) % len(choices)
            elif key == "space":
                checked[idx] = not checked[idx]
            elif key == "enter":
                _erase(height)
                result = [c for c, on in zip(choices, checked) if on]
                print(f"  ✓ {', '.join(result) if result else '(none)'}")
                return result
            elif key in ("q", "esc"):
                _erase(height)
                return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def prompt_text(title: str, *, default: str = "") -> Optional[str]:
    suffix = f" [{default}]" if default else ""
    try:
        raw = input(f"{title}{suffix}\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    if raw.lower() == "q":
        return None
    return raw if raw else default


def _fallback_numbered(
    title: str,
    choices: list[str],
    *,
    multi: bool = False,
) -> Optional[str] | Optional[list[str]]:
    print(title)
    for i, c in enumerate(choices, 1):
        print(f"  {i}. {c}")
    if multi:
        raw = input("Numbers (comma-separated), or q: ").strip()
        if raw.lower() == "q":
            return None
        out: list[str] = []
        for part in raw.split(","):
            part = part.strip()
            if part:
                out.append(choices[int(part) - 1])
        return out
    raw = input("Number, or q: ").strip()
    if raw.lower() == "q":
        return None
    return choices[int(raw) - 1]
