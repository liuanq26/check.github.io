"""step meta：从 run 库取 BPR/BER/events/起止时间（替代 runstatus.sh + check_ip.sh）。"""

from typing import Dict, List, Optional

from ..context import Context
from ..utils import proc
from ..utils.log import Logger

SQL = (
    "use run; select run_number,numberOfEvents,startTime,endTime,BPR_PRB,BER_PRB "
    "from RunParams where run_number in ({ids});"
)

CHUNK = 500


def _query(host: str, ids: List[int], cfg, log: Logger) -> Optional[Dict[int, dict]]:
    sql = SQL.format(ids=",".join(str(i) for i in ids))
    cmd = [
        "mysql",
        f"--connect-timeout={int(cfg.get('db.timeout', 10))}",
        "-h", host,
        "-u", str(cfg.get("db.user", "guest")),
        f"-p{cfg.get('db.password', '')}",
        "-N", "-B", "-e", sql,
    ]
    res = proc.run(cmd, timeout=int(cfg.get("db.timeout", 10)) + 20)
    if not res.ok:
        log.warn(f"{host}: {res.tail(200)}")
        return None

    rows: Dict[int, dict] = {}
    for line in res.out.splitlines():
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 6:
            continue
        run_no, nevents, estart, eend, bpr, ber = parts[:6]
        try:
            rows[int(run_no)] = {
                "nevents": int(float(nevents)) if nevents not in ("", "NULL") else None,
                "estart": "" if estart == "NULL" else estart,
                "eend": "" if eend == "NULL" else eend,
                "bpr": float(bpr) if bpr not in ("", "NULL") else None,
                "ber": float(ber) if ber not in ("", "NULL") else None,
            }
        except ValueError:
            continue
    return rows


def run(ctx: Context, date: str) -> None:
    rows = ctx.store.runs_of(date)
    todo = [
        r["run"] for r in rows
        if ctx.force or not ctx.store.step_done(r["run"], "meta")
    ]
    if not todo:
        ctx.log.info(f"{date}: meta already done, skip")
        return

    hosts = list(ctx.cfg.get("db.hosts") or [])
    retries = int(ctx.cfg.get("db.retries", 2))

    data: Dict[int, dict] = {}
    for host in hosts:
        for _ in range(retries):
            got = None
            for start in range(0, len(todo), CHUNK):
                chunk = todo[start:start + CHUNK]
                part = _query(host, chunk, ctx.cfg, ctx.log)
                if part is None:
                    got = None
                    break
                got = got or {}
                got.update(part)
            if got is not None:
                data = got
                break
        if data:
            ctx.log.info(f"{date}: meta via {host} {len(data)}/{len(todo)}")
            break

    if not data:
        ctx.log.warn(f"{date}: all db hosts failed, continue without meta")
        for run_no in todo:
            ctx.store.set_step(run_no, "meta", "failed", "db unreachable")
        return

    for run_no in todo:
        info = data.get(run_no)
        if not info:
            ctx.store.set_step(run_no, "meta", "failed", "no RunParams row")
            continue
        ctx.store.upsert_run(run_no, **info)
        ctx.store.set_step(run_no, "meta", "done")
