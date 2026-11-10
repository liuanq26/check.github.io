"""配置加载。

root      = 软件包目录（oldcal_check.exe 所在处）
result    = 运行产物根目录，默认在软件包同级，可用 --result 或 paths.result 改
"""
import copy
import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

# <pkg>/lib/oldcal_check/config.py -> <pkg>
PKG_ROOT = Path(__file__).resolve().parent.parent.parent

DEFAULTS: Dict[str, Any] = {
    "paths": {
        "result": "",
        "plot": "plot",
        "ntuple": "ntuple",
        "hist": "hist",
        "jobs": "",           # 空 = 日期目录直接放在 result 根下
        "reports": "reports",
        "state": ".state",    # 相对软件包目录
    },
    "batch": {
        "group": "",
        "submit_cmd": "boss.condor",
        "queue_cmd": "hep_q -u {user}",
        "extra_args": [],
        "poll_interval": 60,
        "max_wait": 43200,
        "submit_timeout": 180,
    },
    "data": {
        "raw_dir": "/besfs8/offline/data/cal/round20/{date}",
        "file_glob": "*GBB*raw",
        "run_regex": r"^run_(\d+)_GBB",
    },
    "db": {
        "hosts": ["bes3db2.ihep.ac.cn"],
        "user": "guest",
        "password": "guestpass",
        "timeout": 10,
        "retries": 2,
    },
    "check": {
        "source_dir": "check",
        "source": "check_pdf.cpp",
        "binary_name": "check_pdf",
        "lib_dir": "",
        "compile_flags": "-Wall -g",
        "link_libs": "-lRooFitCore -lRooFit -ltbb",
        "profiles": {
            "noiseRun": {
                "hist_dir": "hist",
                "cwd": "plot",
                "output": "noise_{runmin}_{runmax}.pdf",
            }
        },
    },
    "report": {
        "cover_mode": "auto",
        "cover_font": "/usr/share/fonts/google-droid-sans-fonts/DroidSansFallbackFull.ttf",
        "page_mm": [200, 127],
        "output": "mdc_{from}_{to}.pdf",
    },
    "steps": {
        "order": ["plan", "meta", "genjob", "submit", "wait", "collect", "check", "report"],
    },
    "prompt": {
        "last_file": "",  # 空 = ~/.oldcal_check/last.json
    },
}

SHARED_PREFIXES = ("/besfs", "/workfs", "/scratchfs", "/publicfs", "/cvmfs")


def _deep_merge(base: Dict[str, Any], override: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


# ---------------------------------------------------------------- YAML 兜底
def _strip_comment(line):
    out = []
    quote = None
    for ch in line:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            out.append(ch)
        elif ch == "#":
            break
        else:
            out.append(ch)
    return "".join(out).rstrip()


def _split_inline(text):
    parts, cur, quote, depth = [], [], None, 0
    for ch in text:
        if quote:
            cur.append(ch)
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            cur.append(ch)
        elif ch in "[{":
            depth += 1
            cur.append(ch)
        elif ch in "]}":
            depth -= 1
            cur.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if cur:
        parts.append("".join(cur).strip())
    return [p for p in parts if p != ""]


def _scalar(text):
    s = text.strip()
    if s in ("", "null", "~", "None"):
        return None
    low = s.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        return [_scalar(x) for x in _split_inline(inner)] if inner else []
    if s.startswith("{") and s.endswith("}"):
        out = {}
        for item in _split_inline(s[1:-1].strip()):
            key, _, value = item.partition(":")
            out[key.strip()] = _scalar(value)
        return out
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        return s


def _parse_block(items, idx, indent):
    if idx >= len(items):
        return None, idx

    if items[idx][1].startswith("-"):
        result = []
        while idx < len(items):
            ind, text = items[idx]
            if ind != indent or not text.startswith("-"):
                break
            rest = text[1:].strip()
            idx += 1
            if rest:
                result.append(_scalar(rest))
            elif idx < len(items) and items[idx][0] > indent:
                value, idx = _parse_block(items, idx, items[idx][0])
                result.append(value)
            else:
                result.append(None)
        return result, idx

    result = {}
    while idx < len(items):
        ind, text = items[idx]
        if ind != indent or text.startswith("-") or ":" not in text:
            break
        key, _, rest = text.partition(":")
        key = key.strip().strip("'\"")
        rest = rest.strip()
        idx += 1
        if rest:
            result[key] = _scalar(rest)
        elif idx < len(items) and items[idx][0] > indent:
            value, idx = _parse_block(items, idx, items[idx][0])
            result[key] = value
        else:
            result[key] = None
    return result, idx


def _mini_yaml(text):
    items = []
    for raw in text.splitlines():
        line = _strip_comment(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        items.append((indent, line.strip()))
    if not items:
        return {}
    value, _ = _parse_block(items, 0, items[0][0])
    return value


def _load_file(path):
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text) or {}
    return _mini_yaml(text)


# ---------------------------------------------------------------- Config
class Config(object):
    def __init__(self, result=None, config_file=None, overrides=None):
        self.package = PKG_ROOT
        self.config_file = Path(config_file) if config_file else (PKG_ROOT / "config" / "default.yaml")

        file_data = {}
        if self.config_file.is_file():
            file_data = _load_file(self.config_file)

        self.data = _deep_merge(DEFAULTS, _deep_merge(file_data, overrides or {}))
        self._result = result

    # ---------- 取值 ----------
    def get(self, dotted, default=None):
        cur = self.data
        for part in dotted.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return default
        return cur

    def p(self, dotted, **fmt):
        """取一个路径配置；相对路径基于 result 目录。"""
        raw = self.get(dotted)
        if raw is None:
            return None
        text = str(raw)
        if fmt:
            text = text.format(**fmt)
        path = Path(text).expanduser()
        return path if path.is_absolute() else (self.result_dir / path)

    # ---------- 目录 ----------
    @property
    def result_dir(self):
        if self._result:
            path = Path(self._result).expanduser()
        else:
            raw = str(self.get("paths.result") or "").strip()
            if not raw:
                # 没给任何配置：软件包同级的 result
                return (PKG_ROOT.parent / "result").resolve()
            path = Path(raw).expanduser()
        if not path.is_absolute():
            # 相对路径按当前工作目录解析，和包放在哪无关
            path = Path.cwd() / path
        return path.resolve()

    def _sub(self, key):
        return self.result_dir / str(self.get("paths." + key))

    @property
    def plot_dir(self):
        return self._sub("plot")

    @property
    def ntuple_dir(self):
        return self._sub("ntuple")

    @property
    def hist_dir(self):
        return self._sub("hist")

    @property
    def jobs_dir(self):
        sub = str(self.get("paths.jobs") or "").strip()
        return self.result_dir / sub if sub else self.result_dir

    @property
    def reports_dir(self):
        return self._sub("reports")

    @property
    def state_dir(self):
        raw = str(self.get("paths.state") or ".state").strip()
        path = Path(raw).expanduser()
        return path if path.is_absolute() else (self.package / path)

    @property
    def state_db(self):
        return self.state_dir / "state.db"

    def date_dir(self, date):
        return self.jobs_dir / date

    def ensure_dirs(self):
        for folder in (self.result_dir, self.plot_dir, self.ntuple_dir, self.hist_dir,
                       self.jobs_dir, self.reports_dir, self.state_dir,
                       self.state_dir / "logs", self.state_dir / "cover"):
            folder.mkdir(parents=True, exist_ok=True)

    # ---------- 检查程序 ----------
    @property
    def check_source_dir(self):
        return self.package / str(self.get("check.source_dir") or "check")

    @property
    def check_source(self):
        return self.check_source_dir / str(self.get("check.source") or "check_pdf.cpp")

    @property
    def check_binary(self):
        return self.plot_dir / str(self.get("check.binary_name") or "check_pdf")

    # ---------- 批处理 ----------
    def submit_command(self):
        cmd = str(self.get("batch.submit_cmd") or "boss.condor").split()
        group = self.get("batch.group") or ""
        if group:
            cmd += ["-g", str(group)]
        cmd += [str(x) for x in (self.get("batch.extra_args") or [])]
        return cmd

    # ---------- 杂项 ----------
    def is_shared_path(self):
        text = str(self.result_dir)
        return text.startswith(SHARED_PREFIXES)

    def last_file(self):
        custom = self.get("prompt.last_file") or ""
        if custom:
            return Path(custom).expanduser()
        return Path(os.path.expanduser("~")) / ".oldcal_check" / "last.json"
