"""BOSS job submission: boss.condor [ -g <group> ] rec<run>.txt"""

import re
from pathlib import Path
from typing import Optional, Tuple

from ..context import Context
from ..utils import proc

SUCCESS_MARK = "Application Manager Terminated successfully"
_JOBID_PATTERNS = [
    re.compile(r"(?:job|Job|JOB)\D{0,12}?(\d{4,})"),
    re.compile(r"^\s*(\d{4,})\s*$", re.M),
    re.compile(r"submitted.*?(\d{4,})", re.I),
]


def parse_job_id(text: str) -> Optional[str]:
    for pattern in _JOBID_PATTERNS:
        m = pattern.search(text or "")
        if m:
            return m.group(1)
    return None


def submit(ctx: Context, date: str, run: int) -> Tuple[Optional[str], object]:
    """Submit rec<run>.txt in the date folder; return (job_id, Result)."""
    workdir = ctx.date_dir(date)
    script = f"rec{run}.txt"
    cmd = ctx.cfg.submit_command() + [script]
    if ctx.dry:
        ctx.log.info(f"[dry-run] (cd {workdir} && {' '.join(cmd)})")
        return None, None
    res = proc.run(
        cmd,
        cwd=workdir,
        timeout=float(ctx.cfg.get("batch.submit_timeout", 180)),
        log_file=workdir / f"rec{run}.submit.log",
    )
    job_id = parse_job_id(res.combined) if res.ok else None
    return job_id, res


def bosslog_finished(path: Path) -> bool:
    """Look for the BOSS finish mark in the log tail.

    Gaudi also prints "Terminated successfully" when a service fails to
    initialise, so a FATAL anywhere in the tail means failure.
    """
    if not path.is_file():
        return False
    try:
        size = path.stat().st_size
        with open(path, "rb") as fh:
            if size > 200_000:
                fh.seek(size - 200_000)
            tail = fh.read().decode("utf-8", "replace")
    except OSError:
        return False
    if SUCCESS_MARK not in tail:
        return False
    return "FATAL" not in tail


_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _clean(text: str) -> str:
    return _ANSI.sub("", text).replace("\r", "").strip()


def job_error(ctx, date, run) -> str:
    """Last meaningful error; otherwise the last useful log line."""
    folder = ctx.date_dir(date)
    chunks = []
    for name in ("rec%d.txt.bosslog" % run, "rec%d.bosslog" % run):
        path = folder / name
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
            break
    err_file = folder / ("rec%d.txt.bosserr" % run)
    if err_file.is_file() and err_file.stat().st_size:
        chunks.append(err_file.read_text(encoding="utf-8", errors="replace"))

    lines = [l for l in (_clean(x) for x in "\n".join(chunks).splitlines()) if l]
    if not lines:
        return "no bosslog"

    def useful(line):
        low = line.lower()
        if "terminated successfully" in low:
            return False
        if line.startswith(("2.", "1.", "0.")) and "u " in line and "s " in line:
            return False
        return True

    hits = [l for l in lines if useful(l) and ("error" in l.lower() or "fatal" in l.lower())]
    for idx in range(len(lines) - 1, -1, -1):
        if "fatal" in lines[idx].lower() and useful(lines[idx]):
            message = lines[idx][:200]
            for nxt in lines[idx + 1:idx + 4]:
                if "error" in nxt.lower() and useful(nxt):
                    message += " | " + nxt[:160]
                    break
            return message
    if hits:
        return hits[-1][:300]
    for line in reversed(lines):
        if useful(line):
            return line[:300]
    return lines[-1][:300]


def bosslog_error(path: Path) -> Optional[str]:
    """Pick one meaningful error summary from a bosslog."""
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    bad = [
        _clean(line) for line in text.splitlines()
        if "ERROR" in line.upper() or "FATAL" in line.upper()
    ]
    for line in reversed(bad):
        if "fatal" in line.lower():
            return line[:300]
    for line in reversed(bad):
        if "could not load" in line.lower() or "cannot find" in line.lower():
            return line[:300]
    return bad[-1][:300] if bad else None


def queue_job_ids(ctx) -> Optional[set]:
    """Cluster job ids currently in the queue; None if unavailable."""
    import getpass

    template = ctx.cfg.get("batch.queue_cmd") or ""
    if not template:
        return None
    cmd = str(template).replace("{user}", getpass.getuser())
    res = proc.run(cmd, timeout=60)
    if not res.ok:
        return None
    ids = set()
    for line in res.out.splitlines():
        parts = line.split()
        if parts and re.match(r"^\d+\.\d+$", parts[0]):
            ids.add(parts[0].split(".")[0])
    return ids
