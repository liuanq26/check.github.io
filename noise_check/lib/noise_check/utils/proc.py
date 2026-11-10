"""Unified subprocess execution: timeout, log to disk, non-UTF8 tolerant."""
import os
import shlex
import subprocess
import time
from pathlib import Path


class Result(object):
    def __init__(self, cmd, rc, out, err, seconds):
        self.cmd = cmd
        self.rc = rc
        self.out = out
        self.err = err
        self.seconds = seconds

    @property
    def ok(self):
        return self.rc == 0

    @property
    def combined(self):
        return (self.out or "") + (("\n" + self.err) if self.err else "")

    def tail(self, n=800):
        text = self.combined.strip()
        return text[-n:] if len(text) > n else text


def _decode(data):
    if data is None:
        return ""
    if isinstance(data, bytes):
        return data.decode("utf-8", "replace")
    return data


def run(cmd, cwd=None, timeout=None, env=None, log_file=None, shell=False):
    if isinstance(cmd, str) and not shell:
        argv = shlex.split(cmd)
    else:
        argv = cmd
    display = cmd if isinstance(cmd, str) else " ".join(shlex.quote(str(c)) for c in cmd)

    started = time.time()
    full_env = dict(os.environ)
    # The launcher replaces PYTHONPATH with our python3 lib; child processes
    # (boss.condor, ROOT tools, ...) need the original BOSS environment.
    if "NOISE_ORIG_PYTHONPATH" in full_env:
        full_env["PYTHONPATH"] = full_env["NOISE_ORIG_PYTHONPATH"]
    if env:
        full_env.update(env)

    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            env=full_env,
            shell=shell,
        )
        out = _decode(proc.stdout)
        err = _decode(proc.stderr)
        rc = proc.returncode
    except FileNotFoundError:
        out, err, rc = "", "command not found: " + display, 127
    except subprocess.TimeoutExpired as exc:
        out = _decode(exc.stdout)
        err = _decode(exc.stderr)
        err += "\ntimeout(%ss): %s" % (timeout, display)
        rc = 124

    seconds = time.time() - started
    res = Result(display, rc, out, err, seconds)

    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(path), "a", encoding="utf-8") as fh:
            fh.write("$ %s\n(cwd=%s)\n%s\n[rc=%d %.1fs]\n\n"
                     % (display, cwd, res.combined, rc, seconds))
    return res
