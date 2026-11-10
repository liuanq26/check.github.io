# oldcal-check

BESIII MDC calibration check. One executable, one result directory, zero third-party
Python packages.

```bash
./oldcal_check.exe                 # interactive panel
./oldcal_check.exe 260918          # auto: submit, or collect when jobs are done
./oldcal_check.exe submit 260918   # phase 1 only
./oldcal_check.exe collect 260918  # phase 2 only
./oldcal_check.exe status 260918
./oldcal_check.exe selfcheck
```

## Submit confirmation

Jobs are never submitted silently. Before the submit phase:

```
plan
  result  /besfs10/users/liuaq/result
  range   260918..260920 (3 days)
  runs    37
          260918   2  new      -> submit   2 job(s)
          260919  12  running  -> wait     12 run(s)
          260920  23  new      -> submit   23 job(s)
  cmd     boss.condor rec<run>.txt

submit 25 job(s)? [y/N]
```

```
previous run did not pass:
  260918 run 94207: RawDataInputSvc FATAL ... | ERROR invalid json:
  260918 run 94208: RawDataInputSvc FATAL ... | ERROR invalid json:
resubmit 260918? (deletes those date folders first) [y/N]
```

- default is **no**: enter alone does nothing
- resubmit is asked separately, because it deletes `result/<date>/` and the products
  of those runs; saying no leaves everything untouched
- after the resubmit question there is one more `submit N job(s)? [y/N]` for the
  remaining new submissions
- the panel's own `enter = submit N job(s)` covers the submit question; the resubmit
  question is still asked
- `--yes` / `-y` skips both
- without a terminal the tool refuses and tells you to add `--yes`

## Two phases

```
submit :  plan -> meta -> genjob -> submit        (returns immediately)
collect:  verify -> collect -> check -> report    (run again after the jobs finish)
```

`./oldcal_check.exe 260918` decides by itself:

| state | meaning | action |
|---|---|---|
| `new` | not submitted yet | submit |
| `running` | job ids still in `hep_q` | wait, run again later |
| `failed` | left the queue, bosslog has no success mark | `rm -rf` the date dir, resubmit |
| `ready` | every bosslog ended ok | collect + check + report |

A successful job must contain `Application Manager Terminated successfully` **and no
`FATAL`** in the bosslog - Gaudi prints the success line even after a failed service
init.

## Layout

```
oldcal_check/                  package, copy it anywhere
  oldcal_check.exe             entry point
  Parameter.txt             physics thresholds
  config/default.yaml
  lib/oldcal_check/            code
  templates/rec.txt.j2
  check/                    checker sources (compiled on first use)
  .state/                   state.db + logs + cover cache (created on first run)

<result>/                   whatever path you pass with --result
  260918/                   rec<run>.txt, .bosslog, .submit.log
  260919/
  plot/                     check_pdf binary + noise_<min>_<max>.pdf
  hist/                     hist<run>.root
  ntuple/                   xtNtuple<run>.root
  reports/                  mdc_<from>_<to>.pdf, anomaly_<date>.txt/.pdf
```

Nothing is written into `result/` except those six items - no hidden state directory.

`--result` is the result root itself: it is created when missing and used as-is when
it already exists. A relative path is resolved against the current working
directory, so the package location does not matter.

`paths.result` in the config has the same meaning; with neither, the default is
`../result` next to the package.

It must be on a shared filesystem (`/besfs*`, `/workfs*`, `/scratchfs*`): worker
nodes write `ntuple/` and `hist/` directly.

State (`state.db`, logs, cover cache) lives in `<package>/.state/`. Point
`paths.state` at an absolute path if you want the history shared between copies.

## Panel

```
oldcal-check
  enter = default, q = quit

result  [/besfs10/users/liuaq/result]
start   [260918]
end     [260918]

plan
  result  /besfs10/users/liuaq/result
  range   260918..260920 (3 days)
  runs    37
          260918   2  new      -> submit
          260919  12  running  -> wait
  steps   submit: plan meta genjob submit | result: collect check report

enter = run, n = edit, q = quit:
```

Last values are kept in `~/.oldcal_check/last.json`.

## Thresholds: `Parameter.txt`

```
m            = 200      # lookback window in runs
n            = 1.0      # sigma multiplier
min_runs     = 5        # skip the check when there is less history
min_rel_band = 0.01     # band never narrower than +/-1% of the mean

# name        m     n     on/off   label
reso          200   1.0   on       resolution (um)
pcms          200   1.0   on       sigmaP (MeV/c)
...
```

For every run and every enabled quantity:

```
mean, sigma = statistics of the previous m runs that have this quantity
band        = mean +/- n * sigma
```

Values are read from `result/plot/fitResults.txt` (already written by `check_pdf.cpp`)
and stored in `state.db`, so the history accumulates across days.

Out of band produces:

* `result/reports/anomaly_<date>.txt` - one line per point
* `result/reports/anomaly_<date>.pdf` - cover page + the plot pages that failed
* warnings on stdout after the plots are written:

```
WARN  260918 run 94207  reso  1.950  out of [1.740, 1.760]  mean 1.750 n=1.0 m=200
```

## Verify / submit rules

* success: bosslog has the success mark and no `FATAL`
* failure: job gone from `hep_q` while the bosslog has no success mark -> immediate
  failure, no 12h wait
* products: both `ntuple/xtNtuple<run>.root` and `hist/hist<run>.root` must exist

## Submit command

```yaml
batch:
  group: ""            # boss.condor rec<run>.txt
  # group: physics     # boss.condor -g physics rec<run>.txt
  submit_cmd: boss.condor
  queue_cmd: "hep_q -u {user}"
```

`boss.condor` here is the hepjob wrapper; its `-g` accepts only `physics` / `ihepai`.

## Environment

Always run through `oldcal_check.exe`. Sourcing the BOSS env puts python2.7 paths in
`PYTHONPATH`, which breaks python3; the launcher strips it for python3 and restores it
for child processes.

Compatible with CentOS 7 + Python 3.6 + SQLite 3.7: no dataclasses, no
`from __future__ import annotations`, no `capture_output`, no SQL UPSERT. PyYAML is
optional (a small built-in parser is used when it is missing).

## Old package

`oldcal_check_bak/` keeps the previous layout. To reuse its products:

```bash
R=/besfs10/users/liuaq/result
mkdir -p $R/{ntuple,hist}
mv /besfs10/users/liuaq/oldcal_check_bak/NTuple/* $R/ntuple/ 2>/dev/null
mv /besfs10/users/liuaq/oldcal_check_bak/hist/*   $R/hist/    2>/dev/null
```
