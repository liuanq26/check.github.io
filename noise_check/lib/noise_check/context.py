"""State shared by the pipeline steps (python 3.6 compatible)."""
from pathlib import Path


class Context(object):
    def __init__(self, cfg, store, log, dry=False, force=False):
        self.cfg = cfg
        self.store = store
        self.log = log
        self.dry = dry
        self.force = force

    # ---------- conventional paths ----------
    def date_dir(self, date):
        return self.cfg.date_dir(date)

    def job_script(self, date, run):
        return self.date_dir(date) / ("rec%d.txt" % run)

    def bosslog(self, date, run):
        """xboss writes <jobopt>.bosslog, i.e. rec<run>.txt.bosslog."""
        folder = self.date_dir(date)
        names = ("rec%d.txt.bosslog" % run, "rec%d.bosslog" % run)
        for name in names:
            candidate = folder / name
            if candidate.is_file():
                return candidate
        return folder / names[0]

    def logpath(self, date):
        return self.cfg.state_dir / "logs" / ("%s.log" % date)
