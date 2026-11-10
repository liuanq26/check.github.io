"""步骤之间共享的上下文（py3.6 兼容，不用 dataclass）。"""
from pathlib import Path


class Context(object):
    def __init__(self, cfg, store, log, dry=False, force=False):
        self.cfg = cfg
        self.store = store
        self.log = log
        self.dry = dry
        self.force = force

    # ---------- 约定好的路径 ----------
    def date_dir(self, date):
        return self.cfg.date_dir(date)

    def job_script(self, date, run):
        return self.date_dir(date) / ("rec%d.txt" % run)

    def bosslog(self, date, run):
        """xboss 会写成 <jobopt>.bosslog，即 rec<run>.txt.bosslog；兼容两种命名。"""
        folder = self.date_dir(date)
        names = ("rec%d.txt.bosslog" % run, "rec%d.bosslog" % run)
        for name in names:
            candidate = folder / name
            if candidate.is_file():
                return candidate
        return folder / names[0]

    def logpath(self, date):
        return self.cfg.state_dir / "logs" / ("%s.log" % date)
