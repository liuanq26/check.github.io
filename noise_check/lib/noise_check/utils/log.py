"""Logger: terminal plus .state/logs/<date>.log."""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class Logger:
    def __init__(self, path: Optional[Path] = None, quiet: bool = False) -> None:
        self.path = Path(path) if path else None
        self.quiet = quiet
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def bind(self, date: str) -> "Logger":
        if self.path is not None:
            self.path = self.path.parent / f"{date}.log"
        return self

    def _emit(self, level: str, msg: str) -> None:
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {level:<5} {msg}"
        if not self.quiet or level in ("ERROR", "WARN"):
            stream = sys.stderr if level in ("ERROR", "WARN") else sys.stdout
            print(line, file=stream, flush=True)
        if self.path:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    def info(self, msg: str) -> None:
        self._emit("INFO", msg)

    def warn(self, msg: str) -> None:
        self._emit("WARN", msg)

    def error(self, msg: str) -> None:
        self._emit("ERROR", msg)

    def raw(self, msg: str) -> None:
        print(msg, flush=True)
        if self.path:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(msg + "\n")
