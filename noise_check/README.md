# noise-check

BESIII MDC 噪声自动检查。一个入口、一个结果目录，不依赖第三方 Python 包。

本程序是仿照旁边的 `oldcal_check` 搭建的，流水线、确认提示、状态库和报告方式保持一致。
`noise_check/` 里原来的 `genJob.sh`、`process_hist.sh`、`run_range.sh`、`runstatus.sh`、
`compile_new.sh`、`temp.txt` 和 `plot_pdf.cpp` 都保留；其中 `plot_pdf.cpp` 仍是检查程序，
自动流程使用的是由 `temp.txt` 改写来的 `templates/rec.txt.j2`。

```bash
./noise_check.exe                 # 交互面板
./noise_check.exe 260918          # 自动：提交；作业完成后再次运行则收集+检查+报告
./noise_check.exe submit 260918   # 只做第一阶段
./noise_check.exe collect 260918  # 只做第二阶段
./noise_check.exe status 260918
./noise_check.exe selfcheck
```

## 提交确认

不会静默提交。提交前会先打印计划：

```
plan
  result  /besfs10/users/liuaq/noise_result
  range   260918..260920 (3 days)
  runs    37
          260918   2  new      -> submit   2 job(s)
          260919  12  running  -> wait     12 run(s)
          260920  23  new      -> submit   23 job(s)
  cmd     boss.condor -g offlinerun rec<run>.txt

submit 25 job(s)? [y/N]
```

失败日期会单独询问一次（会先删除该日期的目录和产物）：

```
previous run did not pass:
  260918 run 94207: RawDataInputSvc FATAL ... | ERROR ...
  260918 run 94208: RawDataInputSvc FATAL ... | ERROR ...
resubmit 260918? (deletes those date folders first) [y/N]
```

- 默认是 **no**，直接回车不提交
- 重新提交单独询问，因为会删除 `result/<date>/` 和这些 run 的 `hist/`、`nt/` 产物
- 之后还会再问一次 `submit N job(s)? [y/N]`
- `--yes` / `-y` 跳过确认；没有终端时会拒绝提交并提示加 `--yes`
- 面板里的 `enter = submit N job(s)` 覆盖提交问题，重新提交问题仍会单独问

## 两个阶段

```
submit :  plan -> meta -> genjob -> submit        （提交后立即返回）
collect:  verify -> collect -> check -> report    （作业结束后再运行一次）
```

`./noise_check.exe 260918` 会根据状态自动决定：

| 状态 | 含义 | 动作 |
|---|---|---|
| `new` | 还没提交 | submit |
| `running` | 作业还在 `hep_q` 里 | wait，稍后再运行 |
| `failed` | 已离开队列，bosslog 没有成功标记 | 删除日期目录后重提 |
| `ready` | 所有 bosslog 都正常结束 | collect + check + report |

成功作业必须同时满足：bosslog 里有
`Application Manager Terminated successfully`，并且尾部没有 `FATAL`。
Gaudi 在服务初始化失败时也可能打印成功行，所以必须排除 `FATAL`。

## 目录结构

```
noise_check/                  软件包，可整体复制到别处
  noise_check.exe             唯一入口
  Parameter.txt              物理阈值
  config/default.yaml
  lib/noise_check/            代码
  templates/rec.txt.j2        自动生成的作业模板（由 temp.txt 改写）
  plot_pdf.cpp                检查程序源码（首次检查时自动编译）
  genJob.sh 等                原来的脚本，保留作参考，自动流程不调用
  .state/                     state.db + 日志 + 封面缓存（首次运行时创建）

<result>/                      --result 指定的结果根目录
  260918/                     rec<run>.txt、.bosslog、.submit.log
  260919/
  plot/                       plot_pdf 二进制、noise_<min>_<max>.pdf、
                              graph.root、noiseResults.txt
  hist/                       hist<run>.root（必需）
  ntuple/                     nt<run>.root（可选）
  reports/                    noise_<from>_<to>.pdf、anomaly_<date>.txt/.pdf
```

结果目录默认是软件包同级的 `../noise_result`，即
`/besfs10/users/liuaq/noise_result`。这样不会和 `oldcal_check` 的 `result/hist` 混在一起
（两者都叫 `hist<run>.root`）。

`--result` 给的是结果根目录本身；不存在会自动创建，已存在则直接使用。相对路径按当前
工作目录解析。`paths.result` 作用相同；两者都没给时才用默认的 `../noise_result`。

结果目录必须在共享文件系统上（`/besfs*`、`/workfs*`、`/scratchfs*`），因为计算节点会直接
写 `hist/` 和 `ntuple/`。状态库、日志和封面缓存放在 `<package>/.state/`，可以用
`paths.state` 改成绝对路径以便多份程序共享历史。

## 面板

```
noise-check
  enter = default, q = quit

result  [/besfs10/users/liuaq/noise_result]
start   [260918]
end     [260918]

plan
  result  /besfs10/users/liuaq/noise_result
  range   260918..260920 (3 days)
  runs    37
          260918   2  new      -> submit
          260919  12  running  -> wait
  steps   submit: plan meta genjob submit | result: collect check report

enter = run, n = edit, q = quit:
```

上次的值保存在 `~/.noise_check/last.json`。

## 阈值：Parameter.txt

```
m            = 200      # 回看窗口（run 数）
n            = 1.0      # sigma 倍数
min_runs     = 5        # 历史不足时跳过检查
min_rel_band = 0.01     # band 至少为均值的 +/-1%

# name        m     n     on/off   label
occStp        200   1.0   on       step noise occupancy (T&Q match)
occOut        200   1.0   on       outer noise occupancy (T&Q match)
occStp_T      200   1.0   on       step noise occupancy (T channel)
occOut_T      200   1.0   on       outer noise occupancy (T channel)
nhitStp       200   1.0   off      raw mean nhit (step)
...
```

对每个 run、每个打开的量：

```
mean, sigma = 前 m 个有该量的 run 的统计
band        = mean +/- n * sigma
```

数值来自 `result/plot/noiseResults.txt`，由 `plot_pdf.cpp` 在生成 PDF 时一起写出，并存进
`state.db`，因此历史可以跨日期累积。

`noiseResults.txt` 每行一个 run，格式为：

```
94207 OK 1000 nevents=1000 nhitStp=26 ... occStp=0.00155 ...
```

超出 band 会产生：

* `result/reports/anomaly_<date>.txt`：每个点一行
* `result/reports/anomaly_<date>.pdf`：说明页 + 出问题的 PDF 页
  （`occStp`/`occOut` 取第 1 页，`occStp_T`/`occOut_T` 取第 2 页）
* 终端在 PDF 写完后输出警告：

```
WARN  260918 run 94207  occStp  0.005435  out of [0.002041, 0.004946]  mean 0.003494 n=1.0 m=200
```

`check` 的步骤名是 `noiseRun`，对应 `config/default.yaml` 里的 `check.profiles.noiseRun`。
PDF 页面固定为两页：第 1 页是 T&Q match 后的 step/outer 噪声占有率，第 2 页是 T 通道的
step/outer 噪声占有率。

## 校验 / 提交规则

* 成功：bosslog 有成功标记且尾部没有 `FATAL`
* 失败：作业已不在 `hep_q`，bosslog 存在但没有成功标记 -> 立即判失败，不等 12 小时
* 产物：`hist/hist<run>.root` 必须存在；`nt/nt<run>.root` 可选
  （`collect.require_ntuple: true` 可以改成必需）

作业模板直接把 `MdcNoiseAlg.histfile` 和 `NTupleSvc.Output` 写成绝对路径，正常情况下
`collect` 只做核对；如果产物落在日期目录里，会自动搬到 `hist/` 或 `ntuple/`。

## 提交命令

```yaml
batch:
  group: offlinerun        # boss.condor -g offlinerun rec<run>.txt
  # group: ""              # boss.condor rec<run>.txt
  submit_cmd: boss.condor
  queue_cmd: "hep_q -u {user}"
```

原来的 `genJob.sh` 用的是 `boss.condor -g offlinerun`，这里保持一致。如果你的
`boss.condor` 包装不接受 `offlinerun`，加 `--group ""` 或把 `group` 改成空。

## 环境

始终通过 `noise_check.exe` 运行。BOSS 环境会把 `PYTHONPATH` 指向 python2.7 的库，直接跑
python3 可能报 `_posixsubprocess` 之类的错误；入口脚本会给 python3 换成自己的 `lib`，
并把原值通过 `NOISE_ORIG_PYTHONPATH` 传给子进程（`boss.condor`、ROOT 等仍然拿到完整
BOSS 环境）。

兼容 CentOS 7 + Python 3.6 + SQLite 3.7：没有 dataclass，没有
`from __future__ import annotations`，没有 `capture_output`，没有 SQL UPSERT。
PyYAML 可选；没有时用内置的小 YAML 解析器。`reportlab` 可选；没有时说明页用内置的
最小 PDF 生成器（英文 ASCII）。

## 与 oldcal_check 的对应关系

| oldcal_check | noise_check |
|---|---|
| `oldcal_check.exe` | `noise_check.exe` |
| `rec.txt.j2`（MDC 刻度） | `templates/rec.txt.j2`（MdcNoiseAlg） |
| `check/check_pdf.cpp` | `plot_pdf.cpp` |
| `fitResults.txt` | `noiseResults.txt` |
| 需要 `xtNtuple` + `hist` | 只需要 `hist`，`nt` 可选 |
| `boss.condor rec<run>.txt` | `boss.condor -g offlinerun rec<run>.txt` |
| 结果默认 `../result` | 结果默认 `../noise_result` |

原来的 `compile_new.sh` 仍可单独使用（它编译 `a.out`）；自动流程不用它，而是按
`config/default.yaml` 里的 `check.*` 参数编译成 `result/plot/plot_pdf`。

## 快速开始

```bash
cd /besfs10/users/liuaq/noise_check
# 按需编辑 Parameter.txt 里的 m / n / min_runs / min_rel_band
./noise_check.exe --result /besfs10/users/liuaq/noise_result 260918
```

第一次会先编译 `plot_pdf.cpp`。提交后等作业结束，再运行一次同一条命令即可收集、检查并
生成 `reports/noise_<from>_<to>.pdf`。
