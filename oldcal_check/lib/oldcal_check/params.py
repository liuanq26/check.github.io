"""Parameter.txt 解析：阈值参数（m/n）和各检查量开关。"""
import os
from pathlib import Path

DEFAULTS = {
    "m": 200.0,
    "n": 1.0,
    "min_runs": 5,
    "min_rel_band": 0.01,
}


def _strip(line):
    for mark in ("#", "//"):
        pos = line.find(mark)
        if pos >= 0:
            line = line[:pos]
    return line.strip()


def load(path=None, package=None):
    """返回 {'m','n','min_runs','min_rel_band','quantities': {name: {...}}}。"""
    if path is None:
        base = Path(package) if package else Path(__file__).resolve().parent.parent.parent
        path = Path(base) / "Parameter.txt"
    path = Path(path)

    params = dict(DEFAULTS)
    params["quantities"] = {}
    params["path"] = str(path)
    params["error"] = None

    if not path.is_file():
        params["error"] = "Parameter.txt not found: %s" % path
        return params

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = _strip(raw)
        if not line:
            continue

        if "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            try:
                number = float(value)
            except ValueError:
                continue
            if key in ("m", "n", "min_runs", "min_rel_band"):
                params[key] = number
            continue

        parts = line.split()
        if len(parts) < 3:
            continue
        name = parts[0]
        try:
            q_m = float(parts[1])
            q_n = float(parts[2])
        except ValueError:
            continue
        flag = parts[3].lower() if len(parts) > 3 else "on"
        label = " ".join(parts[4:]) if len(parts) > 4 else name
        params["quantities"][name] = {
            "m": q_m,
            "n": q_n,
            "enabled": flag in ("on", "yes", "true", "1"),
            "label": label,
        }

    return params
