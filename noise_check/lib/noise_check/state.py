"""SQLite state store: the single source of truth for the pipeline."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS batches (
    date       TEXT PRIMARY KEY,
    status     TEXT,
    n_runs     INTEGER DEFAULT 0,
    note       TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    run        INTEGER PRIMARY KEY,
    date       TEXT,
    status     TEXT,
    job_id     TEXT,
    nevents    INTEGER,
    estart     TEXT,
    eend       TEXT,
    bpr        REAL,
    ber        REAL,
    bosslog_ok INTEGER DEFAULT 0,
    ntuple     TEXT,
    hist       TEXT,
    checks     TEXT,
    pdf        TEXT,
    error      TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS steps (
    run         INTEGER,
    step        TEXT,
    status      TEXT,
    started_at  TEXT,
    finished_at TEXT,
    message     TEXT,
    PRIMARY KEY (run, step)
);

CREATE INDEX IF NOT EXISTS idx_runs_date ON runs(date);
CREATE INDEX IF NOT EXISTS idx_steps_step ON steps(step, status);

CREATE TABLE IF NOT EXISTS qvalues (
    run        INTEGER,
    quantity   TEXT,
    value      REAL,
    date       TEXT,
    updated_at TEXT,
    PRIMARY KEY (run, quantity)
);

CREATE INDEX IF NOT EXISTS idx_qvalues_q ON qvalues(quantity, run);
"""

RUN_FIELDS = {
    "date", "status", "job_id", "nevents", "estart", "eend", "bpr", "ber",
    "bosslog_ok", "ntuple", "hist", "checks", "pdf", "error",
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Store:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path), timeout=30)
        self.conn.row_factory = sqlite3.Row
        try:
            self.conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.DatabaseError:
            pass
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        self.dry = False

    def close(self) -> None:
        self.conn.close()

    # ---------- batches ----------
    def upsert_batch(self, date: str, **fields: Any) -> None:
        if self.dry:
            return
        self.conn.execute(
            "INSERT OR IGNORE INTO batches(date, created_at, updated_at) VALUES(?,?,?)",
            (date, _now(), _now()),
        )
        sets, vals = ["updated_at=?"], [_now()]
        for key in ("status", "n_runs", "note"):
            if key in fields:
                sets.append(f"{key}=?")
                vals.append(fields[key])
        vals.append(date)
        self.conn.execute(f"UPDATE batches SET {', '.join(sets)} WHERE date=?", vals)
        self.conn.commit()

    def batch(self, date: str) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM batches WHERE date=?", (date,)).fetchone()

    # ---------- runs ----------
    def upsert_run(self, run: int, date: Optional[str] = None, **fields: Any) -> None:
        if self.dry:
            return
        self.conn.execute(
            "INSERT OR IGNORE INTO runs(run, date, updated_at) VALUES(?,?,?)",
            (run, date, _now()),
        )
        sets, vals = ["updated_at=?"], [_now()]
        if date:
            sets.append("date=?")
            vals.append(date)
        for key, value in fields.items():
            if key not in RUN_FIELDS:
                raise KeyError(f"unknown field {key}")
            sets.append(f"{key}=?")
            vals.append(value)
        vals.append(run)
        self.conn.execute(f"UPDATE runs SET {', '.join(sets)} WHERE run=?", vals)
        self.conn.commit()

    def run_row(self, run: int) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM runs WHERE run=?", (run,)).fetchone()

    def runs_of(self, date: str) -> List[sqlite3.Row]:
        return list(self.conn.execute("SELECT * FROM runs WHERE date=? ORDER BY run", (date,)))

    def all_runs(self) -> List[sqlite3.Row]:
        return list(self.conn.execute("SELECT * FROM runs ORDER BY run"))

    def date_of_run(self, run: int) -> Optional[str]:
        row = self.conn.execute("SELECT date FROM runs WHERE run=?", (run,)).fetchone()
        return row["date"] if row else None

    # ---------- steps ----------
    def set_step(self, run: int, step: str, status: str, message: Optional[str] = None) -> None:
        if self.dry:
            return
        now = _now()
        self.conn.execute(
            "INSERT OR IGNORE INTO steps(run, step, status) VALUES(?,?,?)",
            (run, step, status),
        )
        sets = ["status=?"]
        vals = [status]
        if status == "running":
            sets.append("started_at=COALESCE(started_at, ?)")
            vals.append(now)
        elif status in ("done", "failed", "skip", "timeout"):
            sets.append("finished_at=?")
            vals.append(now)
        if message is not None:
            sets.append("message=?")
            vals.append(message)
        vals.extend([run, step])
        self.conn.execute(
            "UPDATE steps SET %s WHERE run=? AND step=?" % ", ".join(sets), vals
        )
        self.conn.commit()

    def step_status(self, run: int, step: str) -> Optional[str]:
        row = self.conn.execute(
            "SELECT status FROM steps WHERE run=? AND step=?", (run, step)
        ).fetchone()
        return row["status"] if row else None

    def step_done(self, run: int, step: str) -> bool:
        return self.step_status(run, step) in ("done", "skip")

    def step_message(self, run: int, step: str) -> Optional[str]:
        row = self.conn.execute(
            "SELECT message FROM steps WHERE run=? AND step=?", (run, step)
        ).fetchone()
        return row["message"] if row else None

    def failed_runs(self, date: str) -> List[int]:
        return [r["run"] for r in self.runs_of(date) if r["status"] == "failed"]

    # ---------- physics values ----------
    def set_value(self, run, quantity, value, date=None):
        if self.dry:
            return
        self.conn.execute(
            "INSERT OR REPLACE INTO qvalues(run, quantity, value, date, updated_at) "
            "VALUES(?,?,?,?,?)",
            (run, quantity, value, date, _now()),
        )
        self.conn.commit()

    def value(self, run, quantity):
        row = self.conn.execute(
            "SELECT value FROM qvalues WHERE run=? AND quantity=?", (run, quantity)
        ).fetchone()
        return row["value"] if row else None

    def recent_values(self, quantity, before_run, limit):
        rows = self.conn.execute(
            "SELECT value FROM qvalues WHERE quantity=? AND run<? AND value IS NOT NULL "
            "ORDER BY run DESC LIMIT ?",
            (quantity, before_run, int(limit)),
        ).fetchall()
        return [r["value"] for r in rows]

    # ---------- reset one date ----------
    def reset_date(self, date):
        """Remove this date's run/step/value rows (used before resubmitting)."""
        if self.dry:
            return 0
        runs = [r["run"] for r in self.runs_of(date)]
        for run in runs:
            self.conn.execute("DELETE FROM steps WHERE run=?", (run,))
            self.conn.execute("DELETE FROM qvalues WHERE run=?", (run,))
        self.conn.execute("DELETE FROM runs WHERE date=?", (date,))
        self.conn.execute("DELETE FROM batches WHERE date=?", (date,))
        self.conn.commit()
        return len(runs)

    # ---------- summary ----------
    def summary(self, date: str) -> Dict[str, int]:
        rows = self.runs_of(date)
        out = {"total": len(rows), "ok": 0, "failed": 0, "pending": 0}
        for r in rows:
            if r["status"] in ("done", "ok"):
                out["ok"] += 1
            elif r["status"] == "failed":
                out["failed"] += 1
            else:
                out["pending"] += 1
        return out
