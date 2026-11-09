#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dino_backend.py — ASA 生物数据独立后端（dino-import.html 脱离 HA 的 Phase 3 核心）
部署：Win Server 2019 物理服务器（192.168.199.3），纯 Python 标准库，无需 pip install。
运行：python dino_backend.py  （或注册为 Windows 计划任务/服务）

链路：
  浏览器 → dino.whiterober.ccwu.cc (CF Pages 页面)
         → data.whiterober.ccwu.cc (CNAME → work.whiterober.cn → DDNS+端口转发 → 本机)
         → 本服务（RCON 127.0.0.1 / 本机 DinoData 直读）

接口（替代原 HA script/webhook/sensor）：
  GET  /healthz                        健康检查
  GET  /api/themes                     服务器主题（原 sensor.asa_server_themes）
  GET  /api/status/:server             单服状态（refresh/wild/player_pos/track）
  POST /api/refresh_tamed?server=X     刷新 tamed（原 script.refresh_tamed + webhook）
  POST /api/search_wild?server=X&species=Y  搜野生（原 script.search_wild_dinos）
  POST /api/track_dino                 RCON TrackDino（原 script.track_dino）
  POST /api/stop_track_dino            RCON StopTrackDino（原 script.stop_track_dino）
  POST /api/player_pos                 RCON PlayerPos（原 script.player_pos）
  POST /api/ingame_time?server=X       游戏内时间（原生 RCON GetInGameTime；60s TTL + 同键并发合并）
  POST /api/worldprobe_biometemps?server=X&skip=&count=&brief=&filter=  区域温度（ABiomeZoneVolume 绝对温度 ℃；TTL 60s + 同键合并）
  POST /api/wind_status?server=X&fresh=     风力发电机耐久（风机清单+逐台 5 字段；TTL 60s + 同键合并；v4670）
  POST /api/world_clock?server=X&fresh=     存档世界时钟逆推（RCON worldTime 锚点 − 存档 mtime；TTL 3 分钟；v5714）
  GET  /asa-data/*                     静态资源（汉化/图标/颜色 8 个 JSON）
  GET  /dino-data/*                    数据 JSON（<缩写>_cryo/tamed/wild_*.json 直读）

配置：环境变量（无则默认），或直接改下方 CONFIG 常量。
  DINO_DATA     DinoData 目录（默认 D:\\ARK Server\\DinoData）
  ASA_DATA      静态资源目录（默认同 DINO_DATA 下 asa-data，可改）
  RCON_HOST     默认 127.0.0.1（本机游戏服）
  RCON_PASSWORD RCON 密码（默认 1219wu1219）
  PORT          监听端口（默认 8080）
  ALLOW_ORIGIN  CORS 允许来源（默认 https://dino.whiterober.ccwu.cc）
"""
import json
import os
import re
import re as _re
import shutil            # v6228：更新分发用 copy2 / disk_usage
import stat as _stat     # v6255：分发前清只读（S_IWRITE）
import socket
import struct
import subprocess
import threading
import time
import calendar as _cal   # v6176：日志时间戳为 UTC，需 timegm
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# ================= 应用日志（2026-11-05 方案A：只增不改） =================
# 原则：
#   1) 旁路记录：不替换任何现有 print、不改任何 except 类型、不改任何返回值/控制流
#   2) 初始化全程 try/except —— 日志不可用绝不能阻塞服务启动（降级 NullHandler）
#   3) 独立文件 dino_backend.app.log，不碰 watchdog 的 dino_backend.log（stdout 重定向）
#   4) 轮转 5MB x 3，UTF-8（Windows 默认 GBK 会把中文写日志写炸）
import logging as _logging


def _log_setup():
    try:
        from logging.handlers import RotatingFileHandler
        lg = _logging.getLogger('dino')
        if lg.handlers:
            return lg
        lg.setLevel(_logging.INFO)
        lg.propagate = False
        _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dino_backend.app.log')
        h = RotatingFileHandler(_p, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8', delay=True)
        h.setFormatter(_logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(threadName)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        lg.addHandler(h)
        return lg
    except Exception:
        try:
            lg = _logging.getLogger('dino')
            lg.addHandler(_logging.NullHandler())
            return lg
        except Exception:
            return None


_LOG = _log_setup()


def _sexc(tag, msg=''):
    """记录当前异常（含栈）；自身绝不抛错，也不改变控制流。"""
    try:
        if _LOG is not None:
            _LOG.exception('[%s] %s' % (tag, msg))
    except Exception:
        pass


def _sinfo(msg):
    """普通信息日志；失败静默。"""
    try:
        if _LOG is not None:
            _LOG.info(msg)
    except Exception:
        pass

# ================= 配置 =================
# P0（2026-11-04）：方舟安全回档 —— 只读能力模块（list / verify / audit）
#   独立模块，加载失败不拖垮主服务（_arkbk=None 时相关路由返回 500）
try:
    import ark_backup as _arkbk
except Exception as _e_arkbk:      # noqa: F841
    _arkbk = None

# ============ P3（2026-11-04）：安全回档引擎（job 编排 / 状态探测）============
# 依据：plans\搞事系统_方舟安全回档_方案.md §5.5.3 / §6.3-§6.7 / §6.10
# 设计：真正的文件级动作在 ark_backup（swap_ark / create_backup / precheck），
#       本层只负责「调度 + 状态机 + 鉴权 + 串行互斥」。
_ARKBK_JOBS = {}                 # jobId -> dict
_ARKBK_JOB_LOCK = threading.Lock()
_ARKBK_BUSY = {}                 # server -> jobId（同服互斥，防并发回档）
# v6058（按推荐补全）：**服务器级互斥** —— 回档期间挡住外部对该服的 start/kill/restart。
#   原 `_srvctl_acquire(server, action)` 是 **(服务器, 动作)** 粒度 ⇒ `('Cen','start')` 与
#   `('Cen','kill')` 是两把不同的锁、互不排斥 ⇒ 回档 stopped→restoring 的无锁窗口里，
#   别人点启动就会把进程拉起来读半截档。这里用独立字典做「整台服务器」级占用。
_ARKBK_HOLD = {}                 # server -> jobId（回档进行中）
_ARKBK_JOB_KEEP = 1800           # 已结束 job 保留 30 分钟，之后 GC 掉
# v6058：阶段权重（原来的前端 TOTAL=8 是**等权**估算，restoring 花 40s 与 saveworld 花 2s
#   各算 1/8，百分比是假的）。改为后端按真实耗时量级下发 pct。
_ARKBK_STEP_PCT = {'saveworld': 6, 'precheck': 12, 'snapshot': 20, 'stopping': 30,
                   'stopped': 38, 'restoring': 60, 'starting': 72, 'verifying': 92}
_ARKBK_JOB_TTL = 7200            # 2 小时
_ARKBK_POOL = __import__('concurrent.futures', fromlist=['ThreadPoolExecutor']).ThreadPoolExecutor(max_workers=1)
# v6058：原顺序把 snapshot 排在 stopping **之后**，与实际实现（备份 → 停服 → 换档）相反，
#   该常量全文件无使用点，纯误导（曾让进度条按错误顺序实现）⇒ 按真实执行顺序修正。
_ARKBK_PHASES = ('queued', 'saveworld', 'precheck', 'snapshot', 'stopping', 'stopped',
                 'restoring', 'starting', 'verifying', 'done', 'failed')

# ===== v6127（M2）：回档/演练进度并入统一任务总线 =====
_ARKBK_GROUPS = (
    ('save', u'存档'),
    ('check', u'载入校验'),
    ('swap', u'停服换档'),
    ('start', u'起服'),
    ('verify', u'校验'),
)
_ARKBK_GROUP = {'queued': 'save', 'saveworld': 'save', 'precheck': 'check',
                'snapshot': 'swap', 'stopping': 'swap', 'stopped': 'swap',
                'restoring': 'swap', 'starting': 'start', 'verifying': 'verify'}


def _arkbk_task_push(job):
    """v6127：把回档 job 镜像到统一任务总线（action=rollback / rollback_dry）。

    回档进度不再由回档浮窗自绘，而是与其他动作共用同一份列表。
    """
    try:
        ph = str(job.get('phase') or '')
        cur = _ARKBK_GROUP.get(ph) or ''
        states = {}
        for s in (job.get('steps') or []):
            g = _ARKBK_GROUP.get(str(s.get('phase') or ''))
            if not g:
                continue
            states[g] = 'ok' if s.get('ok') else 'fail'
        steps = []
        for k, lab in _ARKBK_GROUPS:
            st = states.get(k, 'wait')
            if k == cur and st == 'wait':
                st = 'run'
            steps.append({'key': k, 'label': lab, 'state': st})
        okv = job.get('ok')
        phase = 'ok' if okv is True else ('fail' if okv is False else 'run')
        # v6130：任务已结束（尤其演练提前停）⇒ 未执行的步骤标「跳过」，
        #   否则任务已「完成 100%」而尾部步骤永远停在「等待」，自相矛盾。
        if phase in ('ok', 'fail'):
            for _s in steps:
                if _s.get('state') in ('wait', 'run'):
                    _s['state'] = 'skip'
        msg = ''
        for s in (job.get('steps') or []):
            if s.get('msg'):
                msg = str(s.get('msg'))
        # v6276（用户口径「原本启动条要显示的信息，完整整合显示在融合任务条内」）：
        #   回档的「⑥启动 → ⑦等上线」段原先只显示「已下发启动队列」并一停 600 秒，
        #   而启动队列同时另生成一条独立 srv|start 条（同台服两条，且动态在另一条上）。
        #   现由 _utask_boot_mirror 把启动进度写进 job 的 boot* 字段，这里注入：
        #     · msg 用启动队列原生消息（如「加载世界存档…（45s）」）
        #     · pct 按 starting(72) → verifying(92) 段用启动原生进度**映射满该段**
        #   独立启动条已被抑制 ⇒ 同台服只保留回档这一条。
        _pct_out = int(job.get('pct') or 0)
        try:
            if (ph in ('starting', 'verifying') and not bool(job.get('dryRun'))
                    and job.get('bootMsg') is not None):
                _bm = str(job.get('bootMsg') or '')
                if _bm:
                    msg = _bm
                _bp = max(0, min(100, int(job.get('bootPct') or 0)))
                _pct_out = 72 + int(round(_bp * 0.20))
        except Exception:
            _pct_out = int(job.get('pct') or 0)
        _utask_put('arkbk|%s' % str(job.get('server') or ''), job.get('server'),
                   'rollback_dry' if job.get('dryRun') else 'rollback',
                   job.get('operator') or '',
                   label=(u'回档演练' if job.get('dryRun') else u'安全回档'),
                   msg=msg, pct=_pct_out, phase=phase,
                   steps=steps, err=(job.get('error') or ''),
                   meta={'jobId': job.get('id')})
    except Exception:
        _sexc('arkbk_task_push')


def _arkbk_rcon_alive(server, timeout=3):
    """RCON 端口 TCP 可达 ⇒ 视为在跑（方案 §6.10：不走 srvctl/status，那里要 10 分钟）"""
    port = (SERVERS or {}).get(server)
    if not port:
        return {'rconPort': None, 'rconReachable': False, 'running': False}
    try:
        sk = socket.create_connection((RCON_HOST, port), timeout=timeout)
        sk.close()
        return {'rconPort': port, 'rconReachable': True, 'running': True}
    except Exception:
        return {'rconPort': port, 'rconReachable': False, 'running': False}


def _arkbk_new_job(server, point_id, operator, dry_run, action='rollback'):
    jid = 'ark%s' % (int(time.time() * 1000) % 10 ** 12)
    job = {
        'id': jid, 'server': server, 'pointId': point_id, 'operator': operator,
        'action': action, 'dryRun': bool(dry_run),
        'phase': 'queued', 'ok': None, 'error': '',
        't0': time.time(), 't0str': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'steps': [], 'precheck': None, 'pct': 0, 'tEnd': 0,
    }
    with _ARKBK_JOB_LOCK:
        # 清理过期 job
        dead = [k for k, v in _ARKBK_JOBS.items() if time.time() - v['t0'] > _ARKBK_JOB_TTL]
        for k in dead:
            _ARKBK_JOBS.pop(k, None)
        _ARKBK_JOBS[jid] = job
        _ARKBK_BUSY[server] = jid
    # v6135：回档申请 hard 锁；若同服有 soft 锁（自动任务）则回档优先，直接中止它
    try:
        _lk = _srv_lock_get(server)
        if _lk.get('kind') in SRV_LOCK_SOFT:
            _restart_abort(server, u'回档优先')
        _srv_lock_set(server, 'rollback', 'arkbk|%s' % server, u'安全回档',
                      operator, ttl=7200)
    except Exception:
        _sexc('arkbk_lock')
    _arkbk_task_push(job)   # v6127：任务一建立就出现在共享列表
    return job


def _arkbk_step(job, phase, ok, msg='', extra=None):
    """记一步（线程安全地原地更新 job）"""
    with _ARKBK_JOB_LOCK:
        job['phase'] = phase
        # v6058：按阶段权重推进百分比（后端权威，前端不再自己数步骤）
        try:
            job['pct'] = int(_ARKBK_STEP_PCT.get(phase, job.get('pct') or 0))
        except Exception:
            pass
        job['steps'].append({
            'phase': phase, 'ok': bool(ok), 'msg': (msg or '')[:300],
            'at': int((time.time() - job['t0']) * 1000),
        })
        if extra:
            job.update(extra)
    try:
        if _arkbk:
            _arkbk._log('job %s [%s] %s %s' % (job['id'], phase, 'OK' if ok else 'FAIL', (msg or '')[:200]))
    except Exception:
        pass
    _arkbk_task_push(job)   # v6127：每一步同步到统一任务总线


def _arkbk_finish(job, ok, err=''):
    with _ARKBK_JOB_LOCK:
        job['ok'] = bool(ok)
        job['phase'] = 'done' if ok else 'failed'
        job['error'] = (err or '')[:500]
        job['elapsedMs'] = int((time.time() - job['t0']) * 1000)
        # v6058：完成置 100%、记结束时刻（GC 与 lastjob 的保留期判据）
        job['pct'] = 100 if ok else int(job.get('pct') or 0)
        job['tEnd'] = time.time()
        if _ARKBK_BUSY.get(job['server']) == job['id']:
            _ARKBK_BUSY.pop(job['server'], None)
        # v6058：解除服务器级互斥 —— 所有出口都会走 finish，放这里最稳
        if _ARKBK_HOLD.get(job['server']) == job['id']:
            _ARKBK_HOLD.pop(job['server'], None)
    _arkbk_task_push(job)   # v6127：结束态（含失败原因）同步到任务总线
    _srv_lock_clear(job.get('server'), 'arkbk|%s' % job.get('server'))   # v6135：释放 hard 锁


def _arkbk_do_rollback(job, argv, cfg):
    """执行体（在线程池里跑）。argv = {server, pointId, confirm, ackRisk, dryRun, skipSaveworld}"""
    server = argv['server']
    point = argv['pointId']
    dry = bool(argv.get('dryRun'))
    try:
        # ① 状态 + saveworld（§5.5.3 ②，§15 C2：必须在 precheck 之前）
        st = _arkbk_rcon_alive(server)
        job['running'] = st.get('running')
        if st.get('running') and not argv.get('skipSaveworld'):
            # v6120：保存步骤补全为「RCON 已保存 → .ark 写盘 → DinoData 全部导出文件落盘且稳定」
            #   原实现只等 .ark mtime 20s；插件在存档事件后**异步**导出 cryo/tamed/item/players/eggs，
            #   第 ② 步立刻 max_age=0 重解析会读到上一轮或半截文件（闸门判错人），第 ④ 步 kill 还会截断导出。
            _t_save = time.time()
            r = _srvctl_one(server, 'saveworld', None, cfg)
            _dw = (r.get('data') or {}) if r.get('ok') else {}
            if r.get('ok') and not _dw.get('ok'):
                _dw = _dinodata_wait_stable(server, since_ts=_t_save, budget=120)
            job['dataWait'] = _dw
            _ark_ok = _arkbk_wait_ark_mtime(server, budget=30) if r.get('ok') else False
            ok_save = bool(r.get('ok')) and bool(_dw.get('ok'))
            if ok_save:
                _msg = '已保存世界 %sms · .ark %s · DinoData 稳定 %.0fs（%d 文件）' % (
                    r.get('ms'), '已写盘' if _ark_ok else '未检出变化',
                    float(_dw.get('waited') or 0), int(_dw.get('files') or 0))
            elif r.get('ok'):
                _msg = 'saveworld 已返回，但 DinoData 未落盘稳定（%s）' % (_dw.get('reason') or 'unknown')
            else:
                _msg = str(r.get('message'))
            _arkbk_step(job, 'saveworld', ok_save, _msg, extra={'dataWait': _dw})
            if not r.get('ok'):
                _arkbk_finish(job, False, 'saveworld 失败：' + str(r.get('message')))
                return
            if not _dw.get('ok'):
                _arkbk_finish(job, False, 'DinoData 未落盘稳定（%s），已中止：未停服、未换档'
                                             % (_dw.get('reason') or 'unknown'))
                return
        else:
            _arkbk_step(job, 'saveworld', True,
                        '服已停，跳过 saveworld' if not st.get('running') else '调用方要求跳过 saveworld')

        # ② 闸门：saveworld 之后**强制 exe 重解析当前档**（方案 §6.6 的 reparse 阶段）
        #    ⚠ 不这样做会算错人：`_cryo.json.gz` 若刚导出（ageSec 仍 < 30 分钟）会被判
        #      「新鲜」而直接复用，可它是 saveworld **之前**的名单 ⇒ 期间进出的角色
        #      全部漏判（🟡 该拦的没拦、🔴 该报的没报）。max_age=0 强制走重解析分支。
        _cur_p3 = _arkbk.current_players(server, max_age=0)
        if not _cur_p3.get('ok'):
            _arkbk_finish(job, False, '重解析当前档失败：' + str(_cur_p3.get('error')))
            return
        job['reparsed'] = bool(_cur_p3.get('reparsed'))
        pc = _arkbk.precheck(server, point, current=_cur_p3)
        _arkbk_step(job, 'precheck', pc.get('ok'), pc.get('notice') or pc.get('error') or '',
                    extra={'precheck': pc})
        if not pc.get('ok'):
            _arkbk_finish(job, False, '闸门执行失败：' + str(pc.get('error')))
            return

        verdict = pc.get('verdict')
        if verdict != 'clear':
            if not argv.get('ackRisk'):
                _arkbk_finish(job, False, '存在风险角色（%s），需 ackRisk:true' % verdict)
                return
            cn_need = _arkbk_server_cn(server)
            if (argv.get('confirm') or '') != cn_need:
                _arkbk_finish(job, False, '存在风险角色，需输入服务器中文名「%s」确认' % cn_need)
                return

        if dry:
            _arkbk_step(job, 'stopping', True, '[dry-run] 不执行停服/换档/启动')
            _arkbk_finish(job, True, '')
            return

        # v6058：从这里开始会真正动服务器 ⇒ 置**服务器级互斥**（挡住外部 start/kill/restart）。
        #   解除在 _arkbk_finish（所有出口都经过它）。
        with _ARKBK_JOB_LOCK:
            _ARKBK_HOLD[server] = job['id']

        # ③ 备份当前档（§9 每服恒 1 份）
        # ⚠ 撤销回档（action=restore）时**不能**备份 —— 否则会把 pre_restore.ark 覆盖成
        #    「当前档」，接着 swap 的又是刚备份的当前档 ⇒ 原地打转，撤销失效。
        #    撤销的兵底由 swap_ark 内的 `<当前档>.pre_swap.ark` 保留。
        if argv.get('skipBackup'):
            _arkbk_step(job, 'snapshot', True, '撤销回档：跳过新建备份（现有 pre_restore.ark 即为还原源）')
        else:
            bk = _arkbk.create_backup(server, operator=job.get('operator', ''), job_id=job['id'])
            _arkbk_step(job, 'snapshot', bk.get('ok'),
                        ('已备份 %.1f MB' % bk.get('mb', 0)) if bk.get('ok') else str(bk.get('error')))
            if not bk.get('ok'):
                _arkbk_finish(job, False, '备份失败，已中止（未降级）')
                return

        # ④ 停服
        if st.get('running'):
            # v6120：kill 前复核 DinoData（防「边导出边强杀」留半截文件）
            #   硬失败只针对 .tmp/.part/.lock/.writing 这类明确「写入中」标记；
            #   普通 mtime 变动（如恰好碰上自动存档）只记警告，避免把回档卡死。
            _dw2 = _dinodata_wait_stable(server, since_ts=time.time() - 3, budget=20, quiet=2.0,
                                         require_update=False)
            _busy_files = _dw2.get('busy') or []
            if _busy_files:
                _arkbk_step(job, 'stopping', False,
                            'DinoData 存在写入中标记文件：%s' % ','.join(_busy_files[:3]))
                _arkbk_finish(job, False, '停服前 DinoData 仍标记为写入中，已中止（未强杀）')
                return
            if not _dw2.get('ok'):
                _arkbk_step(job, 'stopping', True,
                            '停服前复核：DinoData 仍有变动（%s），按计划继续' % (_dw2.get('reason') or ''))
            r = _srvctl_one(server, 'kill', None, cfg)
            _arkbk_step(job, 'stopping', r.get('ok'),
                        ('已强杀 %sms' % r.get('ms')) if r.get('ok') else str(r.get('message')))
            if not r.get('ok'):
                _arkbk_finish(job, False, '停服失败：' + str(r.get('message')))
                return
            gone = _arkbk_wait_port_closed(server, budget=90)
            _arkbk_step(job, 'stopped', gone, '端口已关闭' if gone else '等待端口关闭超时')
            if not gone:
                _arkbk_finish(job, False, '进程可能仍在运行，未换档')
                return
        else:
            _arkbk_step(job, 'stopping', True, '服已停，跳过停服')
            _arkbk_step(job, 'stopped', True, '已在停止状态')

        # ⑤ 换档
        rp = _arkbk.resolve_point(server, point)
        if not rp.get('ok'):
            _arkbk_finish(job, False, '目标档解析失败：' + str(rp.get('error')))
            return
        sw = _arkbk.swap_ark(server, rp['abs'])
        _arkbk_step(job, 'restoring', sw.get('ok'),
                    ('已换档 %.1f MB' % sw.get('sourceMB', 0)) if sw.get('ok') else str(sw.get('error')),
                    extra={'swap': sw})
        if not sw.get('ok'):
            _arkbk_finish(job, False, '换档失败：' + str(sw.get('error')))
            return

        # v6059（用户口径「要记录已执行撤销的次数，当前备份档」）：
        #   只有撤销（action=restore）才计数；换档成功即已生效 ——
        #   即使随后启动失败，这次撤销也算「执行过」。
        if job.get('action') == 'restore':
            try:
                _bu = _arkbk.bump_undo(server)
                if _bu.get('ok'):
                    job['undoCount'] = _bu.get('undoCount')
            except Exception:
                pass

        # ⑥ 启动
        try:
            _srvctl_startq_new(job.get('operator') or 'arkbackup', [server])
            _arkbk_step(job, 'starting', True, '已下发启动队列')
        except Exception as e:
            _arkbk_step(job, 'starting', False, '%s: %s' % (type(e).__name__, e))
            _arkbk_finish(job, False, '启动下发失败：' + str(e))
            return

        # ⑦ 等上线（v6057：同时盯启动队列；失败即判失败）
        _t_up = time.time()
        up, _why = _arkbk_wait_online(server, budget=600)
        _arkbk_step(job, 'verifying', up,
                    ('RCON 已可连（%ds）' % int(time.time() - _t_up)) if up else _why)
        if up:
            _arkbk_finish(job, True, '')
        else:
            # v6057：原来这里是 `_arkbk_finish(job, True, '已启动，但…')` ——
            # 把「启动失败」当成「完成（带提示）」上报，前端进度条因此显示"完成"而非红条，
            # 这是用户「一直卡着没人发现」的直接原因之一。
            _arkbk_finish(job, False, _why)
    except Exception as e:
        _arkbk_finish(job, False, '%s: %s' % (type(e).__name__, e))


def _arkbk_wait_ark_mtime(server, budget=20):
    """saveworld 后等当前档 mtime 变化（最多 budget 秒）"""
    try:
        md = _arkbk.detect_map_dir(server)[0]
        if not md:
            return False
        nm = _arkbk._active_name(server, md)
        if not nm:
            return False
        p = os.path.join(_arkbk.ARK_ROOT, server, 'ShooterGame', 'Saved', 'SavedArks', md, nm)
        base = os.path.getmtime(p)
        t0 = time.time()
        while time.time() - t0 < budget:
            time.sleep(1)
            try:
                if os.path.getmtime(p) != base:
                    return True
            except Exception:
                pass
    except Exception:
        pass
    return False


# ===== v6120：DinoData「保存后落盘且稳定」统一屏障 =====
#   背景：回档 / 保存世界 / 刷新数据 都只是发一条 RCON SaveWorld 就返回；插件是在**存档事件之后异步**
#   导出 <服>_cryo.json.gz / _tamed.json / _item.json.gz / _players.json.gz / _eggs.json.gz 等文件。
#   不等它们写完就继续（重解析 / kill）会读到上一轮或半截文件 ⇒ 闸门判错人、前端读档报错。
_DD_SAVE_FAMILIES = ('_cryo.json.gz', '_cryo.json', '_tamed.json', '_item.json.gz', '_item.json',
                     '_players.json.gz', '_eggs.json.gz')
_DD_BUSY_SUFFIX = ('.tmp', '.part', '.lock', '.writing')


def _dinodata_files(server):
    """枚举该服在 DinoData 下的全部相关文件 -> {文件名: {size, mtime, busy}}"""
    out = {}
    try:
        names = os.listdir(DINO_DATA)
    except Exception:
        return out
    prefs = (server + '_', server + '.')
    probe_pfx = 'egg_probe_status_' + server
    for fn in names:
        if not (fn.startswith(prefs) or fn.startswith(probe_pfx)):
            continue
        busy = fn.lower().endswith(_DD_BUSY_SUFFIX)
        try:
            stt = os.stat(os.path.join(DINO_DATA, fn))
            out[fn] = {'size': stt.st_size, 'mtime': int(stt.st_mtime), 'busy': busy}
        except Exception:
            continue
    return out


def _dinodata_read_ok(server):
    """v6190（用户口径）：校验该服在 DinoData 下**全部产物**的完整性 -> 损坏列表。

    原实现只抽检 4 个 gz + 3 个 json 固定后缀 —— 实测插件每轮还写
    _notes.json.gz / _alliances.json / _cryo.json.db / _cryo.json.snap，全都没验。
      · .gz        -> gzip 全量解压验尾 CRC（>30MB 只读头，避免阻塞）
      · .json      -> 开头必须是 { 或 [
      · .db        -> SQLite 文件头 'SQLite format 3'
      · 其他(.snap/.cache等) -> 至少 size > 0（上面已判）
    前缀过滤保持不变 ⇒ **仅涵盖当前目标服**，不跨服。"""
    bad = []
    try:
        import gzip
    except Exception:
        gzip = None
    try:
        names = os.listdir(DINO_DATA)
    except Exception:
        return bad
    prefix = (server + '_', server + '.')
    for fn in names:
        if not fn.startswith(prefix):
            continue
        p = os.path.join(DINO_DATA, fn)
        if not os.path.isfile(p):
            continue
        try:
            sz = os.path.getsize(p)
        except Exception:
            continue
        low = fn.lower()
        if sz <= 0:
            bad.append(fn + ' size=0')
            continue
        if low.endswith(_DD_BUSY_SUFFIX):
            continue
        if low.endswith('.gz'):
            if gzip is None:
                continue
            try:
                with gzip.open(p, 'rb') as f:
                    if sz <= 30 * 1024 * 1024:
                        f.read()
                    else:
                        f.read(2)
            except Exception as e:
                bad.append('%s %s' % (fn, type(e).__name__))
        elif low.endswith('.json'):
            try:
                with open(p, 'rb') as f:
                    head = f.read(64).lstrip()
                if not head or head[:1] not in (b'{', b'['):
                    bad.append(fn + ' 非 JSON 开头')
            except Exception as e:
                bad.append('%s %s' % (fn, type(e).__name__))
        elif low.endswith('.db'):
            try:
                with open(p, 'rb') as f:
                    head = f.read(16)
                if not head.startswith(b'SQLite format 3'):
                    bad.append(fn + ' 非 SQLite 头')
            except Exception as e:
                bad.append('%s %s' % (fn, type(e).__name__))
    return bad


def _dinodata_wait_stable(server, since_ts=None, budget=90, quiet=3.0, poll=0.5, require_update=True,
                          progress=None):
    """等 DinoData 中该服存档族文件「落盘且稳定」。

    判据（三条全中才算 ok）：
      ① 至少一个存档族文件 mtime ≥ since_ts-2  ⇒ 本轮保存确实写出了文件
      ② 连续 quiet 秒内存档族 size/mtime 均无变化 ⇒ 已经写完、不在写
      ③ 无 .tmp/.part/.lock/.writing 标记文件，且 gzip/json 完整性可读（防半截文件）

    返回 {ok, waited, files, updated, quiet, reason, bad, busy}
      reason: '' | no_files | writing | still_changing | unreadable
    """
    t0 = time.time()
    since = float(since_ts or t0)
    prev = None
    last_change = t0
    updated = {}
    _last_pub = -1   # v6181：progress 每秒最多回调一次（poll=0.5s 会重复触发）
    while True:
        cur = _dinodata_files(server)
        now = time.time()
        # v6190（用户口径）：**不再按后缀白名单过滤** —— 实测插件每轮还写
        #   _notes.json.gz / _alliances.json / _cryo.json.db / _cryo.json.snap，白名单会漏掉
        #   「仍在写」的信号（18MB 的 .db 尤其）。前缀过滤（本服）保持不变。
        fam = dict(cur)
        for fn, meta in fam.items():
            if int(meta.get('mtime') or 0) >= since - 2 and fn not in updated:
                updated[fn] = int(meta.get('mtime') or 0)
        busy = sorted([fn for fn, meta in cur.items() if meta.get('busy')])
        if prev is not None and fam == prev:
            stable_for = now - last_change
        else:
            last_change = now
            stable_for = 0.0
        if fam and (updated or not require_update) and not busy and stable_for >= quiet:
            bad = _dinodata_read_ok(server)
            if not bad:
                return {'ok': True, 'waited': round(now - t0, 1), 'files': len(cur),
                        'updated': sorted(updated)[:12], 'quiet': round(stable_for, 1),
                        'reason': '', 'bad': [], 'busy': []}
        if now - t0 >= budget:
            if not fam:
                reason = 'no_files'
            elif busy:
                reason = 'writing'
            elif require_update and not updated:
                reason = 'no_update'      # 文件稳定但本轮保存没有写出任何存档族文件
            elif stable_for < quiet:
                reason = 'still_changing'
            else:
                reason = 'unreadable'
            return {'ok': False, 'waited': round(now - t0, 1), 'files': len(cur),
                    'updated': sorted(updated)[:12], 'quiet': round(stable_for, 1),
                    'reason': reason, 'bad': _dinodata_read_ok(server), 'busy': busy}
        # v6181（用户口径「稳定等待期看不出来」）：每秒回调一次进度，供任务条显示「已等 Ns」
        if progress is not None:
            try:
                _wsec = int(now - t0)
                if _wsec != _last_pub:
                    _last_pub = _wsec
                    progress(round(now - t0, 1), round(stable_for, 1), budget)
            except Exception:
                pass
        prev = fam
        time.sleep(poll)


def _arkbk_wait_port_closed(server, budget=90):
    t0 = time.time()
    while time.time() - t0 < budget:
        if not _arkbk_rcon_alive(server, timeout=2).get('rconReachable'):
            return True
        time.sleep(2)
    return False


def _arkbk_wait_online(server, budget=600):
    """等服务器上线；**同时**盯启动队列 —— 队列一报失败就立即返回真实原因。

    v6057（用户口径「没有触发启动，你怎么就没发现一直卡着啊」）：
      原 `_arkbk_wait_port_open` 只看 RCON 端口，而启动队列在 Cen 撤销回档时
      **14 秒**（20:34:53 下发 → 20:35:08 报错）就已经记录了
      「启动过程中进程已退出（ASA 状态 Stopped）｜…LogCFCore: Error querying server mods:
        ApiError: Failed (serverUnreachable)」，
      回档流程却继续干等到 20:39:54（满 300 秒）才报「等待上线超时（可稍后手动查看）」，
      真实原因被完全吞掉，界面上也没有任何红色告警 ⇒ 用户直到自己去看才发现。
      改为每 2 秒同时检查队列 `done[]`，队列有结论就立刻结束。

    返回 (up: bool, reason: str)
    """
    t0 = time.time()
    _seen_proc = False
    while time.time() - t0 < budget:
        if _arkbk_rcon_alive(server, timeout=2).get('rconReachable'):
            return True, ''
        try:
            _q = _startq_view() or {}
            for _d in (_q.get('done') or []):
                if _d.get('server') != server:
                    continue
                try:
                    _te = float(_d.get('t_end') or 0)
                except Exception:
                    _te = 0
                if _te < t0:
                    continue                    # 上一轮的旧记录，忽略
                if _d.get('ok'):
                    continue                    # 队列认为起成功，只是端口还没通 -> 继续等
                _err = str(_d.get('err') or _d.get('msg') or '启动队列报错')
                return False, '启动失败：' + _err
        except Exception:
            pass
        # v6058（按推荐补全）：**进程状态硬判据** —— 队列没覆盖到的情形（队列被清空、
        #   或启动不是本队列发起）由 ASA /server-status 兜底：先见 Starting/Running、
        #   后变 Stopped ⇒ 进程起来过又退出，立即失败，不再等满预算。
        try:
            _pst = (_srvctl_proc_snapshot() or {}).get(server) or ''
            if _pst in ('Starting', 'Running'):
                _seen_proc = True
            elif _pst == 'Stopped' and _seen_proc:
                return False, ('启动失败：进程启动后又退出（ASA 状态 Stopped，%ds）'
                               % int(time.time() - t0))
        except Exception:
            pass
        time.sleep(2)
    return False, '等待上线超时（%ds 内 RCON 未就绪，可到「服务器控制」看启动队列）' % int(budget)


def _arkbk_job_gc():
    """清理**已结束且超过保留期**的 job（v6058：原实现没有主动 GC，
    只在新 job 创建时顺带清 2 小时以上的 ⇒ 失败条会一直挂着，重开面板还被 lastjob 恢复）。"""
    now = time.time()
    dead = []
    with _ARKBK_JOB_LOCK:
        for k, v in list(_ARKBK_JOBS.items()):
            if v.get('phase') not in ('done', 'failed'):
                continue
            if now - float(v.get('tEnd') or v.get('t0') or 0) > _ARKBK_JOB_KEEP:
                dead.append(k)
        for k in dead:
            _ARKBK_JOBS.pop(k, None)
    return len(dead)


def _arkbk_server_cn(server):
    """服务器中文名（execute/rollback 的 confirm 用）"""
    try:
        return (SERVER_THEMES.get(server) or {}).get('name') or server
    except Exception:
        return server

DINO_DATA = os.environ.get('DINO_DATA', r'D:\ARK Server\DinoData')

# ============ Wiki 按需抓取（v72e）============
# 思路：前端点开物种时才抓，抓到后落盘缓存；不用把 1000+ 物种预置进 CF
WIKI_CACHE_DIR = os.environ.get('WIKI_CACHE', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wiki_cache'))
WIKI_ROOT = 'https://wikily.gg/zh-cn/ark-survival-ascended/dinosaurs'
WIKI_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
WIKI_SKIP_WORDS = (u'使用计算器', u'广告', 'Cookie', u'订阅',
                   u'登录', u'下载', u'切换游戏', u'去广告', u'会员',
                   u'显示全部', u'打开完整', u'查看全部', u'查看详情')   # v111：页面按钮文字，不是正文

# ===== v286：ARK Wiki（wiki.gg）第二数据源 =====
# 原因：wikily 物品页只有「快速信息 / 制作配方 / 武器属性」等数值表格，
#       没有「使用说明 / 按键」章节 —— 武器专属按键（黏液枪 R 切黏液类型、Ctrl 采尸体）
#       与使用要点（电锯水下不可用、弩永远满蓄力）只存在于 ARK Wiki 的 Usage / Notes 段。
ARK_ROOT = 'https://ark.wiki.gg/wiki/'
_ARK_SEC_NAMES = ('Usage', 'Usage & Strategies', 'Notes', 'Notes/Tips', 'Notes / Tips',
                  'Use', 'Uses', 'Using', 'Tips')
# v5818（实测根因）：ARK Wiki 现版物品页的 H2 是 **Use**（不是 Usage），如 Grappling_Hook 页：
#   Navigation menu | Contents | Use | Grappling Hook Physics | Fleeing Behavior |
#   Dragging with the Grappling Hook | Notes | Changelog | Spotlight
#   原实现只精确匹配 'Usage' / 'Usage & Strategies' ⇒ **几乎所有物品都抽不到**（只黏液枪等极少数命中）。
#   改为前缀判定：use / usage / uses / using / note(s) / tip(s)。
_ARK_SEC_RE = r'^(?:use|usage|uses|using|note|notes|tip|tips)\b'

def _ark_is_sec(t):
    """H2 标题是否属于「使用/要点」类段落（v5818 前缀判定，替代精确枚举）"""
    import re as _re
    return bool(_re.match(_ARK_SEC_RE, str(t or '').strip(), _re.I))


def _wiki_strip(s):
    import re as _re, html as _h
    s = _re.sub(r'<script\b.*?</script>', '', s, flags=_re.S | _re.I)
    s = _re.sub(r'<style\b.*?</style>', '', s, flags=_re.S | _re.I)
    s = _re.sub(r'<[^>]+>', '', s)
    return _re.sub(r'\s+', ' ', _h.unescape(s)).strip()


def _wiki_strip_sp(s):
    """v260: 标签替换为空格再 strip，保留标签边界。

    _wiki_strip 直接删标签，会把 <span>× 9</span><span>30m 42s</span>
    粘成「× 930m 42s」⇒ 驯服食物口数/时长被放大 10 倍（Rex 曾显示口数 930）。
    """
    import re as _re, html as _h
    s = _re.sub(r'<script\b.*?</script>', '', s, flags=_re.S | _re.I)
    s = _re.sub(r'<style\b.*?</style>', '', s, flags=_re.S | _re.I)
    s = _re.sub(r'<[^>]+>', ' ', s)
    return _re.sub(r'\s+', ' ', _h.unescape(s)).strip()


# v260: 解析器版本戳 —— 缓存 _pv 低于此值判未就绪并重抓
_WIKI_PARSE_VER = 309   # v309(v5818)：段名改前缀判定（Use/Usage/Notes/Tips，原只认 Usage ⇒ 几乎全空）；改写解析必升版本号
# v5646：升到 302 —— lootRows 每行新增 mapSlug（wikily 行 href 的 ?map=，权威地图归属）。
#   版本戳不升的话 _ready() 会把旧缓存（无 mapSlug）判为已就绪，永不重解析，前端地图图标永远缺失。
                         # v287：物品补 ARK Wiki 专属按键（ark 字段）


def _wiki_h2seg(raw, name, maxlen=6000):
    import re as _re
    for m in _re.finditer(r'<h2[^>]*>(.*?)</h2>', raw, _re.S):
        if _wiki_strip(m.group(1)) == name:
            start = m.end()
            nxt = _re.search(r'<h2[^>]*>', raw[start:start + maxlen])
            end = start + (nxt.start() if nxt else maxlen)
            return raw[start:min(end, start + maxlen)]
    return ''


def _wiki_parse_overview(raw):
    import re as _re
    out = {'zh': '', 'intro': [], 'tips': []}
    m = _re.search(r'<h1[^>]*>(.*?)</h1>', raw, _re.S)
    if m:
        out['zh'] = _re.sub(r'^[\s\W]+', '', _wiki_strip(m.group(1)))[:20]
    for p in _re.findall(r'<p[^>]*>(.*?)</p>', _wiki_h2seg(raw, u'\u6982\u89c8'), _re.S):
        t = _wiki_strip(p)
        if len(t) >= 25 and not any(w in t for w in WIKI_SKIP_WORDS) and t not in out['intro']:
            out['intro'].append(t)
    for li in _re.findall(r'<li[^>]*>(.*?)</li>', _wiki_h2seg(raw, u'\u6280\u5de7'), _re.S):
        t = _wiki_strip(li)
        if 15 <= len(t) <= 220 and not any(w in t for w in WIKI_SKIP_WORDS) and t not in out['tips']:
            out['tips'].append(t)
    return out


def _wiki_parse_stats(raw):
    """v5851（用户口径「能力为啥都没取到」）：解析 wikily「基础属性」表

    输出与前端 OVERVIEW.stats 同口径：[[属性名, 基础值, 每级倍率], ...]
      · 前端列 = 基础 / 野生 +/级（base*pw）/ 已驯服 +/级 / 野生成长（pw）
      · wikily 表头 = 属性 | 基础 | 野生 +/级 | 已驯服 +/级 | 野生成长
      · pw = 野生+/~/基础（实测生命 10000 / +2000 / 20% 三者一致）
    """
    import re as _re
    seg = ''
    for _t in (u'基础属性', u'Stats', u'Base Stats'):
        seg = _wiki_h2seg_like(raw, _t)
        if seg:
            break
    if not seg:
        return []

    def _num(s):
        s = str(s or '').replace(',', '').replace(u'，', '').replace(u'%', '').replace('*', '').strip()
        m = _re.search(r'-?\d+(?:\.\d+)?', s)
        return float(m.group(0)) if m else None

    out, seen = [], set()
    for r in _re.findall(r'<tr[^>]*>([\s\S]*?)</tr>', seg):
        cells = [_wiki_strip(x) for x in _re.findall(r'<t[dh][^>]*>([\s\S]*?)</t[dh]>', r)]
        if len(cells) < 3:
            continue
        nm = str(cells[0] or '').strip()
        if (not nm) or nm in seen or len(nm) > 12:
            continue
        if nm in (u'属性', u'Attribute', u'Attributes', u'Stats'):
            continue
        base = _num(cells[1])
        add = _num(cells[2])
        if base is None:
            continue
        pw = (add / base) if (base and add) else 0.0
        seen.add(nm)
        out.append([nm, base, pw])
        if len(out) >= 12:
            break
    return out


def _wiki_nextdata(raw):
    """提取 Next.js 的 self.__next_f 载荷，反转义后拼成一整段（数据全在里面）"""
    import re as _re
    out = []
    for c in _re.findall(r'self\.__next_f\.push\(\[1,\s*"((?:[^"\\]|\\.)*)"\]\)', raw):
        try:
            out.append(json.loads('"' + c + '"'))
        except Exception:
            pass
    return ''.join(out)


_WIKI_ALIAS = None


def _wk_json_load(names, pick=None):
    """通用：按候选文件名顺序加载 json（脚本同目录 / data 子目录）。返回 (obj, path)"""
    here = os.path.dirname(os.path.abspath(__file__))
    for n in names:
        for p in (os.path.join(here, n), os.path.join(here, 'data', n)):
            try:
                if os.path.isfile(p):
                    with open(p, 'r', encoding='utf-8') as f:
                        obj = json.loads(f.read()) or {}
                    if pick:
                        obj = pick(obj)
                    return obj, p
            except Exception as e:
                print('[wiki] load fail %s: %s' % (p, str(e)[:80]))
    return None, ''


_NAME_FIX = None
_NAME_FIX_MT = 0.0


def _wk_name_fix_path():
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (os.path.join(here, 'wiki_name_fix.json'), os.path.join(here, 'data', 'wiki_name_fix.json')):
        if os.path.isfile(p):
            return p
    return ''


def _wk_name_fix():
    """wikily 中文页错译名 -> 项目正式名（按 mtime 热加载，改 json 无需重启进程）"""
    global _NAME_FIX, _NAME_FIX_MT
    p = _wk_name_fix_path()
    if not p:
        return _NAME_FIX or {}
    try:
        mt = os.path.getmtime(p)
    except OSError:
        return _NAME_FIX or {}
    if _NAME_FIX is not None and mt <= _NAME_FIX_MT:
        return _NAME_FIX
    try:
        with open(p, 'r', encoding='utf-8') as f:
            obj = json.loads(f.read()) or {}
        mp = obj.get('map') if isinstance(obj, dict) and 'map' in obj else obj
        _NAME_FIX = {str(k): str(v) for k, v in (mp or {}).items() if k and v}
        _NAME_FIX_MT = mt
        print('[wiki] name fix loaded %d from %s' % (len(_NAME_FIX), p))
    except Exception as e:
        print('[wiki] name fix fail %s: %s' % (p, str(e)[:80]))
        _NAME_FIX = _NAME_FIX or {}
    return _NAME_FIX


def _wk_name_fix_obj(o):
    """v5700：递归把 wikily 错译名替换成项目正式名（只改字符串值，不改键）"""
    fx = _wk_name_fix()
    if not fx:
        return o
    if isinstance(o, str):
        for a, b in fx.items():
            if a in o:
                o = o.replace(a, b)
        return o
    if isinstance(o, list):
        return [_wk_name_fix_obj(x) for x in o]
    if isinstance(o, dict):
        return {k: _wk_name_fix_obj(v) for k, v in o.items()}
    return o


def _wk_index_scan(cache_dir, zh_of, field):
    """通用：扫描缓存目录生成清单 {键: 中文名}"""
    out = {}
    try:
        if os.path.isdir(cache_dir):
            for f in os.listdir(cache_dir):
                if not f.endswith('.json'):
                    continue
                kk = f[:-5]
                try:
                    out[kk] = zh_of(kk)
                except Exception:
                    out[kk] = ''
    except Exception:
        pass
    d = {'ok': True, 'count': len(out)}
    d[field] = out
    return d


def _wk_lookup(names, index, limit=8):
    """通用：名字列表 -> 多形态 -> 白名单归一索引命中（去重保序）"""
    out = []
    for x in names:
        for f in _wk_forms(x):
            real = index.get(_re.sub(r'[^a-z0-9]', '', f))
            if real and real not in out:
                out.append(real)
    return out[:limit]


def _wiki_alias():
    """短名 -> 全名兜底表（v163：走 _wk_json_load 统一加载）"""
    global _WIKI_ALIAS
    if _WIKI_ALIAS is not None:
        return _WIKI_ALIAS
    obj, p = _wk_json_load(['wiki_alias.json'])
    _WIKI_ALIAS = obj if isinstance(obj, dict) else {}
    if p:
        print('[wiki] alias loaded %d from %s' % (len(_WIKI_ALIAS), p))
    return _WIKI_ALIAS

_WIKI_EN_MAP = None


def _wiki_en_map():
    """项目 DinoEntry 表：类名短名 -> 英文名（v163：走 _wk_json_load 统一加载）"""
    global _WIKI_EN_MAP
    if _WIKI_EN_MAP is not None:
        return _WIKI_EN_MAP
    obj, p = _wk_json_load(['dino_en_map.json'])
    _WIKI_EN_MAP = obj if isinstance(obj, dict) else {}
    if p:
        print('[wiki] en_map loaded %d from %s' % (len(_WIKI_EN_MAP), p))
    return _WIKI_EN_MAP

_WIKI_SLUGS = None
_WIKI_SLUGS_RAW = []


def _wiki_slugs():
    """wikily 全量恐龙 slug 白名单（557 条）-> 归一化索引（v163：走 _wk_json_load）"""
    global _WIKI_SLUGS, _WIKI_SLUGS_RAW
    if _WIKI_SLUGS is not None:
        return _WIKI_SLUGS
    _WIKI_SLUGS = {}
    _WIKI_SLUGS_RAW = []
    obj, p = _wk_json_load(['wiki_slugs.json'],
                           pick=lambda o: (o.get('slugs') if isinstance(o, dict) else o) or [])
    for s in (obj or []):
        s = str(s or '').strip()
        if not s:
            continue
        n = _re.sub(r'[^a-z0-9]', '', s.lower())
        if n:
            _WIKI_SLUGS[n] = s
            _WIKI_SLUGS_RAW.append(s)
    if p:
        print('[wiki] slugs loaded %d from %s' % (len(_WIKI_SLUGS), p))
    return _WIKI_SLUGS

_WK_PRE = ('Aberrant ', 'Brute ', 'Alpha ', 'Beta ', 'Gamma ', 'Corrupted ', 'Enraged ', 'Astral ',
           'Ghost ', 'Skeletal ', 'Tek ', 'Mega ', 'Primal ', 'Celestial ', 'Elder ', 'Lightning ',
           'Infused ', 'X-', 'R-', 'Bionic ')
_WK_SUF = (' Ghost', ' Alpha', ' Beta', ' Gamma', ' (Autumn)', ' (Spring)', ' (Summer)', ' (Winter)',
           ' Drone', ' Male', ' Female', ' Tentacle', ' Tentacles', ' (Large)', ' (Small)', ' (Shark)',
           ' (Squid)')

# 同物异名 / 拼写差异（仅当项目表缺项时兜底）
_WK_ALIAS = {
    'T-Rex': 'Rex', 'TRex': 'Rex', 'Mosasaur': 'Mosasaurus', 'Dilophosaur': 'Dilophosaurus',
    'Therizinosaur': 'Therizinosaurus', 'Parasaur': 'Parasaurolophus', 'Polar Bear': 'Dire Bear',
}


def _wk_peel(nm):
    """名字 -> 逐级降级形态（细 -> 粗），剥变体前缀/后缀/所有格/括号"""
    out = [nm]
    s = nm
    for _ in range(6):
        changed = False
        for p in _WK_PRE:
            if s.startswith(p):
                s = s[len(p):]
                changed = True
        for f in _WK_SUF:
            if s.endswith(f):
                s = s[:-len(f)]
                changed = True
        m = _re.match(r"^[A-Za-z'\-]+'s\s+(.+)$", s)
        if m:
            s = m.group(1)
            changed = True
        m2 = _re.match(r'^(.+?)\s*\([^)]*\)\s*$', s)
        if m2 and m2.group(1).strip():
            s = m2.group(1).strip()
            changed = True
        s = s.strip()
        if not changed:
            break
        if s and s not in out:
            out.append(s)
    return out


def _wk_forms(x):
    r = []
    for f in (str(x).lower().replace(' ', '-'), str(x).lower().replace(' ', ''),
              str(x).lower().replace(' ', '_')):
        f = _re.sub(r'[^a-z0-9\-_]', '', f)
        if f and f not in r:
            r.append(f)
    return r


_UE_BP_RE = _re.compile(r'^(.*?)_character_bp(?:_([A-Za-z0-9_]+))?$', _re.I)
# v6030：另有「Xxx_Character_C」这种**没有 _bp、没有变体**的写法（如 Leech_Character_C）。
#   wiki 站上这类物种以主名收录（白名单 v20261029 明确含 'leech'），
#   而旧正则只认 _character_bp ⇒ 候选退化成 'leech-character' ⇒ 404 ⇒
#   概览/驯服/采集/繁殖 全空、AI 整理也因无原文而 ready=false。
#   只放开「纯 _Character」这一种；带变体的 Xxx_Character_Y 仍返回 []（不超范围）。
_UE_PLAIN_RE = _re.compile(r'^(.*?)_character$', _re.I)


def _wk_ue_names(key):
    """UE 类名 -> wiki 页名形态（v5872）

    背景（用户口径「wikily 不可能没有飞龙的数据页」）：
      UE 类名是「主名_Character_BP_变体」，wiki 上的页名却是英文语序「变体 主名」
      例：Wyvern_Character_BP_Fire_C -> Fire Wyvern -> fire-wyvern
      （wiki.gg 同：Fire_Wyvern）
      缺了这一步反转，候选只剩 wyvern-character-bp-fire，白名单必然不命中 -> 全部 404。

    返回按可信度排序的名称列表（不含归一化，交给 _wk_forms 处理）：
      'Wyvern_Character_BP_Fire_C' -> ['Fire Wyvern', 'Wyvern Fire', 'Wyvern']
      'Ankylo_Character_BP_C'      -> ['Ankylo']
      'Rex'                        -> []   （非 UE 类名形态，不参与）
    """
    s = str(key or '').strip()
    if s.lower().endswith('_c'):
        s = s[:-2]
    m = _UE_BP_RE.match(s)
    if not m:
        # v6030：兼容纯 _Character 形态（Leech_Character_C -> Leech -> 候选 leech）
        _m2 = _UE_PLAIN_RE.match(s)
        if not _m2:
            return []
        _b2 = _re.sub(r'_+', ' ', (_m2.group(1) or '')).strip()
        return [_b2] if _b2 else []
    base = _re.sub(r'_+', ' ', (m.group(1) or '')).strip()
    var = _re.sub(r'_+', ' ', (m.group(2) or '')).strip()
    out = []
    if var and base:
        out.append(var + ' ' + base)
        out.append(base + ' ' + var)
    elif var and not base:
        out.append(var)
    if base:
        out.append(base)
    return out


def _wiki_slug_cands(key):
    """短名/物种名 -> wikily slug 候选（v175）。

    策略：真实 slug 白名单优先（变体降级 + 多形态），命中的即为站上存在的页面；
    白名单未命中时退回项目 en_map/alias 直出（兼容新物种未进白名单的情况）。
    """
    k = str(key or '').strip()
    sn = _wiki_slugs()
    em = _wiki_en_map()
    al = _wiki_alias()
    res = []

    seq = []
    for base in _wk_peel(k):
        seq.append(base)
        if em.get(base):
            seq.append(em[base])
        if al.get(base):
            seq.append(al[base])
        if _WK_ALIAS.get(base):
            a = _WK_ALIAS[base]
            seq.append(a)
            if em.get(a):
                seq.append(em[a])
    # v5872：UE 类名反转形态追加在**末尾** —— 已有物种的候选顺序完全不变，
    #   只有原始形态全军覆没时才会用到 'Fire Wyvern' 这类名称。
    try:
        for _un in _wk_ue_names(k):
            seq.append(_un)
    except Exception:
        pass

    res = _wk_lookup(seq, sn)

    # v192：精确名未收录时，试站上以 Alpha/Beta/Gamma 形态收录的写法
    # 实例：Abyssalus the Void Beneath 的 blueprintPath 是 Kraken_Character_BP_Gamma
    if not res:
        _alt = []
        for base in _wk_peel(k):
            for _sfx in (' Gamma', ' Alpha', ' Beta'):
                _alt.append(base + _sfx)
                if em.get(base):
                    _alt.append(em[base] + _sfx)
                if al.get(base):
                    _alt.append(al[base] + _sfx)
                if _WK_ALIAS.get(base):
                    _alt.append(_WK_ALIAS[base] + _sfx)
        res = _wk_lookup(_alt, sn)

    # v163：仍是未命中 -> 试「同族变体」：白名单里以 "<短名>-" 开头的 slug
    #   实例：前端只传短名 Abyssalus，站上收录为 abyssalus-the-void-beneath-gamma
    #   排序：gamma 优先（多数 BOSS 的最终形态），其次 alpha / beta，其余按长度升序
    if not res:
        _pref = _re.sub(r'[^a-z0-9]+', '-', k.lower()).strip('-')
        if _pref and _pref != '':
            _p2 = _pref + '-'
            fam = [s for s in _WIKI_SLUGS_RAW if s.startswith(_p2)]

            def _rank(x):
                if x.endswith('-gamma'):
                    return 0
                if x.endswith('-alpha'):
                    return 1
                if x.endswith('-beta'):
                    return 2
                return 3
            fam.sort(key=lambda x: (_rank(x), len(x), x))
            res = fam[:3]

    if res:
        return res[:8]

    # 兜底：原逻辑（en_map / alias / 短名 / 驼峰）
    out = []

    def add(x):
        x = _re.sub(r'[^a-z0-9]+', '-', str(x or '').lower()).strip('-')
        if x and x not in out:
            out.append(x)

    for src in (em.get(k), al.get(k), al.get(k.lower())):
        if src:
            add(src)
    add(k)
    try:
        add(_re.sub(r'(?<!^)(?=[A-Z])', '-', k))
    except Exception:
        pass
    return out[:4]

def _wiki_abs(u):
    u = str(u or '')
    if u.startswith('/'):
        return 'https://wikily.gg' + u
    return u


def _wiki_h2seg_like(raw, kw, maxlen=12000):
    """取 h2 文本包含 kw 的那一段（到下一个 h2），原型页 h2 常带副标题"""
    import re as _re
    for m in _re.finditer(r'<h2[^>]*>([\s\S]*?)</h2>', raw):
        if kw in _wiki_strip(m.group(1)):
            start = m.end()
            nxt = _re.search(r'<h2[^>]*>', raw[start:start + maxlen])
            end = start + (nxt.start() if nxt else maxlen)
            return raw[start:min(end, start + maxlen)]
    return ''


def _wiki_bracket(s, start):
    """从 s[start] 的 [ 或 { 起做括号配对（字符串感知），返回结束位置（不含）"""
    op = s[start]
    cl = ']' if op == '[' else '}'
    depth = 0
    i = start
    in_str = False
    esc = False
    while i < len(s):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == op:
                depth += 1
            elif ch == cl:
                depth -= 1
                if depth == 0:
                    return i + 1
        i += 1
    return -1


def _wiki_parse_home(raw):
    """首页全量富数据：技能 / 伤害 / 采集加成 / 鞍 / 击杀经验 / 驯服食物 / 食性"""
    import re as _re
    nd = _wiki_nextdata(raw)
    out = {}

    # ---- 技能 abilities[] ----
    skills = []
    m = _re.search(r'"abilities":\[', nd)
    if m:
        e = _wiki_bracket(nd, m.end() - 1)
        if e > 0:
            try:
                skills = json.loads(nd[m.end() - 1:e])
            except Exception:
                skills = []
    if isinstance(skills, list) and skills:
        sk = []
        for x in skills[:40]:
            if not isinstance(x, dict) or not x.get('title'):
                continue
            sk.append({'id': x.get('id'),
                       'zh': x.get('title'),
                       'desc': x.get('description') or '',
                       'key': x.get('inputHint') or x.get('inputHintText') or '',
                       'kind': x.get('kind') or '',
                       'video': _wiki_abs(x.get('videoUrl') or ''),
                       'poster': _wiki_abs(x.get('thumbnailUrl') or '')})
        if sk:
            out['skills'] = sk

    # ---- 采集伤害 damage{} ----
    dmg = {}
    m = _re.search(r'"damage":\{', nd)
    if m:
        e = _wiki_bracket(nd, m.end() - 1)
        if e > 0:
            try:
                dmg = json.loads(nd[m.end() - 1:e])
            except Exception:
                dmg = {}
    if isinstance(dmg, dict) and dmg:
        out['damage'] = dmg

    # ---- 采集加成（HTML「采集能力」段）----
    seg = _wiki_h2seg_like(raw, u'采集能力')
    caps = []
    if seg:
        seen = set()
        for part in _wiki_strip(seg).split(u'资源详情'):
            # _wiki_strip 会把 <span>树脂</span><span>10x</span> 拼成 "树脂10x"（无空格），故用 \s*
            # 部分物种带等级标记（如星尾兽 "沙 21x #7"），允许尾部 #N
            mm = _re.search(r'([\u4e00-\u9fa5A-Za-z]{1,10}?)\s*(\d+(?:\.\d+)?)x(?:\s*#\d+)?\s*$', part.strip())
            if not mm:
                continue
            nm = mm.group(1).strip()
            if not nm or len(nm) < 1 or nm in seen:
                continue
            seen.add(nm)
            caps.append({'zh': nm, 'mult': mm.group(2)})
            if len(caps) >= 24:
                break
    if caps:
        out['caps'] = caps

    # ---- 鞍（名称 / 制作经验）----
    sad = _re.findall(r'"base_xp":([\d.]+),"slug":"([^"]*saddle[^"]*)","name":"([^"]+)","xp":(\d+)', nd)
    if sad:
        out['saddles'] = [{'slug': a[1], 'zh': a[2], 'base': float(a[0]), 'xp': int(a[3])}
                          for a in sad[:12]]

    # ---- 击杀经验（注意：鞍的 xp 要大得多，必须用 no_xp 前缀精确定位）----
    xpk = _re.findall(r'"no_xp":(?:true|false),"xp":(\d+)', nd)
    if xpk:
        out['xpKill'] = int(xpk[0])

    # ---- 食性 ----
    m = _re.search(r'"diet":"([^"]*)"', nd)
    if m:
        out['diet'] = m.group(1)
        # v125：食性中文由后端统一给出（前端不再硬编码映射）
        _DIET_ZH = {'Herbivore': u'草食', 'Carnivore': u'肉食',
                    'Omnivore': u'杂食', 'Piscivore': u'鱼食'}
        out['dietZh'] = _DIET_ZH.get(m.group(1), m.group(1))
    if '"is_carnivore":true' in nd:
        out['carn'] = True

    # ---- 驯服食物 ----
    # v91：优先取页面**结构化组件**「最佳食物」（所有物种都有；原来只认「最佳驯服食物是」
    #   正文句子，只有甲龙这类页面才有，导致 Dodo/Rex/Triceratops 全空）。
    #   结构：["$","div","最佳食物",{"children":[["$","dt",...],"最佳食物"],
    #          ["$","dd",null,{"children":["$","$L38",null,
    #            {"href":"/zh-cn/.../items/basic-kibble","children":"基础饲料"}]}]]}]
    foods = []
    _mb = _re.search(u'\\["\\$","div","最佳食物"', nd)
    if _mb:
        _seg = nd[_mb.start():_mb.start() + 1600]
        _mh = _re.search(u'"href":"/zh-cn/[^"]*/items/[^"]*","children":"([^"]+)"', _seg)
        if _mh:
            _b = _mh.group(1).strip()
            if _b and len(_b) <= 20 and u'<' not in _b:
                foods.append(_b)
    # 正文句子补充「次选」（甲龙这类页面才有，不影响主食物）
    m = _re.search(u'最佳驯服食物是', nd)
    if m:
        tail = nd[m.end():m.end() + 120]
        tail = _re.split(u'[。\\n"]', tail)[0]
        for x in _re.split(u'[，,、]', tail):
            x = x.strip()
            for t in (u'也可作为次选', u'可作为次选', u'也可以', u'也可', u'等'):
                x = x.replace(t, '')
            x = x.strip()
            if 1 < len(x) <= 12 and not x.startswith(u'是') and x not in foods:
                foods.append(x)
    if foods:
        out['tamingFoods'] = foods[:6]

    # ---- v95：各 tab 的前置文案 ----
    # 实测首页有 18 个 h2，5 个 tab 都有引导段落，之前一条没抓（只有概览/繁殖抓了）。
    # 统一放 HOME，前端各 render 读取。
    _TXT_SPECS = (
        # v111：门槛 12 字（低于 12 多是被 v111 的 SKIP_WORDS 漏掉的按钮/标签文字）
        ('tameIntro',    u'驯服',           (12, 600)),
        ('gatherIntro',  u'采集能力',       (12, 600)),
        ('harvestIntro', u'掉落与采集资源', (12, 600)),
        ('expIntro',     u'经验值',         (6, 400)),
        ('abilIntro',    u'战斗与技能',     (12, 500)),
    )
    # v114：wiki 驯服食物表（h2「驯服」段的 <li>，格式如
    #   「基础饲料 最佳 亲和度 400 × 3 1m 43s + 74 Lvl (224)」）
    try:
        _tseg = _wiki_h2seg_like(raw, u'驯服', 12000)
        if _tseg:
            _tf = []
            for _li in _re.findall(r'<li[^>]*>(.*?)</li>', _tseg, _re.S):
                # v260: 用带标签边界的 strip，杜绝「× 9」+「30m」粘连
                _t = _wiki_strip_sp(_li)
                if not _t or u'×' not in _t or u'Lvl' not in _t:
                    continue
                _best = bool(_re.search(r'最佳', _t))
                _t2 = _t.replace(r'最佳', ' ')
                _ma = _re.search(r'亲和度\s*([0-9.]+)', _t2)
                _ml = _re.search(r'\+\s*(\d+)\s*Lvl', _t2)
                # v260: 先抠时长并从文本移除，再取口数（否则 30m 的 30 被吃掉）
                _dur = u''
                _t3 = _t2
                _mh2 = _re.search(r'(\d+)\s*h\s*(\d+)\s*m\s*(\d+)\s*s', _t2)
                _md = _re.search(r'(\d+)\s*m\s*(\d+)\s*s', _t2)
                _ms = _re.search(r'(\d+)\s*s(?![a-zA-Z0-9])', _t2)
                if _mh2:
                    _dur = u'%s小时%s分%s秒' % (_mh2.group(1), _mh2.group(2), _mh2.group(3))
                    _t3 = _t2.replace(_mh2.group(0), ' ', 1)
                elif _md:
                    _dur = u'%s分%s秒' % (_md.group(1), _md.group(2))
                    _t3 = _t2.replace(_md.group(0), ' ', 1)
                elif _ms:
                    _dur = u'%s秒' % _ms.group(1)
                    _t3 = _t2.replace(_ms.group(0), ' ', 1)
                _mq = _re.search(r'×\s*(\d+)', _t3)
                _nm = _re.split(r'×', _t3)[0]
                # v5732 修复：亲和度可能是小数（如 187.5），原 \d+ 只吃掉「187」⇒ 残留「.5」污染食物名
                _nm = _re.sub(r'\s*亲和度\s*[0-9.]+\s*', ' ', _nm)
                _nm = _re.sub(r'\s+', ' ', _nm).strip()[:24]
                if not _nm or len(_nm) < 2:
                    continue
                _tf.append({'zh': _nm, 'best': _best,
                            'aff': (float(_ma.group(1)) if _ma else 0),
                            'qty': int(_mq.group(1)) if _mq else 0,
                            'dur': _dur,
                            'lvl': int(_ml.group(1)) if _ml else 0})
                if len(_tf) >= 8:
                    break
            if _tf:
                out['tameFoods'] = _tf
    except Exception:
        pass


    for _k, _kw, _rng in _TXT_SPECS:
        try:
            _seg = _wiki_h2seg_like(raw, _kw, 9000)
            if not _seg:
                continue
            _arr = []
            for _p in _re.findall(r'<p[^>]*>(.*?)</p>', _seg, _re.S):
                _t = _wiki_strip(_p)
                if not (_rng[0] <= len(_t) <= _rng[1]):
                    continue
                if any(w in _t for w in WIKI_SKIP_WORDS):
                    continue
                if _t in _arr:
                    continue
                _arr.append(_t)
                if len(_arr) >= 3:
                    break
            if _arr:
                out[_k] = _arr
        except Exception:
            pass

    # ---- v5732（用户口径）: wikily「更多XX驯服信息」折叠块 -> tameIntro（驯服置顶文案）----
    #   源 = SSR HTML 里的 <details class="ark-otame-fold"><summary>更多XX驯服信息</summary><div><p>…</p></div></details>
    #   说明：这是**自动抓取**，对全部物种持续生效（非针对某一物种的一次性硬编码）；
    #         前端仍交给 tcSentences() 渲染，保持 .tc-more/.tc-expand 自动折叠结构不变。
    try:
        _mf = _re.search(u'<details class="ark-otame-fold"><summary>[^<]*</summary><div>(.*?)</div></details>', raw, _re.S)
        if _mf:
            _mt = _wiki_strip(_mf.group(1))
            if _mt and len(_mt) >= 12:
                _arrT = [x for x in (out.get(u'tameIntro') or []) if x]
                if _mt not in _arrT:
                    out[u'tameIntro'] = [_mt] + _arrT
    except Exception:
        pass

    # v260: 无食物表时从「驯服」引导段兜底（毒蜥这类被动驯服喂蛋的物种）
    if not out.get('tameFoods'):
        _ti = u' '.join([str(x) for x in (out.get('tameIntro') or [])])
        if _ti:
            _fb = []
            _nmseen = set()
            for _m4 in _re.finditer(r'(?:使用|需使用|要用|采用)\s*([^\s，。、；][^，。、；]{1,24}?)\s*(?:作为食物|作为诱饵|作为驯服食物|作为饲料)', _ti):
                _n4 = _m4.group(1).strip()
                if _n4 and _n4 not in _nmseen:
                    _nmseen.add(_n4)
                    _fb.append({'zh': _n4, 'best': True, 'aff': 0, 'qty': 0, 'dur': u'', 'lvl': 0})
            for _m4 in _re.finditer(r'([^\s，。、；][^，。、；]{1,24}?)\s*也可用作?替代', _ti):
                _n4 = _m4.group(1).strip()
                if _n4 and _n4 not in _nmseen:
                    _nmseen.add(_n4)
                    _fb.append({'zh': _n4, 'best': False, 'aff': 0, 'qty': 0, 'dur': u'', 'lvl': 0})
            _mq4 = _re.search(r'大约需要\s*(\d+)\s*个', _ti)
            _mdur4 = _re.search(r'耗时约\s*(\d+)\s*分钟', _ti)
            if _fb:
                for _x in _fb:
                    if _x['best']:
                        if _mq4:
                            _x['qty'] = int(_mq4.group(1))
                        if _mdur4:
                            _x['dur'] = u'约%s分钟' % _mdur4.group(1)
                out['tameFoods'] = _fb[:6]
                out['tameFoodsFrom'] = 'intro'

    return out


def _wiki_parse_abil(raw):
    """技能页：从 nd 里抓 title/videoUrl/thumbnailUrl 三元组"""
    import re as _re
    nd = _wiki_nextdata(raw)
    skills = []
    pat = r'"title":"((?:[^"\\]|\\.)*)","videoUrl":"((?:[^"\\]|\\.)*)","thumbnailUrl":"((?:[^"\\]|\\.)*)"'
    for m in _re.finditer(pat, nd):
        t = m.group(1)
        if not t or len(t) > 40:
            continue
        v = _wiki_abs(m.group(2))
        if not v:
            continue
        if any(x['zh'] == t for x in skills):
            continue
        skills.append({'zh': t, 'video': v, 'poster': _wiki_abs(m.group(3))})
        if len(skills) >= 40:
            break
    return {'skills': skills}


def _wiki_raw_tables(raw):
    """把页面里所有 <table> 抓成 [[cells], …]（不绑标题；繁殖页表格用）"""
    import re as _re
    out = []
    for tb in _re.findall(r'<table[^>]*>([\s\S]*?)</table>', raw, _re.I):
        rows = []
        for tr in _re.findall(r'<tr[^>]*>([\s\S]*?)</tr>', tb, _re.I):
            cells = [_wiki_strip(c) for c in _re.findall(r'<t[hd][^>]*>([\s\S]*?)</t[hd]>', tr, _re.I)]
            cells = [c for c in cells if c]
            if cells:
                rows.append(cells)
        if len(rows) >= 2:
            out.append(rows)
    return out


def _wiki_parse_harvest(raw):
    """收割页：wikily 现用 ark-hc-cards 卡片承载资源，**资源名在卡片 <h4>**。

    v5793 根因（用户口径「收割 TAB 里的里的数据表格 完全看不懂」）：
      · 资源节点产量：表其实嵌在 <article><h4>石头</h4><table>…</table></article> 里，
        旧实现只抽 <table>、只把 <h2> 当标题 ⇒ 资源名全丢，前端出现 2~6 张一模一样的
        「产量/低/平均/高」表，完全无法分辨；
      · 尸体产量：wikily 已改为卡片（<h4>生肉</h4> + <p>数值），页面里根本没有 <table>
        ⇒ 旧实现产出 0 张表。
    v5793 改法：按 <article> 顺序扫描，把最近的 <h2> 绑成 group、卡片 <h4> 绑成 title；
      卡片内含 <table> 就取它的行，否则把卡片 <p> 归纳成「项目 / 数值」两列。
    """
    import re as _re
    _FIX = ((u'corpse yield', u'尸体产量'),)     # wikily 部分 h2 混英文，顺手汉化
    h2 = []
    for m in _re.finditer(r'<h2[^>]*>([\s\S]*?)</h2>', raw, _re.I):
        t = _wiki_strip(m.group(1))
        if not t:
            continue
        for _b, _g in _FIX:
            if _b in t:
                t = t.replace(_b, _g).strip()
        h2.append((m.start(), t))
    titles = []
    for _p, t in h2:
        if t not in titles:
            titles.append(t)

    def _grp(pos):
        g = u''
        for p, t in h2:
            if p < pos:
                g = t
            else:
                break
        return g

    tabs = []
    for m in _re.finditer(r'<article[^>]*>([\s\S]*?)</article>', raw, _re.I):
        body = m.group(1)
        mh = _re.search(r'<h4[^>]*>([\s\S]*?)</h4>', body, _re.I)
        nm = _wiki_strip(mh.group(1)) if mh else u''
        if not nm:
            continue
        rows = []
        for tb in _re.findall(r'<table[^>]*>([\s\S]*?)</table>', body, _re.I):
            rs = []
            for tr in _re.findall(r'<tr[^>]*>([\s\S]*?)</tr>', tb, _re.I):
                cells = [_wiki_strip(c) for c in _re.findall(r'<t[hd][^>]*>([\s\S]*?)</t[hd]>', tr, _re.I)]
                cells = [c for c in cells if c]
                if cells:
                    rs.append(cells)
            if len(rs) >= 2:
                rows = rs
                break
        if not rows:
            ps = [_wiki_strip(x) for x in _re.findall(r'<p[^>]*>([\s\S]*?)</p>', body, _re.I)]
            kv = []
            for x in ps:
                if not x:
                    continue
                m1 = _re.search(r'每次掷骰\s*([\d.]+\s*%)', x)
                if m1:
                    kv.append([u'每次掷骰', m1.group(1).replace(' ', u'')])
                    continue
                m2 = _re.match(r'^([\d,.]+)\s*平均$', x)
                if m2:
                    kv.append([u'平均', m2.group(1)])
                    continue
                m3 = _re.search(r'近战时\s*([\d,.]+\s*-\s*[\d,.]+)', x)
                if m3:
                    kv.append([u'近战100%', m3.group(1)])
                    continue
                m4 = _re.search(r'峰值[:：]?\s*(.+)$', x)
                if m4:
                    kv.append([u'峰值', _re.sub(u'近战%时', u'', m4.group(1)).strip()])
                    continue
            if kv:
                rows = [[u'项目', u'数值']] + kv
        if rows:
            tabs.append({'title': nm, 'group': _grp(m.start()), 'rows': rows})
            if len(tabs) >= 40:
                break
    if not tabs:
        # 兜底：页面没有 ark-hc-cards 卡片、但仍有裸 <table> 的旧版式
        for i, rows in enumerate(_wiki_raw_tables(raw)[:6]):
            tabs.append({'title': (titles[i + 2] if len(titles) > i + 2 else (u'表 %d' % (i + 1))),
                         'group': u'', 'rows': rows})
    return {'tables': tabs[:40], 'titles': titles[:8]}   # v5793c：14 -> 40（实测恐熊 23 组：20 资源节点 + 生肉/兽皮/优质生肉；按数量截断会把排在最后的尸体产出整段挤掉）


def _wiki_parse_breed(raw):
    """繁殖页：中文段落 + 表格"""
    import re as _re
    out = {'intro': [], 'tables': []}
    for p in _re.findall(r'<p[^>]*>(.*?)</p>', raw, _re.S):
        t = _wiki_strip(p)
        if len(t) >= 20 and not any(w in t for w in WIKI_SKIP_WORDS) and t not in out['intro']:
            out['intro'].append(t)
        if len(out['intro']) >= 14:
            break
    out['tables'] = _wiki_raw_tables(raw)   # v5793：繁殖页仍是真 <table>，用裸表提取保持旧结构
    return out


def _wiki_parse_gather(raw):
    """采集页（/buildings）只存放建筑模板，且正文混英文+页脚导航 → 不再采用；
       采集加成与节点产量统一由首页 HOME.caps 提供（v73b）"""
    return {'intro': [], 'skip': 1}






# ============ Wiki 按需抓取（v72f 分级版）============
# 思路：概览先抓先落盘（约 4 秒），其余子页后续批次补清洗
WIKI_SUBS = [('breeding-calculator', 'BREED'), ('harvesting', 'HARVEST'),
             ('buildings', 'GATHER'), ('abilities', 'ABIL'), ('spawn-command', 'SPAWN')]
# v72q：worker 实际抓取顺序与落盘 block 名（首项为空 sub = 抓首页）
_WIKI_STEPS = [('', 'HOME'), ('abilities', 'ABIL'), ('harvesting', 'HARVEST'),
               ('breeding-calculator', 'BREED_DESC'), ('buildings', 'GATHER')]
_WIKI_LOCK = threading.Lock()
_WIKI_TASKS = {}


def _wiki_cache_path(key):
    return os.path.join(WIKI_CACHE_DIR, key + '.json')


def _wiki_load(key):
    p = _wiki_cache_path(key)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, 'r', encoding='utf-8') as f:
            return json.loads(f.read())
    except Exception:
        return None


def _wiki_save(key, data):
    try:
        if isinstance(data, dict):
            data['_pv'] = _WIKI_PARSE_VER
        os.makedirs(WIKI_CACHE_DIR, exist_ok=True)
        p = _wiki_cache_path(key)
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False, separators=(',', ':')))
        os.replace(tmp, p)
        return True
    except Exception as e:
        print('[wiki] save fail ' + key + ': ' + str(e)[:100])
        return False


def _wiki_log(msg):
    """worker 运行日志（写文件，便于定位卡在哪一步）"""
    try:
        os.makedirs(WIKI_CACHE_DIR, exist_ok=True)
        p = os.path.join(WIKI_CACHE_DIR, '_worker.log')
        line = time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + str(msg)[:400] + '\n'
        with open(p, 'a', encoding='utf-8') as f:
            f.write(line)
        # 超过 400KB 截半，避免无限增长
        if os.path.getsize(p) > 400 * 1024:
            with open(p, 'r', encoding='utf-8', errors='replace') as f:
                ls = f.readlines()[-800:]
            with open(p, 'w', encoding='utf-8') as f:
                f.writelines(ls)
    except Exception:
        _sexc('wiki_log')
        pass


def _wiki_fetch_page(url, timeout=18):
    import urllib.request as _u
    req = _u.Request(url, headers={'User-Agent': WIKI_UA, 'Accept': 'text/html'})
    r = _u.urlopen(req, timeout=timeout)
    return r.read().decode('utf-8', 'replace')


def _wiki_worker(key):
    """后台抓取：首页(概览+经验+食性) -> 各子页清洗后逐块落盘（分级可用）"""
    slug = str(key).lower()
    steps = _WIKI_STEPS
    total = len(steps)
    _wiki_log('worker START %s steps=%d' % (key, total))
    try:
        data = _wiki_load(key) or {}
        for i, (sub, block) in enumerate(steps):
            with _WIKI_LOCK:
                t = _WIKI_TASKS.get(key)
                if t:
                    t['done'] = i
            _blk = data.get(block)
            _okJump = bool(_blk) and not (isinstance(_blk, dict) and _blk.get('_fail'))
            # v269：关键修复 —— 只有「整份缓存已是当前解析版本」时才允许跳过。
            # 否则 _ready 因缺 _pv 判未就绪 -> 触发 worker -> worker 全跳过不写盘 -> _pv 永远补不上
            # -> 每 5 秒无限触发 worker 的死循环。
            if int(data.get('_pv') or 0) < _WIKI_PARSE_VER:
                _okJump = False
            # v73f：HOME 旧结构只有 xp/diet，必须含 xpKill 才算完整（仅在允许跳过时才有意义）
            if _okJump and block == 'HOME' and 'xpKill' not in (_blk if isinstance(_blk, dict) else {}):
                _okJump = False
            if _okJump:
                continue
            _t0 = time.time()
            raw = None
            _used = slug
            # v78：子页优先复用首页已确认的真实 slug（ankylo -> ankylosaurus）
            _known = str((data.get('DATA') or {}).get('slug') or '')
            if sub and _known:
                _cands = [_known]
            else:
                _cands = _wiki_slug_cands(key)
            for _si, _cand in enumerate(_cands):
                url = WIKI_ROOT + '/' + _cand + (('/' + sub) if sub else '')
                _wiki_log('start %s %s slug=%s' % (key, block, _cand))
                try:
                    # v6107（用户口径「雪鸮怎么会没取到 wikily 数据」）：
                    #   实测雪鸮首页 741 KB，从本机读到 78.9s 才抛 The read operation timed out
                    #   → 触发 ark 兜底 → 只得到 HOME/ABIL，前端 tabs/tabHtml/zh 全空。
                    #   原值 60s(HOME)/18s(子页) 对大页面不够；改为 150s/45s。
                    raw = _wiki_fetch_page(url, 150 if block == 'HOME' else 45)
                    _used = _cand
                    if _si > 0:
                        _wiki_log('slug hit %s -> %s' % (key, _cand))
                    break
                except Exception as _e1:
                    if '404' in str(_e1) and _si < len(_cands) - 1:
                        continue
                    _wiki_log('FAIL %s %s %dms %s' % (key, block, int((time.time() - _t0) * 1000), str(_e1)[:140]))
                    data[block] = {'_fail': 1, 'at': int(time.time() * 1000), 'err': str(_e1)[:120]}
                    _wiki_save(key, data)
                    raw = None
                    break
            if raw is None and sub == '':
                # v5831：wikily 首页全部候选失败 → 先试第二数据源 ark.wiki.gg（纯载具只有这个源有）
                try:
                    if _ark_seed(key, data):
                        _wiki_save(key, data)
                        _wiki_log('worker DONE %s (ark fallback %s)' % (key, str((data.get('DATA') or {}).get('_arkSlug') or '')))
                        with _WIKI_LOCK:
                            _t9 = _WIKI_TASKS.get(key)
                            if _t9:
                                _t9['status'] = 'ready'
                                _t9['data'] = data
                                _t9['done'] = total
                        break
                except Exception as _eA:
                    _wiki_log('arkFAIL %s %s' % (key, str(_eA)[:140]))
                # v105：两源都失败 → 直接给全部 block 标 fail 并结束，
                #   不再让 4 个子页各试 3 个候选（原来会白跑 40+ 秒，前端轮询到超时）。
                _now = int(time.time() * 1000)
                for _sb, _bk in steps:
                    if not data.get(_bk):
                        data[_bk] = {'_fail': 1, 'at': _now, 'err': 'wiki 无此物种页面'}
                try:
                    _wiki_save(key, data)
                except Exception:
                    pass
                _wiki_log('worker ABORT %s (首页所有 slug 候选均失败)' % key)
                break
            if raw is None:
                continue
            if block == 'HOME':
                ov = _wiki_parse_overview(raw)
                try:
                    extra = _wiki_parse_home(raw)
                except Exception:
                    extra = {}
                # v5734（用户口径）：额外抓「驯服计算器页 /taming-calculator」的 ark-tame-after，
                #   只取 data-ark-fact-text="intro" 组（物种介绍 4 段）并入 tameIntro。
                #   说明：物种主页只有 ark-otame-fold（1 段短文案），用户要的那段在计算器页，主页搜不到。
                try:
                    _craw = _wiki_fetch_page(WIKI_ROOT + '/' + _used + '/taming-calculator', 30)
                    _mi = _re.search(u'<div data-ark-fact-text="intro"[^>]*>(.*?)</div>', _craw, _re.S)
                    if _mi:
                        _arrT2 = list(extra.get(u'tameIntro') or [])
                        for _pp in _re.findall(r'<p[^>]*>(.*?)</p>', _mi.group(1), _re.S):
                            _tt = _wiki_strip(_pp)
                            if _tt and len(_tt) >= 12 and _tt not in _arrT2:
                                _arrT2.append(_tt)
                        if _arrT2:
                            extra[u'tameIntro'] = _arrT2
                            _wiki_log('calc intro %s +%d' % (key, len(_arrT2)))
                except Exception as _eC:
                    _wiki_log('calcFAIL %s %s' % (key, str(_eC)[:100]))
                data['DATA'] = {'zh': ov['zh'], 'slug': _used, 'title': '', 'tabs': [],
                                'fetched_at': int(time.time() * 1000), 'tabHtml': {}}
                _st = []
                try:
                    _st = _wiki_parse_stats(raw)
                except Exception as _eS:
                    _st = []
                if _st:
                    _wiki_log('stats %s +%d' % (key, len(_st)))
                data['OVERVIEW'] = {'intro': ov['intro'], 'tips': ov['tips'], 'stats': _st, 'bp': ''}
                # v5851（用户口径「操作方法」）：载具/器械的 Controls / Utility / Fuel 只在 wiki.gg，
                #   wikily 抓成功也要去补一次，并入技能页置顶文案（abilIntro）。
                try:
                    _apName = ''
                    try:
                        _apName = (_wk_ark_pages() or {}).get(key) or ''
                    except Exception:
                        _apName = ''
                    if _apName:
                        _au, _ac, _ar = _ark_fetch(_apName, timeout=30)
                        if _ac == 200 and _ar and len(_ar) > 5000 and 'Just a second' not in _ar[:4000]:
                            _vls = _ark_vehicle_lines(_ar)
                            if _vls:
                                _arrV = list(extra.get(u'abilIntro') or [])
                                for _x in _vls:
                                    if _x not in _arrV:
                                        _arrV.append(_x)
                                if _arrV:
                                    extra[u'abilIntro'] = _arrV
                                _wiki_log('arkVehicle %s %s +%d' % (key, _apName, len(_vls)))
                            # v5855：操作键单独结构化存下来，前端「技能」页直接渲染成键位表
                            try:
                                _cks = _ark_controls(_ar)
                                if _cks:
                                    extra[u'abilKeys'] = _cks
                                    _wiki_log('arkControls %s +%d' % (key, len(_cks)))
                            except Exception as _eK:
                                _wiki_log('arkControlsFAIL %s %s' % (key, str(_eK)[:100]))
                except Exception as _eV:
                    _wiki_log('arkVehicleFAIL %s %s' % (key, str(_eV)[:120]))
                data['HOME'] = extra or {}
            elif block == 'ABIL':
                data['ABIL'] = _wiki_parse_abil(raw)
            elif block == 'HARVEST':
                data['HARVEST'] = _wiki_parse_harvest(raw)
            elif block == 'BREED_DESC':
                data['BREED_DESC'] = _wiki_parse_breed(raw)
            elif block == 'GATHER':
                data['GATHER'] = _wiki_parse_gather(raw)
            _wiki_save(key, data)
            _wiki_log('ok %s %s %dms %dB' % (key, block, int((time.time() - _t0) * 1000), len(raw)))
            time.sleep(0.6)
            with _WIKI_LOCK:
                t = _WIKI_TASKS.get(key)
                if t:
                    t['done'] = i + 1
                    t['data'] = data
        _wiki_log('worker DONE %s blocks=%s' % (key, ','.join([b for (_s2, b) in steps if data.get(b)])))
        with _WIKI_LOCK:
            t = _WIKI_TASKS.get(key)
            if t:
                t['status'] = 'ready'
                t['data'] = data
                t['done'] = total
    except Exception as e:
        import traceback as _tb
        print('[wiki] worker err ' + str(key) + ': ' + str(e)[:160])
        _tb.print_exc()
        with _WIKI_LOCK:
            t = _WIKI_TASKS.get(key)
            if t:
                t['status'] = 'error'
                t['err'] = str(e)[:160]


def _wk_task_get(key, start, cfg):
    """通用 wiki 任务状态机（物种 / 物品共用）。

    流程：键校验 -> 进行中任务 -> 缓存就绪 -> （未启动）error / idle -> 起后台任务 -> fetching
    cfg:
      id_field    : 返回体主键字段名（'key' 物种 / 'cls' 物品）
      tasks, lock : 任务表与锁
      valid       : fn(key)->bool
      load        : fn(key)->cached|None
      is_ready    : fn(cached)->bool
      ready_extra : fn(cached)->dict        额外字段（物种 _miss）
      fail_err    : fn(cached)->str         缓存「全失败」时的错误文案；'' 表示非全失败
      total       : int
      meta        : fn(key)->dict           起任务时附加元数据（物品 slug）
      worker      : fn(key)
    """
    key = str(key or '').strip()
    idf = cfg.get('id_field') or 'key'
    if not key or not (cfg.get('valid') or (lambda x: True))(key):
        return {idf: key, 'status': 'error', 'err': 'bad key'}
    tasks, lock = cfg['tasks'], cfg['lock']
    total = cfg.get('total') or 1
    ready_extra = cfg.get('ready_extra') or (lambda c: {})

    with lock:
        t = tasks.get(key)
    if t and t.get('status') in ('fetching', 'partial'):
        d = {idf: key, 'status': t['status'], 'done': t.get('done', 0),
             'total': t.get('total', total), 'err': t.get('err'),
             'data': (t.get('data') if t.get('data') else None)}
        if t.get('slug'):
            d['slug'] = t['slug']
        return d

    cached = cfg['load'](key)
    miss = None
    if cached and cfg['is_ready'](cached):
        extra = ready_extra(cached) or {}
        miss = extra.get('_miss')
        # v5862（用户口径「战车 的 wiki 似乎没有和 泰克悬浮艇 走同样的解析逻辑」）：
        #   ark 回退物种的 wiki.gg 页面可能本身就是 stub（BattleRig 只有 Equipment/Notes，
        #   没有 HOME/ABIL/HARVEST/GATHER 段）⇒ _miss 永远非空 ⇒ 每次带 start 的请求都重新起抓取任务、
        #   前端永远拿不到 ready（TAB 残缺 + 反复重抓 wiki.gg）。
        #   只要 is_ready 已通过（_src=='ark' 且 _arkVer 达标），就按 ready 返回，_miss 照旧附带供调试。
        _isArkCache = False
        try:
            _isArkCache = ((cached.get('DATA') or {}).get('_src') == 'ark')
        except Exception:
            _isArkCache = False
        if not miss or not start or _isArkCache:
            d = {idf: key, 'status': 'ready', 'done': total, 'total': total,
                 'data': cached, '_from': 'cache'}
            d.update(extra)
            return d

    if not start:
        e = ''
        if cached:
            e = (cfg.get('fail_err') or (lambda c: ''))(cached) or ''
        if e:
            return {idf: key, 'status': 'error', 'done': 0, 'total': total, 'err': e}
        return {idf: key, 'status': 'idle', 'done': 0, 'total': total}

    meta = (cfg.get('meta') or (lambda k: {}))(key) or {}
    tk = {'status': 'fetching', 'done': 0, 'total': total, 'err': None,
          'data': cached, 'startedAt': int(time.time() * 1000)}
    tk.update(meta)
    with lock:
        tasks[key] = tk
    threading.Thread(target=cfg['worker'], args=(key,), daemon=True).start()
    d = {idf: key, 'status': 'fetching', 'done': 0, 'total': total, 'data': cached}
    d.update(meta)
    if cached:
        d['_miss'] = miss
    return d


# ===================== v5751：上游机翻错误读取层纠正 =====================
# 背景（用户 2026-10-31 报「负重上限低于200的生物可以使霸王龙昏迷」明显理解错）：
#   · 该句**上游 wikily.gg 中文站原文就错**（实测直抓 /dinosaurs/Rex「技巧」段第 4 条逐字一致）
#   · 英文原意：Creatures with a Drag Weight below 200 can be knocked out by the Rex's roar
#     → 机翻把主宾颠倒（B 使 A 昏迷）+ 把 Drag Weight（拖拽重量）误译成「负重上限」
#   · 缓存里已固化旧文本，而 _WIKI_PARSE_VER 递增会让 **557 个物种全部重抓**（代价极大）
#   ⇒ 改为**读取时纠正**：API 返回前对 OVERVIEW.tips 做已知错误替换（幂等、零重抓成本）
WIKI_TIP_FIX = (
    (u'负重上限低于200的生物可以使霸王龙昏迷',
     u'霸王龙的咆哮可让拖拽重量（Drag Weight）低于200的生物昏迷。'),
)


def _wiki_tipfix(obj):
    """把 OVERVIEW.tips 里的**已知机翻错误**就地纠正（原地改，返回原对象）"""
    try:
        d = (obj or {}).get('data') or {}
        tps = (d.get('OVERVIEW') or {}).get('tips') or []
        for i, t in enumerate(tps):
            st = str(t or '')
            for bad, good in WIKI_TIP_FIX:
                if bad in st:
                    tps[i] = good
                    break
    except Exception:
        pass
    return obj


def _wiki_get(key, start=True):
    """取物种 wiki 状态（v163：流程统一走 _wk_task_get）"""
    def _ready(c):
        # v5835（用户口径「概览不要强行填充」）：ark 回退数据允许 OVERVIEW.intro 为空，
        #   否则概览留空时本函数恒 False，任务永远不 ready（前端会一直转圈并反复重抓）。
        #   版本过低时返回 False 照样触发重抓（v5833 口径不变）。
        _d0 = c.get('DATA') or {}
        if _d0.get('_src') == 'ark':
            return int(_d0.get('_arkVer') or 0) >= _ARK_SEED_VER
        if not (c.get('OVERVIEW') or {}).get('intro'):
            return False
        # v260: 老缓存版本戳低 -> 强制重抓（旧驯服食物口数/时长是错的）
        return int(c.get('_pv') or 0) >= _WIKI_PARSE_VER

    def _extra(c):
        return {'_miss': [b for (_s, b) in _WIKI_STEPS if not c.get(b)]}

    def _fail(c):
        # v166：缓存里全是 _fail（首页抓取失败）时必须回 error，否则前端空转到超时
        vals = [v for v in c.values() if isinstance(v, dict)]
        if vals and all(v.get('_fail') for v in vals):
            for v in vals:
                if v.get('err'):
                    return str(v.get('err'))[:120]
            return u'该物种暂无数据'
        return ''

    return _wk_name_fix_obj(_wk_task_get(key, start, {
        'id_field': 'key', 'tasks': _WIKI_TASKS, 'lock': _WIKI_LOCK,
        'valid': lambda k: bool(_re.match(r'^[A-Za-z0-9_]+$', k)),
        'load': _wiki_load, 'is_ready': _ready, 'ready_extra': _extra,
        'fail_err': _fail, 'total': len(_WIKI_STEPS), 'worker': _wiki_worker,
    }))


def _wiki_index():
    """已缓存的物种清单 {短名: 中文名}（v163：走 _wk_index_scan）"""
    def _zh(kk):
        d = _wiki_load(kk) or {}
        return ((d.get('DATA') or {}).get('zh') or '')
    return _wk_index_scan(WIKI_CACHE_DIR, _zh, 'species')



# ===================== v5740：dododex 玩家技巧（前端「技巧」TAB） =====================
# 设计要点：
#   · dododex 无 CF 拦截（实测普通 UA 直取 200，与 ark.wiki.gg 的 403 完全不同）
#   · 单页 20 条 tip；分页 /tips/<slug>/2；分类 /tips/<slug>/taming-ko|utility|...
#   · 缓存独立于 wiki 缓存、自带 _ts 做 30 天 TTL —— **不参与 _WIKI_PARSE_VER 判定**
#     （升 _WIKI_PARSE_VER 会让全部 557 个物种的 wiki 缓存失效重抓，代价极大；
#       本轮未改 wiki 解析逻辑，故刻意不升）
#   · 翻译不在后端做：前端复用「大肥鱼」AI 模块自带的 token 配置（lbAiCfgGet），
#     翻完 POST 回写中文映射，按 tip id 合并、已存在不覆盖 ⇒ 一个人翻过，所有人秒开
DODO_ROOT = 'https://www.dododex.com'
DODO_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
           '(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36')
DODO_TTL = 30 * 86400            # 缓存 30 天
DODO_PAGES = 2                   # 最多抓 2 页（约 40 条原始）
DODO_KEEP_CAT = ('taming-ko', 'utility', 'encountering')   # 丢弃 funny/opinion/stories/name-ideas
DODO_MIN_POINTS = 100            # 低赞多是「我朋友笑了」这类废话
DODO_MIN_LEN = 60                # 过短无信息量
DODO_TOP_N = 15                  # 单物种最多 15 条
DODO_LOG_TTL = 6 * 3600          # 抓取失败后 6 小时内不再重试（别反复打人家站）

_DODO_CAT_ZH = {
    'taming-ko': u'驯服·击晕', 'utility': u'实用', 'encountering': u'遭遇',
    'funny': u'搞笑', 'opinion': u'观点', 'stories': u'故事', 'name-ideas': u'起名',
}

# 单条 tip 的正则 —— 结构取自 2026-10-31 实抓的原始 HTML，改前必须先 dump 原文核对
_DODO_TIP_RE = _re.compile(
    r'<div class="lightbox marginBottom row aifs tip" data-tipid="(\d+)">'
    r'.*?<span class="pill">.*?</i>\s*([\d,]+)\s*point'
    r'.*?<a class="pill noDec" href="/tips/[^/"]+/([a-z\-]+)">([^<]+)</a>'
    r'.*?<time datetime="([^"]+)"'
    r'.*?<div class="tipText lh">(.*?)</div>',
    _re.S)

# dododex 自家 AI 汇总（页面顶部「Dododex users say: …」一段连贯玩法摘要）
_DODO_SUM_RE = _re.compile(r'Dododex users say:</div>\s*<div>(.*?)</div>', _re.S)


_DODO_SLUGS = None


def _dodo_slugs():
    """dododex 权威 slug 表（247 条，2026-10-31 从 dododex.com/sitemap.xml 的 /taming/ 提取）"""
    global _DODO_SLUGS
    if _DODO_SLUGS is not None:
        return _DODO_SLUGS
    _DODO_SLUGS = set()
    obj, p = _wk_json_load(['dodo_slugs.json'],
                           pick=lambda o: (o.get('slugs') if isinstance(o, dict) else o) or [])
    for s in (obj or []):
        s = str(s or '').strip().lower()
        if s:
            _DODO_SLUGS.add(s)
    if p:
        print('[dodo] slugs loaded %d from %s' % (len(_DODO_SLUGS), p))
    return _DODO_SLUGS


_DODO_NORM = None


def _dodo_norm_map():
    """dododex slug 的归一化索引 {纯小写字母数字: 原 slug}，供 en_map 英文名比对用"""
    global _DODO_NORM
    if _DODO_NORM is not None:
        return _DODO_NORM
    _DODO_NORM = {}
    for s in _dodo_slugs():
        n = _re.sub(r'[^a-z0-9]', '', s)
        if n and n not in _DODO_NORM:
            _DODO_NORM[n] = s
    return _DODO_NORM


def _dodo_slug(key):
    """物种键 -> dododex slug（**必须命中 dododex 权威表**，否则 tips 页 404）

    2026-10-31 实测教训（踩过）：
      · dododex 用**英文全名** —— ankylosaurus / argentavis / tusoteuthis / doedicurus，
        不是社区短名（ankylo / argy / tuso / doed）；
      · 项目 dino_en_map 里是带空格的俗名，且拼写有误（Rex -> 'Tyranosaurus Rex'）⇒
        直接拿它归一化会得到 `tyranosaurus-rex`，实测 404；
      · wikily 与 dododex 命名高度一致（557 ∩ 247 = **188 条**），
        故正解是走项目成熟的 `_wiki_slug_cands()`（wikily 白名单候选链）做桥梁。
    """
    k = str(key or '').strip()
    if not k:
        return ''
    ds = _dodo_slugs()
    kl = k.lower()
    # ① 已是 dododex slug（前端传 wikily slug / 已命中的类名时走这里）
    if kl in ds:
        return kl
    # ② 走 wikily slug 候选链：类名 -> 短名 -> en_map/alias -> wikily 白名单命中
    cands = []
    if ds:
        try:
            cands = [str(c or '').strip().lower() for c in _wiki_slug_cands(k)]
            for c in cands:
                if c and c in ds:
                    return c
        except Exception:
            cands = []
    # ③ en_map / alias 的英文名归一化后与 dododex 表**精确**比对
    #    实例：Ankylo -> 'Ankylosaurus'（dododex ankylosaurus）/ Tuso -> 'Tusoteuthis' /
    #          Dolphin -> 'Ichthyosaurus' / BionicRex -> 'Tek Rex'（dododex tek-rex）
    base = k
    for suf in ('_ASA', '_C'):
        if base.endswith(suf):
            base = base[:-len(suf)]
    if base.endswith('_Character_BP'):
        base = base[:-len('_Character_BP')]
    nm = _dodo_norm_map()
    if nm:
        names = []
        try:
            em = _wiki_en_map() or {}
            al = _wiki_alias() or {}
            for x in (em.get(base), em.get(k), al.get(base), al.get(k), base):
                if x:
                    names.append(str(x))
            # 变体前缀剥离：dododex **没有** Tek/Bionic/Aberrant 等变种的独立 tips 页
            #   （实测 247 条表里无 tek-rex），技巧与普通种通用 ⇒ 回退查普通种
            for _pre in ('Bionic', 'Tek', 'Aberrant', 'Corrupted', 'Enraged', 'Astral',
                         'Ghost', 'Skeletal', 'Brute', 'Alpha', 'Beta', 'Gamma', 'Mega',
                         'Primal', 'Celestial', 'Elder', 'Infused'):
                if base.startswith(_pre) and len(base) > len(_pre):
                    names.append(base[len(_pre):])
        except Exception:
            names.append(base)
        for s0 in names:
            n0 = _re.sub(r'[^a-z0-9]', '', s0.lower())
            if n0 and n0 in nm:
                return nm[n0]
        # ④ 前缀模糊：候选与 dododex 表互为前缀（ankylo -> ankylosaurus / tuso -> tusoteuthis）
        for s0 in (names + cands):
            n0 = _re.sub(r'[^a-z0-9]', '', str(s0).lower())
            if len(n0) < 4:
                continue
            hit = [v for k2, v in nm.items() if k2.startswith(n0) or n0.startswith(k2)]
            if hit:
                hit.sort(key=len)
                return hit[0]
    # ⑤ 仍未命中：退回朴素转换（大概率 404，由上层降级成「dododex 暂未收录」）
    return _re.sub(r'[^A-Za-z0-9]+', '-', base).strip('-').lower()


def _dodo_fetch_page(url, timeout=25):
    """dododex 专用抓取（独立 UA/语言头；带 gzip 解压兜底）"""
    import urllib.request as _u
    req = _u.Request(url, headers={
        'User-Agent': DODO_UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip',
    })
    r = _u.urlopen(req, timeout=timeout)
    raw = r.read()
    try:
        if 'gzip' in (r.headers.get('Content-Encoding') or '').lower():
            import gzip as _gz
            raw = _gz.decompress(raw)
    except Exception:
        pass
    return raw.decode('utf-8', 'replace')


def _dodo_parse(html):
    """解析一页 tips -> (items[], summary)"""
    items, seen = [], set()
    for m in _DODO_TIP_RE.finditer(html or ''):
        tid, pts, cat, catraw, dt, raw = (m.group(1), m.group(2), m.group(3),
                                         m.group(4), m.group(5), m.group(6))
        if tid in seen:
            continue
        seen.add(tid)
        try:
            p = int(_re.sub(r'[^0-9]', '', pts) or 0)
        except Exception:
            p = 0
        txt = _wiki_strip(raw)
        if not txt:
            continue
        items.append({
            'id': tid,
            'points': p,
            'cat': cat,
            'catZh': _DODO_CAT_ZH.get(cat, cat),
            'catRaw': _wiki_strip(catraw),
            'date': (dt or '')[:10],
            'text': txt,
        })
    sm = ''
    ms = _DODO_SUM_RE.search(html or '')
    if ms:
        sm = _wiki_strip(ms.group(1))
    return items, sm


def _dodo_pick(items):
    """过滤 + 排序 + 截断（高赞优先，同分按日期新者优先）"""
    keep = []
    for x in (items or []):
        if x.get('cat') not in DODO_KEEP_CAT:
            continue
        if int(x.get('points') or 0) < DODO_MIN_POINTS:
            continue
        if len(str(x.get('text') or '')) < DODO_MIN_LEN:
            continue
        keep.append(x)
    keep.sort(key=lambda x: str(x.get('date') or ''), reverse=True)   # 先按日期新->旧
    keep.sort(key=lambda x: -int(x.get('points') or 0))                # 再按赞数稳定排序
    return keep[:DODO_TOP_N]


def _dodo_fetch(slug):
    """抓 dododex 前 N 页 -> (全部原始 items, summary)"""
    allitems, summary = [], ''
    for i in range(DODO_PAGES):
        url = DODO_ROOT + '/tips/' + slug + ('' if i == 0 else ('/%d' % (i + 1)))
        try:
            html = _dodo_fetch_page(url, 25)
        except Exception as e:
            _wiki_log('dodo fetch fail %s p%d: %s' % (slug, i, str(e)[:120]))
            break
        its, sm = _dodo_parse(html)
        if sm:
            summary = sm
        if not its:
            break
        allitems.extend(its)
    seen, ded = set(), []
    for x in allitems:
        if x['id'] in seen:
            continue
        seen.add(x['id'])
        ded.append(x)
    return ded, summary


def _dodo_cache_path(slug, zh=False):
    return os.path.join(WIKI_CACHE_DIR, 'dodo_%s%s.json' % (slug, '_zh' if zh else ''))


def _dodo_read(slug, zh=False):
    p = _dodo_cache_path(slug, zh)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, 'r', encoding='utf-8') as f:
            return json.loads(f.read())
    except Exception:
        return None


def _dodo_write(slug, obj, zh=False):
    try:
        os.makedirs(WIKI_CACHE_DIR, exist_ok=True)
        p = _dodo_cache_path(slug, zh)
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(json.dumps(obj, ensure_ascii=False, separators=(',', ':')))
        os.replace(tmp, p)
        return True
    except Exception as e:
        print('[dodo] save fail: ' + str(e)[:120])
        return False


def _dodo_get(key, force=False):
    """取某物种的技巧（带 30 天缓存；失败退避 6 小时）"""
    slug = _dodo_slug(key)
    if not slug:
        return {'ok': False, 'err': 'no-slug', 'items': [], 'summary': ''}
    c = _dodo_read(slug)
    now = int(time.time())
    fresh = bool(c) and (now - int(c.get('_ts') or 0) < DODO_TTL)
    if force or not fresh:
        # 失败退避：上次抓取失败且未到 6 小时，直接用旧缓存（没有就返回空）
        if (not force) and c and c.get('_failTs') and (now - int(c.get('_failTs') or 0) < DODO_LOG_TTL):
            return {'ok': True, 'slug': slug, 'ts': c.get('_ts'), 'stale': True,
                    'summary': c.get('summary') or '', 'rawN': c.get('rawN') or 0,
                    'items': c.get('items') or []}
        its, sm = _dodo_fetch(slug)
        if its:
            c = {'_ts': now, 'slug': slug, 'summary': sm,
                 'rawN': len(its), 'items': _dodo_pick(its)}
            _dodo_write(slug, c)
        else:
            _wiki_log('dodo empty %s (raw items=0)' % slug)
            if c:
                c['_failTs'] = now
                _dodo_write(slug, c)
                return {'ok': True, 'slug': slug, 'ts': c.get('_ts'), 'stale': True,
                        'summary': c.get('summary') or '', 'rawN': c.get('rawN') or 0,
                        'items': c.get('items') or []}
            return {'ok': False, 'slug': slug, 'err': 'fetch',
                    'items': [], 'summary': '', 'note': u'dododex 暂未收录该物种的技巧'}
    return {'ok': True, 'slug': slug, 'ts': c.get('_ts'),
            'summary': c.get('summary') or '', 'rawN': c.get('rawN') or 0,
            'items': c.get('items') or []}


def _dodo_zh_doc(key):
    """整份中文缓存文档：{'map': {tipId: 译文}, 'merged': {secs:[{h,t}]}}"""
    slug = _cache_slug(key)   # v5871：按变体隔离（飞龙 _Ice/_Fire 不再共用 merged）
    return (_dodo_read(slug, zh=True) or {}), slug


def _dodo_zh_map(key):
    slug = _cache_slug(key)   # v5871：按变体隔离
    z = _dodo_read(slug, zh=True) or {}
    return (z.get('map') or {}), slug


def _dodo_zh_merge(key, pairs, merged=None, force=False):
    """前端回写中文。

    · pairs  = 逐条译文 [{id, text}] —— 已存在的不覆盖（多客户端并发安全）
    · merged = 整合后的攻略长文 {'secs': [{'h': 标题, 't': 正文}]}
              —— v5742 新增。整篇只**写一次**（已有则不覆盖），保证所有人看到同一份。
    """
    slug = _cache_slug(key)   # v5871：回写也要按变体隔离
    if not slug:
        return 0
    z = _dodo_read(slug, zh=True) or {}
    m = z.get('map') or {}
    n = 0
    for it in (pairs or []):
        if not isinstance(it, dict):
            continue
        tid = str(it.get('id') or '').strip()
        tx = str(it.get('text') or '').strip()
        if (not tid) or (not tx) or (tid in m):
            continue
        m[tid] = tx[:2000]
        n += 1
    # 长文：校验结构后写入。
    # v5754（用户报「长文里 juvenile/Tek/Alpha/boss 又回来了」）：
    #   原实现 secs 是「只写一次」，pv 只覆盖 auth ⇒ prompt 升级后长文永远停在最老那版。
    #   现改为：**secs 与 auth 共用同一个 pv 门槛** —— 旧缓存无该字段，或 pv 变大，才允许覆盖。
    if isinstance(merged, dict):
        _pv_new = merged.get('pv') if isinstance(merged.get('pv'), int) else 0
        _mg_old = z.get('merged') if isinstance(z.get('merged'), dict) else {}
        _pv_old = _mg_old.get('pv') if isinstance(_mg_old.get('pv'), int) else 0
        _upg = (_pv_new > _pv_old) or bool(force)   # v5768：重新整理时可强制覆盖
        secs = merged.get('secs')
        if isinstance(secs, list) and secs and ((not (_mg_old.get('secs') or [])) or _upg):
            clean = []
            for s in secs[:12]:
                if not isinstance(s, dict):
                    continue
                hh = str(s.get('h') or '').strip()[:60]
                tt = str(s.get('t') or '').strip()[:6000]
                if tt:
                    clean.append({'h': hh, 't': tt})
            if clean:
                _mm = dict(_mg_old)
                _mm['secs'] = clean
                if _pv_new:
                    _mm['pv'] = _pv_new
                _mm['ts'] = int(time.time())
                z['merged'] = _mm
                _mg_old = _mm
                n += 1
        # v5748：原文权威要点（技巧 TAB 置顶块）
        # v5750：pv 变大时允许覆盖旧 auth（prompt/数据源升级后自动刷新）
        auth = merged.get('auth')
        _has_old = bool(_mg_old.get('auth') or [])
        if isinstance(auth, list) and auth and ((not _has_old) or _upg):
            _a = []
            for s in auth[:12]:
                tx = str(s or '').strip()[:1200]
                if tx:
                    _a.append(tx)
            if _a:
                _mm = dict(_mg_old)
                _mm['auth'] = _a
                if _pv_new:
                    _mm['pv'] = _pv_new
                _mm['ts'] = int(time.time())
                z['merged'] = _mm
                n += 1
    if n:
        z['_ts'] = int(time.time())
        z['slug'] = slug
        z['map'] = m
        _dodo_write(slug, z, zh=True)
    return n


# ===================== v5745：wikily 原文整理（按物种共享缓存） =====================
# 背景（用户 2026-10-31 口径）：
#   「原文案 通过 AI整理归纳后，再重新分配到 各个TAB里」+「原样搬，但是只包括 wikily 取的」
#   ⇒ 素材仅限后端从 wikily 抓来的 6 类描述，项目自己写的 UI 提示不参与。
#   「原文案 和 技巧 完全独立处理，互不干涉」⇒ 与 dodo_* 缓存完全隔离，各存各的。
# 6 类素材：OVERVIEW.intro / OVERVIEW.tips / HOME.tameIntro / BREED_DESC / ABIL.skills[].desc / SPAWN.intro
# 因每个物种的原文都不同 ⇒ **按物种存**，一次整理全服共享。
_WT_LOCK = threading.Lock()
# v5746：`ovTips`（原概览·技巧·原文要点）已改归「技巧」线（喂进技巧整合，见前端 lbTipsDigest），
#   不再由本模块整理
# v5780（用户口径「我发现了 根源是你漏了置顶正文都应该 AI 整理」）：补 `gatherIntro`（采集 Tab 置顶正文）。
#   后端此前**已经解析出** gatherIntro（见 _WIKI_PAGES 里的 ('gatherIntro', u'采集能力', (12,600))），
#   但没列进本元组 ⇒ 整理结果被 _wt_write 的 clean 白名单直接丢弃，前端永远拿不到。
# v5781（用户口径「置顶正文都应该 AI 整理」）：补 harvestIntro / abilIntro / expIntro 三个 Tab 的置顶正文。
#   至此 9 个 Tab 中 8 个走本模块（技巧走 dodo 独立管道）：
#     概览 ovIntro · 驯服 tameIntro · 繁殖 breedDesc · 采集 gatherIntro · 收割 harvestIntro
#     技能 abilIntro + abil · 经验 expIntro · 生成 spawnIntro
_WT_BLOCKS = ('ovIntro', 'tameIntro', 'gatherIntro', 'harvestIntro', 'abilIntro', 'expIntro',
              'breedDesc', 'abil', 'spawnIntro', 'gearTips')


_WT_VAR_RE = _re.compile(r'_character_bp_([a-z0-9]+)_c$', _re.I)


def _wt_variant(key):
    """v5871：从物种类名抽变体后缀：Wyvern_Character_BP_Fire_C -> 'fire'；无变体 -> ''"""
    m = _WT_VAR_RE.search(str(key or '').strip())
    if not m:
        return ''
    v = m.group(1).lower()
    return '' if v in ('', 'c') else v


def _cache_slug(key):
    """v5871（用户口径「火焰飞龙 wiki 为啥显示的是寒冰飞龙的数据」）：

    **AI 整理类缓存的文件名应用键** = dododex slug + 变体后缀。
    原因：飞龙三姐妹（寒冰/火焰/毒素）在 dododex 上同属 `wyvern` 一个 slug
      ⇒ `wikitext_wyvern.json` / `dodo_wyvern_zh.json` 被三个物种共用，谁先整理另外两个就读到谁的内容。
    只用于「AI 整理结果」类缓存（wikitext_* / dodo_*_zh）；
      原始英文心得 `dodo_<slug>.json` **保持共用**（dododex 上本就是同一页）。
    """
    sg = _dodo_slug(key)
    if not sg:
        return ''
    v = _wt_variant(key)
    return (sg + '_' + v) if v else sg


def _wt_path(slug):
    return os.path.join(WIKI_CACHE_DIR, 'wikitext_%s.json' % slug)


def _wt_read(slug):
    """返回该物种已整理的原文（无则 None）"""
    if not slug:
        return None
    p = _wt_path(slug)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, 'r', encoding='utf-8') as f:
            return json.loads(f.read())
    except Exception:
        return None


def _wt_flat_item(x):
    """v5838：把 AI 整理结果里的数组元素拍成可读字符串（对象则抽字段值）"""
    if x is None:
        return ''
    if isinstance(x, str):
        return x.strip()
    if isinstance(x, (int, float, bool)):
        return str(x)
    if isinstance(x, dict):
        for _k in ('t', 'text', 'point', 'zh', 'desc', 'title', 'name', 'note', 'n', 'd', 'v', 'k', 'a', 'p'):
            _v = x.get(_k)
            if isinstance(_v, str) and _v.strip():
                return _v.strip()
        _vals = []
        for _k2, _v2 in x.items():
            if isinstance(_v2, str) and _v2.strip():
                _vals.append(_v2.strip())
            elif isinstance(_v2, (int, float, bool)):
                _vals.append(str(_v2))
        return u'：'.join(_vals)
    return ''


def _wt_write(slug, blocks, force=False):
    """写入整理结果 —— **只写一次**（已有则不覆盖），保证全服看到同一份"""
    if (not slug) or (not isinstance(blocks, dict)):
        return 0
    with _WT_LOCK:
        # v5768（用户实测「再次整理后刷新页面还是原来的缓存」）：原逻辑「只写一次」导致
        #   点「重新整理」时新结果被直接丢弃 ⇒ 加 force：前端连点「重新整理」时传 force=true 覆盖
        if os.path.isfile(_wt_path(slug)) and not force:
            return 0
        clean = {}
        for k in _WT_BLOCKS:
            v = blocks.get(k)
            if k == 'abil':
                if isinstance(v, list):
                    arr = []
                    for it in v[:60]:
                        if not isinstance(it, dict):
                            continue
                        zh = str(it.get('zh') or '').strip()[:80]
                        ds = str(it.get('desc') or '').strip()[:3000]
                        if zh and ds:
                            arr.append({'zh': zh, 'desc': ds})
                    if arr:
                        clean['abil'] = arr
            else:
                if isinstance(v, list):
                    # v5838：AI 可能把元素写成对象（{装备:"…", 说明:"…"}）—— 旧代码 str(x) 会存成
                    #   Python repr（"{'装备': '…'}"）或前端已污染的 "[object Object]"。
                    #   这里抽可读文本再存，两种脏数据都不落地。
                    _arr = []
                    for _x in v[:40]:
                        _tx = _wt_flat_item(_x)
                        if _tx and _tx != '[object Object]' and _tx not in _arr:
                            _arr.append(_tx[:3000])
                    if _arr:
                        clean[k] = _arr
        if not clean:
            return 0
        clean['_ts'] = int(time.time())
        clean['slug'] = slug
        try:
            os.makedirs(WIKI_CACHE_DIR, exist_ok=True)
            p = _wt_path(slug)
            tmp = p + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                f.write(json.dumps(clean, ensure_ascii=False, separators=(',', ':')))
            os.replace(tmp, p)
            return len(clean) - 2
        except Exception as e:
            print('[wikitext] write fail: ' + str(e)[:120])
            return 0


WIKI_ITEM_ROOT = 'https://wikily.gg/zh-cn/ark-survival-ascended/items'
WIKI_ITEM_CACHE = os.path.join(WIKI_CACHE_DIR, 'items')
_WIKI_ITEM_MAP = None
_WIKI_ITEM_TASKS = {}
_WIKI_ITEM_LOCK = threading.Lock()
_WIKI_ITEM_STEPS = [('', 'ITEM')]

# 快速信息键（wikily zh 站原文）
_WK_ITEM_QUICK = [u'重量', u'堆栈大小', u'耐久度', u'记忆印痕', 'Craft XP', u'制作时间',
                  u'护甲值', u'伤害', u'使用时间', u'消耗', u'效果持续时间', u'耐久',
                  u'弹药容量', u'装填时间', u'采集倍率',
                  # v244: 补全快速信息键，避免值粘连到下一键
                  'Spoil time', u'腐坏时间', 'Stack size', 'Weight', 'Engram',
                  u'堆叠上限', u'腐烂时间']
# 属性键（wikily 原文英文键）
_WK_ITEM_STAT = [
    'Equip Time', 'Harvest Tool', 'Melee Damage', 'Ammo Per Clip', 'Ammo Per Shot',
    'Infinite Ammo', 'Reload Duration', 'Time Between Shots', 'Durability Per Shot',
    'Durability Per Melee Hit', 'Harvest Resource Multiplier', 'Hit Damage',
    'Armor', 'Durability', 'Hypothermal Insulation', 'Hyperthermal Insulation',
    'Water Capacity', 'Food', 'Health', 'Stamina', 'Oxygen', 'Torpidity',
    'Night Vision', 'FOV', 'Size', 'Weight', 'Decay Time', 'Socket Count',
    'Craft XP', 'Craft Time', 'Stack Size',
    # v288：黏液枪页实测出现 'Melee Damage Impulse0.2Disable On Electric Storm是'
    #   —— 这两个键不在白名单 ⇒ 值被后文吃进上一条 Melee Damage（显示「基础伤害 Impulse0.2Disable...是」）
    'Impulse', 'Disable On Electric Storm',
]


_WIKI_ITEM_SLUGS = None


def _wiki_item_slugs():
    """wikily 全量物品 slug 白名单（v5697：与 _wiki_slugs 同构，来自 sitemap ?part=pages-* -> /items/）"""
    global _WIKI_ITEM_SLUGS
    if _WIKI_ITEM_SLUGS is not None:
        return _WIKI_ITEM_SLUGS
    _WIKI_ITEM_SLUGS = {}
    obj, p = _wk_json_load(['wiki_item_slugs.json'],
                           pick=lambda o: (o.get('slugs') if isinstance(o, dict) else o) or [])
    for x in (obj or []):
        x = str(x or '').strip()
        if not x:
            continue
        n = _re.sub(r'[^a-z0-9]', '', x.lower())
        if n:
            _WIKI_ITEM_SLUGS[n] = x
    if p:
        print('[wiki_item] slugs loaded %d from %s' % (len(_WIKI_ITEM_SLUGS), p))
    return _WIKI_ITEM_SLUGS


def _wiki_item_map():
    """物品类名 -> wikily 真实 slug（v163：走 _wk_json_load 统一加载）"""
    global _WIKI_ITEM_MAP
    if _WIKI_ITEM_MAP is not None:
        return _WIKI_ITEM_MAP
    obj, p = _wk_json_load(['wiki_item_map.json'],
                           pick=lambda o: (o.get('map') if isinstance(o, dict) else o) or {})
    _WIKI_ITEM_MAP = obj if isinstance(obj, dict) else {}
    if p:
        print('[wiki_item] map loaded %d from %s' % (len(_WIKI_ITEM_MAP), p))
    return _WIKI_ITEM_MAP

def _wk_item_camel(cls):
    s = _re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', str(cls))
    s = _re.sub(r'(?<=[A-Z])(?=[A-Z][a-z])', ' ', s)
    return s.replace('_', ' ').strip()


def _wiki_item_cands(cls):
    """物品类名 -> 候选 slug（v5697：映射优先；驼峰兜底走 sitemap 白名单校验，与 _wiki_slug_cands 同构）

    v5697（用户口径「物品映射表、物种映射表的位置方式为啥不一样」）：
      物种侧有 wiki_slugs.json 白名单做候选存在性校验，物品侧此前**没有**白名单，
      驼峰兜底生成的 slug 无从判断对错（实测 1286 条缺口里驼峰兜底只真中 2 条）。
      现在补 wiki_item_slugs.json（2548 条，来自 sitemap /items/），
      兜底候选一律先过白名单，只返回站上真实存在的 slug；白名单缺失时退回旧行为。
    """
    cls = str(cls or '').strip()
    m = _wiki_item_map()
    sn = _wiki_item_slugs()
    out = []
    s = m.get(cls)
    if s:
        out.append(s)
    for n in (_wk_item_camel(cls), cls):
        f = _re.sub(r'[^a-z0-9]+', '-', n.lower()).strip('-')
        if not f or f in out:
            continue
        if sn:
            real = sn.get(_re.sub(r'[^a-z0-9]', '', f))
            if real and real not in out:
                out.append(real)
        else:
            out.append(f)
    return out[:3]


def _wk_item_split_kv(txt, keys):
    """把 'Key1 v1 Key2 v2' 按已知键拆成 [[key, val], ...]"""
    if not txt:
        return []
    pat = '|'.join(_re.escape(k) for k in sorted(keys, key=len, reverse=True))
    if not pat:
        return []
    parts = _re.split('(' + pat + ')', txt)
    out = []
    i = 1
    while i < len(parts):
        k = parts[i]
        v = (parts[i + 1] if i + 1 < len(parts) else '').strip()
        v = _wk_item_val_clean(v)   # v5690
        if v:
            out.append([k, v[:40]])
        i += 2
    return out


def _wk_item_val_clean(v):
    """v5690（用户报「1使用弹药简易步枪子弹信息素镖麻醉镖」看不懂）：
    属性表最后一项会吃掉其后的非属性小节（如「使用弹药」标题 + 子弹列表 + 富文本图）。
    规则：① 遇 HTML 标签即断 ② 值以数字开头 => 只取开头数字段（含 - . ~ x % , 与空格）
    实例：Harvest Resource Multiplier 的 '1使用弹药...' -> '1'
    """
    s = str(v or '')
    if '<' in s:
        s = s.split('<', 1)[0]
    if s[:1] and s[:1] in u'0123456789-+.~':
        m = _re.match(r'^[-+0-9.,~xX%\s]+', s)
        if m:
            s = m.group(0)
    return s.strip()


def _wiki_cjk_space(s):
    """v244: 中文与字母/数字紧邻时插空格，改善阅读（页面标签间无空格）"""
    s = str(s or '')
    s = _re.sub(r'([\u4e00-\u9fa5])([A-Za-z0-9])', r'\1 \2', s)
    s = _re.sub(r'([A-Za-z0-9%])([\u4e00-\u9fa5])', r'\1 \2', s)
    # 数字/百分点后紧跟大写字母（页面标签间无空格：×1-2Lost -> ×1-2 Lost）
    s = _re.sub(r'([0-9x%])([A-Z][a-z])', r'\1 \2', s)
    return _re.sub(r'\s+', ' ', s).strip()


# ===== v287：ARK Wiki 物品「专属按键」抽取 =====
# 背景：wikily 物品页只有数值表格，没有使用/按键章节；
#       ARK Wiki 的 Usage 段才是武器专属操作（黏液枪 Ctrl 采尸体 / R 切黏液 / RMB 蓄力）的来源。
# 约定：这里只抽「键名 token + 项目键名」，中文动作名由前端查项目键位配置，不重复翻译键位。
_ARK_TOKENS = [
    ('lmb',   r'\blmbs?\b|\bleft\s+(?:mouse|click)\b|\bprimary\s+(?:fire|attack)\b', 'mouse_left',         'xbox_rt'),
    ('rmb',   r'\brmbs?\b|\bright\s+(?:mouse|click)\b|\bsecondary\s+(?:fire|attack)\b', 'mouse_right',        'xbox_lt'),
    ('mmb',   r'\bmmbs?\b|\bmiddle\s+(?:mouse|click)\b', 'mouse_middle',       ''),
    ('ctrl',  r'\b(?:left\s+)?ctrl\b',         'keyboard_ctrl_left', 'xbox_rb'),
    ('shift', r'\b(?:left\s+)?shift\b',        'keyboard_shift_left', 'xbox_stick_l_press'),
    ('space', r'\bspace(?:bar)?\b',            'keyboard_space',     'xbox_button_a'),
    ('tab',   r'\btab\b',                      'keyboard_tab',       'xbox_button_view'),
]
# v5817（用户口径「物品中 为啥只有 黏液枪 有指南」根因之一）：
#   原 `alt` 走「裸词」匹配 ⇒ 石头 / 黏土 / 硫磺 / 制式弩等页面正文里的 "alt" 被误命中，
#   凭空长出 keys=['alt'] ⇒ 指南 Tab 出现但内容无意义（实测 45 个缓存物品里 4 个假指南）。
#   改为与单字母同规则：**只在「括号内」或 press/hold/use + Alt 语境里认**（见 _ARK_SINGLE）。
# 单字母键只在「括号内」或「press/use/hold + X」上下文里认，避免 "a" "an" 之类误命中
_ARK_SINGLE = {
    'r': ('keyboard_r', 'xbox_button_x'),
    'e': ('keyboard_e', 'xbox_button_y'),
    'c': ('keyboard_c', 'xbox_stick_r_press'),
    'x': ('keyboard_x', ''),
    'f': ('keyboard_f', 'xbox_button_x'),
    'g': ('keyboard_g', 'xbox_button_y'),
    'q': ('keyboard_q', 'xbox_lb'),
    'z': ('keyboard_z', ''),
    'v': ('keyboard_v', 'xbox_rb'),
    't': ('keyboard_t', ''),
    'alt': ('keyboard_alt_left', ''),
}


def _ark_slug_from(ws):
    """wikily slug（goo-gun）-> ARK Wiki 页名（Goo_Gun）"""
    parts = [x for x in str(ws or '').split('-') if x]
    return '_'.join(p[:1].upper() + p[1:] for p in parts)


def _ark_keys_from_usage(lines):
    """Usage 段纯文本行 -> [{'k','kbm','pad','en'}]（按首次出现顺序）"""
    import re as _re
    out, seen = [], set()
    for ln in lines:
        toks = []
        low = ln.lower()
        for k, pat, _kbm, _pad in _ARK_TOKENS:
            if k not in toks and _re.search(pat, low):
                toks.append(k)
        for m in _re.finditer(r'\(([^()]{0,40})\)', ln):
            for w in _re.split(r'[\s,]+', m.group(1)):
                w = w.strip().lower()
                if w in _ARK_SINGLE and w not in toks:
                    toks.append(w)
        for m in _re.finditer(r'(?:press(?:ing)?|use|using|hold(?:ing)?)\s+(?:the\s+)?([A-Za-z]{1,6})\b', low):
            w = m.group(1)
            if w in _ARK_SINGLE and w not in toks:
                toks.append(w)
        if not toks:
            continue
        for w in toks:
            if w in seen:
                continue
            kv = None
            for k, _pat, kbm, pad in _ARK_TOKENS:
                if k == w:
                    kv = (kbm, pad)
                    break
            if not kv:
                kv = _ARK_SINGLE.get(w, ('', ''))
            seen.add(w)
            out.append({'k': w, 'kbm': kv[0], 'pad': kv[1], 'en': ln[:170]})
    return out[:12]


_WK_ARK_PAGES = None


def _wk_ark_pages():
    """v5851：物种类名 -> wiki.gg 页名。
    载具 / 器械的「操作方法（Controls）」「能力（Utility / Fuel / Basic Info）」
    **wikily 没有**，只有 wiki.gg 有 ⇒ 这张表里列出来的才会去补抓。"""
    global _WK_ARK_PAGES
    if _WK_ARK_PAGES is not None:
        return _WK_ARK_PAGES
    obj, p = _wk_json_load(['wiki_ark_pages.json'],
                           pick=lambda o: (o.get('map') if isinstance(o, dict) and 'map' in o else o) or {})
    _WK_ARK_PAGES = {str(k): str(v) for k, v in (obj or {}).items() if k and v} if isinstance(obj, dict) else {}
    if p:
        print('[wiki] ark pages loaded %d from %s' % (len(_WK_ARK_PAGES), p))
    return _WK_ARK_PAGES


def _ark_vehicle_lines(raw, limit=24):
    """v5851：wiki.gg 载具页的操作方法 / 能力段 -> 文本行

    v5854（用户口径「技能里为啥没取到操作键」根因）：
      v5851 首版把 basic info 也纳入白名单、且按页面顺序取。而 wiki.gg 载具页里
      Basic Info（Acquiring / Structures / Carriable Creatures）**排在 Controls 之前且很长**
      ⇒ limit 额度在 Basic Info 阶段就吃光，Controls 一条都没轮到。
      现改为：去掉 basic info；按 Controls → Utility → Fuel 优先级；每段单独限行。"""
    segs = []
    for t, seg in _ark_h2_segs(raw):
        tt = str(t or '').strip().lower()
        if tt:
            segs.append((tt, seg))
    out = []
    for keys in (('controls', '操作方法', '操作键'),
                 ('utility', '能力', '用途'),
                 ('fuel', '燃料')):
        for tt, seg in segs:
            if not any(tt.startswith(w) for w in keys):
                continue
            n = 0
            for ln in _ark_clean_lines(_ark_flat_lines(seg, 60)):
                s = str(ln or '').strip()
                if len(s) < 3 or len(s) > 200 or s in out:
                    continue
                out.append(s)
                n += 1
                if n >= 14 or len(out) >= limit:
                    break
            if len(out) >= limit:
                return out[:limit]
    return out[:limit]


def _ark_controls(raw, limit=24):
    """v5855：wiki.gg 载具页 Controls 段 -> [{'k': 键名, 'a': 动作}, ...]

    实测来源行（Hover_Skiff）：
      'N - Toggle headlights. Can be toggled via the radial menu, too.'
      'X - Attempt to land and then deploy stilts/ramp.'
      'Hold  Shift - Sprint'   /  'W S - Forward/backward movement'
      'LMB/RMB to toggle Tractor Turret (changing field of view to below the skiff).'
      'Press LMB to let go of a target.'
    """
    import re as _re
    seg = ''
    for t, s in _ark_h2_segs(raw):
        tt = str(t or '').strip().lower()
        if tt.startswith('controls') or tt.startswith(u'操作'):
            seg = s
            break
    if not seg:
        return []
    out, seen = [], set()
    for li in _re.findall(r'<li[^>]*>([\s\S]*?)</li>', seg):
        s = _wiki_strip(li)
        s = _re.sub(r'\s+', ' ', s).strip()
        if (not s) or len(s) > 220:
            continue
        # 去掉前置动词，保留「键 - 动作」或「键 to 动作」
        m = _re.match(r'^(?:Hold|Tap|Press|Held)?\s*([A-Za-z0-9/ ]{1,18}?)\s*[-–—]\s*(.+)$', s)
        if not m:
            m = _re.match(r'^(?:Hold|Tap|Press|Held)?\s*([A-Za-z0-9/]{1,12}?)\s+to\s+(.+)$', s)
        if not m:
            continue
        k = _re.sub(r'\s+', ' ', str(m.group(1) or '')).strip()
        a = str(m.group(2) or '').strip()
        k = k.replace(u'⇧', 'Shift').replace(u'⌥', 'Alt').strip()
        if (not k) or (not a) or len(k) > 16:
            continue
        key = k.lower() + '|' + a.lower()[:40]
        if key in seen:
            continue
        seen.add(key)
        out.append({'k': k, 'a': a[:140]})
        if len(out) >= limit:
            break
    return out


def _ark_usage_lines(raw):
    """ARK Wiki 物品页 -> 使用段纯文本行（v5818：改用 _ark_is_sec 前缀判定，兼容 "Use"）"""
    for t, seg in _ark_h2_segs(raw):
        if _ark_is_sec(t):
            return _ark_flat_lines(seg, 60)
    return []


def _ark_points_from_page(raw, limit=10):
    """v5817（用户口径「物品中 为啥只有 黏液枪 有指南」根治）：ARK Wiki Usage / Notes 段的
    「使用要点」条目 -> [str]

    背景：原 `ark` 只存 keys（键位 token）⇒ 40/45 物品的 Usage 段抽不出键名就整个空掉，
          指南 Tab 直接消失；而 Usage / Notes 段里的**文字要点**（伤害机制、克制对象、
          使用技巧）一直没被利用。这里把它们抽出来，前端「指南」页按要点列表展示。
    """
    import re as _re
    out, seen = [], set()
    for t, seg in _ark_h2_segs(raw):
        if not _ark_is_sec(t):
            continue
        items = _re.findall(r'<li[^>]*>([\s\S]*?)</li>', seg)
        if not items:
            items = _re.findall(r'<p[^>]*>([\s\S]*?)</p>', seg)
        for it in items:
            try:
                s1 = _wiki_strip(it)
            except Exception:
                s1 = _re.sub(r'<[^>]+>', ' ', it)
            s1 = _re.sub(r'\s+', ' ', s1).strip()
            if not (12 <= len(s1) <= 220):
                continue
            k = s1.lower()
            if k in seen:
                continue
            seen.add(k)
            out.append(s1)
            if len(out) >= limit:
                return out
    return out


def _wk_item_mats(raw, self_zh=''):
    """制作材料 -> [[中文名, 数量, slug], ...]

    v292：优先按 <a class="ark-slot" href=".../items/<slug>"> 结构化提取。
      wikily 一侧中文译名与项目不一致（电子元件 vs 项目「电路元件」），靠中文名对齐必断；
      slug 是机器标识，前端据此查项目 LB_ITEM_ZH 得项目译名 + 项目图标。
      页面无链接时回退旧「×N 名称」文本正则（slug 留空）。
    """
    import re as _re
    out = []
    seen = set()
    self_zh = str(self_zh or '').strip()

    def _push(nm, q, slug):
        nm = str(nm or '').strip()
        if not nm or nm in seen or nm == self_zh:
            return
        # v5849（用户实测「金属锭 4,100 被拆成 4 和 ,100金属锭」）：数量先去千分位
        q = str(q).replace(',', '').replace(u'，', '').replace(' ', '').strip()
        try:
            q = int(q)
        except Exception:
            return
        if q <= 0:
            return
        seen.add(nm)
        out.append([nm, q, str(slug or '')])

    if raw:
        for m in _re.finditer(r'<a\b([^>]*)>([\s\S]{0,900}?)</a>', raw, _re.I):
            attrs, body = m.group(1), m.group(2)
            hm = _re.search(r'href="[^"]*?/items/([A-Za-z0-9\-]+)"', attrs)
            if not hm:
                continue
            slug = hm.group(1).lower()
            tm = _re.search(r'title="([^"]{1,40})"', attrs)
            nm = tm.group(1).strip() if tm else ''
            if not nm:
                nm2 = _re.search(u'ark-slot-name[^>]*>([^<]{1,30})<', body)
                nm = nm2.group(1).strip() if nm2 else ''
            qm = _re.search(u'ark-slot-count[^>]*>[^0-9]{0,10}([0-9][0-9,]*)', body)
            if not qm:
                qm = _re.search(u'×\\s*([0-9][0-9,]*)', body)
            _push(nm, (qm.group(1) if qm else 0), slug)
            if len(out) >= 20:
                return out

    txt = _wiki_strip(raw or '')
    _BAD = (u'制作', u'配方', u'工作台', u'经验', u'时间', u'倍率',
            u'计算', u'印痕', u'等级', u'数量', u'品质')
    for m2 in _re.finditer(u'×\\s*([0-9][0-9,]*)\\s*([^\\s×<>0-9,][^\\s×<>]{0,18})', txt):
        nm = m2.group(2).strip()
        if any(b in nm for b in _BAD) or _re.search(r'[0-9]$', nm):
            continue
        _push(nm, m2.group(1), '')
        if len(out) >= 20:
            break
    return out


# ===== v5659：wikily 物品页内嵌「完整掉落表 TSV」解析 =====
#   背景：原实现只解析 `ark-ils-row` / `ark-ils-pick` 的 HTML，而 wikily 服务端只渲染约 10 条
#        （实测金属锭：页面声称 166 箱子来源，HTML 只拿到 9 个 crate，缺失 86%）。
#   实测：页面 RSC payload 里内嵌了完整 TSV（金属锭 168 行 / 黏液枪 136 行，与页面计数吻合）。
#   列结构（\t 分隔）：
#     序号 / crate类名 / 地图slug / 类型(supply|cave|mission|horde) / 箱子等级 / (空) /
#     掉落表名 / 概率(0~1) / 品质(英文) / 评分下限 / 评分上限 / (空) / (空)
# =====
_WK_OFF_MAPS = {
    'theisland', 'scorchedearth', 'aberration', 'extinction', 'ragnarok', 'valguero',
    'lostcolony', 'genesis', 'genesisocean', 'astraeos', 'thecenter',
    'crystal-isles', 'crystal_isles', 'crystal', 'fjordur',
}
# 同一张图的陆地/海洋分区合并（wikily 拆成两个 slug，对玩家是同一张图）
_WK_MAP_MERGE = {'genesisocean': 'genesis'}

_WK_TSV_RE = None


def _wk_loot_tsv(raw):
    """解析物品页 RSC 里的完整掉落表 TSV → {crate: {...}}"""
    global _WK_TSV_RE
    if not raw:
        return {}
    import re as _re
    if _WK_TSV_RE is None:
        _WK_TSV_RE = _re.compile(
            r'(?<![0-9])(\d{1,4})\\t([A-Za-z0-9_]{6,80})\\t([a-z0-9\-]{3,24})\\t([a-z]{3,10})'
            r'\\t(-?\d{1,3})\\t[^\\]*\\t([A-Za-z0-9_]*)\\t([0-9.eE\-]+)\\t([A-Za-z]*)'
            r'\\t([0-9.eE\-]*)\\t([0-9.eE\-]*)')
    out = {}
    try:
        it = _WK_TSV_RE.finditer(raw)
    except Exception:
        return {}
    for m in it:
        crate = m.group(2)
        slug = (m.group(3) or '').lower()
        typ = m.group(4)
        lvl = m.group(5)
        q = m.group(8) or ''
        rmin = m.group(9) or ''
        rmax = m.group(10) or ''
        try:
            chance = float(m.group(7))
        except Exception:
            chance = 0.0
        d = out.get(crate)
        if d is None:
            d = out[crate] = {'crate': crate, 'type': typ, 'lvl': lvl, 'maps': [],
                              'chance': 0.0, 'q': '', 'rmin': '', 'rmax': ''}
        if slug and slug not in d['maps']:
            d['maps'].append(slug)
        # 概率只认官方图（Mod 图的概率不代表本服）
        if slug in _WK_OFF_MAPS and chance > d['chance']:
            d['chance'] = chance
        if not d['q'] and q:
            d['q'] = q
        if not d['rmin'] and rmin:
            d['rmin'] = rmin
            d['rmax'] = rmax
    return out


def _wk_tsv_tags(crate):
    """从类名恢复难度/环境 tag（TSV 本身不带 tags）"""
    s = crate or ''
    t = []
    if 'Alpha' in s:
        t.append(u'阿尔法')
    elif 'Beta' in s:
        t.append(u'贝塔')
    elif 'Gamma' in s:
        t.append(u'伽马')
    for k, v in (('Legendary', 'Legendary'), ('Hard', u'困难'), ('Medium', u'中等'), ('Easy', u'简单')):
        if k in s:
            t.append(v)
            break
    if 'Double' in s:
        t.append('Double')      # 前端 v5636 已显式剔除
    return t[:4]


def _wk_loot_rows(seg, raw=''):
    """战利品来源明细（wikily「在战利品箱中找到」段）

    返回 [{'k':精选标签, 'crate':箱子类名, 'name':英文箱名, 'tags':[难度/环境],
           'map':地图文本, 'lvl':等级, 'q':品质, 'qr':品质范围, 'chance':概率%}, ...]

    v301 说明：wikily 只在服务端渲染约 10 条（精选 3 条 ark-ils-pick + 「任务」组 6 条
    ark-ils-row + 其他来源 1 条），其余 120+ 条要点「显示全部」异步加载，静态抓取取不到。
    因此本字段是「可得的明细」，全量数量由 lootSum 提供，前端据此标注「共 N 条」。
    """
    import re as _re
    out = []
    seen = set()

    # v5659：**优先走内嵌完整 TSV**（HTML 只渲染约 1/6，见文件头说明）
    _tsv = _wk_loot_tsv(raw)
    if _tsv:
        # v5660：剔除 Double/double 变体 —— 与基础箱同名同概率，会渲染成两条一模一样的行
        #   仅当该「基名」只剩 Double 版时才保留（防误删独有箱子）
        def _wk_nod(c):
            return _re.sub(r'[_\-]?double$', '', str(c).lower())
        _base_has = set()
        for _c in _tsv:
            if 'double' not in _c.lower():
                _base_has.add(_wk_nod(_c))
        for _crate, _d in _tsv.items():
            if 'double' in _crate.lower() and _wk_nod(_crate) in _base_has:
                continue
            _maps = []
            for _s in _d['maps']:
                _s2 = _WK_MAP_MERGE.get(_s, _s)
                if _s2 not in _maps:
                    _maps.append(_s2)
            _off = [x for x in _maps if x in _WK_OFF_MAPS]
            _qr = ''
            if _d['rmin']:
                try:
                    _qr = u'%.1f~%.1f' % (float(_d['rmin']), float(_d['rmax']))
                except Exception:
                    _qr = ''
            out.append({
                'k': '',
                'crate': _crate,
                'name': '',
                'tags': _wk_tsv_tags(_crate),
                'map': '',
                'mapSlug': (_off[0] if _off else (_maps[0] if _maps else '')),
                'maps': _maps,
                'offMaps': _off,
                'lvl': _d['lvl'],
                'q': _d['q'],
                'qr': _qr,
                'chance': round(_d['chance'] * 100.0, 3) if _d['chance'] else 0.0,
                'type': _d['type'],
            })
        out.sort(key=lambda r: (-(r.get('chance') or 0), r.get('crate') or ''))
        return out[:220]

    if not seg:
        return out

    def _txt(x):
        t = _re.sub(r'<[^>]+>', ' ', x or '')
        return _re.sub(r'\s+', ' ', t).strip()

    for m in _re.finditer(r'<a class="ark-ils-(pick|row)"([\s\S]{0,1400}?)</a>', seg):
        body = m.group(2)
        hm = _re.search(r'crate=([A-Za-z0-9_]+)', body)
        crate = hm.group(1) if hm else ''
        # v5645（Bug 修复）：wikily 每个掉落行（含精选 pick 行）的 href 自带 ?map=<slug>，
        #   这是**权威地图归属**；此前只抓 crate 未抓 map ⇒ 前端只能靠类名猜，多数箱子无地图图标。
        msm = _re.search(r'[?&]map=([A-Za-z0-9_\-]+)', body)
        map_slug = msm.group(1).lower() if msm else ''
        nm = _re.search(r'ark-ils-name">([^<]*)<', body)
        name = _txt(nm.group(1)) if nm else ''
        if not crate and not name:
            continue
        key = crate or name
        if key in seen:
            continue
        seen.add(key)

        tags = [_txt(t) for t in _re.findall(r'ark-ils-tag"[^>]*>([^<]*)<', body) if _txt(t)]
        pk = _re.search(r'ark-ils-pick-k">([^<]*)<', body)
        mp = _re.search(r'ark-ils-pick-map">([\s\S]{0,120}?)</span>', body)
        lvl = _re.search(r'ark-ils-lvl">([^<]*)<', body)
        q = _re.search(r'ark-ils-q"[^>]*>(?:<b[^>]*>)?([^<]*)<', body)
        qr = _re.search(r'<small>([^<]*)</small>', body)
        ch = _re.search(r'ark-ils-(?:pick-)?chance"[^>]*>(?:\s*<b>)?\s*([0-9]+(?:\.[0-9]+)?)', body)
        # pick 行的等级/品质在 ark-ils-pick-stats 的裸 <span> 里（与 row 行的 class 不同）
        if not lvl:
            lvl = _re.search(u'<span>\\s*等级\\s*([^<]*)</span>', body)
        if not q:
            q = _re.search(u'<span[^>]*>\\s*最多\\s*([^<]*)</span>', body)
        # 精选标签中文化（wikily 中文站只译了 Highest chance，另两个仍是英文）
        kw = _txt(pk.group(1)) if pk else ''
        kw = {'Best quality': u'最好品质', 'Lowest level': u'最低等级',
              'Highest chance': u'最高概率'}.get(kw, kw)

        maptxt = _txt(mp.group(1)) if mp else ''
        out.append({
            'k': kw,
            'crate': crate,
            'name': name[:40],
            'tags': tags[:4],
            'map': maptxt[:40],
            'mapSlug': map_slug,
            'lvl': _txt(lvl.group(1)).replace(u'等级', '').strip() if lvl else '',
            'q': _txt(q.group(1)).replace(u'最多', '').strip() if q else '',
            'qr': _txt(qr.group(1)).replace(u'品质', '').strip() if qr else '',
            'chance': float(ch.group(1)) if ch else 0.0,
        })
    return out[:30]


def _wiki_item_parse(raw):
    """物品页解析：h1 中文名 / GFI / 快速信息 / 制作材料 / 属性 / 品质倍率表"""
    clean = _re.sub(r'<!--.*?-->', '', raw or '', flags=_re.S)
    out = {'zh': '', 'gfi': '', 'quick': [], 'mats': [], 'attrs': [],
           'quality': {'cols': [], 'rows': []}, 'loot': '',
           # v240: desc / kick / tags / station / effects / same / loot* (文案与扩展)
           'desc': '', 'kick': '', 'tags': [], 'station': [], 'effects': [],
           'same': [], 'lootSum': '', 'lootTop': [], 'lootMap': [], 'lootKind': [],
           'lootRows': [],
           # v287：ARK Wiki 专属按键/使用段（wikily 没有按键章节，只能从这里取）
           'ark': {}}

    m = _re.search(r'<h1[^>]*>([\s\S]{0,400}?)</h1>', clean)
    if m:
        out['zh'] = _wiki_strip(m.group(1))[:40]

    m = _re.search(r'<code[^>]*class="ark-code"[^>]*>([\s\S]{0,200}?)</code>', clean)
    if m:
        out['gfi'] = _wiki_strip(m.group(1))[:120]
    else:
        m = _re.search(r'((?:admin)?cheat\s+gfi\s+[A-Za-z0-9_]+[^<\n]{0,30})', clean, _re.I)
        if m:
            out['gfi'] = m.group(1).strip()[:120]

    # 快速信息
    seg = _wiki_strip(_wiki_h2seg_like(clean, u'快速信息', 8000))
    if not seg:
        seg = _wiki_strip(_wiki_h2seg_like(clean, 'Quick Info', 8000))
    out['quick'] = _wk_item_split_kv(seg, _WK_ITEM_QUICK)

    # 制作材料（v292：结构化提取，见 _wk_item_mats —— 元素为 [名称, 数量, wikily slug]）
    rraw = _wiki_h2seg_like(clean, u'制作配方', 20000)
    if not rraw:
        rraw = _wiki_h2seg_like(clean, 'Crafting', 20000)
    out['mats'] = _wk_item_mats(rraw, out.get('zh') or '')

    # 属性
    aseg = _wiki_strip(_wiki_h2seg_like(clean, u'武器属性', 12000))
    if not aseg:
        aseg = _wiki_strip(_wiki_h2seg_like(clean, u'属性', 12000))
    if not aseg:
        aseg = _wiki_strip(_wiki_h2seg_like(clean, 'Stats', 12000))
    out['attrs'] = _wk_item_split_kv(aseg, _WK_ITEM_STAT)

    # 战利品箱（获取 tab）
    lseg = _wiki_strip(_wiki_h2seg_like(clean, u'战利品箱', 12000))
    if not lseg:
        lseg = _wiki_strip(_wiki_h2seg_like(clean, 'Loot', 12000))
    out['loot'] = lseg[:800]

    # 品质倍率表
    for tb in _re.findall(r'<table[^>]*>([\s\S]*?)</table>', clean):
        _thd = _re.search(r'<thead[^>]*>([\s\S]*?)</thead>', tb)
        ths = [_wiki_strip(x) for x in _re.findall(r'<th[^>]*>([\s\S]*?)</th>', (_thd.group(1) if _thd else tb))]
        if not ths:
            continue
        if ths[0] not in ('Quality', u'品质', u'品\u8d28'):
            continue
        cols = [x for x in ths[1:] if x][:8]
        rows = []
        for r2 in _re.findall(r'<tr[^>]*>([\s\S]*?)</tr>', tb):
            th0 = _re.findall(r'<th[^>]*>([\s\S]*?)</th>', r2)
            tds = [_wiki_strip(x) for x in _re.findall(r'<td[^>]*>([\s\S]*?)</td>', r2)]
            if th0 and tds:
                rows.append({'name': _wiki_strip(th0[0])[:20], 'vals': tds[:8]})
        if cols and rows:
            out['quality'] = {'cols': cols, 'rows': rows[:8]}
            break

    # ===== v240: 文案与扩展数据 =====
    # ① 一句话描述（页面顶部引言）
    m = _re.search(r'<p[^>]*class="[^"]*ark-quote[^"]*"[^>]*>([\s\S]{0,800}?)</p>', clean)
    if m:
        out['desc'] = _wiki_strip(m.group(1))[:300]

    # ② 分类 / 等级（页面顶部小字）
    m = _re.search(r'<p[^>]*class="[^"]*ark-kicker[^"]*"[^>]*>([\s\S]{0,500}?)</p>', clean)
    if m:
        out['kick'] = _wiki_strip(m.group(1))[:60]

    # ③ 标签（武器 / 铁匠台 / 有品质 / 蓝图）
    m = _re.search(r'<ul[^>]*class="[^"]*ark-tags[^"]*"[^>]*>([\s\S]{0,900}?)</ul>', clean)
    if m:
        _TAGMAP = {'Player Inventory': u'玩家背包', 'Has quality': u'有品质',
                   'Blueprint': u'蓝图', 'Weapon': u'武器', 'Resource': u'资源',
                   'Structure': u'结构物', 'Consumable': u'消耗品', 'Armor': u'护甲'}
        for li in _re.findall(r'<li[^>]*>([\s\S]*?)</li>', m.group(1)):
            t = _wiki_strip(li)[:20]
            t = _TAGMAP.get(t, t)
            if t and t not in out['tags']:
                out['tags'].append(t)
        out['tags'] = out['tags'][:8]

    flat = _wiki_strip(clean)

    # ④ 制作工作台
    m = _re.search(r'Available crafting stations:\s*([^.<]{2,160})', flat)
    if not m:
        m = _re.search(r'可用制作工作台[：:]\s*([^.<]{2,160})', flat)
    if m:
        _STMAP = {'Player Inventory': u'玩家背包', 'Smithy': u'铁匠台',
                  'Tek Replicator': u'泰克复制器', 'Campfire': u'篝火'}
        for s2 in _re.split(u'[,，]', m.group(1)):
            s2 = s2.strip()[:20]
            s2 = _STMAP.get(s2, s2)
            if s2 and s2 not in out['station']:
                out['station'].append(s2)
        out['station'] = out['station'][:6]

    # ⑤ 属性效果
    eseg = _wiki_strip(_wiki_h2seg_like(clean, u'属性效果', 8000))
    if not eseg:
        eseg = _wiki_strip(_wiki_h2seg_like(clean, 'Stat effects', 8000))
    if eseg:
        # v244: 按「键：」出现位置切片（页面标签间无空格，非贪婪正则会把下一键吞进值里）
        _marks = [(mm.start(), mm.end(), mm.group(1).strip())
                  for mm in _re.finditer(r'([^\s：:\d]{2,10})[：:]', eseg)]
        for _i, (_st, _en2, _k) in enumerate(_marks):
            _vend = _marks[_i + 1][0] if _i + 1 < len(_marks) else len(eseg)
            _v = eseg[_en2:_vend].strip()
            if _k and _v and len(_v) <= 40:
                out['effects'].append([_k, _v])
                if len(out['effects']) >= 8:
                    break

    # ⑥ 同类物品
    sseg = _wiki_h2seg_like(clean, u'此类型的更多物品', 30000)
    if not sseg:
        sseg = _wiki_h2seg_like(clean, 'More items of this type', 30000)
    if sseg:
        _REL = [(u'同一系列', u'同一系列'), (u'属性相近', u'属性相近'),
                ('Used to craft', u'用于制作'), ('Crafting materials', u'制作材料'),
                ('Taming food cards', u'驯服食物'), ('Has quality', u'有品质'),
                ('Consumable', u'消耗品'), ('Same family', u'同一系列'),
                ('Similar stats', u'属性相近')]
        _used = set()
        for h3 in _re.findall(r'<h3[^>]*>([\s\S]{0,200}?)</h3>', sseg):
            nm = _wiki_strip(h3)[:28]
            if not nm or nm in _used:
                continue
            _used.add(nm)
            pos = sseg.find(h3)
            tail = _wiki_strip(sseg[pos:pos + 900]) if pos >= 0 else ''
            head = tail[:len(nm) + 120]
            rel = ''
            for en, zh in _REL:
                if en in head:
                    rel = zh
                    break
            out['same'].append([nm, rel])
            if len(out['same']) >= 8:
                break

    # ⑦ 战利品箱分布
    lseg2 = _wiki_h2seg_like(clean, u'在战利品箱中找到', 60000)
    if not lseg2:
        lseg2 = _wiki_h2seg_like(clean, 'Found in loot crates', 60000)
    if lseg2:
        ltxt = _wiki_strip(lseg2)
        m = _re.search(r'(\d+)\s*箱子来源\s*横跨\s*(\d+)\s*地图(?:\s*·\s*(\d+)\s*其他箱子来源)?', ltxt)
        if not m:
            m = _re.search(r'(\d+) crate sources across (\d+) maps(?: · (\d+) other crate sources)?', ltxt)
        if m:
            out['lootSum'] = u'%s 个箱子来源，横跨 %s 张地图%s' % (
                m.group(1), m.group(2),
                (u'，另有 %s 个其它来源' % m.group(3)) if m.group(3) else u'')
        for lab, pat in ((u'最高概率', u'最高概率\\s*([\\s\\S]{0,90}?)(?=Best quality|最多|Lowest level|地图|$)'),
                         (u'最好品质', r'Best quality\s*([\s\S]{0,90}?)(?=Lowest level|地图|$)'),
                         (u'最低等级', r'Lowest level\s*([\s\S]{0,90}?)(?=地图|$)')):
            mm = _re.search(pat, ltxt)
            if mm:
                v2 = _re.sub(r'\s+', ' ', mm.group(1)).strip()[:70]
                v2 = _wiki_cjk_space(v2)
                if v2:
                    out['lootTop'].append([lab, v2])
        # v245: 页面标签间无空格（Astraeos18Ragnarok23），故不用空白分隔
        mm = _re.search(r'地图([A-Z][\s\S]{0,600}?)箱子来源', ltxt)
        if not mm:
            mm = _re.search(r'Maps?\s*([A-Z][\s\S]{0,600}?)crate sources', ltxt)
        if mm:
            _seen_m = set()
            for g in _re.finditer(r'([A-Z][A-Za-z.\-]*(?: [A-Z][A-Za-z.\-]*)*)(\d+)', mm.group(1)):
                nm, n2 = g.group(1).strip(), int(g.group(2))
                if nm in ('Mod maps', 'Mod', 'Double', 'Lv', 'Tier') or nm in _seen_m:
                    continue
                if 0 < n2 <= 999:
                    _seen_m.add(nm)
                    out['lootMap'].append([nm, n2])
            out['lootMap'].sort(key=lambda x: -x[1])
            out['lootMap'] = out['lootMap'][:14]
        # v301：来源明细（wikily 仅 SSR 约 10 条，全量数量见 lootSum）
        out['lootRows'] = _wk_loot_rows(lseg2, clean)   # v5659：传整页 raw（TSV 在 RSC payload 里）
        _KIND = [('Supply drops', u'空投'), ('Caves', u'洞穴'), (u'洞穴', u'洞穴'),
                 ('Deep sea', u'深海'), (u'深海', u'深海'), ('Hordes', u'巢穴'),
                 (u'巢穴', u'巢穴'), ('Surface', u'地表'), (u'地表', u'地表')]
        for h3 in _re.findall(r'<h3[^>]*>([\s\S]{0,200}?)</h3>', lseg2):
            t = _wiki_strip(h3)
            g = _re.match(u'([^\\d]{2,24}?)\\s*(\\d+)$', t)
            if not g:
                continue
            raw_k, n2 = g.group(1).strip(), g.group(2)
            kz = raw_k
            for en, zh in _KIND:
                if en == raw_k:
                    kz = zh
                    break
            out['lootKind'].append([_wiki_cjk_space(kz)[:14], n2])

    return out


def _wiki_item_cache_path(cls):
    return os.path.join(WIKI_ITEM_CACHE, _re.sub(r'[^A-Za-z0-9_]', '_', str(cls)) + '.json')


def _wiki_item_load(cls):
    p = _wiki_item_cache_path(cls)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, 'r', encoding='utf-8') as f:
            return json.loads(f.read())
    except Exception:
        return None


def _wiki_item_save(cls, data):
    try:
        os.makedirs(WIKI_ITEM_CACHE, exist_ok=True)
        p = _wiki_item_cache_path(cls)
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False))
        os.replace(tmp, p)
    except Exception as e:
        _wiki_log('item save fail %s: %s' % (cls, str(e)[:80]))


def _wiki_item_worker(cls):
    _wiki_log('item worker START %s' % cls)
    try:
        data = _wiki_item_load(cls) or {}
        cands = _wiki_item_cands(cls)
        with _WIKI_ITEM_LOCK:
            t = _WIKI_ITEM_TASKS.get(cls)
            if t:
                t['slug'] = cands[0] if cands else ''
        raw = None
        used = ''
        err = ''
        for c in cands:
            url = WIKI_ITEM_ROOT + '/' + c
            t0 = time.time()
            try:
                raw = _wiki_fetch_page(url, 40)
                used = c
                _wiki_log('item ok %s slug=%s %dms %dB' % (cls, c, int((time.time() - t0) * 1000), len(raw)))
                break
            except Exception as e1:
                err = str(e1)[:100]
                _wiki_log('item FAIL %s slug=%s %s' % (cls, c, err))
        if raw:
            parsed = _wiki_item_parse(raw)
            # v287：ARK Wiki 专属按键（wikily 无按键章节，取 Usage 段抽键名 token）
            try:
                _ak = _ark_slug_from(used)
                if _ak:
                    _u2, _c2, _raw2 = _ark_fetch(_ak, timeout=20)
                    _keys = _ark_keys_from_usage(_ark_usage_lines(_raw2))
                    # v5817：同时抽「使用要点」（Usage / Notes 段条目），指南页按键为空时也有内容
                    _pts = _ark_points_from_page(_raw2, 10)
                    parsed['ark'] = {'slug': _ak, 'keys': _keys, 'points': _pts,
                                     'at': int(time.time() * 1000)}
                    _wiki_log('item ark %s slug=%s keys=%s pts=%d' % (
                        cls, _ak, ','.join(x['k'] for x in _keys) or '-', len(_pts)))
            except Exception as _e2:
                parsed['ark'] = {'slug': '', 'keys': [], 'err': str(_e2)[:80]}
                _wiki_log('item ark FAIL %s: %s' % (cls, str(_e2)[:100]))
            data['DATA'] = {'slug': used, 'zh': parsed.get('zh') or '', 'at': int(time.time() * 1000)}
            data['PARSED'] = parsed
            data['_pv'] = _WIKI_PARSE_VER      # v294：物品缓存打解析版本戳，供 _ready 判是否需重抓
            _wiki_item_save(cls, data)
            with _WIKI_ITEM_LOCK:
                t = _WIKI_ITEM_TASKS.get(cls)
                if t:
                    t['status'] = 'ready'
                    t['done'] = 1
                    t['data'] = data
            _wiki_log('item DONE %s slug=%s mats=%d attrs=%d' % (cls, used, len(parsed.get('mats') or []), len(parsed.get('attrs') or [])))
        else:
            _wiki_item_save(cls, {'_fail': 1, 'err': err or u'该物品暂无资料', 'at': int(time.time() * 1000)})
            with _WIKI_ITEM_LOCK:
                t = _WIKI_ITEM_TASKS.get(cls)
                if t:
                    t['status'] = 'error'
                    t['err'] = err or u'该物品暂无资料'
                    t['done'] = 1
    except Exception as e:
        _wiki_log('item worker EXC %s: %s' % (cls, str(e)[:160]))
        with _WIKI_ITEM_LOCK:
            t = _WIKI_ITEM_TASKS.get(cls)
            if t:
                t['status'] = 'error'
                t['err'] = str(e)[:120]


def _wiki_item_get(cls, start=True):
    """取物品 wiki 状态（v163：流程统一走 _wk_task_get）"""
    def _ready(c):
        # v250: 老缓存（v240 之前只有 7 字段、无 desc）判为未就绪 -> 自动重新抓取
        # v287: 加 'ark' 门槛 -> 老缓存补抓 ARK Wiki 专属按键
        # v294: 加版本戳门槛 —— 解析逻辑一改（如材料改 slug 对齐）就必须重抓；
        #       原实现只判字段、不判版本，提升 _WIKI_PARSE_VER 对物品完全无效（缓存永远命中旧值）
        pa = c.get('PARSED') or {}
        return (bool(pa) and ('desc' in pa) and ('ark' in pa)
                and int(c.get('_pv') or 0) >= _WIKI_PARSE_VER)

    def _fail(c):
        if c.get('_fail'):
            return str(c.get('err') or u'该物品暂无资料')[:120]
        return ''

    return _wk_task_get(cls, start, {
        'id_field': 'cls', 'tasks': _WIKI_ITEM_TASKS, 'lock': _WIKI_ITEM_LOCK,
        'valid': lambda k: bool(_re.match(r'^[A-Za-z0-9_]+$', k)),
        'load': _wiki_item_load, 'is_ready': _ready,
        'fail_err': _fail, 'total': 1, 'worker': _wiki_item_worker,
        'meta': lambda k: {'slug': ((_wiki_item_cands(k) or [''])[0])},
    })


# ===== v5819（用户口径「指南 TAB 常驻 + 复用物种技巧 AI 模块」）=====
#   物品指南页的 AI 整理结果（中文要点 + 分节），**全服共享一份**：
#   一人点过「一键整理」，其他人打开同物品直接命中缓存，不再各花 token。
#   存储：单文件 {cls: {points:[str], secs:[{h,t}], pv:int, ts:int}}
ITEM_TIPS_FILE = os.environ.get('ITEM_TIPS_FILE',
                                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'item_tips_zh.json'))
_ITEM_TIPS_LOCK = threading.Lock()


def _item_tips_read(cls):
    cls = str(cls or '').strip()
    if not cls:
        return None
    try:
        with _ITEM_TIPS_LOCK:
            if not os.path.exists(ITEM_TIPS_FILE):
                return None
            with open(ITEM_TIPS_FILE, 'r', encoding='utf-8') as f:
                d = json.load(f)
        v = d.get(cls) if isinstance(d, dict) else None
        return v if isinstance(v, dict) else None
    except Exception:
        return None


def _item_tips_merge(cls, merged=None, force=False):
    """前端 AI 整理完回写。points / secs 各自「只写一次」，或 pv 变大 / force 时覆盖。"""
    cls = str(cls or '').strip()[:120]
    if (not cls) or (not isinstance(merged, dict)):
        return 0
    try:
        with _ITEM_TIPS_LOCK:
            d = {}
            if os.path.exists(ITEM_TIPS_FILE):
                try:
                    with open(ITEM_TIPS_FILE, 'r', encoding='utf-8') as f:
                        d = json.load(f) or {}
                except Exception:
                    d = {}
            cur = d.get(cls) if isinstance(d.get(cls), dict) else {}
            pv_new = merged.get('pv') if isinstance(merged.get('pv'), int) else 0
            pv_old = cur.get('pv') if isinstance(cur.get('pv'), int) else 0
            upg = (pv_new > pv_old) or bool(force)
            n = 0
            # v5822：AI 提取的「动作 → 键」（器械类无官方键位时）
            akeys = merged.get('keys')
            if isinstance(akeys, list) and akeys and ((not cur.get('keys')) or upg):
                ka = []
                for x in akeys[:12]:
                    if not isinstance(x, dict):
                        continue
                    an = str(x.get('a') or '').strip()[:40]
                    kz = str(x.get('k') or '').strip()[:40]
                    # v5823：保留 Xbox 手柄键（p），与键鼠（k）成对存储
                    pz = str(x.get('p') or '').strip()[:40]
                    if an and (kz or pz):
                        ka.append({'a': an, 'k': kz, 'p': pz})
                if ka:
                    cur['keys'] = ka
                    n += 1
            pts = merged.get('points')
            if isinstance(pts, list) and pts and ((not cur.get('points')) or upg):
                arr = []
                for x in pts[:16]:
                    tx = str(x or '').strip()[:1200]
                    if tx:
                        arr.append(tx)
                if arr:
                    cur['points'] = arr
                    n += 1
            secs = merged.get('secs')
            if isinstance(secs, list) and secs and ((not cur.get('secs')) or upg):
                cl2 = []
                for x in secs[:12]:
                    if not isinstance(x, dict):
                        continue
                    hh = str(x.get('h') or '').strip()[:60]
                    tt = str(x.get('t') or '').strip()[:6000]
                    if tt:
                        cl2.append({'h': hh, 't': tt})
                if cl2:
                    cur['secs'] = cl2
                    n += 1
            if n:
                if pv_new:
                    cur['pv'] = pv_new
                cur['ts'] = int(time.time())
                d[cls] = cur
                tmp = ITEM_TIPS_FILE + '.tmp'
                with open(tmp, 'w', encoding='utf-8') as f:
                    json.dump(d, f, ensure_ascii=False)
                os.replace(tmp, ITEM_TIPS_FILE)
            return n
    except Exception:
        return 0


def _wiki_item_index():
    """已缓存的物品清单 {类名: 中文名}（v163：走 _wk_index_scan）"""
    def _zh(kk):
        d = _wiki_item_load(kk) or {}
        return ((d.get('DATA') or {}).get('zh') or '')
    return _wk_index_scan(WIKI_ITEM_CACHE, _zh, 'items')

def _wiki_probe(slug):
    # 探测：出网 / 耗时 / 解析 / 缓存目录可写
    import time as _t, urllib.request as _u
    out = {'ok': False, 'slug': slug, 'cacheDir': WIKI_CACHE_DIR}
    try:
        os.makedirs(WIKI_CACHE_DIR, exist_ok=True)
        tp = os.path.join(WIKI_CACHE_DIR, '_p.tmp')
        f = open(tp, 'w'); f.write('x'); f.close()
        os.remove(tp)
        out['writable'] = True
    except Exception as e:
        out['writable'] = False
        out['cacheErr'] = str(e)[:140]
    url = WIKI_ROOT + '/' + slug
    out['url'] = url
    t0 = _t.time()
    try:
        req = _u.Request(url, headers={'User-Agent': WIKI_UA, 'Accept': 'text/html'})
        r = _u.urlopen(req, timeout=30)
        raw = r.read().decode('utf-8', 'replace')
        out['httpStatus'] = r.getcode()
        out['ms'] = int((_t.time() - t0) * 1000)
        out['bytes'] = len(raw)
        pv = _wiki_parse_overview(raw)
        out['zh'] = pv['zh']
        out['introN'] = len(pv['intro'])
        out['tipsN'] = len(pv['tips'])
        out['intro0'] = (pv['intro'][0][:60] if pv['intro'] else '')
        out['ok'] = bool(pv['zh'] and pv['intro'])
    except Exception as e:
        out['ms'] = int((_t.time() - t0) * 1000)
        out['err'] = str(e)[:160]
    return out

# ===== v286：ARK Wiki 抓取 / 解析 / 探测 =====
def _ark_h2_segs(raw):
    """ARK Wiki 页面按 h2 切段 -> [(标题, 段HTML)]"""
    import re as _re
    heads = []
    for m in _re.finditer(r'<h2[^>]*>([\s\S]{0,200}?)</h2>', raw):
        heads.append((_wiki_strip(m.group(1)), m.end()))
    out = []
    for i, (t, st) in enumerate(heads):
        en = heads[i + 1][1] - 250 if i + 1 < len(heads) else len(raw)
        out.append((t, raw[st:max(st, en)]))
    return out


def _ark_flat_lines(seg, limit=40):
    """段 HTML -> 纯文本行（块级元素补换行，避免行间粘连）"""
    import re as _re, html as _h
    s = _re.sub(r'<script\b.*?</script>', ' ', seg, flags=_re.S | _re.I)
    s = _re.sub(r'<style\b.*?</style>', ' ', s, flags=_re.S | _re.I)
    s = _re.sub(r'</(p|div|li|tr|h[1-6]|dd|dt|table|section)>', '\n', s, flags=_re.I)
    s = _re.sub(r'<br\s*/?>', '\n', s, flags=_re.I)
    s = _re.sub(r'<[^>]+>', '', s)
    # v5833：_ark_h2_segs 在「下一个标题前 250 字符」处硬截断，可能把 HTML 标签切一半；
    #   半个标签没有闭合 '>' ⇒ 上面那条正则匹配不到 ⇒ 原样残留在正文里
    #   （实测 BattleRig 的 OVERVIEW.tips[0] 就是 308 字符的「<img ... data-fi」截断串）。
    #   下面这条兜底：要求 '<' 后紧跟 / ! 或字母 —— 完整标签与截断标签都能吃掉，
    #   且不会误伤「Drag Weight < 200」这类正文（曾用 `<[^>]*$` 直接删尾部，会把「<」之后整段删掉）。
    s = _re.sub(r'<[/!]?[A-Za-z][^>]*>?', '', s)
    s = _re.sub(r'[ \t\u00a0]+', ' ', s)
    lines = [x.strip() for x in _h.unescape(s).split('\n')]
    return [x for x in lines if len(x) > 3][:limit]


def _ark_fetch(slug, timeout=30):
    import urllib.request as _u
    url = ARK_ROOT + str(slug or '').strip().replace(' ', '_')
    req = _u.Request(url, headers={
        'User-Agent': WIKI_UA,
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    r = _u.urlopen(req, timeout=timeout)
    return url, r.getcode(), r.read().decode('utf-8', 'replace')


def _ark_probe(slug):
    """v286：探测后端能否取到 ARK Wiki（出网 / CF 拦截 / Usage·Notes 段可用性）"""
    import time as _t, re as _re
    out = {'ok': False, 'src': 'ark', 'slug': slug}
    t0 = _t.time()
    try:
        url, code, raw = _ark_fetch(slug, timeout=30)
        out['url'] = url
        out['httpStatus'] = code
        out['ms'] = int((_t.time() - t0) * 1000)
        out['bytes'] = len(raw)
        if 'Just a second' in raw[:4000] or 'cf-browser-verification' in raw[:9000]:
            out['err'] = 'cloudflare challenge'
            return out
        segs = _ark_h2_segs(raw)
        out['h2'] = [t for t, _ in segs][:24]
        got = {}
        for t, seg in segs:
            if t in _ARK_SEC_NAMES and t not in got:
                got[t] = _ark_flat_lines(seg, 30)
        for k in _ARK_SEC_NAMES:
            if k in got:
                out[k] = got[k]
        flat = ' '.join(_ark_flat_lines(raw, 4000))
        out['keyHits'] = sorted(set(
            m.group(1) for m in _re.finditer(
                r'press(?:ing)?\s+(?:the\s+)?([A-Za-z0-9+]{1,10})\s*(?:key|button)', flat, _re.I)
        ))[:20]
        out['ok'] = bool(got)
    except Exception as e:
        out['ms'] = int((_t.time() - t0) * 1000)
        out['err'] = str(e)[:200]
    return out


# ===== v5831（用户口径「wikily没数据的 至少要保留技巧TAB，然后可以玩家通过AI从wiki取信息渲染其他TAB」）=====
#   实测：wikily 的 dinosaurs 分类不含纯载具（battlerig/canoe/raft/train 全 404），
#        但第二数据源 ark.wiki.gg 有页面（BattleRig 200/186KB · Canoe 200/168KB）。
#        ⇒ wikily 首页所有候选失败时，回退 ark.wiki.gg 拉起基础资料，写进项目同一套 block 结构。
#   ark 页面 h2 实测（BattleRig）：Navigation menu | Contents | Crafting/Obtaining | Equipment | Notes | Changelog
# v5832（用户口径「回退到 wiki 时，其他 TAB 都只填置顶文案；技巧只从 wiki 分解；留空的不显示 TAB」）：
#   v5831 的「ark 章节 -> 结构化 block」映射已删除 —— 它把 Crafting 塞进概览正文、
#   Taming 塞进概览技巧、Abilities 塞进技能正文，内容张冠李戴。
#   现改为**每个 TAB 只填它自己的置顶文案（章节首段）**，没对应章节就不填、也不显示 TAB。
_ARK_SEC_PAT = (
    ('tips',   r'^(?:notes?|use|usage|uses|using|tip|tips)\b'),
    # v5849（用户口径「操作方法 / 能力为啥都没取到」）：
    #   wiki.gg 载具 / 器械页的这几段此前全被丢弃（实测 Hover_Skiff 页）。
    ('ctrl',   r'^(?:controls?|操作|控制)\b'),
    ('util',   r'^(?:utility|utilities|用途|使用)\b'),
    ('fuel',   r'^(?:fuel|fueling|燃料)\b'),
    ('base',   r'^(?:basic info|基本信息|基础信息)\b'),
    ('equip',  r'^(?:equipment|gear|attachments?|modules?|upgrades?)\b'),
    ('gather', r'^(?:harvesting|gathering|harvest|resources)\b'),
    ('abil',   r'^(?:abilities|ability|attacks?|skills?)\b'),
    ('tame',   r'^(?:taming|domestication)\b'),
    ('breed',  r'^(?:breeding|reproduction)\b'),
    ('exp',    r'^(?:experience|exp)\b'),
    ('spawn',  r'^(?:spawning|spawn)\b'),
)
_ARK_SKIP_H2 = ('Navigation menu', 'Contents', 'Changelog', 'Spotlight', 'Gallery',
                'References', 'External links', 'See also', 'Trivia', 'Media', 'Notes and references')
# v5833：ark 回退数据的版本戳。旧数据（_arkVer 缺失或更低）下次打开时自动重抓；
#   只影响 _src == 'ark' 的少数物种，**不动 _WIKI_PARSE_VER**（否则 557 个 wikily 物种全部重抓）。
# v5834：升 5834 —— 修复「页首全是站点 UI 文案」后必须让 ark 物种再重抓一次。
# v5835：升 5835 —— 概览不再强行填充（lead 为空就保持空）+ _avail 去掉技巧位。
_ARK_SEED_VER = 5835

# v5834（用户口径「其他 TAB 都只填置顶文案」）：
#   实测 BattleRig 页第一个 <h2> 之前**没有正文**，只有 infobox + MediaWiki 导航栏 ⇒
#   _ark_lead_lines() 捞回 6 条全是站点噪声：
#     'BattleRig - ARK Official Community Wiki' / 'Indie game deals' / 'Create account' /
#     'Log in' / 'Toggle personal tools menu' / 'Create account'
#   概览置顶文案整段变成垃圾。这里统一加噪声黑名单，lead 与各章节首段都要过一遍。
_ARK_NOISE_RE = (
    r'^.{1,80}\s+-\s+ARK Official Community Wiki$',
    r'^(?:Jump to content|Navigation menu|Main page|Contents|Current events|Random page|'
    r'Recent changes|Help|Contribute|Create account|Log in|Log out|Personal tools|'
    r'Search|Indie game deals|Donate|Special pages|What links here|Related changes|'
    r'Printable version|Permanent link|Page information|Cite this page|Read|Edit|'
    r'Edit source|View history|Talk|From ARK: Survival Ascended Wiki|From ARK Wiki)$',
    r'^Toggle\b',
    r'^(?:Deutsch|Español|Français|Italiano|Magyar|Nederlands|Polski|Português|'
    r'Português do Brasil|Suomi|Svenska|Türkçe|日本語|한국어|中文|Русский)$',
)
_ARK_NOISE_CACHE = None


def _ark_is_noise(s):
    """v5834：是否 MediaWiki 站点 UI 文案（页标题 / 登录注册 / 侧栏 / 语言列表）"""
    global _ARK_NOISE_CACHE
    if _ARK_NOISE_CACHE is None:
        import re as _re0
        _ARK_NOISE_CACHE = [_re0.compile(p, _re0.I) for p in _ARK_NOISE_RE]
    for _rx in _ARK_NOISE_CACHE:
        if _rx.match(s):
            return True
    return False


def _ark_clean_lines(lines):
    """v5834：去空 / 去短串 / 去站点 UI 噪声 / 去重"""
    out = []
    for x in (lines or []):
        t = str(x or '').strip()
        if len(t) < 8:
            continue
        if _ark_is_noise(t):
            continue
        if t not in out:
            out.append(t)
    return out


def _ark_lead_lines(raw, limit=6):
    """页首正文（第一个 h2 之前的内容）—— 概览置顶文案的唯一来源（已过噪声过滤）"""
    s = str(raw or '')
    i = s.find('<h2')
    head = s[:i] if i > 0 else s[:60000]
    return _ark_clean_lines(_ark_flat_lines(head, limit * 4))[:limit]


def _ark_seed(key, data):
    """wikily 无页面时用 ark.wiki.gg 拉起资料。
    v5832（用户口径「其他 TAB 都只填置顶文案；技巧只从 wiki 分解；留空的不显示 TAB」）：
      · 概览 OVERVIEW.intro   <- 页首 lead 段（无 lead 时用首个可用章节首段兜底）
      · 采集 HOME.gatherIntro + GATHER.intro <- Harvesting 章节首段
      · 技能 HOME.abilIntro   + ABIL.notes   <- Abilities 章节首段
      · 经验 HOME.expIntro                   <- Experience 章节首段
      · 装备 EQUIP.intro                     <- Equipment 章节首段
      · 技巧 OVERVIEW.tips                   <- Notes/Use/Tips 章节原文（前端只拿它做 AI 分解）
      · 驯服 HOME.tameIntro / 繁殖 BREED_DESC / 生成 SPAWN.intro：只写文案供 AI 整理，
        **不给 TAB**（缺结构化数据，显示出来只有「未收录」一句，与「留空的不显示」冲突）
      · DATA._avail = 实际有内容的 TAB 索引（0 概览/3 采集/5 技能/6 经验/7 技巧/9 装备）
    返回 True = 至少拿到一段可用资料。"""
    import re as _re
    cands = []
    def _add(x):
        x = str(x or '').strip()
        if x and x not in cands:
            cands.append(x)
    _add(key)
    _add(str(key).replace('_', ' '))
    _add(str(key).replace('_', ''))
    # v5872：UE 类名反转形态（Wyvern_Character_BP_Fire -> Fire Wyvern）
    #   ark.wiki.gg 的页名就是英文语序（Fire_Wyvern），不反转必然 404。
    try:
        for _un2 in _wk_ue_names(key):
            _add(_un2)
    except Exception:
        pass
    try:
        em = _wiki_en_map()
        _add(em.get(key))
        _add(em.get(str(key).lower()))
    except Exception:
        pass
    raw = None
    used = ''
    for c in cands[:5]:
        try:
            _u2, code, r = _ark_fetch(c, timeout=30)
            if code == 200 and len(r) > 20000 and 'Just a second' not in r[:4000]:
                raw = r
                used = c
                break
        except Exception:
            continue
    if not raw:
        return False
    # v5834：ark 回退前 worker 已给各 block 写过 {_fail:1}（wikily 404）；若本次没有对应章节，
    #   这些失败标记会原样留在缓存里（实测 BattleRig 的 HOME/GATHER/ABIL 就是 {_fail,at,err}）
    #   ⇒ 先清掉，避免前端拿到「有块但全是失败标记」的脏结构。
    for _b in ('HOME', 'GATHER', 'ABIL', 'BREED_DESC', 'SPAWN', 'HARVEST', 'TAME', 'BREED', 'EXP'):
        _v = data.get(_b)
        if (isinstance(_v, dict) and _v.get('_fail')) or (isinstance(_v, list) and not _v):
            data.pop(_b, None)
    lead = _ark_lead_lines(raw, 6)
    sec = {}
    for t, seg in _ark_h2_segs(raw):
        tt = str(t or '').strip()
        if (not tt) or (tt in _ARK_SKIP_H2):
            continue
        for k, pat in _ARK_SEC_PAT:
            if _re.match(pat, tt, _re.I):
                # v5834：段内同样过噪声过滤（MediaWiki 工具栏文案会混进段首）
                ls = _ark_clean_lines(_ark_flat_lines(seg, 12))[:6]   # 只要章节首段 = 置顶文案
                if ls:
                    # v5849：同一类别可出现多个章节（Abilities + Controls + Utility）⇒ 累计合并
                    _cur = sec.setdefault(k, [])
                    for _x in ls:
                        if _x not in _cur:
                            _cur.append(_x)
                break
    # v5835（用户口径「概览里不要强行填充，而是直接空置」）：
    #   lead 为空就保持空 —— 不再拿章节首段兜底（那会把装备清单当成「概述」塞进概览）。
    #   _wiki_get 的 _ready 已对 ark 数据放宽（允许 OVERVIEW.intro 为空）。
    ov = list(lead)
    tips = _ark_clean_lines(sec.get('tips') or [])
    if not tips:
        # 无 Notes/Use 章节时用页首 + 各章节首段拼技巧素材（仍全部来自 wiki 原文）
        tips = list(ov)
        for _k in ('equip', 'gather', 'abil', 'ctrl', 'util', 'fuel', 'base', 'tame', 'breed', 'exp'):
            for _x in (sec.get(_k) or [])[:3]:
                if _x not in tips:
                    tips.append(_x)
        tips = tips[:20]
    if not (ov or sec or tips):
        return False
    home = {}
    av = []
    if ov:
        av.append(0)
    if sec.get('gather'):
        home['gatherIntro'] = sec['gather'][:6]
        data['GATHER'] = {'about': '', 'intro': sec['gather'][:6], 'caps': [],
                          'nodes': [], 'nodeRes': [], 'params': {}}
        av.append(3)
    # v5849：wiki.gg 的 Controls（操作键）/ Utility（能力用途）/ Basic Info（载具能力描述）
    #   与 Abilities 同属「能力 + 操作」，一并写进技能块。
    _ab = []
    for _k in ('abil', 'ctrl', 'util', 'base'):
        for _x in (sec.get(_k) or []):
            if _x not in _ab:
                _ab.append(_x)
    _ab = _ab[:12]
    if _ab:
        home['abilIntro'] = _ab[:6]
        data['ABIL'] = {'skills': [], 'notes': _ab, 'videos': [], 'mats': []}
        av.append(5)
    if sec.get('exp'):
        home['expIntro'] = sec['exp'][:6]
        av.append(6)
    # v5835（用户口径「技巧 TAB 按有没有整理出技巧来决定展示」）：
    #   技巧位不再由后端 _avail 决定 —— 前端按 LB_TIPS.merged 是否有整理结果动态加。
    if sec.get('equip'):
        data['EQUIP'] = {'intro': sec['equip'][:6]}
        av.append(9)
    if sec.get('tame'):
        home['tameIntro'] = sec['tame'][:6]
    if sec.get('breed'):
        data['BREED_DESC'] = sec['breed'][:6]
    if sec.get('spawn'):
        data['SPAWN'] = {'intro': sec['spawn'][:6]}
    if home:
        data['HOME'] = home
    av.sort()
    data['DATA'] = {'zh': '', 'slug': str(key).lower(), 'title': '', 'tabs': [],
                    'fetched_at': int(time.time() * 1000), 'tabHtml': {},
                    '_src': 'ark', '_arkSlug': used, '_avail': av, '_arkVer': _ARK_SEED_VER}
    data['OVERVIEW'] = {'intro': ov[:6], 'tips': tips[:20], 'stats': [], 'bp': ''}
    return True


# ===== v5874：地图 Wiki（源 = wikily.gg 中文站，与物种 wiki 同一个站、同一个抓取器）=====
# 用户口径（2026-11-01）：
#   · 「按照wiki里的规则，在没有AI整理之前 只显示从wikily取到的中文内容」
#   · 「我说的同构是和物种物品wiki的所有规则方法样式结构完全逐字节照抄」
#   · 「Bob 是被整个项目过滤掉的，直接别考虑」
#   · v5873 的错误：主源误用 ark.wiki.gg（英文站）并把英文原文整块渲染 ⇒ 本版全部删掉
# 设计（对齐物种侧）：
#   · 源：WIKI_MAP_ROOT + '/<slug>'（zh-cn），抓取走 _wiki_fetch_page（与 _wiki_worker 同一函数）
#   · 只保留中文行（纯英文行丢弃）—— 未整理前只显示 wikily 中文原文
#   · 缓存 wiki_cache/mapwiki_<id>.json；**失败不落缓存**
_MW_ROOT = 'https://wikily.gg/zh-cn/ark-survival-ascended/maps'
_MW_SLUGS = {
    'Isl': 'the-island', 'Sco': 'scorched-earth', 'Cen': 'the-center', 'Abe': 'aberration',
    'Ext': 'extinction', 'Ast': 'astraeos', 'Rag': 'ragnarok', 'Val': 'valguero',
    'Los': 'lost-colony', 'Gen': 'genesis',
}
_MW_NAMES = {'Isl': u'孤岛', 'Sco': u'焦土', 'Cen': u'核心岛', 'Abe': u'畸变', 'Ext': u'灭绝',
             'Ast': u'星耀', 'Rag': u'仙境', 'Val': u'瓦尔盖罗', 'Los': u'失落地', 'Gen': u'创世'}
_MW_VER = 7   # v5899：ark 页地址修正 → 旧缓存失效重抓
# 块键 -> TAB 中文名（顺序即 TAB 顺序；空块不显示，与物种侧「留空的不显示 TAB」同口径）
_MW_TABS = (
    ('OVERVIEW', u'概览'),
    ('BIOME', u'群系'),
    ('RES', u'资源'),
    ('CAVE', u'洞穴'),
    ('CREATURE', u'生物'),
    ('BOSS', u'首领'),
    ('TIPS', u'技巧'),
    ('BASE', u'基地'),
    ('LORE', u'笔记'),
    ('STATS', u'统计'),
)

_MW_BLOCKS = tuple(k for (k, _z) in _MW_TABS)
# 章节标题（wikily 中文站实测）-> 块。按顺序匹配，命中即停
# v5878（用户口径「sco对应不到数据；除了isl为啥其他都只有统计数据」）：
#   每张图的「详细指南」小节标题**完全不一样**（实测）：
#     Isl: 地理与区域 / 独特之处 / 生存技巧 / 重要资源位置 / 推荐基地位置 / 探险家笔记与背景故事
#     Sco: 严酷气候与天气事件 / 区域与地标 / 独特之处与挑战 / 沙漠生存指南 / 必备资源指南 / 独有生物 / 战略基地位置
#     Cen: 独特的区域与地标 / 独特之处与优势 / 生存与建造指南 / 资源指南 / 最佳基地位置 / 首领挑战 / 必看地点
#     Abe: 地下环境 / 独特之处 / Aberration 生存指南 / 必备资源指南 / 独有生物 / 战略基地位置 / 发展路线
#     Ast: 多样的生物群系与区域 / 独特之处与机制 / 生存策略 / 资源指南 / 值得关注的生物 / 首领与小首领战 / …
#   固定标题硬匹配只能认出孤岛 ⇒ 改为「语义归类」，顺序即优先级（先命中先归类）。
_MW_TITLE_MAP = (
    ('CAVE',     u'洞穴|神器'),
    ('RES',      u'资源|物资|材料'),          # 优先于「指南」：「必备资源指南」应归资源
    ('BASE',     u'基地'),
    ('BOSS',     u'首领|竞技场|arena'),
    ('CREATURE', u'独有生物|关注.*生物'),
    ('BIOME',    u'区域|群系|地标|地形|环境|生态'),   # 「生物群系」含「群系」⇒ 需排在生物之前
    ('OVERVIEW', u'独特|特色|机制|气候|天气|神话|外观|模组'),   # 优先于「挑战」：「独特之处与挑战」归概览
    ('TIPS',     u'生存|技巧|策略|指南|路线|挑战'),
    ('LORE',     u'探险家笔记|explorer'),
    ('STATS',    u'统计'),
)
# v5879（用户口径「灭绝 暂无 wiki 资料（解析失败：'CREATURE'） 除了isl 全部报错」）：
#   语义分类键必须全部登记在 _MW_TABS 内，否则 blocks[hit] 抛 KeyError。
#   这里做模块级自检：以后新增语义分类忘了登记 TAB，启动即报错，不会拖到运行时才炸。
assert set((k for (k, _kw) in _MW_TITLE_MAP)) <= set((k for (k, _z) in _MW_TABS)), \
    'semantic key missing in _MW_TABS'
# ark.wiki.gg 英文地图页（第二数据源，**只作 AI 素材，不在界面展示**）
_MW_ARK_PAGES = {
    'Isl': 'The_Island', 'Sco': 'Scorched_Earth', 'Cen': 'The_Center', 'Abe': 'Aberration',
    'Ext': 'Extinction', 'Ast': 'Astraeos', 'Rag': 'Ragnarok', 'Val': 'Valguero',
    'Los': 'Lost_Colony', 'Gen': 'Genesis:_Part_1',   # v5899：原 'Genesis' 是消歧义页（实测 40KB / 10 个导航标题），真正创世页为 Genesis:_Part_1（836KB / 41 小节）
}
_ARK_MAP_SEC = (
    ('OVERVIEW', r'^(?:overview|introduction|unique environmental features|environmental features)\b'),
    ('BIOME',    r'^(?:biomes?|regions?|areas?|environment)\b'),
    ('RES',      r'^(?:resources?|harvestables?|resource nodes?)\b'),
    ('CAVE',     r'^(?:caves?|caverns?)\b'),
    ('BOSS',     r'^(?:boss ?arenas?|bosses?|arena|artifacts?)\b'),
    ('CREATURE', r'^(?:unique creatures|new creatures)\b'),
    ('TIPS',     r'^(?:notes?\s*/\s*trivia|notes?|trivia|tips?|guides?|strategies)\b'),
    ('BASE',     r'^(?:outposts?|recommended base|base locations?)\b'),
)
# 明确丢弃（导航/模板/FAQ/其他地图）
_MW_SKIP = (u'精选地图地点', u'热门建筑模板', u'Spawn Containers', u'地图问题',
            u'探索其他地图', u'野外指南', u'探险家笔记系列')


def _mw_h_segs(raw):
    """按 h2/h3/h4 平铺切段 -> [(level, 标题, 本段HTML)]（中文站 h4 是区域/资源小节）"""
    import re as _re2
    hs = []
    for m in _re2.finditer(r'<h([2-4])[^>]*>([\s\S]{0,300}?)</h\1>', raw):
        hs.append((int(m.group(1)), _wiki_strip(m.group(2)), m.start(), m.end()))
    out = []
    for i, (lv, t, st0, st) in enumerate(hs):
        en = hs[i + 1][2] if i + 1 < len(hs) else len(raw)
        out.append((lv, t, raw[st:max(st, en)]))
    return out


def _mw_has_zh(s):
    import re as _re3
    return bool(_re3.search(u'[\u4e00-\u9fff]', str(s or '')))


def _mw_block_lines(seg, maxn=12, maxlen=300):
    """段 HTML -> 中文行。有 h4 子标题时合成「子标题：正文」，否则按段落/列表逐行"""
    import re as _re4
    h4s = list(_re4.finditer(r'<h4[^>]*>([\s\S]{0,200}?)</h4>', seg))
    out = []
    if h4s:
        for k, m in enumerate(h4s):
            t = _wiki_strip(m.group(1)).strip()
            st = m.end()
            en = h4s[k + 1].start() if k + 1 < len(h4s) else len(seg)
            txt = ' '.join(_ark_flat_lines(seg[st:en], 14))
            txt = _re4.sub(r'\s+', ' ', txt).strip()
            if t and txt:
                out.append((t + u'：' + txt)[:maxlen])
            elif t and _mw_has_zh(t):
                out.append(t[:maxlen])
    else:
        for x in _ark_flat_lines(seg, maxn * 3):
            x = _re4.sub(r'\s+', ' ', str(x or '')).strip()
            if len(x) >= 8 and (not _ark_is_noise(x)) and x not in out:
                out.append(x[:maxlen])
    return [x for x in out if _mw_has_zh(x)][:maxn]


def _mw_stats_lines(seg):
    """「统计」的 <dl><dd>值</dd><dt>键</dt> → 「键 值」"""
    import re as _re5
    out = []
    # 结构 A：<dd>值</dd><dt>键</dt>
    for m in _re5.finditer(r'<dd[^>]*>([\s\S]{0,60}?)</dd>\s*<dt[^>]*>([\s\S]{0,60}?)</dt>', seg):
        v = _wiki_strip(m.group(1)).strip()
        k = _wiki_strip(m.group(2)).strip()
        if k and v and _mw_has_zh(k):
            out.append(u'%s %s' % (k, v))
    # 结构 B：<dt>键</dt><dd>值</dd>（部分地图页用这个顺序）
    if not out:
        for m in _re5.finditer(r'<dt[^>]*>([\s\S]{0,60}?)</dt>\s*<dd[^>]*>([\s\S]{0,60}?)</dd>', seg):
            k = _wiki_strip(m.group(1)).strip()
            v = _wiki_strip(m.group(2)).strip()
            if k and v and _mw_has_zh(k):
                out.append(u'%s %s' % (k, v))
    return out[:20]


_MW_PT_RE = _re.compile(u'[\uff08(][^\uff09)]{0,24}?(\\d{1,3}(?:\\.\\d+)?)\\s*[,，]\\s*(\\d{1,3}(?:\\.\\d+)?)\\s*[\uff09)]')
# v5895：允许括号内先写区域名——螰变 wikily 页写的是「传送门（肥沃区，45,30）」，
#   旧正则要求左括号后紧跟数字 ⇒ points.BASE 恒为空 ⇒ 基地地图不渲染（用户实鍏反馈）。


def _mw_points(lines):
    """从「基地位置」段落里解析 (x,y) 坐标 -> [{n, x, y}]（名称取括号前的文字）"""
    out = []
    for s in (lines or []):
        t = str(s or '')
        m = _MW_PT_RE.search(t)
        if not m:
            continue
        try:
            x = float(m.group(1))
            y = float(m.group(2))
        except Exception:
            continue
        if not (0 <= x <= 100 and 0 <= y <= 100):
            continue
        nm = t[:m.start()].strip()
        nm = nm.lstrip(u'\u2022\u00b7\u25cf-\u2014>\u203a ').strip(u' \uff1a:\uff0c,\u3002 ')
        if len(nm) > 28:
            nm = nm[:28]
        out.append({'n': nm, 'x': x, 'y': y})
    return out[:24]


# v5884（用户口径「笔记不要显示具体详细数据」）：探险家笔记段里混着表格/清单类数据
#   （每条笔记的坐标、已找到/未找到计数、Record #N · 21.2, 77.0 ……），只保留叙述性段落。
_MW_LORE_BAD = _re.compile(
    u'已找到|未找到|列表显示|记录进度|Record #|Note #|Dossier|图鉴#|'
    u'\\d{1,3}\\.\\d+\\s*[,，]\\s*\\d{1,3}\\.\\d+', _re.I)


def _mw_lore_filter(lines):
    out = []
    for s in (lines or []):
        t = str(s or '').strip()
        if len(t) < 12:
            continue
        if _MW_LORE_BAD.search(t):
            continue
        if t not in out:
            out.append(t)
    return out[:10]


def _mw_parse(raw):
    """wikily 中文地图页 -> {块: [中文行]}；块与 TAB 一一对应"""
    blocks = dict((k, []) for k in _MW_BLOCKS)
    for _lv, t, seg in _mw_h_segs(raw):
        tt = str(t or '').strip()
        if not tt:
            continue
        if any((sk in tt) for sk in _MW_SKIP):
            continue
        hit = ''
        for k, kw in _MW_TITLE_MAP:
            try:
                if _re.search(kw, tt, _re.I):
                    hit = k
                    break
            except Exception:
                if kw in tt:
                    hit = k
                    break
        if not hit:
            continue
        if hit == 'STATS':
            ls = _mw_stats_lines(seg)
        else:
            ls = _mw_block_lines(seg, 12)
        if ls:
            cur = blocks.setdefault(hit, [])   # v5879：防御性，键缺失也不炸
            for x in ls:
                if x and x not in cur:
                    cur.append(x)
    if blocks.get('LORE'):
        blocks['LORE'] = _mw_lore_filter(blocks['LORE'])
    for k in _MW_BLOCKS:
        if not blocks[k]:
            blocks.pop(k, None)
        else:
            blocks[k] = blocks[k][:14]
    return blocks, _mw_points(blocks.get('BASE'))


def _mw_ark_blocks(mid):
    """ark.wiki.gg 英文地图页 -> {块: [英文行]}。**只作 AI 素材，不在界面展示**。
       失败返回 {} （不影响主流程）。"""
    name = _MW_ARK_PAGES.get(mid) or ''
    if not name:
        return {}
    try:
        _u, code, raw = _ark_fetch(name, timeout=45)
    except Exception as e:
        print('[mapwiki] arkFAIL %s %s' % (mid, str(e)[:100]))
        return {}
    if code != 200 or (not raw) or len(raw) < 20000 or 'Just a second' in raw[:4000]:
        return {}
    blocks = {}
    try:
        lead = _ark_clean_lines(_ark_lead_lines(raw, 10))
        if lead:
            blocks['OVERVIEW'] = list(lead)[:8]
        for t, seg in _ark_h2_segs(raw):
            tt = str(t or '').strip()
            if (not tt) or (tt in _ARK_SKIP_H2) or _ark_is_noise(tt):
                continue
            for k, pat in _ARK_MAP_SEC:
                if _re.match(pat, tt, _re.I):
                    ls = _ark_clean_lines(_ark_flat_lines(seg, 30))[:12]
                    if ls:
                        cur = blocks.setdefault(k, [])
                        for x in ls:
                            if x not in cur:
                                cur.append(x)
                    break
    except Exception as e:
        print('[mapwiki] arkParseFAIL %s %s' % (mid, str(e)[:100]))
        return {}
    return blocks


def _mw_path(mid):
    return os.path.join(WIKI_CACHE_DIR, 'mapwiki_%s.json' % str(mid).lower())


def _mw_load(mid):
    p = _mw_path(mid)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, 'r', encoding='utf-8') as f:
            return json.loads(f.read())
    except Exception:
        return None


def _mw_save(mid, d):
    try:
        os.makedirs(WIKI_CACHE_DIR, exist_ok=True)
        p = _mw_path(mid)
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(json.dumps(d, ensure_ascii=False, separators=(',', ':')))
        os.replace(tmp, p)
        return True
    except Exception as e:
        print('[mapwiki] save fail: ' + str(e)[:120])
        return False


def _mw_build(mid):
    """抓 wikily 中文地图页并解析。失败**不落缓存**（下次自动重试）"""
    slug = _MW_SLUGS.get(mid) or ''
    rec = {'ok': False, 'id': mid, 'name': _MW_NAMES.get(mid, mid), 'status': 'error',
           'slug': slug, 'err': u'未知地图'}
    if not slug:
        return rec
    url = _MW_ROOT + '/' + slug
    t0 = time.time()
    try:
        raw = _wiki_fetch_page(url, 45)
    except Exception as e:
        rec['err'] = u'抓取失败：' + str(e)[:140]
        rec['ms'] = int((time.time() - t0) * 1000)
        print('[mapwiki] FAIL %s %s' % (mid, rec['err']))
        return rec
    rec['ms'] = int((time.time() - t0) * 1000)
    rec['bytes'] = len(raw)
    if (not raw) or len(raw) < 20000:
        rec['err'] = u'页面内容过短（%d 字节）' % len(raw)
        return rec
    try:
        blocks, bpts = _mw_parse(raw)
    except Exception as e:
        rec['err'] = u'解析失败：' + str(e)[:140]
        return rec
    avail = [k for k in _MW_BLOCKS if blocks.get(k)]
    if not avail:
        rec['err'] = u'页面无可解析章节'
        print('[mapwiki] EMPTY %s' % mid)
        return rec
    # v5878（用户口径「喂给AI应该是三个源的所有数据信息 而不是只有wikily」）：
    #   ai 里放全部素材源：wikily 中文（展示用那份）+ ark.wiki.gg 英文
    #   （第三源 dododex 经实测**没有地图页**，待用户指定替代源后再补）
    ai = {'wikily': dict((k, list(v)) for k, v in blocks.items())}
    try:
        _arkb = _mw_ark_blocks(mid)
        if _arkb:
            ai['ark'] = _arkb
    except Exception as _eA:
        print('[mapwiki] arkBLOCKFAIL %s %s' % (mid, str(_eA)[:100]))
    out = {'ok': True, 'id': mid, 'status': 'ready',
           'data': {'DATA': {'zh': _MW_NAMES.get(mid, mid), 'slug': slug, 'src': 'wikily',
                             'fetched_at': int(time.time() * 1000), 'avail': avail},
                    'blocks': blocks, 'ai': ai,
                    'points': {'BASE': bpts}},
           'avail': avail, '_v': _MW_VER, 'at': int(time.time()), 'ms': rec['ms'],
           'bytes': len(raw)}
    print('[mapwiki] OK %s %s blocks=%s' % (mid, slug, ','.join(avail)))
    return out


def _mw_get(mid, force=False):
    mid = str(mid or '').strip()
    if mid not in _MW_SLUGS:
        return {'ok': False, 'status': 'error', 'id': mid, 'err': 'unknown map id'}
    if not force:
        cd = _mw_load(mid)
        if cd and int(cd.get('_v') or 0) >= _MW_VER and cd.get('ok'):
            out = dict(cd)
            out['cached'] = True
            return out
    d = _mw_build(mid)
    if d.get('ok'):
        _mw_save(mid, d)
    out = dict(d)
    out['cached'] = False
    return out


def _mw_index():
    maps = {}
    for k in _MW_SLUGS:
        cd = _mw_load(k) or {}
        maps[k] = {'name': _MW_NAMES.get(k, k), 'ready': bool(cd.get('ok')),
                   'at': cd.get('at') or 0, 'avail': cd.get('avail') or []}
    return {'ok': True, 'count': len(_MW_SLUGS), 'maps': maps}


def _mw_probe(only=''):
    ids = [only] if str(only or '') in _MW_SLUGS else list(_MW_SLUGS.keys())
    out = {}
    for k in ids:
        rec = {'id': k, 'name': _MW_NAMES.get(k, k), 'slug': _MW_SLUGS.get(k, ''), 'h': []}
        url = _MW_ROOT + '/' + (rec['slug'] or '')
        rec['url'] = url
        t0 = time.time()
        try:
            raw = _wiki_fetch_page(url, 45)
            rec['ms'] = int((time.time() - t0) * 1000)
            rec['bytes'] = len(raw)
            try:
                rec['h'] = [('%d|%s' % (lv, t)) for (lv, t, _s) in _mw_h_segs(raw)][:46]
                bl, bp = _mw_parse(raw)
                rec['points'] = len(bp)
                rec['avail'] = [x for x in _MW_BLOCKS if bl.get(x)]
                rec['n'] = dict((x, len(bl.get(x) or [])) for x in _MW_BLOCKS)
            except Exception as e2:
                rec['parseErr'] = str(e2)[:140]
        except Exception as e:
            rec['ms'] = int((time.time() - t0) * 1000)
            rec['err'] = str(e)[:140]
        out[k] = rec
    return {'ok': True, 'probe': out}


def _mw_text_path(mid):
    return os.path.join(WIKI_CACHE_DIR, 'mapwiki_text_%s.json' % str(mid).lower())


def _mw_text_read(mid):
    p = _mw_text_path(mid)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, 'r', encoding='utf-8') as f:
            return json.loads(f.read())
    except Exception:
        return None


def _mw_text_write(mid, blocks, force=False):
    """AI 整理结果落盘（全服共享一份；force=true 覆盖），字段与物种侧同构"""
    mid = str(mid or '').strip()
    if (mid not in _MW_SLUGS) or (not isinstance(blocks, dict)):
        return 0
    with _WT_LOCK:
        if os.path.isfile(_mw_text_path(mid)) and not force:
            return 0
        clean = {}
        for k in _MW_BLOCKS:
            v = blocks.get(k)
            if not isinstance(v, list):
                continue
            arr = []
            for x in v[:40]:
                tx = _wt_flat_item(x)
                if tx and tx != '[object Object]' and tx not in arr:
                    arr.append(tx[:3000])
            if arr:
                clean[k] = arr
        # v5880（用户口径「AI整理过后，点位名称要跟着翻译」）：点位名中文映射单独存 BASEPTS
        _bp = blocks.get('BASEPTS')
        if isinstance(_bp, list):
            _barr = []
            for _it in _bp[:24]:
                if not isinstance(_it, dict):
                    continue
                try:
                    _x = float(_it.get('x'))
                    _y = float(_it.get('y'))
                except Exception:
                    continue
                _nm = str(_it.get('n') or '').strip()[:28]
                if _nm and (0 <= _x <= 100) and (0 <= _y <= 100):
                    _barr.append({'n': _nm, 'x': _x, 'y': _y})
            if _barr:
                clean['BASEPTS'] = _barr
        if not clean:
            return 0
        clean['_ts'] = int(time.time())
        clean['id'] = mid
        try:
            os.makedirs(WIKI_CACHE_DIR, exist_ok=True)
            p = _mw_text_path(mid)
            tmp = p + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                f.write(json.dumps(clean, ensure_ascii=False, separators=(',', ':')))
            os.replace(tmp, p)
            return len(clean) - 2
        except Exception as e:
            print('[mapwiki] text write fail: ' + str(e)[:120])
            return 0


ASA_DATA = os.environ.get('ASA_DATA', os.path.join(DINO_DATA, 'asa-data'))

# ===== 2026-10-27 配置改动规则（/api/cfg_rules）=====
# 说明：ARK 服务器 ini 为本地文件；后端与游戏服同机（D:\ARK Server）⇒ 直接本地读，无需插件导出。
CFG_SERVERS_DIR = os.environ.get('CFG_SERVERS_DIR', os.path.join(os.path.dirname(DINO_DATA), 'Servers'))
CFG_BASELINE_PATH = os.environ.get('CFG_BASELINE', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cfg_factory_baseline.json'))
CFG_FILE_MAP = {'GUS': 'GameUserSettings.ini', 'GAME': 'Game.ini', 'ENGINE': 'Engine.ini'}
# 只允许系统拥有者拉取（用户名白名单，逗号分隔；默认 whiterober）
CFG_OWNERS = set(x.strip() for x in os.environ.get('CFG_OWNER', 'whiterober').split(',') if x.strip())
_CFG_CACHE = {}
_CFG_BASELINE = {'mtime': -1.0, 'doc': None}
_CFG_PROC = {'ts': 0.0, 'map': None}
# 只按「密码/密钥」语义脱敏（不含 spectator，避免 bSpectatorManualFloatingNames 被误判）
_CFG_SECRET_TOKENS = ('password', 'secret', 'token', 'apikey', 'api_key')
# 2026-10-27：全局服务器域名（所有人共享；仅拥有者可写）——用于拼接服务器信息 / open 命令
SRV_CONFIG_FILE = os.environ.get('SRV_CONFIG', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server_config.json'))
# 2026-10-28：粑粑笔记（公开只读 / 仅拥有者导入覆盖）—— 单文件，前端「导出/导入 MD」对称
BB_NOTES_FILE = os.environ.get('BB_NOTES_FILE', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bb_notes.json'))
BB_NOTES_MAX = 200          # 条数上限
BB_NOTES_BODY_MAX = 8000    # 单条正文上限（字符）
# 2026-10-27：只返回「服务端相关段」——客户端设置段（ShooterGameUserSettings/ScalabilityGroups 等）一律不返回
CFG_SERVER_SECTIONS = ('serversettings', 'sessionsettings', 'multihome', 'messageoftheday',
                       'ragnarok', 'oasisaur', 'shootergamemode', 'gamesession')


def _srv_cfg_read():
    try:
        with open(SRV_CONFIG_FILE, 'r', encoding='utf-8') as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _srv_cfg_write(doc):
    tmp = SRV_CONFIG_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    os.replace(tmp, SRV_CONFIG_FILE)


def _bb_notes_read():
    """读粑粑笔记；文件不存在/损坏时返回 missing 标记（前端据此回落静态兜底）。"""
    try:
        with open(BB_NOTES_FILE, 'r', encoding='utf-8') as f:
            d = json.load(f)
        if isinstance(d, dict) and isinstance(d.get('notes'), list):
            d.setdefault('version', 1)
            d.setdefault('updated', '')
            return d
    except FileNotFoundError:
        return {'version': 1, 'updated': '', 'notes': [], 'missing': True}
    except Exception:
        _sexc('bb_notes_read')
        pass
    return {'version': 1, 'updated': '', 'notes': [], 'missing': True}


def _bb_notes_write(doc):
    tmp = BB_NOTES_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    os.replace(tmp, BB_NOTES_FILE)


def _bb_notes_norm(raw):
    """规范化导入数据：只保留 icon/title/body；去纯空白条目。返回 (notes, err)。"""
    if not isinstance(raw, list):
        return [], 'notes 必须是数组'
    if len(raw) > BB_NOTES_MAX:
        return [], '条目过多（上限 %d）' % BB_NOTES_MAX
    out = []
    for it in raw:
        if not isinstance(it, dict):
            continue
        title = str(it.get('title') or '').strip()[:200]
        body = str(it.get('body') or '')
        if len(body) > BB_NOTES_BODY_MAX:
            return [], '单条正文超长（上限 %d 字）' % BB_NOTES_BODY_MAX
        icon = str(it.get('icon') or '').strip() or 'mdi:information-outline'
        if not (title or body.strip()):
            continue
        out.append({'icon': icon, 'title': title, 'body': body})
    if not out:
        return [], '没有任何有效条目'
    return out, ''


def _srv_domain_norm(v):
    s = str(v or '').strip()
    for p in ('https://', 'http://'):
        if s.lower().startswith(p):
            s = s[len(p):]
    return s.strip().strip('/')


def _cfg_iso(ts):
    try:
        return time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(ts))
    except Exception:
        return None


def _cfg_ini_path(server, file_key):
    return os.path.join(CFG_SERVERS_DIR, server, 'ShooterGame', 'Saved', 'Config', 'WindowsServer', CFG_FILE_MAP[file_key])


def _cfg_section_ok(sec):
    low = str(sec or '').lower().replace('%2f', '/').replace('%2F', '/')
    return any(t in low for t in CFG_SERVER_SECTIONS)


def _cfg_is_secret(k):
    low = str(k).lower()
    return any(t in low for t in _CFG_SECRET_TOKENS)


def _cfg_parse_ini(path):
    """返回 (entries, sections, dups, size)；entries 保序且保留重复键（如 ConfigOverrideItemCraftingCosts）。"""
    raw = open(path, 'rb').read()
    enc = 'utf-16' if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8'
    txt = raw.decode(enc, errors='replace')
    if txt and txt[0] == '\ufeff':
        txt = txt[1:]
    sec = ''
    entries = []
    sections = []
    dups = []
    seen = {}
    for ln in txt.splitlines():
        s = ln.strip()
        if not s or s[0] in ';#':
            continue
        if s.startswith('[') and s.endswith(']'):
            sec = s[1:-1]
            if sec not in sections:
                sections.append(sec)
            continue
        if '=' in s:
            if not _cfg_section_ok(sec):
                continue
            k, v = s.split('=', 1)
            k = k.strip()
            v = v.strip()
            ck = (sec.lower(), k.lower())
            if ck in seen:
                dups.append(sec + '|' + k)
            seen[ck] = seen.get(ck, 0) + 1
            entries.append((sec, k, v))
    return entries, sections, dups, len(raw)


def _cfg_same(a, b):
    """值是否等价：布尔忽略大小写；数值给容差（0.999989986 与 1 视为相同）。"""
    sa = str(a).strip()
    sb = str(b).strip()
    if sa == sb:
        return True
    if sa.lower() == sb.lower():
        return True
    try:
        fa = float(sa)
        fb = float(sb)
        return abs(fa - fb) <= max(1e-4, 1e-6 * max(abs(fa), abs(fb)))
    except Exception:
        return False


def _cfg_baseline():
    try:
        m = os.path.getmtime(CFG_BASELINE_PATH)
    except OSError:
        return None
    if _CFG_BASELINE['doc'] is not None and _CFG_BASELINE['mtime'] == m:
        return _CFG_BASELINE['doc']
    doc = None
    try:
        with open(CFG_BASELINE_PATH, 'r', encoding='utf-8') as f:
            doc = json.load(f)
    except Exception:
        doc = None
    _CFG_BASELINE['mtime'] = m
    _CFG_BASELINE['doc'] = doc
    return doc


def _cfg_proc_start(server, force=False):
    """该服 ArkAscendedServer.exe 的启动时间（epoch 秒）；取不到返回 None。60s 缓存。
    v6182：force=True 时强制刷新（启动幂等检查用，避免刚启动 <60s 时命中旧空缓存）。"""
    now = time.time()
    if force or _CFG_PROC['map'] is None or (now - _CFG_PROC['ts']) > 60:
        m = {}
        try:
            ps = ("Get-CimInstance Win32_Process -Filter \"Name='ArkAscendedServer.exe'\" | "
                  "ForEach-Object { '{0}|{1}|{2}' -f $_.ProcessId, "
                  "[int]([datetime]$_.CreationDate - (Get-Date '1970-01-01')).TotalSeconds, $_.CommandLine }")
            r = subprocess.run(['powershell', '-NoProfile', '-Command', ps],
                               capture_output=True, timeout=25)
            out = (r.stdout or b'').decode('utf-8', 'replace')
            for line in out.splitlines():
                parts = line.strip().split('|', 2)
                if len(parts) != 3:
                    continue
                _pid, _start, _cmd = parts
                try:
                    st = float(_start)
                except ValueError:
                    continue
                low = (_cmd or '').lower()
                for a in SERVERS.keys():
                    if ('\\servers\\' + a.lower() + '\\') in low or ('/servers/' + a.lower() + '/') in low:
                        m[a] = st
                        break
        except Exception:
            m = {}
        _CFG_PROC['ts'] = now
        _CFG_PROC['map'] = m
    return (_CFG_PROC['map'] or {}).get(server)


def _cfg_build(server, file_key, mtime, proc_start):
    path = _cfg_ini_path(server, file_key)
    fname = CFG_FILE_MAP[file_key]
    doc = {'ok': True, 'server': server, 'file': fname, 'file_key': file_key,
           'generated_at': time.strftime('%Y-%m-%dT%H:%M:%S+08:00'),
           'partial': False, 'missing': []}
    if mtime is None or mtime < 0 or not os.path.isfile(path):
        doc['path_exists'] = False
        doc['items'] = []
        doc['count'] = 0
        doc['changed_count'] = 0
        doc['note'] = 'ini 不可读（文件不存在或该服未安装）'
        doc['partial'] = True
        doc['missing'].append('ini')
        doc['proc_start'] = _cfg_iso(proc_start) if proc_start else None
        doc['pending_restart'] = None
        doc['baseline'] = {'present': False}
        return doc
    entries, sections, dups, size = _cfg_parse_ini(path)
    base = _cfg_baseline()
    bfile = None
    if isinstance(base, dict) and isinstance(base.get('files'), dict):
        for k, v in base['files'].items():
            if str(k).lower() == fname.lower():
                bfile = v
                break
    if bfile is None:
        doc['partial'] = True
        doc['missing'].append('baseline')
    blink = {}
    if bfile:
        for bs, bd in bfile.items():
            blink[str(bs).lower()] = {str(x).lower(): y for x, y in (bd or {}).items()}
    total = {}
    for sec, k, _v in entries:
        ck = (str(sec).lower(), k.lower())
        total[ck] = total.get(ck, 0) + 1
    occ = {}
    items = []
    for sec, k, v in entries:
        ck = (str(sec).lower(), k.lower())
        idx = occ.get(ck, 0)
        occ[ck] = idx + 1
        bv = (blink.get(ck[0]) or {}).get(ck[1])
        secret = _cfg_is_secret(k)
        items.append({
            'section': sec, 'key': k,
            'value': ('***' if secret else v),
            'masked': bool(secret),
            'default': (None if bv is None else ('***' if secret else bv)),
            'changed': (None if bv is None else (not _cfg_same(bv, v))),
            'occurrence': idx,
            'dup': total.get(ck, 0) > 1,
        })
    doc['items'] = items
    doc['sections'] = sections
    doc['path_exists'] = True
    doc['ini_size'] = size
    doc['ini_mtime'] = _cfg_iso(mtime)
    doc['dups'] = dups[:50]
    doc['count'] = len(items)
    doc['changed_count'] = sum(1 for x in items if x['changed'] is True)
    doc['baseline'] = {'present': bool(bfile),
                       'generated_at': (base or {}).get('generated_at'),
                       'source': (base or {}).get('source'),
                       'coverage': (base or {}).get('coverage')}
    doc['proc_start'] = _cfg_iso(proc_start) if proc_start else None
    doc['pending_restart'] = (bool(proc_start) and mtime > proc_start) if proc_start else None
    return doc


def _cfg_rules_cached(server, file_key):
    key = (server, file_key)
    proc_start = _cfg_proc_start(server)
    path = _cfg_ini_path(server, file_key)
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        mtime = -1.0
    hit = _CFG_CACHE.get(key)
    if hit and hit.get('mtime') == mtime and hit.get('ps') == proc_start:
        return hit['etag'], hit['body']
    doc = _cfg_build(server, file_key, mtime, proc_start)
    body = json.dumps(doc, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    etag = '"%x-%x"' % ((int((mtime if mtime > 0 else 0) * 1000)) & 0x7fffffff, len(body))
    if len(_CFG_CACHE) > 32:
        _CFG_CACHE.clear()
    _CFG_CACHE[key] = {'mtime': mtime, 'etag': etag, 'body': body, 'ps': proc_start}
    return etag, body


# ===== 2026-10-27：规则快照（拥有者上传 → 全玩家共享读）=====
_CFG_SNAP = {'mtime': -1.0, 'doc': None}
_CFG_SNAP_LOCK = threading.Lock()


def _cfg_snapshot_path():
    p = os.environ.get('CFG_SNAPSHOT')
    if p:
        return p
    return os.path.join(os.path.dirname(ACCOUNTS_FILE), 'cfg_rules_snapshot.json')


def _cfg_snapshot():
    p = _cfg_snapshot_path()
    try:
        m = os.path.getmtime(p)
    except OSError:
        return None
    if _CFG_SNAP['doc'] is not None and _CFG_SNAP['mtime'] == m:
        return _CFG_SNAP['doc']
    doc = None
    try:
        with open(p, 'r', encoding='utf-8') as f:
            doc = json.load(f)
    except Exception:
        doc = None
    _CFG_SNAP['mtime'] = m
    _CFG_SNAP['doc'] = doc
    return doc


def _cfg_snapshot_write(doc):
    p = _cfg_snapshot_path()
    tmp = p + '.tmp'
    with _CFG_SNAP_LOCK:
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(doc, f, ensure_ascii=False, separators=(',', ':'))
        os.replace(tmp, p)
        try:
            st = os.stat(p)
            _CFG_SNAP['mtime'] = st.st_mtime
            _CFG_SNAP['doc'] = doc
        except OSError:
            _CFG_SNAP['mtime'] = -1.0
            _CFG_SNAP['doc'] = None
    return os.path.getsize(p)


_CFG_JOB = {'running': False, 'done': 0, 'total': 0, 'current': '', 'errors': [], 'started': 0.0, 'finished': 0.0}
_CFG_JOB_LOCK = threading.RLock()


def _cfg_live_doc(server, file_key):
    p = _cfg_ini_path(server, file_key)
    try:
        mtime = os.path.getmtime(p)
    except OSError:
        mtime = -1.0
    return _cfg_build(server, file_key, mtime, _cfg_proc_start(server))


def _cfg_job_view():
    with _CFG_JOB_LOCK:
        return {'running': _CFG_JOB['running'], 'done': _CFG_JOB['done'], 'total': _CFG_JOB['total'],
                'current': _CFG_JOB['current'], 'errors': list(_CFG_JOB['errors']),
                'started': _CFG_JOB['started'], 'finished': _CFG_JOB['finished']}


def _cfg_refresh_all():
    servers = sorted(SERVERS.keys())
    with _CFG_JOB_LOCK:
        _CFG_JOB.update({'running': True, 'done': 0, 'total': len(servers), 'current': '',
                         'errors': [], 'started': time.time(), 'finished': 0.0})
    snap = {'schema': 1, 'generated_at': time.strftime('%Y-%m-%dT%H:%M:%S+08:00'),
            'updated_by': 'backend', 'servers': {}}
    try:
        for s in servers:
            with _CFG_JOB_LOCK:
                _CFG_JOB['current'] = s
            ent = {}
            for fk in ('GUS', 'GAME'):
                try:
                    ent[fk] = _cfg_live_doc(s, fk)
                except Exception as e:
                    with _CFG_JOB_LOCK:
                        _CFG_JOB['errors'].append('%s/%s %s' % (s, fk, repr(e)))
                    ent[fk] = {'ok': False, 'server': s, 'file': CFG_FILE_MAP[fk], 'file_key': fk,
                               'partial': True, 'missing': ['ini'], 'items': [], 'count': 0,
                               'changed_count': 0, 'path_exists': False, 'note': '读取失败'}
            snap['servers'][s] = ent
            with _CFG_JOB_LOCK:
                _CFG_JOB['done'] += 1
        _cfg_snapshot_write(snap)
    except Exception as e:
        with _CFG_JOB_LOCK:
            _CFG_JOB['errors'].append('fatal ' + repr(e))
    finally:
        with _CFG_JOB_LOCK:
            _CFG_JOB.update({'running': False, 'current': '', 'finished': time.time()})


def _cfg_refresh_start(by):
    with _CFG_JOB_LOCK:
        if _CFG_JOB['running']:
            return False, _cfg_job_view()
    threading.Thread(target=_cfg_refresh_all, kwargs={}, daemon=True).start()
    return True, _cfg_job_view()


def _cfg_all_slim():
    """全服概览：只含改动项 + 计数（体积小；详情再单拉）。"""
    snap = _cfg_snapshot()
    src = (snap or {}).get('servers') or {}
    out = {'ok': True, 'from_snapshot': bool(snap),
           'generated_at': (snap or {}).get('generated_at'),
           'updated_by': (snap or {}).get('updated_by'),
           'servers': {}}
    for s in sorted(SERVERS.keys()):
        ent = src.get(s) or {}
        item_ent = {}
        for fk in ('GUS', 'GAME'):
            d = ent.get(fk)
            if not isinstance(d, dict):
                continue
            item_ent[fk] = {'count': d.get('count'), 'changed_count': d.get('changed_count'),
                            'ini_mtime': d.get('ini_mtime'), 'pending_restart': d.get('pending_restart'),
                            'partial': d.get('partial'), 'path_exists': d.get('path_exists'),
                            'items': [x for x in (d.get('items') or []) if x.get('changed') is True]}
        out['servers'][s] = item_ent
    body = json.dumps(out, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    mm = _CFG_SNAP['mtime'] if _CFG_SNAP['mtime'] and _CFG_SNAP['mtime'] > 0 else 0
    etag = '"a%x-%x"' % (int(mm * 1000) & 0x7fffffff, len(body))
    return etag, body


def _cfg_rules_read(server, file_key):
    """优先返回快照（全玩家共享）；无快照时退回现场读。"""
    snap = _cfg_snapshot()
    if isinstance(snap, dict):
        doc = ((snap.get('servers') or {}).get(server) or {}).get(file_key)
        if isinstance(doc, dict):
            out = dict(doc)
            out['from_snapshot'] = True
            out['snapshot_at'] = snap.get('generated_at')
            out['snapshot_by'] = snap.get('updated_by')
            body = json.dumps(out, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
            mm = _CFG_SNAP['mtime'] if _CFG_SNAP['mtime'] and _CFG_SNAP['mtime'] > 0 else 0
            etag = '"s%x-%x"' % (int(mm * 1000) & 0x7fffffff, len(body))
            return etag, body
    return _cfg_rules_cached(server, file_key)

# 2026-08-28 修复：硬编码 RCON 目标为物理服务器内网 IP（游戏服 MultiHomeIp 绑定地址，实测返回真实 JSON）。
# 不用 os.environ 读取——服务器残留系统环境变量 RCON_HOST=127.0.0.1 会覆盖默认值导致连到错误服务（返回 Keep Alive）。
RCON_HOST = '192.168.199.3'
RCON_PASSWORD = os.environ.get('RCON_PASSWORD', '1219wu1219')
PORT = int(os.environ.get('PORT', '8080'))
RCON_TIMEOUT = int(os.environ.get('RCON_TIMEOUT', '15'))
ALLOW_ORIGIN = os.environ.get('ALLOW_ORIGIN', 'https://dino.whiterober.ccwu.cc')
ACCOUNTS_FILE = os.environ.get('ACCOUNTS_FILE', r'D:\dino_backend\accounts.json')
HARVEST_DIR = os.environ.get('HARVEST_DIR', os.path.join(os.path.dirname(ACCOUNTS_FILE), 'userdata'))  # 采集流程玩家文档
# R2 / WebP 全自动更新配置（cf_config.json：api_token/account_id/r2_bucket/r2_endpoint/r2_s3_access_key/r2_s3_secret_key）
CF_CONFIG_FILE = os.environ.get('CF_CONFIG_FILE', os.path.join(os.path.dirname(ACCOUNTS_FILE), 'cf_config.json'))
WEBP_MAP_FILE = os.path.join(os.path.dirname(ACCOUNTS_FILE), 'webp_map.json')
VOLCANO_FILE = os.path.join(os.path.dirname(ACCOUNTS_FILE), 'volcano_anchor.json')  # v1096：火山喷发锚点（已弃用，保留兼容；v1107 改用插件权威查询）
VOLCANO_ERUPT_FILE = os.path.join(os.path.dirname(ACCOUNTS_FILE), 'volcano_erupt_anchor.json')  # v1138：共享「真喷发锚点」——任何客户端捕获 phase→eruption 后上报，落盘持久化（跨客户端/换设备/后端重启均不丢）
VOLCANO_SERVERS = {'Gen'}  # 阶段一：仅创世有火山计时
VOLC_STATE_TTL_MS = 3000   # 2026-09-14：火山状态内存缓存 TTL——后端单点轮询 ⇒ N 个客户端也只 3s 一次 RCON（插件文档 §4 强约束）
VOLC_LOG_TTL_MS = 2000     # v1146（用户定稿）：火山**事件台账**独立缓存槽——仅当 hooks.events 变化 / 30s 兜底时才被前端请求
_VOLC_STATE_CACHE = {}     # server -> {'ts': epoch_ms, 'data': {...}}

# ---- WorldProbe 公共设施实时查询（2026-09-30，插件 v9；用户口径：短时缓存共用 + 前端 CD）----
WP_TYPES_TTL_MS = 600000   # 类别字典（极稳定，10min）
WP_QUERY_TTL_MS = 5000     # 单服单类查询：短时缓存共用——N 个客户端 TTL 窗口内只发 1 次 RCON
WP_WEATHER_TTL_MS = 3000  # v4411b（2026-10-07·全图 dll 已推送）：60s→3s 全局秒级（插件内 3.6ms / RCON 往返 1.1~1.5s）
# 分档机制保留：如需为个别图单独降速（如旧 dll），把 {'图':60000} 填进下表即可
WP_WX_TTL_FAST = {}
WP_ZONES_TTL_MS = 60000    # 2026-10-03：天气区域（WorldProbe zones）——插件侧名单长缓存，本层 60s 与前端复用对齐
WP_BIOMET_TTL_MS = 60000   # 2026-10-04：区域温度（biometemps）——插件每调用实时重读；本层 60s + 同键并发合并
WP_SCAN_TTL_MS = 10000     # 聚合路由（子查询另有各自 5s 缓存）
WP_CLASS_TTL_MS = 10000    # 类级计数（scan filter）；类计数变化慢
WP_LIMIT_DEFAULT = 500     # v4243（用户口径）：默认 500（插件上限 2000；旧值 20/100 系误设）
WP_LIMIT_MAX = 2000        # v4243（用户口径）：与插件上限 2000 对齐（旧值 100 误设）
WP_SERVER_MAX = 11         # scan 聚合最多图数（= SERVERS 全量）
_WP_TYPES_CACHE = {}       # server -> {'ts': ms, 'data': {...}}
_WP_QUERY_CACHE = {}       # (server,type,limit) -> {'ts': ms, 'data': {...}}
_WP_WEATHER_CACHE = {}     # server -> {'ts': ms, 'data': {...}}
_WP_ZONES_CACHE = {}       # server -> {'ts': ms, 'data': {...}}   # 2026-10-03：天气区域（zones）
_WP_BIOMET_CACHE = {}      # (server,skip,count,brief,filter) -> {'ts': ms, 'data': {...}}   # 2026-10-04：biometemps
_WP_SCAN_CACHE = {}        # (type,(servers),limit) -> {'ts': ms, 'data': {...}}
_WP_CLASS_CACHE = {}       # (cls,(servers)) -> {'ts': ms, 'data': {...}}
# ---- v4367（2026-10-06）：WorldProbe 事件扩展路由（wave/sandstorm/meteor/actor/badwx/wprobs）----
WP_WAVE_TTL_MS = 60000     # Gen 巨浪（worldprobe wave）
WP_SAND_TTL_MS = 60000     # Rag 沙尘暴（worldprobe sandstorm，插件 v122b3+）
WP_METEOR_TTL_MS = 2000    # Ext 陨石雨（worldprobe meteor，实时性要求高）
WP_ACTOR_TTL_MS = 3000     # 2026-10-10（用户口径）：30s→3s——与前端 3s 轮询对齐，火山倒计时秒级新鲜；依据：陨石雨路由 2s 先例 + actor 为轻查询（跳过大头只读 11 值）+ 仅浮窗打开时请求 + 同键并发合并保留（N 客户端仍 1 次穿透）
WP_BADWX_TTL_MS = 300000   # 坏天气权重（worldprobe badwx，变化极慢）
WP_WPROBS_TTL_MS = 300000  # 全服概率聚合（权重数组长驻）
_WP_WAVE_CACHE = {}        # (server, cmd) -> {'ts': ms, 'data': {...}}
_WP_SAND_CACHE = {}        # (server, cmd) -> {'ts': ms, 'data': {...}}
_WP_METEOR_CACHE = {}      # (server, cmd) -> {'ts': ms, 'data': {...}}
_WP_ACTOR_CACHE = {}       # (server, cmd) -> {'ts': ms, 'data': {...}}
_WP_BADWX_CACHE = {}       # (server, cmd) -> {'ts': ms, 'data': {...}}
_WP_WPROBS_CACHE = {}      # server -> {'ts': ms, 'data': {...}}
# ---- v4670（2026-10-16）：风力发电机耐久（wind_status；风机耐久变化极慢 ~0.0139/s，60s 缓存）----
WIND_TTL_MS = 600000       # v4687：60s→10 分钟（前端同 TTL + 预热；风机耐久变化极慢）+ 同键并发合并
WIND_FIELDS = 'Health,MaxHealth,PoweredBatteryDurabilityToDecreasePerSecond,DecayDestructionPeriod,CurrentWind'
WIND_DECAY_MULT = 0.35   # v4686（2026-10-16 实测标定）：实际消耗 = PoweredBatteryDurabilityToDecreasePerSecond × 0.35（25min 差分实测 0.0049/s，prop 值 0.0141/s；满耐久由此吻合 14 天）
_WIND_CACHE = {}           # (server, 'wind') -> {'ts': ms, 'data': {...}}
# ---- v5714（2026-10-30）：存档世界时钟逆推（world_clock）----
# 原理：RCON worldTime 与真实秒 1:1（插件实测 Δ21.11/Δ21s）
#   ⇒ fileWorldTime = rconWorldTime - (锚点现实时刻 - 存档 mtime)
WORLD_CLOCK_TTL_MS = 180000   # 3 分钟：worldTime 线性，mtime 不变则结果不变；TTL 主要防抖
WORLD_CLOCK_JUMP_SEC = 120    # 与上次锚点外推值偏差 > 120s ⇒ 判定重启/回档
_WORLD_CLOCK_CACHE = {}        # (server, 'wclock') -> {'ts': ms, 'data': {...}}
_WP_LOCKS = {}             # 查询键 -> Lock（同键并发合并：后到者等锁→双检缓存，只发 1 条 RCON）
_WP_LOCKS_GUARD = threading.Lock()
_WP_CACHE_MAX = 2000       # 宽松上限；超限按 ts 清掉一半最旧（防 key 泄漏）
_WP_SCAN_EXECUTOR = __import__('concurrent.futures', fromlist=['ThreadPoolExecutor']).ThreadPoolExecutor(max_workers=4)

# ---- 游戏内时间（2026-10-03：原生 RCON GetInGameTime；对标 HA sensor.ingame_time_cache）----
INGAME_TTL_MS = 3000      # v4460（用户口径·对齐火山 3s）：后端单点采集 + 同键并发合并，N 客户端合计每图 ≤1 次 RCON/3s（原生 RCON 成本低）
_INGAME_CACHE = {}        # server -> {'ts': ms, 'data': {...}}
_INGAME_LOCKS = {}        # server -> Lock（同键并发合并：后到者等锁 → 双检缓存）
_INGAME_LOCKS_GUARD = threading.Lock()
_INGAME_RE = re.compile(r'Day\s+(\d+),\s+(\d{1,2}):(\d{2}):(\d{2})')
WEBP_DIR = os.path.join(os.path.dirname(ACCOUNTS_FILE), 'webp96')

# 服务器 RCON 端口表（与 apps.yaml 对齐）
SERVERS = {
    'Isl': 32320, 'Sco': 32321, 'Cen': 32322, 'Abe': 32323, 'Ext': 32324,
    'Ast': 32325, 'Rag': 32326, 'Val': 32327, 'Bob': 32319, 'Los': 32328,
    'Gen': 32329,
}

# 服务器主题（原 apps.yaml server_themes；独立后内置，避免依赖 HA）
SERVER_THEMES = {
    'Isl': {'name': '孤岛', 'icon': 'mdi:island', 'emoji': '🏝️', 'primary_color': '#4CAF50',
            'light_color': '#81C784', 'dark_color': '#388E3C',
            'bg_image': "url('https://img.whiterober.ccwu.cc/ASA/misc/Isl_compressed.jpg')",
            'overlay_color': 'rgba(76, 175, 80, 0.7)'},
    'Sco': {'name': '焦土', 'icon': 'mdi:volcano', 'emoji': '🔥', 'primary_color': '#FF5722',
            'light_color': '#FF8A65', 'dark_color': '#D84315',
            'bg_image': "url('https://img.whiterober.ccwu.cc/ASA/misc/Sco_compressed.jpg')",
            'overlay_color': 'rgba(255, 87, 34, 0.7)'},
    'Cen': {'name': '核心岛', 'icon': 'mdi:orbit', 'emoji': '💎', 'primary_color': '#9C27B0',
            'light_color': '#CE93D8', 'dark_color': '#7B1FA2',
            'bg_image': "url('https://img.whiterober.ccwu.cc/ASA/misc/Cen_compressed.jpg')",
            'overlay_color': 'rgba(156, 39, 176, 0.7)'},
    'Abe': {'name': '畸变', 'icon': 'mdi:radioactive', 'emoji': '☢️', 'primary_color': '#00BCD4',
            'light_color': '#4DD0E1', 'dark_color': '#0097A7',
            'bg_image': "url('https://img.whiterober.ccwu.cc/ASA/misc/Abe_compressed.jpg')",
            'overlay_color': 'rgba(0, 188, 212, 0.7)'},
    'Ext': {'name': '灭绝', 'icon': 'mdi:meteor', 'emoji': '☄️', 'primary_color': '#F44336',
            'light_color': '#EF9A9A', 'dark_color': '#D32F2F',
            'bg_image': "url('https://img.whiterober.ccwu.cc/ASA/misc/Ext_compressed.jpg')",
            'overlay_color': 'rgba(244, 67, 54, 0.7)'},
    'Ast': {'name': '星耀', 'icon': 'mdi:star-four-points', 'emoji': '✨', 'primary_color': '#3F51B5',
            'light_color': '#9FA8DA', 'dark_color': '#303F9F',
            'bg_image': "url('https://img.whiterober.ccwu.cc/ASA/misc/Ast_compressed.jpg')",
            'overlay_color': 'rgba(63, 81, 181, 0.7)'},
    'Rag': {'name': '仙境', 'icon': 'mdi:lighthouse-on', 'emoji': '🗼', 'primary_color': '#FF9800',
            'light_color': '#FFB74D', 'dark_color': '#F57C00',
            'bg_image': "url('https://img.whiterober.ccwu.cc/ASA/misc/Rag_compressed.jpg')",
            'overlay_color': 'rgba(255, 152, 0, 0.7)'},
    'Val': {'name': '瓦尔盖罗', 'icon': 'mdi:forest', 'emoji': '🌲', 'primary_color': '#4CAF50',
            'light_color': '#A5D6A7', 'dark_color': '#388E3C',
            'bg_image': "url('https://img.whiterober.ccwu.cc/ASA/misc/Val_compressed.jpg')",
            'overlay_color': 'rgba(76, 175, 80, 0.7)'},
    'Bob': {'name': '俱乐部', 'icon': 'mdi:party-popper', 'emoji': '🎉', 'primary_color': '#E91E63',
            'light_color': '#F48FB1', 'dark_color': '#C2185B',
            'bg_image': "url('https://img.whiterober.ccwu.cc/ASA/misc/Bob_compressed.jpg')",
            'overlay_color': 'rgba(233, 30, 99, 0.7)'},
    'Los': {'name': '失落地', 'icon': 'mdi:castle', 'emoji': '🏰', 'primary_color': '#795548',
            'light_color': '#BCAAA4', 'dark_color': '#5D4037',
            'bg_image': "url('https://img.whiterober.ccwu.cc/ASA/misc/Los_compressed.jpg')",
            'overlay_color': 'rgba(121, 85, 72, 0.7)'},
    'Gen': {'name': '创世', 'icon': 'mdi:dna', 'emoji': '🧬', 'primary_color': '#009688',
            'light_color': '#80CBC4', 'dark_color': '#00796B',
            'bg_image': "url('https://img.whiterober.ccwu.cc/ASA/misc/Gen_compressed.jpg')",
            'overlay_color': 'rgba(0, 150, 136, 0.7)'},
}

# RCON 命令
CMD_TAMED = 'TransferIdentityFix.ArkTamedDinos'
CMD_WILD = 'TransferIdentityFix.WildDinos'
CMD_TRACK = 'TransferIdentityFix.TrackDino'
CMD_TRACK_LOC = 'TransferIdentityFix.TrackLocation'  # v809：坐标打点（蛋/静态目标）
CMD_STOP_TRACK = 'TransferIdentityFix.StopTrackDino'
CMD_PLAYER_POS = 'TransferIdentityFix.PlayerPos'
CMD_GET_DINO = 'TransferIdentityFix.ArkGetDino'
CMD_MOVE_DEATH_BAG = 'TransferIdentityFix.MoveDeathBag'
CMD_MOVE_ALL_PENDINGS = 'TransferIdentityFix.MoveAllPendings'
CMD_RENAME_DINO = 'TransferIdentityFix.RenameDino'
CMD_RENAME_CONTAINER = 'TransferIdentityFix.RenameContainer'   # v1326：容器箱改名（仅容器，床/棺/牌/碑后端会拒绝并给 hint）
CMD_SET_SIGN_TEXT = 'TransferIdentityFix.SetSignText'   # 2026-09-19（插件 0.4.0）：牌子/墓碑写文字（SignText；客户端需重进视野/重连）
CMD_SET_BED_NAME = 'TransferIdentityFix.SetBedName'     # 2026-09-19（插件 0.4.0）：床/棺材/睡眠舱改名（BedName；客户端需重进视野/重连）
CMD_EGG_PROBE = 'TransferIdentityFix.EggProbe'
CMD_INV_PROBE = 'TransferIdentityFix.InvProbe'  # 2026-09-04：库存扫描（饲料槽/风行蜥/未成年背包物品）
CMD_CRAFTING_COST = 'TransferIdentityFix.CraftingCost'  # 2026-09-13：单蓝图制作材料（只读、无副作用）
CMD_VOLCANO = 'TransferIdentityFix.Volcano'  # 2026-09-14：火山喷发权威状态（插件 v0.5.0；只读、无副作用）
CMD_WORLDPROBE = 'TransferIdentityFix.WorldProbe'  # 2026-09-30：公共设施实时查询（插件 v9；只读、无副作用）
CRAFTING_COST_SERVERS = set(SERVERS.keys())  # 2026-09-15：全服放开（用户确认所有地图均已部署 CraftingCost 命令；原阶段一白名单 {'Abe'}）
CMD_LIST_PLAYERS = 'ListPlayers'  # v532：原生 RCON 在线玩家列表（联盟位置只查在线成员）
CMD_INGAME_TIME = 'TransferIdentityFix.GetInGameTime'  # 2026-11-08：我们插件自带（可让 ExtendedRcon 退役）
CMD_SAVE_WORLD = 'SaveWorld'  # v17：原生 RCON 保存世界（强制存档，cryo.json.gz 落地后前端拉最新球数据）

# 内存状态缓存（供 /api/states/sensor.* 兼容轮询）：key = sensor 名，value = {state, attributes}
STATUS_MEM = {}

# ================= 独立登录 =================
# accounts.json：{登录账号: {pwd: 密码, nick: 玩家昵称}}（昵称用于匹配 players[].name → eosId）
_ACCOUNTS = None


def _accounts():
    global _ACCOUNTS
    if _ACCOUNTS is None:
        try:
            with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                _ACCOUNTS = json.load(f)
        except Exception:
            _ACCOUNTS = {}
    return _ACCOUNTS


def check_login(username, password):
    """校验登录，成功返回玩家昵称 nick，失败返回 None。"""
    acc = _accounts().get(username)
    if not acc:
        return None
    if str(acc.get('pwd', '')) != str(password):
        return None
    return acc.get('nick') or username


# ===== P1 新增：角色等级判定（零侵入；不被既有逻辑调用，仅新接口/登录响应用）=====
def _role_level(username):
    """3=系统拥有者　2=二级管理员(accounts.role=='admin2')　1=普通玩家。
    拥有者硬编码判定（不依赖 accounts 里的 role 字段）。
    异常一律回落 1，绝不抛错。"""
    try:
        if username == 'whiterober':
            return 3
        return 2 if ((_accounts().get(username, {}) or {}).get('role') or '') == 'admin2' else 1
    except Exception:
        return 1


# ===== v6155（用户口径「不依赖计划任务」）：后端远程重启（两级 spawn）=====
#   核心矛盾：后端退出后必须有人把它拉起；而后端 spawn 的子进程与后端同属一个 Job，
#   进程退出 / Stop-ScheduledTask 会连带杀掉它 ⇒ 必须让子进程**脱离 Job**。
#   两级策略（不新建任何计划任务）：
#     ① CREATE_BREAKAWAY_FROM_JOB + DETACHED_PROCESS + CREATE_NEW_PROCESS_GROUP（纯 Python，约 10ms）
#     ② 失败回退 WMI（Invoke-CimMethod Win32_Process.Create）—— 父进程是 WmiPrvSE，天然不在本 Job
#   两者都失败 ⇒ 拒绝退出（绝不留下「点了就死」）。
#   重启动作复用后端同目录现成的 restart_dino_backend.bat [等待秒数]。
ADMIN_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'admin.log')
_BOOT_TS = time.time()   # 供 /api/health 报运行时长


def _admin_log(line):
    try:
        with open(ADMIN_LOG, 'a', encoding='utf-8') as f:
            f.write('[%s] %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), line))
    except Exception:
        pass


def _admin_spawn_restart(wait_secs=3):
    """启动「延迟 N 秒后执行 restart_dino_backend.bat」且**脱离本进程 Job** 的进程。
    返回 (ok, how, err)；how ∈ {'breakaway','wmi',''}"""
    bat = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'restart_dino_backend.bat')
    if not os.path.isfile(bat):
        return False, '', 'restart_dino_backend.bat not found'
    try:
        DETACHED = 0x00000008
        NEW_GROUP = 0x00000200
        BREAKAWAY = 0x01000000
        subprocess.Popen(['cmd.exe', '/c', bat, str(int(wait_secs))], close_fds=True,
                         creationflags=DETACHED | NEW_GROUP | BREAKAWAY)
        return True, 'breakaway', ''
    except Exception as e1:
        err1 = 'breakaway: %r' % (e1,)
    try:
        cmdline = 'cmd.exe /c "%s" %d' % (bat, int(wait_secs))
        ps = ('Invoke-CimMethod -ClassName Win32_Process -MethodName Create '
              '-Arguments @{CommandLine=\'%s\'} | Select-Object -ExpandProperty ReturnValue'
              % cmdline.replace("'", "''"))
        r = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', ps],
                           capture_output=True, timeout=25)
        out = (r.stdout or b'').decode('utf-8', 'replace').strip()
        if r.returncode == 0 and out.startswith('0'):
            return True, 'wmi', ''
        err2 = 'wmi rc=%d out=%s' % (r.returncode, out[:120])
    except Exception as e2:
        err2 = 'wmi: %r' % (e2,)
    return False, '', err1 + ' | ' + err2


def _admin_do_restart(user, how=''):
    """重启进程已拉起 → 稍等后自杀式退出（由那个进程 Stop + Start）"""
    _admin_log('RESTART exit by %s (spawn=%s)' % (user, how))
    time.sleep(1.0)
    os._exit(0)


def _admin_rss_mb():
    """当前进程工作集 MB（失败返回 None）"""
    try:
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                        ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                        ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t)]
        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        h = ctypes.windll.kernel32.GetCurrentProcess()
        if ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb):
            return round(pmc.WorkingSetSize / 1048576.0, 1)
    except Exception:
        pass
    return None


def _health_payload():
    """GET /api/health 载荷（无鉴权、极轻）"""
    now = time.time()
    code = {}
    try:
        st = os.stat(os.path.abspath(__file__))
        code = {'size': st.st_size,
                'mtime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime))}
    except Exception:
        pass
    rq = {}
    try:
        with _RESTART_LOCK:
            rq = {'running': bool(_RESTART.get('running')), 'dry': bool(_RESTART.get('dry')),
                  'current': _RESTART.get('current') or '', 'done': len(_RESTART.get('done') or [])}
    except Exception:
        pass
    return {'ok': True,
            'ts': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now)),
            'startedAt': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(_BOOT_TS)),
            'uptimeSec': int(now - _BOOT_TS),
            'threads': threading.active_count(),
            'rssMB': _admin_rss_mb(),
            'code': code,
            'ipwatch': {'domain': _IPWATCH.get('domain') or '',
                        'lastIp': _IPWATCH.get('lastIp') or '',
                        'lastCheckAt': _IPWATCH.get('lastCheckAt') or '',
                        'mode': _IPWATCH.get('mode') or 'notify'},
            'restart': rq}


# ===== v6023（用户口径）：srvctl 会话 Token（HMAC 无状态签名）=====
# 背景：/api/srvctl/action 等原先只校验前端自报的 username ⇒ 任何人只要知道管理员用户名，
#       一句 curl 就能启停服务器 / 清空全图野龙 / 发任意 RCON，且 srvctl.log 记的是伪造的用户名，事后查不到真凶。
# 设计：登录时发 token（username|expire + HMAC 签名），请求时验签。
#       **完全无状态** ⇒ 重启后端 token 依然有效，绝不会把所有人踢出去重登。
#       签名里带「密码指纹」⇒ 改密码即自动吊销该账号所有旧 token。
# 强度：写接口（action / rcon）强制 token；读接口 token 优先、无 token 时兼容旧的 username 直报（保持探测与兼容）。
import hashlib as _hashlib
import hmac as _hmac
import base64 as _b64

_SRVCTL_SECRET_CACHE = None
_SRVCTL_TOKEN_DAYS = 30


def _srvctl_secret():
    """签名密钥：环境变量 SRVCTL_SECRET 优先；否则读 accounts.json 同目录 srvctl_secret.txt；都没有则生成落盘。"""
    global _SRVCTL_SECRET_CACHE
    if _SRVCTL_SECRET_CACHE:
        return _SRVCTL_SECRET_CACHE
    v = (os.environ.get('SRVCTL_SECRET') or '').strip()
    if not v:
        p = os.path.join(os.path.dirname(ACCOUNTS_FILE), 'srvctl_secret.txt')
        try:
            if os.path.exists(p):
                with open(p, 'r', encoding='utf-8') as f:
                    v = (f.read() or '').strip()
            if not v:
                v = os.urandom(32).hex()
                with open(p, 'w', encoding='utf-8') as f:
                    f.write(v + '\n')
        except Exception:
            v = 'dino-srvctl-fallback-v6023'
    _SRVCTL_SECRET_CACHE = v
    return v


def _srvctl_pwdtag(username):
    """密码指纹：改密码 ⇒ 旧 token 验签失败（天然吊销开关）。"""
    try:
        pwd = str((_accounts().get(username, {}) or {}).get('pwd') or '')
        return _hashlib.sha256(pwd.encode('utf-8')).hexdigest()[:10]
    except Exception:
        return 'x'


def _srvctl_sign(username, expire, pwdtag):
    msg = ('%s|%d|%s' % (username, int(expire), pwdtag)).encode('utf-8')
    return _hmac.new(_srvctl_secret().encode('utf-8'), msg, _hashlib.sha256).hexdigest()


def _srvctl_make_token(username, days=None):
    exp = int(time.time()) + int(days or _SRVCTL_TOKEN_DAYS) * 86400
    raw = _b64.urlsafe_b64encode(('%s|%d' % (username, exp)).encode('utf-8')).decode('ascii').rstrip('=')
    return raw + '.' + _srvctl_sign(username, exp, _srvctl_pwdtag(username))


def _srvctl_check_token(token):
    """校验 token → 返回 username；失败返回 ''。"""
    try:
        t = str(token or '').strip()
        if '.' not in t:
            return ''
        raw, sig = t.split('.', 1)
        pad = '=' * (-len(raw) % 4)
        dec = _b64.urlsafe_b64decode((raw + pad).encode('ascii')).decode('utf-8')
        u, exp_s = dec.rsplit('|', 1)
        exp = int(exp_s)
        if exp < int(time.time()):
            return ''
        if not _hmac.compare_digest(sig, _srvctl_sign(u, exp, _srvctl_pwdtag(u))):
            return ''
        return u
    except Exception:
        return ''


def _srvctl_tk_of(handler, qs=None):
    tk = ''
    try:
        ah = handler.headers.get('Authorization') or ''
        if ah.lower().startswith('bearer '):
            tk = ah[7:].strip()
    except Exception:
        pass
    if not tk and qs:
        try:
            tk = (qs.get('tk') or [''])[0].strip()
        except Exception:
            tk = ''
    return tk


def _srvctl_guard(handler, qs=None, need_token=False):
    """统一鉴权：成功返回 username；失败已 _send 并返回 ''（调用方直接 return）。"""
    u = _srvctl_check_token(_srvctl_tk_of(handler, qs))
    if not u:
        if need_token:
            handler._send(401, {'ok': False, 'code': 'token_invalid',
                                'error': u'会话已过期，请重新登录'})
            return ''
        u = ((qs.get('username') or [''])[0].strip() if qs else '')
        if not u:
            handler._send(401, {'ok': False, 'code': 'login_required', 'error': 'login required'})
            return ''
    if _role_level(u) < 2:
        handler._send(401, {'ok': False, 'code': 'level2_required', 'error': 'level2 required'})
        return ''
    return u


# ===== P3 新增：服务器控制（后端直连 ASA Server Manager，零 HA；前端永不接触 token）=====
# 依据：计划\需求_服务器控制入口_二级管理员.md §6.2 / §7.2 / §7.3
SRVCTL_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'srvctl.log')
# v6177（2026-11-06）：savekill 纳入白名单 —— 后端原子「存档 → DinoData 稳定 → 终止」，
#   由 _srvctl_one 内部递归 saveworld+c kill 完成，不依赖浏览器轮询。
SRVCTL_ACTIONS = ('start', 'stop', 'kill', 'update', 'saveworld', 'savekill',
                  'fullbackup', 'destroy', 'rcon')
SRVCTL_T_TIMEOUT = 60            # 普通动作超时（秒）
SRVCTL_T_DESTROY = 600           # destroy 超时（对齐 HA）
SRVCTL_T_FULLBACKUP = 600        # fullbackup 超时（保守同档）
SRVCTL_ASYNC_ACTIONS = ('destroy', 'fullbackup')   # 走异步 job
_SRVCTL_POOL = __import__('concurrent.futures', fromlist=['ThreadPoolExecutor']).ThreadPoolExecutor(max_workers=4)
_SRVCTL_JOB_POOL = __import__('concurrent.futures', fromlist=['ThreadPoolExecutor']).ThreadPoolExecutor(max_workers=1)
# ===== v6222（用户口径 2026-11-07）：**终止动作全局串行闸** =====
#   背景：存档写各自的 Servers\<srv>\，并行安全；但多台同时**下发终止**会把
#   「玩家跨服传送窗口」瞬间清零 ⇒ 传送被截断。手动脉冲原为 4 并发、编排放行 2 台，
#   都存在该风险，且护栏只能保证「发起那一刻」无传送。
#   本闸：同一时刻只放行一台下发终止，相邻两台间隔 >= KILL_SERIAL_GAP 秒；
#   且闸在「终止前复检」**之前**生效 ⇒ 轮到自己时才复检，结论不会因等待而过期。
KILL_SERIAL_GAP = 5
_KILL_SERIAL = {'lock': __import__('threading').RLock(), 'lastAt': 0.0}


def _kill_serial_wait():
    u"""v6222：等终止串行闸（全局）。仅包住「排队 + 刷新时间」，真正下发在其后。"""
    _lk = _KILL_SERIAL['lock']
    _lk.acquire()
    try:
        _gap = float(KILL_SERIAL_GAP)
        _w = float(_KILL_SERIAL.get('lastAt') or 0) + _gap - time.time()
        if _w > 0:
            time.sleep(min(_w, _gap))
        _KILL_SERIAL['lastAt'] = time.time()
    finally:
        try:
            _lk.release()
        except Exception:
            pass


def _kill_serial_prepare(cfg):
    u"""v6222：本台尚未过闸则等待并打标；savekill 等过之后，其内部递归调用的
       kill（_gate_passed=True）不会重复等第二次。"""
    try:
        if cfg.get('_kill_serial_done'):
            return cfg
        _kill_serial_wait()
        _c = dict(cfg)
        _c['_kill_serial_done'] = True
        return _c
    except Exception:
        return cfg
_SRVCTL_BUSY = {}                # (server, action) -> 起始 ts（同服同动作互斥）
_SRVCTL_BUSY_LOCK = threading.Lock()
_SRVCTL_JOBS = {}                # jobId -> {...}
_SRVCTL_JOBS_LOCK = threading.Lock()
_SRVCTL_JOB_TTL = 3600           # job 结果保留 1 小时


def _rcon_exec(server, command, timeout=15):
    """v54（2026-11-03）：直连 Source RCON 执行命令——与 HA `send_rcon_command_sync` 同路径。

    为什么必须直连：实测 ASA Server Manager 的 `/rcon` 对 `KickPlayer` 这类
    「按玩家定位」的命令**只回显不执行**（游戏内可见黄字但人没被踢）；
    RCON 协议直连由服务器以 admin 身份执行，行为与 HA 版完全一致。

    与 `rcon_command()` 的差别：能区分「连接失败 / 认证失败 / 命令已下发」，
    避免把认证失败误判成成功（rcon_command 认证失败与无响应都返回 b''）。
    返回 (ok, text)。
    """
    port = SERVERS.get(server)
    if not port:
        return False, 'unknown server: %s' % server
    s = None
    try:
        s = socket.create_connection((RCON_HOST, port), timeout=timeout)
        s.sendall(_rcon_packet(1, 3, RCON_PASSWORD))
        auth = _recv_stream(s, timeout)
        if not auth:
            return False, 'auth: no response on port %s' % port
        if len(auth) >= 12 and struct.unpack('<i', auth[4:8])[0] == -1:
            return False, 'auth failed (wrong RCON_PASSWORD) on port %s' % port
        s.sendall(_rcon_packet(2, 2, command))
        data = _recv_stream(s, timeout)
        text = (data or b'').decode('utf-8', errors='ignore')
        # v6124：剔除 RCON 包头残留字节（size/id/type 均 <0x20，实测 'World Saved' 前带 \x18\x02）
        text = ''.join(ch for ch in text if ch >= ' ' or ch in '\n\t').strip()
        return True, (text or 'sent (no response)')
    except Exception as e:
        return False, '%s: %s' % (type(e).__name__, e)
    finally:
        if s is not None:
            try:
                s.close()
            except Exception:
                pass


def _srvctl_cfg():
    """现读 ASA 配置（改 token 即时生效，无需重启）。"""
    d = _srv_cfg_read() or {}

    def _i(k, dv):
        try:
            return int(d.get(k) or dv)
        except Exception:
            return dv

    return {
        'base': str(d.get('asa_base') or 'https://asa.whiterober.com').rstrip('/'),
        'token': str(d.get('asa_token') or ''),
        'timeout': _i('asa_timeout', SRVCTL_T_TIMEOUT),
        'timeout_destroy': _i('asa_timeout_destroy', SRVCTL_T_DESTROY),
        'verify': bool(d.get('asa_verify_tls') or False),
        'dry': bool(d.get('asa_dry_run') or False),
    }


def _asa_mask(tok):
    """全局统一掩码：'****' + 后 6 位；未配置返回空串。"""
    tok = str(tok or '')
    if not tok:
        return ''
    return ('****' + tok[-6:]) if len(tok) > 6 else '****'


def _asa_http(method, url, token, payload=None, timeout=60, verify=False):
    """最小 HTTPS 客户端（标准库）。返回 (http_code, text)；网络异常抛错。"""
    import ssl as _ssl
    import urllib.request as _ur
    data = None
    headers = {'User-Agent': 'dino-backend/srvctl', 'Accept': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    ctx = None
    if not verify:
        try:
            ctx = _ssl._create_unverified_context()
        except Exception:
            ctx = None
    req = _ur.Request(url, data=data, headers=headers, method=method)
    try:
        with _ur.urlopen(req, timeout=timeout, context=ctx) as r:
            return (getattr(r, 'status', 200), r.read().decode('utf-8', 'replace'))
    except _ur.HTTPError as e:
        try:
            return (e.code, e.read().decode('utf-8', 'replace'))
        except Exception:
            return (e.code, '')


def _srvctl_reply_zh(msg):
    """v6201（用户口径 2026-11-06「怎么还留有未翻译的？」）：RCON 回执中文化。

    覆盖范围＝**只翻实际观测到的 4 类**（样本取自 srvctl.log 近 400 行统计 | 出现次数）：
        destroy   '<ctrl>%All Wild Dinos Destroyed'                 | 67
        destroy   '<ctrl>%All Wild Dinos Destroyed   Keep Alive'     | 17
        saveworld 'World Saved'                                     | 42
        saveworld '{"message":"World saved for Bob."}'              |  9（ASAM 旧路径）
    未收录的回执**原样返回**（不猜、不乱翻）。

    ⚠ ASA 的 destroy 回执在 '%' 前还带一个不可见控制字符（如 \x02）⇒ 一律用**子串**匹配，
      绝不能用 startswith / 正则首锚，否则永远匹配不上。
    ⚠ 'Keep Alive' 分支必须**先判**：它包含 'All Wild Dinos Destroyed'，顺序反了会被通用分支吃掉。"""
    s = str(msg or u'')
    if not s:
        return s
    if 'All Wild Dinos Destroyed' in s:
        if 'Keep Alive' in s:
            # Keep Alive：清野龙但保留存活个体（已驯服/已装载的不在清理范围）
            return u'已清空全图野生恐龙（保留存活个体）'
        return u'已清空全图野生恐龙'
    if 'World Saved' in s or 'World saved' in s:
        # ASAM 旧路径回执：{"message":"World saved for Bob."} —— 整条换成「世界已保存（Bob）」
        _m = re.search(r'World saved for ([A-Za-z][A-Za-z0-9_ ]*)', s)
        if _m and s.strip().startswith('{'):
            return u'世界已保存（%s）' % _m.group(1).strip()
        # 其余（'World Saved' / 'World Saved · DinoData 稳定 16s（11 文件）'）：
        #   **只替换回执词**，后缀附加信息必须原样保留（否则日志丢关键排查数据）
        return s.replace('World Saved', u'世界已保存').replace('World saved', u'世界已保存')
    return s


def _srvctl_src_tag(user, src=''):
    """v6202（用户口径 2026-11-07「cen gen 刚才是谁启动的？能看到么？」）：
    审计回执前加**来源标签** —— 原日志只有账号名，看不出这次操作是人工点的还是系统自动触发的。

    | user 值                  | 标签         | 写入方                            |
    |--------------------------|--------------|-----------------------------------|
    | ipwatch                  | [自动重启]   | 自动重启编排 `_restart_exec_startq` |
    | arkbackup / rollback     | [安全回档]   | 安全回档 job                       |
    | (system) / srvctl / 空   | [系统]       | 跳过判定 / 护栏放行 / 内部兜底      |
    | 其他（账号名）            | [人工]       | 前端按钮 / 批量启动 / 任务条重试    |

    v6203（用户口径 2026-11-07「那就实施」）：前端 `lbTaskRetry` 现在会带 `src='retry'`
      ⇒ 重试标 `[重试]`，与普通人工点击 `[人工]` 区分开；
      未带 src 的仍按 user 推断（兼容旧前端 / 直接调 API 的场景）。"""
    # v6203：前端显式来源优先（v6202 遗留盲区：人工点按钮 vs 任务条重试，payload 完全一致）
    _s = str(src or '').strip().lower()
    if _s == 'retry':
        return u'[重试] '
    u = str(user or '').strip()
    if u == 'ipwatch':
        return u'[自动重启] '
    if u in ('arkbackup', 'rollback'):
        return u'[安全回档] '
    if u in ('', '(system)', 'system', 'srvctl'):
        return u'[系统] '
    return u'[人工] '


def _srvctl_log(user, server, action, ok, ms, msg='', src=''):
    """审计：每服一行（时间/用户/服务器/动作/结果/耗时）。"""
    try:
        # v6201：回执先中文化再落盘（未收录的回执原样保留，不影响排查）
        line = '%s\t%s\t%s\t%s\t%s\t%dms\t%s\n' % (
            time.strftime('%Y-%m-%d %H:%M:%S'), user, server, action,
            'OK' if ok else 'FAIL', int(ms),
            (_srvctl_src_tag(user, src) + _srvctl_reply_zh(msg)).replace('\n', ' ')[:200])
        with open(SRVCTL_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line)
    except Exception:
        pass


def _srvctl_terminal_gate(server, force=False):
    """v6179（用户口径）：所有「涉及终止」的动作（kill / savekill）复用自动重启的三重静默护栏。
      L1 在线人数必须 0（Bob 按 RESTART_SKIP_EMPTY 跳过，其在线列表不刷新）
      L3 集群目录 RESTART_CLUSTER_QUIET 秒内无写入
    v6197（用户口径）：**删除 L2「变空静默」** —— 实测与 L1 起点几乎相同、从不拦截，纯冗余。
    force=True ⇒ 不拦截（仍返回 blocked/reasons 供调用方记录日志）。"""
    d = {'players': None, 'lq': None, 'cq': None, 'bobSkip': False}
    reasons = []
    try:
        if server in RESTART_SKIP_EMPTY:
            # v6180（2026-11-06 事故修正）：**绝不能**因为「在线列表不可信」就跳过 L1 ——
            #   实测该豁免导致对**确有玩家在线**的 Bob 直接 kill（护栏零理由 ⇒ 放行）。
            #   改为：一律列入拦截理由，必须用户二次确认（force）才放行。
            # v6189（用户口径 2026-11-06）：Bob 在线列表不可信（只记录进服、不记录退服），
            #   每次终止都弹「不可信，需人工确认」太烦 ⇒ **移除该拦截理由、不再弹窗**。
            #   仅保留 L2 变空静默 + L3 集群目录静默作为保护。
            d['bobSkip'] = True
        else:
            n = _restart_players(server)
            d['players'] = n
            if n is None:
                reasons.append(u'在线人数探测失败（RCON 不可用）')
            elif int(n) > 0:
                reasons.append(u'仍有 %d 人在线' % int(n))
    except Exception:
        reasons.append(u'在线人数探测异常')
    try:
        st = (_RESTART.get('servers') or {}).get(server) or {}
        es = float(st.get('emptySince') or 0)
        if es > 0:
            d['lq'] = max(0.0, time.time() - es)   # v6197：仅回传观测值，不再作为拦截理由
    except Exception:
        pass
    try:
        cq = _restart_cluster_quiet_sec()
        d['cq'] = cq
        if cq is not None and cq < RESTART_CLUSTER_QUIET:
            reasons.append(u'集群目录 %ds 内有写入（需静默 %ds）' % (int(cq), RESTART_CLUSTER_QUIET))
    except Exception:
        pass
    return {'ok': (not reasons) or bool(force), 'blocked': bool(reasons),
            'force': bool(force), 'reasons': reasons, 'detail': d}


def _srvctl_one(server, action, message, cfg, progress=None):
    """单服单动作：返回 {server, profileName, ok, message, ms, retried}。"""
    prof = (SERVER_THEMES.get(server) or {}).get('name') or server
    t0 = time.time()
    retried = False
    last_msg = ''
    # v54b：to 必须在下面的 rcon 直连分支之前定义（v54 把它留在 for 循环前，
    # 导致 _rcon_exec(timeout=min(to, 20)) 抛 UnboundLocalError）
    to = cfg['timeout_destroy'] if action in ('destroy', 'fullbackup') else cfg['timeout']
    # v6179（用户口径）：终止类动作统一走三重静默护栏；force=True 时仅记录不拦截。
    #   _gate_passed 防止 savekill 内部递归调用 kill 时重复探测。
    # v6189（用户口径）：savekill 的护栏移到「保存通过后、终止前」复检 ——
    #   原来在入口判，而保存要 40 秒，期间玩家可以进服 ⇒ 护栏结论过期。
    #   kill 单动作无保存过程，仍在入口判。
    if action == 'kill' and not cfg.get('dry') and not cfg.get('_gate_passed'):
        # v6222：先过终止串行闸，再复检护栏 —— 保证复检结论是「轮到自己那一刻」的
        cfg = _kill_serial_prepare(cfg)
        _gate = _srvctl_terminal_gate(server, force=bool(cfg.get('force')))
        if _gate.get('blocked') and not _gate.get('force'):
            return {'server': server, 'profileName': prof, 'ok': False,
                    'message': (u'安全护栏拦截：' + u'；'.join(_gate.get('reasons') or []))[:300],
                    'ms': int((time.time() - t0) * 1000), 'retried': False,
                    'code': 'safety_blocked', 'gate': _gate}
        if _gate.get('blocked'):
            try:
                _srvctl_log('(system)', server, action, True, 0,
                            (u'护栏强制放行：' + u'；'.join(_gate.get('reasons') or []))[:200])
            except Exception:
                pass
        _cfg2 = dict(cfg); _cfg2['_gate_passed'] = True
        cfg = _cfg2
    # v54（2026-11-03）：RCON 类命令一律直连 RCON，**不回落** ASA Server Manager。
    # 根因：ASA Manager 的 /rcon 对 KickPlayer 只回显黄字、不执行（人踢不掉）；
    # 直连 RCON 由游戏服务器以 admin 身份执行，与 HA send_rcon_command_sync 完全一致。
    # 直连不依赖 asa_token，故本分支放在 token 校验之前。
    if action == 'rcon' and message:
        if cfg.get('dry'):
            return {'server': server, 'profileName': prof, 'ok': True,
                    'message': 'DRY-RUN 未实际下发（asa_dry_run=true）',
                    'ms': 0, 'retried': False, 'dry': True, 'via': 'rcon'}
        r_ok, r_text = _rcon_exec(server, message, timeout=min(to, 20))
        ms = int((time.time() - t0) * 1000)
        return {'server': server, 'profileName': prof, 'ok': bool(r_ok),
                'message': (r_text or ('OK' if r_ok else 'rcon failed'))[:300],
                'ms': ms, 'retried': False, 'via': 'rcon',
                'code': 'rcon_ok' if r_ok else 'rcon_error'}
    # v55（2026-11-03）：saveworld / destroy 也走直连 RCON —— 二者本质就是原生 RCON 命令，
    #   saveworld → SaveWorld          （前端按钮「保存世界」）
    #   destroy   → DestroyWildDinos   （前端按钮「清理恐龙」，清野生恐龙）
    # 走 ASAM 要多跳公网 HTTPS 且依赖 token；直连更快更稳。
    # kill（强制终止）/ start / savekill / fullbackup / update 属进程级操作，RCON 做不到，仍走 ASAM。
    if action in ('saveworld', 'destroy') and not message:
        if cfg.get('dry'):
            return {'server': server, 'profileName': prof, 'ok': True,
                    'message': 'DRY-RUN 未实际下发（asa_dry_run=true）',
                    'ms': 0, 'retried': False, 'dry': True, 'via': 'rcon'}
        _cmd = 'SaveWorld' if action == 'saveworld' else 'DestroyWildDinos'
        _tmo = 180 if action == 'destroy' else 40
        # v6190：瘦档基线必须在 **SaveWorld 之前** 取 ——
        #   原实现在 DinoData 稳定后才取，那时 .ark 已写完 ⇒ 基线 == 当前值
        #   ⇒ 「新档 < 基线 x 0.95」恒不成立，瘦档保护形同虚设。
        try:
            _ak_base0 = int(((_srv_observe_ark(server, (_srv_observe_log(server) or {}).get('map') or '') or {}).get('size')) or 0)
        except Exception:
            _ak_base0 = 0
        _t_save = time.time()
        # v6178：真进度上报（savekill 整合进度条用）
        if progress:
            try: progress(20, u'已下发，等待回执…')
            except Exception: pass
        r_ok, r_text = _rcon_exec(server, _cmd, timeout=_tmo)
        ms = int((time.time() - t0) * 1000)
        _out = {'server': server, 'profileName': prof, 'ok': bool(r_ok),
                'message': (r_text or ('OK' if r_ok else 'rcon failed'))[:300],
                'ms': ms, 'retried': False, 'via': 'rcon', 'cmd': _cmd,
                'code': 'rcon_ok' if r_ok else 'rcon_error'}
        # v6120：保存后补「DinoData 落盘且稳定」确认（原实现只有 RCON ack，插件导出是异步的）
        if action == 'saveworld' and r_ok:
            try:
                _budget = int(cfg.get('save_data_budget') or 45)
            except Exception:
                _budget = 45
            if progress:
                try: progress(35, u'存档中…')
                except Exception: pass
            # ---- v6190（用户口径）：**不再并行等 .ark** ----
            #   磁盘实测：插件在 .ark 稳定后 14~36 秒才导出 DinoData ⇒
            #   「DinoData 已稳定」即等价于「.ark 早已写完」，无需重复等 20 秒。
            #   v6219（P1-3）：DinoData 通过后**只做瘦档比对**（v6198 起已去掉 quick_check），0.2~0.4s。
            def _dw_prog(_w, _sf, _bd, _p=progress):
                try:
                    _p(min(85, 35 + int(min(1.0, float(_w) / 25.0) * 50)),
                       u'校验中 %ds' % int(_w))
                except Exception:
                    pass

            # v6191（用户口径）：**仅 Bob**（RESTART_SKIP_EMPTY，该图存档不落盘、DinoData 恒为空）
            #   跳过 DinoData 等待；否则会白等 budget 秒后判 no_files 失败。
            #   ⚠ 绝不能用「文件数=0 就跳过」——手动清空产物时文件数也是 0，
            #     那会放行一个正在从 0 重建的半截产物。
            _dd_skip = (server in RESTART_SKIP_EMPTY)
            if _dd_skip:
                _dw = {'ok': True, 'waited': 0, 'files': 0, 'reason': 'skip_no_dinodata',
                       'updated': [], 'quiet': 0, 'bad': [], 'busy': []}
                if progress:
                    try: progress(60, u'跳过校验…')
                    except Exception: pass
            else:
                _dw = _dinodata_wait_stable(server, since_ts=_t_save, budget=_budget,
                                            progress=(_dw_prog if progress else None))
            if progress:
                try:
                    progress(86, (u'跳过校验…' if _dd_skip else
                                  (u'复核中…' if _dw.get('ok') else
                                   (u'校验未通过（%s）' % (_dw.get('reason') or 'unknown')))))
                except Exception:
                    pass
            if _dw.get('ok'):
                _ak = _srvctl_check_ark_after_dd(server, base_size=_ak_base0)
            else:
                _ak = {'ok': False, 'path': '', 'size': 0, 'mtime': 0, 'baseSize': _ak_base0,
                       'thin': False, 'waited': 0, 'detail': '',
                       'reason': 'skipped_dd_failed', 'mode': 'skipped'}
            _out['data'] = _dw
            _out['message'] = (_out['message'] + ' · DinoData ' + (
                (u'该图不落盘，已跳过' if _dd_skip else
                 ('稳定 %.0fs（%d 文件）' % (float(_dw.get('waited') or 0), int(_dw.get('files') or 0))))
                if _dw.get('ok') else '未确认稳定（%s）' % (_dw.get('reason') or 'unknown')))[:300]
            # v6184（用户口径「最重要的校验就是 ark」）：.ark 四重判据已在上方并行块内完成（参数与等待均已并入）
            _out['ark'] = _ak
            _out['message'] = (_out['message'] + ' · .ark ' + (
                '落盘 ok(%s, %.1fMB, 瘦档比对)' % (
                    os.path.basename(_ak.get('path') or ''),
                    float(_ak.get('size') or 0) / 1048576.0)
                if _ak.get('ok') else '校验失败（%s%s）' % (
                    _ak.get('reason') or 'unknown',
                    ('，疑似瘦档 %.1fMB < 基线 %.1fMB' % (
                        float(_ak.get('size') or 0) / 1048576.0,
                        float(_ak.get('baseSize') or 0) / 1048576.0)) if _ak.get('thin') else '')))[:300]
            if progress:
                try:
                    progress(88, (u'准备终止' if _ak.get('ok')
                                  else u'校验未通过，已取消'))
                except Exception: pass
            # v6184：DinoData 或 .ark 任一不过 ⇒ 整体判失败（savekill 据此取消终止）
            if not _dw.get('ok') or not _ak.get('ok'):
                _out['ok'] = False
                _out['code'] = 'save_incomplete'
                _out['stage'] = 'verify'
        return _out
    # v6177（2026-11-06 用户实测「存档后终止只存档没终止」）：savekill 改为**后端原子编排** ——
    #   先 SaveWorld（含 DinoData 落盘稳定确认），通过后再 kill，全程由后端负责。
    #   原实现拆在浏览器里（saveworld + 前端轮询 phase 变 ok + 再发 kill），
    #   页面一关/刷新/切走轮询就丢 ⇒ 9 台批量时一台都没终止（srvctl.log 零 kill 记录）。
    if action == 'savekill' and not message:
        if progress:
            try: progress(10, u'开始存档…')
            except Exception: pass
        _r1 = _srvctl_one(server, 'saveworld', None, cfg, progress)
        if not _r1.get('ok'):
            return {'server': server, 'profileName': prof, 'ok': False,
                    'message': (u'存档未通过，已取消终止：' + str(_r1.get('message') or ''))[:300],
                    'ms': int(_r1.get('ms') or 0), 'retried': bool(_r1.get('retried')),
                    'stage': 'saveworld', 'save': _r1.get('data'), 'via': 'backend'}
        # v6189：终止前**复检**三重静默护栏（保存期间可能有人进服 / 集群写入）
        if not cfg.get('dry'):
            # v6222：复检**之前**先排队（全局终止串行闸）—— 多台同时停服会瞬间清零传送窗口
            cfg = _kill_serial_prepare(cfg)
            _gate = _srvctl_terminal_gate(server, force=bool(cfg.get('force')))
            if _gate.get('blocked') and not _gate.get('force'):
                return {'server': server, 'profileName': prof, 'ok': False,
                        'message': (u'安全护栏拦截（终止前复检）：' + u'；'.join(_gate.get('reasons') or []))[:300],
                        'ms': int(_r1.get('ms') or 0), 'retried': False,
                        'code': 'safety_blocked', 'gate': _gate, 'stage': 'gate',
                        'save': _r1.get('data'), 'ark': _r1.get('ark'), 'via': 'backend'}
            if _gate.get('blocked'):
                try:
                    _srvctl_log('(system)', server, action, True, 0,
                                (u'护栏强制放行：' + u'；'.join(_gate.get('reasons') or []))[:200])
                except Exception:
                    pass
        if progress:
            try: progress(90, u'正在终止…')
            except Exception: pass
        _r2 = _srvctl_one(server, 'kill', None, dict(cfg, _gate_passed=True))
        # v6185：把 .ark 校验结果一并回传（成功路径也要让人看到校验过了什么）
        _ak1 = _r1.get('ark') or {}
        _ak_txt = ''
        try:
            if _ak1:
                _ak_txt = u'[.ark %s %.1fMB 稳定%.0fs] ' % (
                    'ok' if _ak1.get('ok') else 'FAIL',
                    float(_ak1.get('size') or 0) / 1048576.0,
                    float(_ak1.get('quiet') or 0))
        except Exception:
            _ak_txt = ''
        return {'server': server, 'profileName': prof, 'ok': bool(_r2.get('ok')),
                'message': (u'存档校验通过' + _ak_txt + u'→ 终止：' + str(_r2.get('message') or ''))[:300],
                'ms': int(_r1.get('ms') or 0) + int(_r2.get('ms') or 0),
                'retried': bool(_r2.get('retried')),
                'stage': 'kill', 'save': _r1.get('data'), 'ark': _ak1, 'via': 'backend'}
    if not cfg.get('token'):
        return {'server': server, 'profileName': prof, 'ok': False,
                'message': 'asa_token 未配置', 'ms': 0, 'retried': False, 'code': 'asa_no_token'}
    if cfg.get('dry'):
        return {'server': server, 'profileName': prof, 'ok': True,
                'message': 'DRY-RUN 未实际下发（asa_dry_run=true）',
                'ms': 0, 'retried': False, 'dry': True}
    for attempt in (0, 1):
        if attempt == 1:
            retried = True
            time.sleep(1)
        try:
            # P3c（实测 2026-11-03）：ASA Server Manager **只接受英文 ID**（Bob），
            # 传中文名（俱乐部）直接 404 Profile not found ⇒ 转发用 server ID
            payload = {'profileName': server}
            if message is not None:
                payload['message'] = message
            code, text = _asa_http('POST', cfg['base'] + '/' + action, cfg['token'],
                                   payload, timeout=to, verify=cfg['verify'])
            ms = int((time.time() - t0) * 1000)
            snippet = (text or '').strip()[:300]
            if 200 <= code < 300:
                return {'server': server, 'profileName': prof, 'ok': True,
                        'message': snippet or 'OK', 'ms': ms, 'retried': retried}
            last_msg = 'HTTP %s %s' % (code, snippet)
            if code in (401, 403):
                return {'server': server, 'profileName': prof, 'ok': False,
                        'message': 'ASA Token 无效或已过期', 'ms': ms,
                        'retried': retried, 'code': 'asa_unauthorized'}
        except Exception as e:
            last_msg = '%s: %s' % (type(e).__name__, e)
    return {'server': server, 'profileName': prof, 'ok': False, 'message': last_msg,
            'ms': int((time.time() - t0) * 1000), 'retried': True, 'code': 'asa_error'}


def _srvctl_acquire(server, action):
    with _SRVCTL_BUSY_LOCK:
        k = (server, action)
        if k in _SRVCTL_BUSY:
            return False
        _SRVCTL_BUSY[k] = time.time()
        return True


def _srvctl_release(server, action):
    with _SRVCTL_BUSY_LOCK:
        _SRVCTL_BUSY.pop((server, action), None)


def _srvctl_run(user, servers, action, message, force=False, src='', silent=False):
    """并发执行（max_workers=4）；results[] 顺序与 servers 一致。失败自动重试 1 轮。
    v6179：force=True ⇒ 终止类动作跳过安全护栏（用户二次确认后放行）。
    v6203：src 透传到审计日志（前端重试传 retry ⇒ 日志标 [重试]）。
    v6219（P0-2）：silent=True ⇒ **不建/不写任务行**（编排内部动作由编排行统一表达）。
      注意三处 _utask_put 必须**同时**跳过，漏一处就会残留任务条。"""
    cfg = _srvctl_cfg()
    if force:
        cfg = dict(cfg); cfg['force'] = True
    results = [None] * len(servers)
    # v6179（用户口径修正）：「整合」指**每条任务内部**贯穿「存档 → 校验完整 → 终止」，
    #   不是把多台合成一条 ⇒ 多选 N 台就建 N 条任务，各自独立进度 + 各自分步圆点。
    if action != 'start' and not silent:
        # v6122：除 start（由 startq 驱动进度）外，先登记任务 → 全客户端共享
        # v6219（P0-2）：silent 时跳过（编排内部动作）
        for _s in servers:
            try:
                _utask_put('%s|%s' % (_s, action), _s, action, user,
                           msg=u'已下发，等待回执…', pct=10, phase='run',
                           steps=(_savekill_steps_obj({}) if action == 'savekill' else None))
            except Exception:
                pass

    def _job(idx, srv):
        # v6179：savekill 把阶段进度写回**本台**任务（含分步圆点，复用自动重启 steps 机制）
        _prog = None
        if action == 'savekill' and not silent:
            def _prog(pct, msg, _s=srv):
                try:
                    _p = int(pct or 0)
                    _utask_put('%s|%s' % (_s, action), _s, action, user,
                               msg=_utask_clean_text(msg), pct=max(3, min(97, _p)), phase='run',
                               steps=_savekill_steps_obj(_savekill_states_by_pct(_p)))
                except Exception:
                    pass
        try:
            results[idx] = _srvctl_one(srv, action, message, cfg, _prog)
        except Exception as e:
            results[idx] = {'server': srv,
                            'profileName': (SERVER_THEMES.get(srv) or {}).get('name') or srv,
                            'ok': False, 'message': repr(e), 'ms': 0,
                            'retried': False, 'code': 'asa_error'}

    futs = [_SRVCTL_POOL.submit(_job, i, s) for i, s in enumerate(servers)]
    for f in futs:
        try:
            f.result()
        except Exception:
            _sexc('srvctl_run')
            pass
    for r in results:
        if r:
            _srvctl_log(user, r.get('server'), action, r.get('ok'), r.get('ms', 0),
                        r.get('message', ''), src=src)
            # v6122：收尾同步任务总线（start 由 startq 自己收尾）
            if action != 'start' and not silent:
                try:
                    _ok = bool(r.get('ok'))
                    _extra = {}
                    if action == 'savekill':
                        # v6179：收尾把三步全置 ok；失败则把「存档」步标 fail
                        if _ok:
                            _extra['steps'] = _savekill_steps_obj(
                                {'saveworld': 'ok', 'verify': 'ok', 'kill': 'ok'})
                        else:
                            _stx = _savekill_states_by_pct(0)
                            _stx['saveworld'] = 'fail'
                            _extra['steps'] = _savekill_steps_obj(_stx)
                    _utask_put('%s|%s' % (r.get('server'), action), r.get('server'), action, user,
                               msg=(r.get('message') or (u'完成' if _ok else u'失败'))[:150],
                               pct=100 if _ok else 0, phase='ok' if _ok else 'fail',
                               err='' if _ok else (r.get('message') or u'失败'), **_extra)
                except Exception:
                    pass
    return [r for r in results if r]


def _srvctl_job_new(user, action, servers, src=''):
    """长任务（destroy / fullbackup）异步 job。
    v6203：src 随 job 带入 _srvctl_run（否则 destroy 的审计永远拿不到来源）。"""
    jid = 'j%d_%d' % (int(time.time() * 1000), len(_SRVCTL_JOBS))
    with _SRVCTL_JOBS_LOCK:
        now = time.time()
        for k in [k for k, v in _SRVCTL_JOBS.items() if now - v.get('ts', 0) > _SRVCTL_JOB_TTL]:
            _SRVCTL_JOBS.pop(k, None)
        _SRVCTL_JOBS[jid] = {'ts': now, 'done': False, 'action': action,
                             'servers': list(servers), 'user': user, 'results': [],
                             'src': (src or '')}

    def _run():
        try:
            res = _srvctl_run(user, servers, action, None, src=src)
        except Exception as e:
            res = [{'server': s, 'profileName': (SERVER_THEMES.get(s) or {}).get('name') or s,
                    'ok': False, 'message': repr(e), 'ms': 0, 'retried': False} for s in servers]
        with _SRVCTL_JOBS_LOCK:
            j = _SRVCTL_JOBS.get(jid)
            if j:
                j['results'] = res
                j['done'] = True
                j['ts'] = time.time()

    _SRVCTL_JOB_POOL.submit(_run)
    return jid


def _srvctl_job_view(jid):
    with _SRVCTL_JOBS_LOCK:
        j = _SRVCTL_JOBS.get(jid)
        if not j:
            return None
        return {'jobId': jid, 'done': bool(j.get('done')), 'action': j.get('action'),
                'servers': j.get('servers') or [], 'results': j.get('results') or []}


# ===== P1（v5983）：真实进度观测（只读，供前端进度条）=====
#   日志：D:\ARK Server\Servers\<ID>\ShooterGame\Saved\Logs\ShooterGame.log（按进程重建，首行=本次启动时刻）
#   存档：D:\ARK Server\Servers\<ID>\ShooterGame\Saved\SavedArks\<Map>\<Map>.ark（mtime=最近落盘时间）
SRVCTL_LOG_REL = os.path.join('ShooterGame', 'Saved', 'Logs', 'ShooterGame.log')
SRVCTL_ARKS_REL = os.path.join('ShooterGame', 'Saved', 'SavedArks')

# 启动里程碑（顺序即进度顺序）；正则基于真实 Isl 日志实测标定
SRVCTL_BOOT_MARKS = [
    ('proc_open',    u'启动游戏进程', r'Log file open,'),
    ('ark_version',  u'读取游戏版本', r'ARK Version:\s*[\d.]+'),
    ('cfcore',       u'初始化模组框架', r'LogCFCore: InternalSettings called'),
    ('mods_check',   u'校验模组文件', r'(No need to update existing mod|Mod valid)'),
    ('mods_load',    u'加载模组资源', r'UShooterEngine::LoadGameMods'),
    ('battleye',     u'启动反作弊', r'BattlEye successfully started'),
    ('world_load',   u'加载世界存档', r'StructureHibernation:.*on this boot'),
    ('started',      u'服务器已启动', r'has successfully started!'),
    ('steam_eos',    u'Steam / EOS 验证', r'EOS ownership validation initialized: Success'),
    ('full_startup', u'应用启动参数', r'Full Startup:\s*[\d.]+ seconds'),
    ('advertising',  u'对外开放加入', r'advertising for join'),
]


def _srv_observe_log(server):
    """读该服 ShooterGame.log -> {path,size,firstLineAt,arkVersion,map,fullStartupSec,marks,mtime,err}"""
    p = os.path.join(CFG_SERVERS_DIR, server, SRVCTL_LOG_REL)
    out = {'path': p, 'size': 0, 'mtime': 0, 'firstLineAt': '', 'arkVersion': '',
           'map': '', 'fullStartupSec': None, 'marks': {}}
    try:
        st = os.stat(p)
        out['size'] = st.st_size
        out['mtime'] = int(st.st_mtime)
        with open(p, 'r', encoding='utf-8', errors='replace') as f:
            txt = f.read()
    except Exception as e:
        out['err'] = '%s: %s' % (type(e).__name__, e)
        return out
    try:
        m = re.search(r'Log file open,\s*(\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})', txt)
        if m:
            out['firstLineAt'] = m.group(1)
        m = re.search(r'ARK Version:\s*([\d.]+)', txt)
        if m:
            out['arkVersion'] = m.group(1)
        m = re.search(r'Commandline:\s*"([^"]+)"', txt)
        if m:
            out['map'] = m.group(1)
        m = re.search(r'Full Startup:\s*([\d.]+) seconds', txt)
        if m:
            out['fullStartupSec'] = float(m.group(1))
        for k, _label, pat in SRVCTL_BOOT_MARKS:
            out['marks'][k] = bool(re.search(pat, txt))
    except Exception as e:
        out['err'] = '%s: %s' % (type(e).__name__, e)
    return out


def _srv_observe_ark(server, map_name):
    """主存档信息 -> {map,path,mtime,size,err}
    v5984-fix：日志里的地图名（如 BobsMissions_WP）与存档**目录名**可能不一致
    （Bob 的目录叫 BobsMissions 但文件名是 BobsMissions_WP.ark）⇒ 按**文件名**匹配优先，
    并且一律排除 size<=0 的空占位文件（曾误选 LostColony_WP.ark 空文件）。"""
    base = os.path.join(CFG_SERVERS_DIR, server, SRVCTL_ARKS_REL)
    out = {'map': map_name or '', 'path': '', 'mtime': 0, 'size': 0}
    try:
        if not os.path.isdir(base):
            out['err'] = 'SavedArks not found'
            return out
        want = ((map_name or '') + '.ark') if map_name else ''
        cands = []
        for d in os.listdir(base):
            dp = os.path.join(base, d)
            if not os.path.isdir(dp):
                continue
            try:
                files = os.listdir(dp)
            except Exception:
                continue
            if want:
                for f in files:
                    if f == want:
                        cands.append((2, os.path.join(dp, f)))
                        break
            for f in files:
                if f.lower().endswith('.ark'):
                    cands.append((1, os.path.join(dp, f)))
                    break
        best = None
        seen = set()
        for pri, fp in cands:
            if fp in seen:
                continue
            seen.add(fp)
            try:
                st = os.stat(fp)
            except Exception:
                continue
            if st.st_size <= 0:
                continue
            score = (pri, st.st_mtime)
            if best is None or score > best[0]:
                best = (score, fp, st)
        if best:
            out['path'] = best[1]
            out['mtime'] = int(best[2].st_mtime)
            out['size'] = best[2].st_size
            if not out['map']:
                out['map'] = os.path.basename(best[1])[:-4]
        else:
            out['err'] = 'ark not found'
    except Exception as e:
        out['err'] = '%s: %s' % (type(e).__name__, e)
    return out


# ===== v6007（用户口径 2026-11-03）：存档完整性校验 =====
def _srv_ark_quickcheck(server):
    """在**服务器本地**（非 UNC）对主 .ark 跑 SQLite `PRAGMA quick_check`，只读。

    背景：实测「存档后终止」写出过比旧档小 19%~56% 的存档（结构完整但内容陈旧）。
    根因是旧实现把「.ark 的 mtime 变了」当成「存档写完」——mtime 在开始写时就变。
    现在前端要求：mtime 变化 -> size+mtime 连续 20s 稳定 -> 本接口 quick_check == ok
    -> 才允许下发 kill。
    """
    out = {'server': server, 'path': '', 'size': 0, 'mtime': 0,
           'ok': False, 'detail': '', 'ms': 0}
    try:
        lg = _srv_observe_log(server) or {}
        ak = _srv_observe_ark(server, lg.get('map') or '') or {}
        p = ak.get('path') or ''
        out['path'] = p
        out['size'] = int(ak.get('size') or 0)
        out['mtime'] = int(ak.get('mtime') or 0)
        if not p or not os.path.isfile(p):
            out['detail'] = 'ark not found'
            return out
        t0 = time.time()
        con = None
        try:
            import sqlite3 as _sq
            con = _sq.connect(p, timeout=30)
            con.execute('PRAGMA query_only = ON')
            rows = con.execute('PRAGMA quick_check').fetchmany(3)
            vals = [str(r[0]) for r in rows]
            out['detail'] = (' / '.join(vals))[:300]
            out['ok'] = (len(vals) == 1 and vals[0].strip().lower() == 'ok')
        finally:
            if con is not None:
                try:
                    con.close()
                except Exception:
                    pass
        out['ms'] = int((time.time() - t0) * 1000)
    except Exception as e:
        out['detail'] = '%s: %s' % (type(e).__name__, e)
    return out


def _srvctl_check_ark_after_dd(server, base_size=0):
    """v6190（用户口径）：DinoData 稳定后的 .ark 快速校验（**不再等 20s**）。

    依据（磁盘实测）：插件在 .ark 落盘稳定后 **14~36 秒**才开始导出 DinoData
    （Gen +14s / Isl +30s / Sco +30s / Cen +33s / Rag +34s / Val +36s）。
    所以「DinoData 已稳定」即等价于「.ark 早已写完」⇒ 只需一次
    quick_check（0.2~0.4s）+ 瘦档判定，无需重复等待。

    另：瘦档基线必须由调用方在 **SaveWorld 之前** 取（见 _ak_base0），
    否则基线与当前值相同 ⇒ 瘦档判定恒不触发。"""
    t0 = time.time()
    try:
        _lg = _srv_observe_log(server) or {}
    except Exception:
        _lg = {}
    try:
        ak = _srv_observe_ark(server, _lg.get('map') or '') or {}
    except Exception:
        ak = {}
    path = ak.get('path') or ''
    sz = int(ak.get('size') or 0)
    mt = int(ak.get('mtime') or 0)
    _base = int(base_size or 0)
    thin = bool(_base and sz and sz < int(_base * 0.95))
    if not path:
        return {'ok': False, 'path': '', 'size': 0, 'mtime': 0, 'baseSize': _base,
                'thin': False, 'waited': round(time.time() - t0, 1),
                'reason': 'ark_not_found', 'detail': '', 'mode': 'after_dd'}
    # v6198（用户口径）：**不再做 quick_check** —— 插件导出 DinoData 前已校验过 .ark 落盘完整性
    #   （实测 .ark 稳定后 14~36 秒才导出），不必重复。此处只做**零成本**的瘦档比对，
    #   用于抓住「结构能读但内容陈旧」（v6007 实测写出过比旧档小 19%~56% 的存档）。
    if not path:
        _why = 'ark_not_found'
    elif sz <= 0:
        _why = 'ark_empty'
    elif thin:
        _why = 'ark_thin'
    else:
        _why = ''
    _ok = (_why == '')
    return {'ok': _ok, 'path': path, 'size': sz, 'mtime': mt, 'baseSize': _base,
            'thin': thin, 'waited': round(time.time() - t0, 1),
            'reason': _why, 'detail': '', 'mode': 'size_only'}


# ===== v6004（用户口径 2026-11-03）：多服启动队列 =====
# 目标：方案 C（快速接棒）+ 硬约束「任何时刻处于 world_load~started 重压期的服 ≤ 2」
#   · 放行闸门：相邻两台下发间隔 ≥ 8 秒（只防「瞬间连起 11 台」）
#   · 重压槽位：marks.world_load 已出现 且 marks.started 未出现 的服数上限 2
#               ⇒ 永远不会出现 3 台同时 world_load
#   · 兜底：重压期超 400 秒未到 started ⇒ 视为异常，释放槽位（防整队死锁）
#   · 实际节奏：两台一组并行推进，11 台约 19~25 分钟（受磁盘 IO 争抢影响）
SRVCTL_STARTQ_MIN_GAP = 8            # 相邻两台最小间隔（秒）
SRVCTL_STARTQ_HEAVY_MAX = 2          # 重压期并发上限
SRVCTL_STARTQ_HEAVY_TIMEOUT = 900    # 槽位占用超时（秒）；v6011：600->900（完成判据改 advertising，每台多等 ~30s）
SRVCTL_STARTQ_ITEM_TIMEOUT = 900     # 单台总超时（秒）
SRVCTL_STARTQ_TICK = 2               # 轮询间隔（秒）
SRVCTL_STARTQ_FIRST_TIMEOUT = 180
# v6343（用户实测「启动失败后没有自动重试」）：启动队列失败自动重新入队的次数上限
#   （实测失败原因多为瞬时性：Error querying server mods: ApiError serverUnreachable / CF 超时）
STARTQ_AUTO_RETRY = 3   # v6344（用户口径）：自动重试上限 2 -> 3    # v6011：等「日志首行出现/变化」上限（原硬编码 90s；实测 Bob 67s 才出首行）
_SRVCTL_STARTQ_LOCK = threading.Lock()   # v6004fix：与 9 处使用名保持一致（原缺前导下划线 -> NameError -> 请求断连）
_SRVCTL_STARTQ = {
    'running': False, 'user': '', 'ts': 0.0, 'total': 0,
    'queue': [], 'active': {}, 'done': [], 'lastSent': 0.0,
}
_SRVCTL_STARTQ_THREAD = None
_SRVCTL_BOOT_ORDER_BE = [k for k, _l, _p in SRVCTL_BOOT_MARKS]
_SRVCTL_BOOT_PCT_BE = {'proc_open': 2, 'ark_version': 5, 'cfcore': 8, 'mods_check': 12,
                       'mods_load': 18, 'battleye': 25, 'world_load': 45, 'started': 75,
                       'steam_eos': 82, 'full_startup': 90, 'advertising': 100}
_SRVCTL_BOOT_LABEL_BE = {k: l for k, l, _p in SRVCTL_BOOT_MARKS}


def _startq_drop(srv, user=''):
    """v6439：把该服从「启动队列」彻底剔除，并**清零自动重试计数**。

    背景（Bob 2026-11-09 实测）：只发 kill 杀进程时，`_startq_loop` 下一轮会看到
      `pst == 'Stopped'` 且 `seenProc == True` ⇒ 判「启动过程中进程已退出」= 失败
      ⇒ 走 `STARTQ_AUTO_RETRY`（3 次）自动重新入队并拉起 ⇒ 用户点中止 = 杀了又拉。
    本函数让「人工终止」成为**明确的不再启动**。

    返回 True 表示确实从队列里移除了东西（active 或 queue 命中）。
    """
    srv = str(srv or '').strip()
    if not srv:
        return False
    removed = False
    with _SRVCTL_STARTQ_LOCK:
        _v = _SRVCTL_STARTQ['active'].pop(srv, None)
        try:
            while srv in _SRVCTL_STARTQ['queue']:
                _SRVCTL_STARTQ['queue'].remove(srv)
                removed = True
        except Exception:
            pass
        # 关键：清零 tries，否则下次启动会被历史计数拖累（少几次重试机会）
        try:
            _trs = _SRVCTL_STARTQ.get('tries')
            if isinstance(_trs, dict):
                _trs.pop(srv, None)
        except Exception:
            pass
        if _v is not None:
            removed = True
            try:
                _SRVCTL_STARTQ['done'].append({
                    'server': srv, 'ok': False,
                    'pct': int(_v.get('pct') or 0),
                    'msg': u'已中止',
                    'err': u'已由 %s 手动中止启动' % (user or u'系统'),
                    't_end': int(time.time())})
            except Exception:
                pass
    if not removed:
        return False
    try:
        _srv_lock_clear(srv, 'queue|%s' % srv)
    except Exception:
        pass
    try:
        _utask_put('%s|start' % srv, srv, 'start', user or 'srvctl',
                   msg=u'已中止启动', pct=0, phase='fail',
                   err=u'已手动中止启动（操作人 %s）—— 不会自动重试' % (user or u'系统'))
    except Exception:
        _sexc('startq_drop_task')
    try:
        _restart_log('STARTQ DROP %s by %s（人工终止 ⇒ 禁止自动重试）' % (srv, user or '?'))
    except Exception:
        pass
    return True


def _startq_pct(marks):
    """按已命中里程碑取最大进度与标签。"""
    idx = -1
    for i, k in enumerate(_SRVCTL_BOOT_ORDER_BE):
        if marks.get(k):
            idx = i
    if idx < 0:
        return 0, u'启动中'
    k = _SRVCTL_BOOT_ORDER_BE[idx]
    return _SRVCTL_BOOT_PCT_BE.get(k, 0), _SRVCTL_BOOT_LABEL_BE.get(k, k)


# v6011：全服进程状态快照（转发 ASA /server-status，10s 缓存）
_SRVCTL_PSNAP = {'ts': 0.0, 'map': {}, 'err': ''}


def _srvctl_proc_snapshot(max_age=10):
    """{server: 'Running'|'Starting'|'Stopped'}；失败/未配置返回 {}。

    日志只能说明「有没有进展」，分不清「慢」与「死」；进程状态才是硬判据。
    与 GET /api/srvctl/status 同源（转发 ASA /server-status），10s 缓存避免打爆 ASA。
    """
    now = time.time()
    if _SRVCTL_PSNAP['map'] and (now - float(_SRVCTL_PSNAP['ts'] or 0)) < max_age:
        return _SRVCTL_PSNAP['map']
    mp = {}
    try:
        cfg = _srvctl_cfg()
        if not cfg.get('token'):
            _SRVCTL_PSNAP.update({'ts': now, 'map': {}, 'err': 'no_token'})
            return {}
        code, text = _asa_http('GET', cfg['base'] + '/server-status', cfg['token'],
                               None, timeout=cfg['timeout'], verify=cfg['verify'])
        if not (200 <= code < 300):
            _SRVCTL_PSNAP.update({'ts': now, 'map': {}, 'err': 'HTTP %s' % code})
            return {}
        for it in (json.loads(text) or {}).get('servers') or []:
            pn = str(it.get('ProfileName') or '')
            if pn in SERVERS:
                mp[pn] = str(it.get('Status') or '')
    except Exception as e:
        _SRVCTL_PSNAP.update({'ts': now, 'map': {},
                              'err': '%s: %s' % (type(e).__name__, e)})
        return {}
    _SRVCTL_PSNAP.update({'ts': now, 'map': mp, 'err': ''})
    return mp


def _startq_logtail(server, n=1):
    """取日志最后 n 行摘要（失败返回空串），用于失败原因里指出崩在哪一行。"""
    try:
        p = os.path.join(CFG_SERVERS_DIR, server, SRVCTL_LOG_REL)
        with open(p, 'r', encoding='utf-8', errors='replace') as f:
            lines = [x.strip() for x in f if x.strip()]
        if not lines:
            return u''
        return u'｜日志尾：' + u' / '.join(x[:150] for x in lines[-n:])
    except Exception:
        return u''


def _startq_heavy_count():
    return sum(1 for v in _SRVCTL_STARTQ['active'].values() if v.get('heavy'))


def _startq_view():
    # v6271（用户口径 2026-11-08「将要启动的也要算在启动队列里 · 一个批次只允许一个结算」）：
    #   原视图只统计**真正下发过 startq** 的台，编排里另外 N 台处于 ready 的完全不可见
    #   ⇒ 面板显示「已完成 0/2 · 排队 0 台」，用户以为「一堆排队的没一个开始」。
    #   这里先把编排中尚未下发启动的服取成快照（锁外读 _RESTART，避免与 _SRVCTL_STARTQ_LOCK 嵌套）。
    _pend_snap, _batch_total = [], 0
    _batch_run = False
    try:
        if _RESTART.get('running'):
            _batch_run = True
            _sv0 = _RESTART.get('servers') or {}
            # v6277（用户实测 2026-11-08「明明批次中仅 4 台，为啥启动队列显示 11 台」）：
            #   原 `_batch_total = len(_sv0)` 把**保持停服**的 7 台（v6272 hold-stopped）也算进来，
            #   再经 `_tot = max(q.total, _batch_total)` 抬到 11 ⇒ 队列行显示「已完成 x/11」，
            #   而实际进队列的只有 4 台。改为只数「原本在运行」的台。
            _batch_total = sum(1 for _v0 in _sv0.values()
                               if bool(_v0.get('wasRunning', True)))
            for _s0, _st0 in _sv0.items():
                # v6276（用户口径「只要批次涉及到启动的，从批次启动开始就常驻启动队列行」）：
                #   原只收 ready/savekill/sync（尚未进起服段）⇒ 批次刚开始时若全部台还在公告/空置，
                #   pending 为空、total=0 ⇒ 前端队列行整块不显示。
                #   现扩到「起服段(startq)」并排除**原本停服**的台
                #   （v6272 原则：原本停服的台直接 done，不进启动队列，不该算进待启动）。
                if not bool(_st0.get('wasRunning', True)):
                    continue
                # v6276b：判据再放宽一档 —— 批次刚开始时台还停在 announce/empty/quiet/saveworld，
                #   若只认 ready/savekill/sync/startq，pending 恒为 0 ⇒ 队列行照样整块不显示，
                #   违反「从批次启动开始就常驻」。改为「本批次内、原本在跑、且尚未完成」全部计入。
                if str(_st0.get('phase') or '') not in ('done', 'fail', 'verify'):
                    _pend_snap.append(_s0)
    except Exception:
        _pend_snap, _batch_total, _batch_run = [], 0, False
    with _SRVCTL_STARTQ_LOCK:
        q = _SRVCTL_STARTQ
        act = []
        now = time.time()
        for srv, v in q['active'].items():
            act.append({'server': srv, 'pct': v.get('pct', 0), 'label': v.get('label', ''),
                        'el': int(now - float(v.get('t0') or now)),
                        'heavy': bool(v.get('heavy')), 'msg': v.get('msg', '')})
        # v6186（用户口径）：「已完成」必须是**启动成功**的台数 ——
        #   原 doneCount=len(done) 把 ok=False 也算完成，导致「已完成 3/3」但实际只起了 1 台。
        _okcnt = sum(1 for x in q['done'] if x.get('ok'))
        # v6271：「将要启动的」= 编排中 ready/savekill/sync 且尚未入队/未在启动的台
        _pend = [x for x in _pend_snap
                 if x not in q['queue'] and x not in q['active']]
        # v6271：total 固定为**批次总数** —— 原来每 tick 用 len(queue)+len(active)+len(done)
        #   重算，是个滑动值（批次跑到一半 total 只有 2）⇒ 出现「2 台一成功一失败就结算」的错觉。
        _tot = max(int(q.get('total') or 0), int(_batch_total or 0))
        # v6278（用户口径 2026-11-08「启动队列在不同客户端显隐不一致，要求更稳定判定」）：
        #   前端原先用**各端本地**的 LB_STARTQ.endAt 计时「跑完 60 秒后消失」⇒ 各端打开时间不同
        #   ⇒ 同一批次在 A 端还显示、B 端已消失。改为后端下发统一时间戳 endTs（最后完成时刻）。
        _endts = 0
        try:
            for _x in q['done']:
                _te = int(_x.get('t_end') or 0)
                if _te > _endts:
                    _endts = _te
        except Exception:
            _endts = 0
        return {'running': bool(q['running']), 'user': q['user'], 'ts': int(q['ts'] or 0),
                'endTs': _endts,
                'total': _tot, 'doneCount': len(q['done']),
                'okCount': _okcnt, 'failCount': len(q['done']) - _okcnt,
                'done': list(q['done']), 'active': act,
                'activeCount': len(act), 'heavyCount': _startq_heavy_count(),
                'queued': list(q['queue']), 'queuedCount': len(q['queue']),
                'pending': _pend, 'pendingCount': len(_pend),
                # v6276：批次视角（前端「批次含启动 ⇒ 从批次开始就常驻队列行」用）
                'batchRunning': bool(_batch_run),
                'batchTotal': int(_batch_total or 0),
                'external': list(_SRVCTL_STARTQ.get('external') or []),
                'heavyMax': SRVCTL_STARTQ_HEAVY_MAX}


def _startq_worker():
    """后台推进：轮询各服实际阶段 -> 收割完成的 -> 有空重压槽位就下发下一台。"""
    try:
        cfg = _srvctl_cfg()
    except Exception:
        cfg = {}
    while True:
        time.sleep(SRVCTL_STARTQ_TICK)
        now = time.time()
        with _SRVCTL_STARTQ_LOCK:
            if not _SRVCTL_STARTQ['running']:
                return
            srv_list = list(_SRVCTL_STARTQ['active'].keys())
        # v6219（P2-3）：外部启动检测（**fail-open**）—— ASAM 界面直接点启动会绕过本队列，
        #   重压池统计不到 ⇒ 可能与队列内启动同时进入 world_load（实际并发 >2）。
        #   每 30s 用 ASA /server-status 快照比对一次；快照失败则保持上次结果，绝不阻断队列。
        try:
            if (now - float(_SRVCTL_STARTQ.get('extTs') or 0)) > 30:
                _SRVCTL_STARTQ['extTs'] = now
                _ps2 = _srvctl_proc_snapshot() or {}
                if _ps2:
                    with _SRVCTL_STARTQ_LOCK:
                        _act2 = set(_SRVCTL_STARTQ['active'].keys())
                        _que2 = set(_SRVCTL_STARTQ['queue'])
                    _ex2 = [_s3 for _s3, _st3 in _ps2.items()
                            if str(_st3) == 'Starting' and _s3 not in _act2 and _s3 not in _que2]
                    _SRVCTL_STARTQ['external'] = _ex2
                    if _ex2:
                        _restart_log('EXTERNAL start: %s（ASAM 侧启动，重压池已让路）' % ','.join(_ex2))
        except Exception:
            pass
        # ---- v6186（用户口径「排队能在进度条上显示序号」）：刷新排队位次 ----
        #   只在位次变化时写，避免每 tick 写盘
        try:
            with _SRVCTL_STARTQ_LOCK:
                _qlist = list(_SRVCTL_STARTQ['queue'])
                _quser = _SRVCTL_STARTQ.get('user') or ''
            if _qlist:
                _posmap = {}
                try:
                    for _t in _UTASK['items']:
                        _k = str(_t.get('key') or '')
                        if _k.endswith('|start'):
                            _posmap[_k[:-6]] = (_t.get('meta') or {}).get('qpos')
                except Exception:
                    _posmap = {}
                _qsrc2 = _SRVCTL_STARTQ.get('qsrc') or {}
                for _i, _s in enumerate(_qlist):
                    _pos = _i + 1
                    if str(_qsrc2.get(_s) or '') in DEPLOY_SRCS:   # v6339：分发条不写 start 任务
                        continue
                    if _posmap.get(_s) == _pos:
                        continue
                    try:
                        # v6194（用户口径）：排队位次已在右侧 `#N` 显示，
                        #   副文不再重复「第 N 位（前面 N-1 台）」。
                        _utask_put('%s|start' % _s, _s, 'start', _quser,
                                   msg=u'排队中…', pct=0, phase='queue',
                                   meta={'qpos': _pos})
                    except Exception:
                        pass
        except Exception:
            pass
        # ---- 采样各服实际阶段（读日志，放锁外）----
        try:
            _psnap = _srvctl_proc_snapshot() or {}
        except Exception:
            _psnap = {}
        for srv in srv_list:
            # v6187：刚占位（sending=True）尚未真正拉起 ⇒ 跳过采样，避免读到上一轮旧日志
            with _SRVCTL_STARTQ_LOCK:
                if bool((_SRVCTL_STARTQ['active'].get(srv) or {}).get('sending')):
                    continue
            try:
                lg = _srv_observe_log(srv) or {}
            except Exception:
                continue
            marks = lg.get('marks') or {}
            fl = str(lg.get('firstLineAt') or '')
            pct, label = _startq_pct(marks)
            with _SRVCTL_STARTQ_LOCK:
                v = _SRVCTL_STARTQ['active'].get(srv)
                if not v:
                    continue
                if v.get('phase') in ('ok', 'fail'):
                    continue
                base_first = v.get('baseFirst') or ''
                # v6011 修复（v6010 根因）：baseFirst 为**空串**（下发时日志文件不存在）
                #   时，原式 `fl and base_first and fl != base_first` 恒 False ⇒
                #   「日志文件从无到有」这条最典型的首次启动路径 100% 误判
                #   「未见新进程启动」（Rag 21:11:59 / Val 21:13:25 实测）。
                #   改为：基线为空时，只要现在能读到首行就算新进程。
                new_proc = bool(fl) and (not base_first or fl != base_first)
                el = now - float(v.get('t0') or now)
                # v6011：进程状态兜底 —— 日志只能证明「有进展」，证明不了「还活着」
                pst = _psnap.get(srv) or ''
                if pst in ('Starting', 'Running'):
                    v['seenProc'] = True
                if v.get('seenProc') and pst == 'Stopped':
                    v.update({'ok': False, 'phase': 'fail', 'heavy': False,
                              'err': u'启动过程中进程已退出（ASA 状态 %s）%s'
                                     % (pst, _startq_logtail(srv))})
                    continue
                if ((not v.get('seenProc')) and pst == 'Stopped'
                        and el > SRVCTL_STARTQ_FIRST_TIMEOUT):
                    v.update({'ok': False, 'phase': 'fail', 'heavy': False,
                              'err': u'进程未启动成功（%ds 后仍为 Stopped）%s'
                                     % (int(el), _startq_logtail(srv))})
                    continue
                if not new_proc:
                    v['msg'] = u'等待新进程启动…（%ds%s）' % (
                        int(el), (u' · ' + pst) if pst else u'')
                    # v6277（用户实测 2026-11-08「重压池释放时没有立即激活排队，
                    #   一直等到某台启动完成后才激活」——核验：调度逻辑本身是对的
                    #   （restart.log 实测 Gen 比 Ext 完成早 42s 下发），问题在这里）：
                    #   本分支只改内存 v、**不推任务总线** ⇒ 融合条 msg 停在上一状态
                    #   「排队中（第 N 位）」，直到新进程日志出现（约 40~60s）才跳变，
                    #   界面上看起来就像"槽位一直没释放"。此刻该台**已下发启动**，必须推送。
                    try:
                        _utask_put('%s|start' % srv, srv, 'start',
                                   v.get('user') or 'srvctl',
                                   msg=v['msg'], pct=int(v.get('pct') or 0), phase='run')
                    except Exception:
                        pass
                    if el > SRVCTL_STARTQ_FIRST_TIMEOUT:
                        v.update({'ok': False, 'phase': 'fail', 'heavy': False,
                                  'err': u'未见新进程启动（%ds 内日志首行未变）%s'
                                         % (SRVCTL_STARTQ_FIRST_TIMEOUT,
                                            _startq_logtail(srv))})
                    continue
                v['pct'] = pct
                v['label'] = label
                v['msg'] = u'%s…（%ds）' % (label, int(el))
                try:
                    _utask_put('%s|start' % srv, srv, 'start', v.get('user') or 'srvctl',
                               msg=v['msg'], pct=pct, phase='run')
                except Exception:
                    pass
                # v6011（用户口径 2026-11-03）：**advertising 才算启动完成**。
                #   原 `started or advertising` 在 started（实测 Isl 119s）就判完成并
                #   交还重压槽位，而 advertising 在 149s ⇒ 中间 30s 可再下发一台，
                #   出现「3 台同时启动」的窗口，违反重压上限 2。
                done_boot = bool(marks.get('advertising'))
                # v6006：槽位从「下发」即占用，直到 advertising（或超时）才释放。
                if done_boot:
                    v.update({'ok': True, 'phase': 'ok', 'pct': 100, 'heavy': False,
                              'msg': u'已对外开放加入 · 全程 %ds' % int(el)})
                    try:
                        _utask_put('%s|start' % srv, srv, 'start', v.get('user') or 'srvctl',
                                   msg=v['msg'], pct=100, phase='ok')
                    except Exception:
                        pass
                elif (now - float(v.get('t0') or now)) > SRVCTL_STARTQ_HEAVY_TIMEOUT:
                    v.update({'ok': False, 'phase': 'fail', 'heavy': False,
                              'err': u'启动超时（%ds），已释放槽位' % SRVCTL_STARTQ_HEAVY_TIMEOUT})
                elif el > SRVCTL_STARTQ_ITEM_TIMEOUT:
                    v.update({'ok': False, 'phase': 'fail', 'heavy': False,
                              'err': u'启动超时（%ds）' % SRVCTL_STARTQ_ITEM_TIMEOUT})
                else:
                    # v6187（用户口径）：名额在 **started** 即释放（世界已加载完、负载下降），
                    #   但「完成」判定仍按 advertising（玩家真能搜到才算完成）。
                    #   原来无条件置 True ⇒ started 后又被重置回占位，P 方案会失效。
                    v['heavy'] = not bool(marks.get('started'))
        # ---- 收割 + 决定是否下发下一台 ----
        srv_next = ''
        with _SRVCTL_STARTQ_LOCK:
            for srv in list(_SRVCTL_STARTQ['active'].keys()):
                v = _SRVCTL_STARTQ['active'][srv]
                if v.get('phase') in ('ok', 'fail'):
                    _SRVCTL_STARTQ['active'].pop(srv, None)
                    _SRVCTL_STARTQ['done'].append({
                        'server': srv, 'ok': bool(v.get('ok')),
                        'pct': 100 if v.get('ok') else v.get('pct', 0),
                        'msg': v.get('msg', ''), 'err': v.get('err', ''),
                        't_end': int(now)})
                    # v6219（一致性 E）：收割即释放 queue 软锁
                    try:
                        _srv_lock_clear(srv, 'queue|%s' % srv)
                    except Exception:
                        pass
                    # v6193（用户实测「队列完全不对」）：**失败必须同步任务总线** ——
                    #   原来只有成功（advertising）分支写过 _utask_put，
                    #   5 个失败分支（进程退出 / 未见新进程 / 未启动成功 / 重压超时 / 单台超时）
                    #   全都只改内存里的 v ⇒ 任务条永远停在最后的 run pct（如 8%），
                    #   而队列概览已判失败 ⇒ 「3 条还在跑 8%」+「已完成 1/4（失败 3）」自相矛盾。
                    if not v.get('ok'):
                        _why = str(v.get('err') or u'启动失败')[:300]
                        _trs = _SRVCTL_STARTQ.get('tries')
                        if not isinstance(_trs, dict):
                            _trs = {}
                            _SRVCTL_STARTQ['tries'] = _trs
                        _tn = int(_trs.get(srv) or 0) + 1
                        if _tn <= STARTQ_AUTO_RETRY:
                            # v6343（用户实测「启动失败后没有自动重试」）：
                            #   瞬时性失败（启动时 CF 查 mods 超时 / 进程退出）自动重新入队，
                            #   上限 STARTQ_AUTO_RETRY 次；重试仍失败才置 fail（仍可手动「重试」）。
                            _trs[srv] = _tn
                            _SRVCTL_STARTQ['queue'].append(srv)
                            try:
                                _qu = _SRVCTL_STARTQ.get('quser')
                                if not isinstance(_qu, dict):
                                    _qu = {}
                                    _SRVCTL_STARTQ['quser'] = _qu
                                _qu[srv] = v.get('user') or _SRVCTL_STARTQ.get('user') or ''
                                _qs2 = _SRVCTL_STARTQ.get('qsrc')
                                if not isinstance(_qs2, dict):
                                    _qs2 = {}
                                    _SRVCTL_STARTQ['qsrc'] = _qs2
                                _qs2[srv] = str(v.get('src') or '')
                                _srv_lock_set(srv, 'queue', 'queue|%s' % srv, u'启动队列',
                                              user=v.get('user') or '', ttl=SRV_LOCK_TTL)
                            except Exception:
                                _sexc('startq_retry_meta')
                            if str(v.get('src') or '') not in DEPLOY_SRCS:
                                try:
                                    _utask_put('%s|start' % srv, srv, 'start',
                                               v.get('user') or 'srvctl',
                                               msg=u'第 %d 次自动重试（%s）'
                                                   % (_tn, _why[:80]),
                                               pct=0, phase='queue')
                                except Exception:
                                    pass
                            try:
                                _srvctl_log(v.get('user') or '', srv, 'start', False, 0,
                                            (u'RETRY %d/%d：%s' % (_tn, STARTQ_AUTO_RETRY, _why))[:250],
                                            src=str(v.get('src') or 'auto'))
                            except Exception:
                                pass
                        else:
                            _trs.pop(srv, None)
                            if str(v.get('src') or '') not in DEPLOY_SRCS:
                                try:
                                    _utask_put('%s|start' % srv, srv, 'start',
                                               v.get('user') or 'srvctl',
                                               msg=(u'启动失败（已自动重试 %d 次）'
                                                    % STARTQ_AUTO_RETRY),
                                               pct=0, phase='fail',
                                               err=_why)
                                except Exception:
                                    pass
                    else:
                        try:
                            _trs_ok = _SRVCTL_STARTQ.get('tries')
                            if isinstance(_trs_ok, dict):
                                _trs_ok.pop(srv, None)
                        except Exception:
                            pass
            # v6219（P2-3）：外部启动也计入重压占用 ⇒ 队列自动让路
            heavy = _startq_heavy_count() + len(_SRVCTL_STARTQ.get('external') or [])
            if (heavy < SRVCTL_STARTQ_HEAVY_MAX and _SRVCTL_STARTQ['queue']
                    and (now - float(_SRVCTL_STARTQ.get('lastSent') or 0)) >= SRVCTL_STARTQ_MIN_GAP):
                srv_next = _SRVCTL_STARTQ['queue'].pop(0)
                _SRVCTL_STARTQ['lastSent'] = now
            if not srv_next and not _SRVCTL_STARTQ['queue'] and not _SRVCTL_STARTQ['active']:
                _SRVCTL_STARTQ['running'] = False
                return
        if not srv_next:
            continue
        # ---- v6187：**出队即占名额**（锁内原子）——
        #   原实现「出队 → _srvctl_one（5~10s）→ 才写入 active」，空窗期内
        #   _startq_heavy_count() 看不到这台 ⇒ 若存在第二个 worker，会再放行一台。
        #   这里先占位（sending=True），真正下发完成后再刷新字段。
        with _SRVCTL_STARTQ_LOCK:
            # v6202：**优先取该服自己的发起人** —— 队列级 user 只在「首次建队」时写，
            #   人工批次与自动重启混队时，worker 原先把后来者记成建队者 ⇒ 来源误判。
            _u0 = ((_SRVCTL_STARTQ.get('quser') or {}).pop(srv_next, '')
                   or _SRVCTL_STARTQ.get('user') or '')
            _s0 = (_SRVCTL_STARTQ.get('qsrc') or {}).pop(srv_next, '')   # v6203：该服来源
            _SRVCTL_STARTQ['active'][srv_next] = {
                't0': now, 'baseFirst': '', 'heavy': True, 't_heavy': now,
                'seenProc': False, 'pct': 0, 'label': u'启动游戏进程',
                'phase': 'run', 'msg': u'已下发，等待进程…', 'err': '',
                'user': _u0, 'sending': True,
                'src': _s0,   # v6343：分发来源不写 srv|start 条
                'tries': int((_SRVCTL_STARTQ.get('tries') or {}).get(srv_next) or 0)}
        # ---- 下发（锁外，ASAM 调用可能耗时数秒）----
        if not _srvctl_acquire(srv_next, 'start'):
            with _SRVCTL_STARTQ_LOCK:
                _SRVCTL_STARTQ['active'].pop(srv_next, None)  # v6187：撞车 ⇒ 先撤销占位再放回队首
                _SRVCTL_STARTQ['queue'].insert(0, srv_next)   # 撞车 -> 放回队首稍后再试
                # v6202：发起人已在上方 pop 出来，必须**放回**，否则重新出队时丢失
                if _u0:
                    _qq = _SRVCTL_STARTQ.get('quser')
                    if not isinstance(_qq, dict):
                        _qq = {}
                        _SRVCTL_STARTQ['quser'] = _qq
                    _qq[srv_next] = _u0
                if _s0:
                    _qsg = _SRVCTL_STARTQ.get('qsrc')
                    if not isinstance(_qsg, dict):
                        _qsg = {}
                        _SRVCTL_STARTQ['qsrc'] = _qsg
                    _qsg[srv_next] = _s0
                _quser0 = _u0 or _SRVCTL_STARTQ.get('user') or ''
            # v6186：放回队首**必须归零任务** —— 否则 pct 保留上一轮的值
            #   （如 cfcore=8），前端 queue 态仍按 pct 画进度条 ⇒ 「排队中却显示 8%」
            try:
                _utask_put('%s|start' % srv_next, srv_next, 'start', _quser0,
                           msg=u'排队中…', pct=0, phase='queue', meta={'qpos': 1})
            except Exception:
                pass
            continue
        try:
            base_first = str((_srv_observe_log(srv_next) or {}).get('firstLineAt') or '')
        except Exception:
            base_first = ''
        try:
            r = _srvctl_one(srv_next, 'start', None, cfg)
        except Exception as e:
            r = {'ok': False, 'message': repr(e)}
        with _SRVCTL_STARTQ_LOCK:
            # v6202：沿用**占位时已确定**的发起人，别被队列级 user 覆盖（混队来源误判）
            u0 = ((_SRVCTL_STARTQ['active'].get(srv_next) or {}).get('user')
                  or _SRVCTL_STARTQ.get('user') or '')
            if r.get('ok'):
                # v6187：占位记录已在出队时写入 ⇒ 这里**原地刷新**（不重建，保留 t0 含下发耗时）
                _v0 = _SRVCTL_STARTQ['active'].get(srv_next)
                if not isinstance(_v0, dict):
                    _v0 = {}
                    _SRVCTL_STARTQ['active'][srv_next] = _v0
                _v0.update({'t0': now, 'baseFirst': base_first,
                            'heavy': True, 't_heavy': now, 'seenProc': False,
                            'pct': 2, 'label': u'启动游戏进程', 'phase': 'run',
                            'msg': u'已下发，等待进程…', 'err': '',
                            'user': u0, 'sending': False})
            else:
                _SRVCTL_STARTQ['active'].pop(srv_next, None)   # v6187：下发失败 ⇒ 撤销占位
                _SRVCTL_STARTQ['done'].append({
                    'server': srv_next, 'ok': False, 'pct': 0, 'msg': '',
                    'err': str(r.get('message') or 'start failed'), 't_end': int(now)})
        _srvctl_release(srv_next, 'start')
        try:
            _srvctl_log(u0, srv_next, 'start', bool(r.get('ok')), r.get('ms', 0),
                        ('queued-sent' if r.get('ok') else str(r.get('message') or '')),
                        src=(_s0 or ''))
        except Exception:
            pass


# ===== v6339（用户口径）：分发融合任务条 =====
#   · 一台服一条 `deploy|<srv>`（MOD/API 共用，同服多次分发覆盖同一条）
#   · 起服阶段不再另开 `srv|start` 独立条（该服的 src 在 DEPLOY_SRCS 里即跳过登记）
#   · 起服失败复用启动队列 + ASA 进程状态判定重试（最多 DEPLOY_START_TRY 次）
DEPLOY_SRCS = ('apideploy', 'moddeploy', 'deploy')
DEPLOY_START_TRY = 3
DEPLOY_START_WAIT = 150


def _deploy_start_retry(srv, user, src=u'deploy', note=None):
    """分发后的起服（含失败重试）。复用启动队列 + ASA 进程状态。
       返回 (ok, err)。"""
    def _n(t):
        try:
            if note:
                note(t)
        except Exception:
            pass
    last = u''
    for att in range(1, DEPLOY_START_TRY + 1):
        _n(u'起服中…（第 %d/%d 次）' % (att, DEPLOY_START_TRY))
        try:
            _srvctl_startq_new(user, [srv], src)
        except Exception as e:
            last = u'起服下发失败：%s' % repr(e)[:160]
            time.sleep(3)
            continue
        t0 = time.time()
        seen = False
        while (time.time() - t0) < DEPLOY_START_WAIT:
            time.sleep(3)
            try:
                ps = str((_srvctl_proc_snapshot() or {}).get(srv) or '')
            except Exception:
                ps = ''
            if ps in ('Starting', 'Running'):
                seen = True
            if seen and ps == 'Running':
                return True, u''
            if seen and ps == 'Stopped':
                last = u'起服过程中进程退出'
                break
            if not ps:
                try:
                    if _cfg_proc_start(srv, force=True):
                        return True, u''
                except Exception:
                    pass
        if not last:
            last = u'起服超时（%d 秒内未见 Running）' % DEPLOY_START_WAIT
        _n(u'第 %d 次起服未成功：%s' % (att, last))
        time.sleep(5)
    return False, last


def _srvctl_startq_new(user, servers, src=''):
    """建启动队列并起 worker；队列已在跑时把新服追加到队尾（自动去重）。

    v6182（用户口径「已经在启动的服，后端没记录，怎么避免重复启动」）：
      内存队列（queue/active/done）在后端重启后会清空，此时对「正在启动」的服再点启动
      就会重复下发 start。故增加**进程判据**：ArkAscendedServer.exe 已存在 ⇒ 直接跳过。
      该判据来自机器上的真实进程，与内存状态无关，重启不失效。"""
    global _SRVCTL_STARTQ_THREAD
    _skip_proc = {}
    _keep = []
    for _s in servers:
        try:
            _ts = _cfg_proc_start(_s, force=True)
        except Exception:
            _ts = None
        if _ts:
            _skip_proc[_s] = u'进程已存在（启动于 %s）' % time.strftime('%H:%M:%S', time.localtime(_ts))
        else:
            _keep.append(_s)
    if _skip_proc:
        try:
            _srvctl_log('(system)', '/'.join(_skip_proc.keys()), 'start', True, 0,
                        (u'start 跳过：' + u'；'.join('%s(%s)' % (k, v) for k, v in _skip_proc.items()))[:250])
        except Exception:
            pass
    servers = _keep
    # v6219（一致性 A）：**起服前守门下沉到这里** —— 原来只有 /api/srvctl/action 路由入口检查
    #   `_ARKBK_HOLD` + `_srv_lock`，而编排（_restart_exec_* -> startq）与回档（L422）**直接调用**
    #   本函数会完全绕过那两道门。下沉后三条路径（手动/回档/编排）自然统一。
    _blocked = {}
    _keep2 = []
    for _s in servers:
        if _ARKBK_HOLD.get(_s):
            _blocked[_s] = u'该服正在执行回档'
            continue
        try:
            _lk = _srv_lock_snapshot().get(_s) or {}
        except Exception:
            _lk = {}
        if _lk.get('kind') in SRV_LOCK_HARD:
            _blocked[_s] = u'该服被 %s 占用' % (_lk.get('kind') or '')
            continue
        _keep2.append(_s)
    if _blocked:
        try:
            _srvctl_log('(system)', '/'.join(_blocked.keys()), 'start', False, 0,
                        (u'start 拒绝：' + u'；'.join('%s(%s)' % (k, v) for k, v in _blocked.items()))[:250])
        except Exception:
            pass
    servers = _keep2
    if not servers:
        return _startq_view()
    with _SRVCTL_STARTQ_LOCK:
        q = _SRVCTL_STARTQ
        if not q['running']:
            q.update({'running': True, 'user': user, 'ts': time.time(), 'total': 0,
                      'queue': [], 'active': {}, 'done': [], 'lastSent': 0.0,
                      'quser': {}, 'qsrc': {}})   # v6202 每台发起人 / v6203 每台来源
        # v6014：done 里只有「成功」的服算占用（防重复启动）；
        #   「失败」的服不再占用 —— 否则任务条上的「重试」会被去重掉，根本不会重新下发。
        # v6195（用户口径）：**去掉「 done(ok) 也算 busy」** ——
        #   v6182 已用**真实进程**做幂等判据（进程存在即跳过），这里再按历史成功记录挡一次，
        #   会导致「队列运行期间回档/自动重启要起服」被静默跳过
        #   （回档只 stop 不 start，而 done 里仍留着旧的 ok 记录）。
        busy = set(q['queue']) | set(q['active'].keys())
        add = [s for s in servers if s not in busy]
        if add:
            q['done'] = [x for x in q['done'] if x.get('server') not in add]
        q['queue'].extend(add)
        # v6202：**每台记自己的发起人** —— 混队（人工 + 自动重启）时各自准确
        _qu = q.get('quser')
        if not isinstance(_qu, dict):
            _qu = {}
            q['quser'] = _qu
        _qs = q.get('qsrc')
        if not isinstance(_qs, dict):
            _qs = {}
            q['qsrc'] = _qs
        for _s in add:
            _qu[_s] = user
            _qs[_s] = src or ''
            # v6219（一致性 E）：入队即加 queue 软锁 —— 锁表能反映「该服在启动队列里」，
            #   与编排的 restart|<srv> 一起构成完整的可见性。收割时释放。
            try:
                _srv_lock_set(_s, 'queue', 'queue|%s' % _s, u'启动队列', user=user, ttl=SRV_LOCK_TTL)
            except Exception:
                pass
        # v6122：入队即登记任务（共享进度）
        # v6339（用户口径）：分发（API/MOD）自身的融合条已含「起服」步骤
        #   ⇒ 不再另开 `srv|start` 独立条（否则用户看到两条）
        for _s in add:
            if str(_qs.get(_s) or '') in DEPLOY_SRCS:
                continue
            try:
                _utask_put('%s|start' % _s, _s, 'start', user,
                           msg=u'排队中…', pct=0, phase='queue')
            except Exception:
                pass
        q['total'] = len(q['queue']) + len(q['active']) + len(q['done'])
        # v6187：判断 + 赋值 + start **全部在锁内** ——
        #   原实现 if need_thread 在锁外，两个并发请求可能各起一个 worker（双 worker ⇒ 同时下发）。
        _need = ((_SRVCTL_STARTQ_THREAD is None) or (not _SRVCTL_STARTQ_THREAD.is_alive()))
        if _need:
            _SRVCTL_STARTQ_THREAD = threading.Thread(target=_startq_worker, daemon=True)
            _SRVCTL_STARTQ_THREAD.start()
    return _startq_view()


def _save_accounts(acc):
    global _ACCOUNTS
    with _ACCOUNTS_LOCK:
        try:
            if os.path.exists(ACCOUNTS_FILE):
                import shutil
                shutil.copy2(ACCOUNTS_FILE, ACCOUNTS_FILE + '.bak')
        except Exception:
            pass
        tmp = ACCOUNTS_FILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(acc, f, ensure_ascii=False, indent=2)
        os.replace(tmp, ACCOUNTS_FILE)
        _ACCOUNTS = acc


# ================= 采集流程（玩家级文档） =================
# GET/POST /api/harvest_flows —— 按登录账号存储；nick 校验；512KB；baseUpdatedAt 冲突检测
_HARVEST_LOCK = threading.Lock()


def _harvest_auth(username, nick):
    """校验账号与昵称（低成本鉴权）。返回 (ok, error)。"""
    acc = _accounts().get(str(username or ''))
    if not acc:
        return False, 'unknown user'
    if str(acc.get('nick') or '') != str(nick or ''):
        return False, 'nick mismatch'
    return True, ''


def _harvest_path(username):
    safe = ''.join(ch for ch in str(username or '') if ch.isalnum() or ch in '_-')[:64]
    if not safe:
        return None
    return os.path.join(HARVEST_DIR, 'harvest_flows_%s.json' % safe)


def _load_harvest_flows(username):
    p = _harvest_path(username)
    if not p or not os.path.isfile(p):
        return None
    try:
        with open(p, 'r', encoding='utf-8') as f:
            doc = json.load(f)
        return doc if isinstance(doc, dict) else None
    except Exception:
        return None


def _save_harvest_flows(username, doc):
    p = _harvest_path(username)
    if not p:
        raise ValueError('bad username')
    with _HARVEST_LOCK:
        os.makedirs(HARVEST_DIR, exist_ok=True)
        try:
            if os.path.isfile(p):
                import shutil as _sh
                _sh.copy2(p, p + '.bak')
        except Exception:
            pass
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(doc, f, ensure_ascii=False, separators=(',', ':'))
        os.replace(tmp, p)
    return doc


# ================= 玩家偏好（关注项等，跨客户端） =================
# GET/POST /api/user_prefs —— 按登录账号存储；nick 校验；与采集流程同目录
_PREFS_LOCK = threading.Lock()


def _prefs_path(username):
    safe = ''.join(ch for ch in str(username or '') if ch.isalnum() or ch in '_-')[:64]
    if not safe:
        return None
    return os.path.join(HARVEST_DIR, 'user_prefs_%s.json' % safe)


def _load_user_prefs(username):
    p = _prefs_path(username)
    if not p or not os.path.isfile(p):
        return None
    try:
        with open(p, 'r', encoding='utf-8') as f:
            doc = json.load(f)
        return doc if isinstance(doc, dict) else None
    except Exception:
        return None


def _save_user_prefs(username, doc):
    p = _prefs_path(username)
    if not p:
        raise ValueError('bad username')
    with _PREFS_LOCK:
        os.makedirs(HARVEST_DIR, exist_ok=True)
        try:
            if os.path.isfile(p):
                import shutil as _sh2
                _sh2.copy2(p, p + '.bak')
        except Exception:
            pass
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(doc, f, ensure_ascii=False, separators=(',', ':'))
        os.replace(tmp, p)
    return doc


# ================= R2 / WebP 全自动更新（一键增量） =================
def _cf_config():
    try:
        with open(CF_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _webp_map():
    try:
        with open(WEBP_MAP_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


_S3_CACHE = {}


def _s3_headers(method, path, payload=b''):
    """R2 S3 签名 V4，返回 (headers, endpoint)。"""
    import hmac, hashlib
    cfg = _cf_config()
    access = cfg.get('r2_s3_access_key', '')
    secret = cfg.get('r2_s3_secret_key', '')
    ep = (cfg.get('r2_endpoint') or '').rstrip('/')
    host = ep.replace('https://', '').replace('http://', '')
    now = datetime.utcnow()
    amz_date = now.strftime('%Y%m%dT%H%M%SZ')
    date_stamp = now.strftime('%Y%m%d')
    payload_hash = hashlib.sha256(payload).hexdigest()
    canonical_uri = path.split('?')[0]
    q = path.split('?')[1] if '?' in path else ''
    canonical_headers = 'host:%s\nx-amz-content-sha256:%s\nx-amz-date:%s\n' % (host, payload_hash, amz_date)
    signed_headers = 'host;x-amz-content-sha256;x-amz-date'
    canonical_request = '\n'.join([method, canonical_uri, q, canonical_headers, signed_headers, payload_hash])
    region = 'auto'; service = 's3'
    scope = '%s/%s/%s/aws4_request' % (date_stamp, region, service)
    string_to_sign = '\n'.join(['AWS4-HMAC-SHA256', amz_date, scope, hashlib.sha256(canonical_request.encode()).hexdigest()])
    def _hmac(key, msg):
        return hmac.new(key, msg.encode(), hashlib.sha256).digest()
    k_date = _hmac(('AWS4' + secret).encode(), date_stamp)
    k_region = _hmac(k_date, region)
    k_service = _hmac(k_region, service)
    k_signing = _hmac(k_service, 'aws4_request')
    signature = hmac.new(k_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()
    headers = {
        'host': host,
        'x-amz-content-sha256': payload_hash,
        'x-amz-date': amz_date,
        'Authorization': 'AWS4-HMAC-SHA256 Credential=%s/%s, SignedHeaders=%s, Signature=%s' % (access, scope, signed_headers, signature),
    }
    return headers, ep


def _r2_request(method, path, payload=b'', headers_extra=None, timeout=30):
    import urllib.request
    headers, ep = _s3_headers(method, path, payload)
    if headers_extra:
        headers.update(headers_extra)
    req = urllib.request.Request(ep + path, data=payload if method in ('PUT', 'POST') else None, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _r2_list(prefix=''):
    """列出 R2 bucket 对象 key 列表（自动分页）。query 按字母排序 + 斜杠编码（S3 SigV4 要求）。"""
    import urllib.parse, re
    cfg = _cf_config()
    bucket = cfg.get('r2_bucket', '')
    keys = []; token = ''
    while True:
        parts = ['list-type=2']
        if prefix:
            parts.append('prefix=' + urllib.parse.quote(prefix, safe=''))
        if token:
            parts.append('continuation-token=' + urllib.parse.quote(token, safe=''))
        parts.sort()
        path = '/%s?%s' % (bucket, '&'.join(parts))
        try:
            body = _r2_request('GET', path).decode('utf-8', 'ignore')
        except Exception:
            break
        for m in re.finditer(r'<Key>([^<]+)</Key>', body):
            keys.append(m.group(1))
        if '<IsTruncated>true</IsTruncated>' not in body:
            break
        m3 = re.search(r'<NextContinuationToken>([^<]+)</NextContinuationToken>', body)
        if not m3:
            break
        token = m3.group(1)
    return keys


def _r2_download(key):
    import urllib.parse
    cfg = _cf_config()
    bucket = cfg.get('r2_bucket', '')
    path = '/%s/%s' % (bucket, urllib.parse.quote(key, safe='/'))
    return _r2_request('GET', path)


def _r2_upload(key, data, content_type):
    import urllib.parse
    cfg = _cf_config()
    bucket = cfg.get('r2_bucket', '')
    path = '/%s/%s' % (bucket, urllib.parse.quote(key, safe='/'))
    return _r2_request('PUT', path, payload=data, headers_extra={'Content-Type': content_type})


def webp_check():
    """R2 只读扫描新图（对比 CF Pages 线上 webp_map 作基准），返回新图数量。不压图（压图由本地增量脚本执行）。"""
    import urllib.request
    # 基准：CF Pages 线上 webp_map.json（前端实际使用；物理服务器不维护映射）
    mp = {}
    try:
        req = urllib.request.Request('https://dino.whiterober.ccwu.cc/webp_map.json',
                                     headers={'User-Agent': 'Mozilla/5.0 (dino-backend)'})
        with urllib.request.urlopen(req, timeout=20) as r:
            mp = json.loads(r.read().decode('utf-8', 'ignore'))
    except Exception:
        mp = {}
    try:
        keys = _r2_list('ASA/')
    except Exception as e:
        return {'ok': False, 'error': 'R2 list failed: %s' % e}
    pngs = [k for k in keys if k.lower().endswith('.png')]
    new_imgs = ['https://img.whiterober.ccwu.cc/' + k for k in pngs if ('https://img.whiterober.ccwu.cc/' + k) not in mp]
    return {'ok': True, 'new_count': len(new_imgs), 'scanned': len(pngs), 'total': len(mp)}


# 玩家名缓存（扫描 DinoData 全部 *_cryo 的 players[].name，5 分钟缓存；绑定 SteamID 时验证存在性）
_PLAYER_NAMES_CACHE = {'ts': 0, 'names': set()}


def _player_names(force=False):
    import gzip
    now = time.time()
    if not force and _PLAYER_NAMES_CACHE['ts'] > now - 300:
        return _PLAYER_NAMES_CACHE['names']
    names = set()
    try:
        for fn in os.listdir(DINO_DATA):
            if not (fn.endswith('_cryo.json.gz') or fn.endswith('_cryo.json')):
                continue
            path = os.path.join(DINO_DATA, fn)
            try:
                if fn.endswith('.gz'):
                    with gzip.open(path, 'rb') as f:
                        j = json.load(f)
                else:
                    with open(path, 'r', encoding='utf-8') as f:
                        j = json.load(f)
                for p in (j.get('players') or []):
                    if p.get('name'):
                        names.add(str(p['name']))
            except Exception:
                pass
    except Exception:
        _sexc('player_names')
        pass
    _PLAYER_NAMES_CACHE['ts'] = now
    _PLAYER_NAMES_CACHE['names'] = names
    return names


def mem_status(name, state, attrs):
    """写内存状态（兼容 HA sensor 轮询）。"""
    STATUS_MEM[name] = {'state': state, 'attributes': attrs}


# ================= RCON =================
def _rcon_packet(request_id, packet_type, payload):
    """标准 Source RCON 包：4 字节 length + request_id + type + body + \x00\x00。
    2026-08-28 修复：此前直接 struct.pack('<ii',...) 缺少 length 头，服务器无法正确解析
    （只回 Keep Alive 保活包、命令从不执行）——必须带 length 头，对齐 AppDaemon create_packet。"""
    payload_bytes = payload.encode('utf-8') + b'\x00\x00'
    packet_length = 4 + 4 + len(payload_bytes)
    return struct.pack(f'<iii{len(payload_bytes)}s', packet_length, request_id, packet_type, payload_bytes)


def rcon_command(host, port, password, command, timeout=RCON_TIMEOUT):
    """标准 Source RCON：认证(Type=3) + 命令(Type=2) + 收响应。返回原始字节。
    2026-08-28 对齐 AppDaemon receive_packets：不区分包边界，阻塞 recv 收原始字节流
    （Keep Alive 保活包与真实响应一起收，_rcon_str 用 rfind('{') 提取 JSON，天然免疫保活包/死循环）。"""
    s = socket.create_connection((host, port), timeout=timeout)
    try:
        # 认证（标准包：length 头 + id=1 + type=3）
        s.sendall(_rcon_packet(1, 3, password))
        auth = _recv_stream(s, timeout)
        if not auth:
            return b''
        # 对齐 AppDaemon：认证失败时服务器返回 request_id == -1（密码错误等），须检测避免静默失败
        if len(auth) >= 12 and struct.unpack('<i', auth[4:8])[0] == -1:
            return b''
        # 命令（标准包：length 头 + id=2 + type=2）
        s.sendall(_rcon_packet(2, 2, command))
        # 收命令响应原始字节流（含可能的分片/保活包；_rcon_str 负责提取 JSON）
        data = _recv_stream(s, timeout)
        return data or b''
    finally:
        s.close()


def _recv_stream(s, timeout):
    """对齐旧架构 receive_packets：阻塞 recv(4096) 循环收原始字节流。
    v13（2026-09-02）：修复 Source RCON 分包截断——服务器按 RCON 包(≤4096)逐包发送，
    多玩家长响应（ListPlayers/ArkTamedDinos/WildDinos 等）拆多个包，recv(4096) 一次往往只
    收到服务器当前已发的第一个包（<4096）。此前 len(part)<buf 立即 break → 后续分包全丢，
    玩家列表被截断（多人只显示前 1 人，与地图 PlayerPos 逐人查询不一致的根因）。
    改法：收到首个数据后降短超时(0.5s)继续收，短超时无新数据才判定响应结束（收全分包）。"""
    s.settimeout(timeout)
    data = b""
    buf = 4096
    first = True
    while True:
        try:
            s.settimeout(timeout if first else 0.5)
            part = s.recv(buf)
        except socket.timeout:
            break
        if not part:
            break
        data += part
        first = False
    return data


def _recv_packet(s, timeout):
    """读一个 Source RCON 包（4 字节长度 + payload）。返回 payload 原始字节。"""
    s.settimeout(timeout)
    try:
        hdr = s.recv(4)
        if len(hdr) < 4:
            return None
        size = struct.unpack('<i', hdr)[0]
        if size <= 0 or size > (1 << 22):
            return None
        body = b''
        while len(body) < size:
            chunk = s.recv(size - len(body))
            if not chunk:
                break
            body += chunk
        return hdr + body
    except socket.timeout:
        return None
    except Exception:
        return None


def extract_json(data):
    """从 RCON 原始响应中提取最后一个 JSON 对象。"""
    if not data:
        return None
    text = data.decode('utf-8', errors='ignore')
    idx = text.rfind('{')
    if idx < 0:
        return None
    # 2026-08-28 修复：RCON 包末尾带 \x00\x00 控制字符，json.loads 会因非法控制字符失败——先剥掉
    chunk = text[idx:].rstrip('\x00\r\n\t ')
    try:
        return json.loads(chunk)
    except Exception:
        return None


# ================= 业务 =================
# RCON 异步执行线程池（search_wild/refresh_tamed 后台执行，POST 立即返回触发成功——对齐旧架构 AppDaemon 异步行为，前端轮询状态文件等结果）
# 2026-08-28 提速：max_workers 2→6——用户一次刷新多台服务器时全部并发提交，避免任务排队（2 个慢任务占池导致后续任务等 20s）
_RCON_EXECUTOR = __import__('concurrent.futures', fromlist=['ThreadPoolExecutor']).ThreadPoolExecutor(max_workers=8)



# 2026-08-31：玩家位置共享缓存——多客户端共用同一份点位数据（联盟成员分布每 1s 全量轮询，
# N 客户端 × M 玩家并发 POST 会重复执行 RCON；TTL 内命中直接复用，RCON 命令量从 客户端数×玩家数/s 降为 玩家数/TTL）
_POS_CACHE = {}       # (server, player) -> [expire_ts, result_dict]
_POS_TTL = 1.5        # 秒
_POS_CACHE_MAX = 500  # 超上限清空重建，防 key 泄漏

def _refresh_task(server, msg='', pct=0, phase='run', err='', user='system'):
    """v6136（F5-lite）：刷新数据也报到统一任务总线，便于在各浮窗看到。"""
    try:
        _utask_put('refresh|%s' % server, server, 'refresh', (user or 'system'),
                   label=u'刷新数据', msg=msg, pct=pct, phase=phase, err=err)
    except Exception:
        _sexc('refresh_task')


def refresh_tamed(server, user='system'):
    """触发 tamed 刷新（v6136：外层包一层任务上报，内部逻辑不变）"""
    _refresh_task(server, msg=u'正在触发导出…', pct=15, user=user)
    r = _refresh_tamed_inner(server)
    okr = bool((r or {}).get('ok'))
    if okr:
        _refresh_task(server, msg=u'导出已触发，等待前端拉取', pct=100, phase='ok', user=user)
    else:
        _refresh_task(server, pct=0, phase='fail', user=user,
                      err=str((r or {}).get('error') or u'触发失败'))
    return r


def _refresh_tamed_inner(server):
    """触发一台服务器 tamed 刷新（RCON ArkTamedDinos）+ 轮询确认更新。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'error': 'unknown server: ' + server}
    try:
        # v542：ArkTamedDinos 导出量大（Ext 服 150+ 只），默认 15s RCON 超时会中断导出 → tamed.json 只生成部分数据 → 前端聚落消失。放宽到 60s（对齐 search_wild）
        raw = rcon_command(RCON_HOST, port, RCON_PASSWORD, CMD_TAMED, timeout=60)
    except Exception as e:
        return {'ok': False, 'server': server, 'error': 'rcon: ' + str(e)}
    resp = extract_json(raw) or {}
    ok = bool(resp.get('ok'))
    if ok and resp.get('cooldown'):
        time.sleep(20.0)
        try:
            raw2 = rcon_command(RCON_HOST, port, RCON_PASSWORD, CMD_TAMED, timeout=60)
            resp2 = extract_json(raw2) or {}
            if resp2.get('ok') and not resp2.get('cooldown'):
                ok = True
                resp = resp2
            elif resp2.get('cooldown'):
                r = {'ok': False, 'server': server, 'cooldown': True, 'error': 'still cooldown after retry', 'ts': str(datetime.now())}
                write_status_file('refresh_status.json', 'cooldown', r)
                write_status_file('refresh_status_%s.json' % server, 'cooldown', r)
                return r
        except Exception as e:
            return {'ok': False, 'server': server, 'error': 'rcon retry: ' + str(e)}
    if not ok:
        r = {'ok': False, 'server': server, 'error': resp.get('error') or 'trigger failed', 'ts': str(datetime.now())}
        write_status_file('refresh_status.json', 'error', r)
        write_status_file('refresh_status_%s.json' % server, 'error', r)
        return r
    # 2026-08-28 提速：去掉 poll_until_updated 最长 30s 轮询（这是新架构 tamed 刷新比旧架构慢的主因）——
    # 对齐旧架构 AppDaemon：RCON 触发成功即立即写 status 返回，tamed.json 文件生成由前端 lbWaitTamed 轮询 savedAt 确认。
    # 2026-08-28 修复：必须写静态 refresh_status.json（前端 lbWaitStatusFile 轮询该文件，缺此文件会一直 404 等到 15s 超时 = 刷新显得慢）
    # 2026-08-28 优化：同时写每台独立状态文件 refresh_status_{server}.json——多台并行时单文件 refresh_status.json 会被互相覆盖 ts，
    # 前端读到的 attrs.server ≠ 自己 abbr → 永不匹配 → 超时失败（并行全失败的根因）。独立文件让并行安全：前端轮询各自文件。
    result = {'ok': True, 'server': server, 'triggered': True, 'updated': None,
              'ts': str(datetime.now())}
    write_status_file('refresh_status.json', 'ok', result)  # 兼容旧前端
    write_status_file('refresh_status_%s.json' % server, 'ok', result)  # 独立文件（并行安全）
    mem_status('sensor.refresh_tamed_status', 'ok', result)
    return result


def save_world(server):
    """强制一台服务器保存世界（RCON SaveWorld）。
    v17（2026-09-02）：供前端「刷新数据」选中服务器时先存档——原生命令返回 'World Saved' 文本（非 JSON），
    非空即视为保存成功；前端再轮询 {server}_cryo.json.gz Last-Modified 确认落盘后拉取。"""
    port = SERVERS.get(server)
    now = str(datetime.now())
    if not port:
        r = {'ok': False, 'server': server, 'error': 'unknown server: ' + server, 'ts': now}
        write_status_file('save_world_status.json', 'error', r)
        write_status_file('save_world_status_%s.json' % server, 'error', r)
        mem_status('sensor.save_world_status', 'error', r)
        return r
    try:
        # v6198（用户口径「统一」）：瘦档基线必须在 SaveWorld **之前** 取
        try:
            _ak_base0 = int(((_srv_observe_ark(server, (_srv_observe_log(server) or {}).get('map') or '') or {}).get('size')) or 0)
        except Exception:
            _ak_base0 = 0
        _t_save = time.time()
        raw = rcon_command(RCON_HOST, port, RCON_PASSWORD, CMD_SAVE_WORLD, timeout=30)
    except Exception as e:
        r = {'ok': False, 'server': server, 'error': 'rcon: ' + str(e), 'ts': now}
        write_status_file('save_world_status.json', 'error', r)
        write_status_file('save_world_status_%s.json' % server, 'error', r)
        mem_status('sensor.save_world_status', 'error', r)
        return r
    text = (raw or b'').decode('utf-8', errors='ignore').strip(' \x00\r\n\t')
    ok = bool(raw)
    # v6120：补「DinoData 全部导出文件已落盘且稳定」确认（原实现只有 RCON 文本，
    #   实际文件是插件在存档事件后异步导出的；不等就会读到上一轮/半截文件）
    _dw = {}
    _ak = {}
    if ok:
        try:
            _dw = _dinodata_wait_stable(server, since_ts=_t_save, budget=90)
        except Exception:
            _dw = {}
        # v6198（用户口径「统一」）：与「保存世界 / 存档后终止」**同一套** .ark 瘦档判定
        if _dw.get('ok'):
            try:
                _ak = _srvctl_check_ark_after_dd(server, base_size=_ak_base0)
            except Exception as e:
                _ak = {'ok': False, 'thin': False, 'reason': 'ark_error', 'detail': repr(e)[:160]}
        else:
            _ak = {'ok': False, 'thin': False, 'reason': 'skipped_dd_failed', 'path': '', 'size': 0,
                   'baseSize': _ak_base0, 'waited': 0, 'mtime': 0, 'detail': '', 'mode': 'skipped'}
    # 顶层 ok 保持「RCON 回执」语义不变（前端 / HA sensor 依赖）；
    # 新增 okStrict（RCON & DinoData & .ark）供需要严格判定的一方使用。
    _ok_strict = bool(ok) and bool(_dw.get('ok')) and bool(_ak.get('ok'))
    r = {'ok': ok, 'server': server, 'saved': ok, 'reply': text[:80],
         'data': _dw, 'ark': _ak, 'okStrict': _ok_strict, 'ts': now}
    write_status_file('save_world_status.json', 'ok' if ok else 'error', r)
    write_status_file('save_world_status_%s.json' % server, 'ok' if ok else 'error', r)
    mem_status('sensor.save_world_status', 'ok' if ok else 'error', r)
    return r


def refresh_eggs(server):
    """触发一台服务器全图蛋信息实时刷新（RCON TransferIdentityFix.EggProbe）+ 写状态。
    蛋数据文件由 exe 侧生成 {server}_eggs.json.gz，前端重拉确认。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'error': 'unknown server: ' + server}
    try:
        raw = rcon_command(RCON_HOST, port, RCON_PASSWORD, CMD_EGG_PROBE)
    except Exception as e:
        return {'ok': False, 'server': server, 'error': 'rcon: ' + str(e)}
    resp = extract_json(raw) or {}
    ok = bool(resp.get('ok'))
    if not ok:
        r = {'ok': False, 'server': server, 'error': resp.get('error') or 'trigger failed', 'ts': str(datetime.now())}
        write_status_file('egg_probe_status.json', 'error', r)
        write_status_file('egg_probe_status_%s.json' % server, 'error', r)
        return r
    result = {'ok': True, 'server': server, 'triggered': True, 'ts': str(datetime.now())}
    write_status_file('egg_probe_status.json', 'ok', result)  # 兼容
    write_status_file('egg_probe_status_%s.json' % server, 'ok', result)  # 独立文件（并行安全）
    mem_status('sensor.egg_probe_status', 'ok', result)
    return result


def list_players(server):
    """在线玩家列表：原生 RCON ListPlayers → 解析 eosId → 写 {server}_online.json。
    前端据此过滤联盟离线成员，只查在线成员位置（每个在线成员仅 1 次 PlayerPos）。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'error': 'unknown server: ' + server}
    try:
        raw = rcon_command(RCON_HOST, port, RCON_PASSWORD, CMD_LIST_PLAYERS)
    except Exception as e:
        # v10（2026-09-01）：RCON 失败也写 ok=false 的 online.json——前端据此判断服务器离线（否则旧文件残留误判在线）
        r = {'ok': False, 'server': server, 'error': 'rcon: ' + str(e)}
        write_status_file('%s_online.json' % server, 'error', r)
        return r
    import re
    # v9（2026-09-01）：str(raw) 是 bytes repr（\n 为字面字符非真实换行）→ splitlines 只 1 行 → 只解析出第 1 个玩家
    # （在线名单带 b':\x00 垃圾前缀 + 多人只显示 1 人的同一根因）。改 decode 后 \n 为真实换行，全部玩家可解析。
    text = (raw or b'').decode('utf-8', errors='ignore')
    if not text.strip():
        # v11（2026-09-01）：连接成功但 ListPlayers 无任何响应（服务器未就绪/假死，超时返回空）→ 视为离线
        r = {'ok': False, 'server': server, 'error': 'no response'}
        write_status_file('%s_online.json' % server, 'error', r)
        return r
    players = []
    for line in text.splitlines():
        line = line.strip()
        if not line or 'No Players' in line:
            continue
        # 实测格式（2026-08-31）：'0. JaronV5, 00026f605e2e4146af882fd3c5d9624e'（无 SteamID: 前缀，直接名字, eoshex）
        # 兼容旧格式：'1. Name, SteamID: eoshex, PlayerUID: 123'
        m = re.search(r'([0-9a-fA-F]{32})', line)
        if not m:
            continue
        eos = m.group(1).lower()
        nm = re.sub(r'^\d+\.\s*', '', line)
        name = nm.split(',')[0].strip()
        players.append({'eosId': eos, 'name': name})
    result = {'ok': True, 'server': server, 'players': players, 'count': len(players), 'ts': str(datetime.now())}
    write_status_file('%s_online.json' % server, 'ok', result)
    return result


def search_wild(server, species):
    """搜野生：RCON WildDinos <species> → 写 wild_status.json。
    v5（2026-08-30）：超时放宽到 60s——Los 服丧尸数量庞大，WildDinos 处理可能超 15s（线程池异步，长阻塞不卡请求）"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    try:
        success, result = _rcon_str(port, CMD_WILD + ' ' + species, timeout=60)
    except Exception as e:
        return {'ok': False, 'server': server, 'species': species, 'error': str(e)}
    ok = False
    cooldown = False
    if success and result:
        try:
            j = json.loads(result)
            ok = bool(j.get('ok') and not j.get('cooldown'))
            cooldown = bool(j.get('cooldown'))
        except Exception:
            # 2026-08-28 修复：非 JSON 响应（Keep Alive 保活包 / 空 / 错误文本）不再按成功处理，
            # 否则前端误判刷新成功但数据文件从未生成（页面显示旧缓存）。改为报错。
            ok = False
    attrs = {'server': server, 'species': species, 'ok': ok, 'cooldown': cooldown,
             'result': str(result)[:200], 'ts': str(datetime.now())}
    # 2026-08-28 优化：同时写每台独立状态文件 wild_status_{server}.json（对齐 refresh_tamed 独立文件方案）——
    # 多台并行搜索时单文件 wild_status.json 会被并发覆盖 ts，前端读到的 attrs.server ≠ 自己 abbr → 永不匹配 → 超时失败。
    # 独立文件让前端可安全并行搜索（各自轮询自己文件）。
    write_status_file('wild_status.json', 'ok' if ok else ('cooldown' if cooldown else 'error'), attrs)
    write_status_file('wild_status_%s.json' % server, 'ok' if ok else ('cooldown' if cooldown else 'error'), attrs)
    mem_status('sensor.search_wild_status', 'ok' if ok else ('cooldown' if cooldown else 'error'), attrs)
    return attrs


def track_dino(server, player, dino1, dino2):
    """实时追踪：RCON TrackDino。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    try:
        success, result = _rcon_str(port, '%s %s %s %s' % (CMD_TRACK, player, dino1, dino2))
    except Exception as e:
        return {'ok': False, 'server': server, 'player': player, 'error': str(e)}
    ok = False
    found = None
    err = None
    if success and result:
        try:
            j = json.loads(result)
            ok = bool(j.get('ok'))
            found = j.get('found')
            err = j.get('error')
        except Exception:
            ok = True
    r = {'ok': ok, 'server': server, 'player': player,
         'dino': '%s_%s' % (dino1, dino2), 'found': found, 'error': err,
         'result': str(result)[:200], 'ts': str(datetime.now())}
    mem_status('sensor.track_dino_status', 'ok' if ok else 'error', r)
    return r


# v809：坐标打点（蛋/静态目标）——RCON TrackLocation <player> <x> <y> <z>；蛋非龙 TrackDino 查不到，改按坐标打点；清除复用 StopTrackDino
def track_location(server, player, x, y, z):
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    try:
        success, result = _rcon_str(port, '%s %s %s %s %s' % (CMD_TRACK_LOC, player, x, y, z or 0))
    except Exception as e:
        return {'ok': False, 'server': server, 'player': player, 'error': str(e)}
    ok = False
    if success and result:
        try:
            j = json.loads(result)
            ok = bool(j.get('ok'))
        except Exception:
            ok = True
    r = {'ok': ok, 'server': server, 'player': player, 'loc': '%s,%s,%s' % (x, y, z or 0),
         'result': str(result)[:200], 'ts': str(datetime.now())}
    mem_status('sensor.track_dino_status', 'ok' if ok else 'error', r)  # 复用 track_dino_status 供前端轮询（ts 变化即本次结果）
    return r


def stop_track_dino(server, player):
    """停止追踪：RCON StopTrackDino。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    try:
        success, result = _rcon_str(port, '%s %s' % (CMD_STOP_TRACK, player))
    except Exception as e:
        return {'ok': False, 'server': server, 'player': player, 'error': str(e)}
    ok = False
    if success and result:
        try:
            j = json.loads(result)
            ok = bool(j.get('ok'))
        except Exception:
            ok = True
    r = {'ok': ok, 'server': server, 'player': player,
         'result': str(result)[:200], 'ts': str(datetime.now())}
    mem_status('sensor.stop_track_dino_status', 'ok' if ok else 'error', r)
    return r


# v3（2026-08-30）：服务器管理——仅管理员 whiterober 可用（前端隐藏 + 后端双重校验）
def move_death_bag(server, target):
    """把部落/玩家的死亡包+尸体转移到最近墓碑（含 charId=0 包）：RCON MoveDeathBag <target>。target=部落ID/玩家名/EOSID"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    try:
        success, result = _rcon_str(port, '%s %s' % (CMD_MOVE_DEATH_BAG, target))
    except Exception as e:
        return {'ok': False, 'server': server, 'target': target, 'error': str(e)}
    r = {'ok': bool(success), 'server': server, 'target': target,
         'result': str(result)[:300], 'ts': str(datetime.now())}
    return r


def move_all_pendings(server, team):
    """把指定部落所有未被消费的 pending 球（cryopod）刷新到该部落墓碑：RCON MoveAllPendings <team>。team=部落ID 必填。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    try:
        success, result = _rcon_str(port, '%s %s' % (CMD_MOVE_ALL_PENDINGS, team))
    except Exception as e:
        return {'ok': False, 'server': server, 'team': team, 'error': str(e)}
    r = {'ok': bool(success), 'server': server, 'team': team,
         'result': str(result)[:300], 'ts': str(datetime.now())}
    return r


def rename_dino(server, dino_id1, dino_id2, new_name):
    """生物改名：RCON TransferIdentityFix.RenameDino <id1> <id2> <新名>（tif.operator 权限，中文名 UTF-8 直传）。
    返回结构化 JSON：ok / dino_id / old_name / new_name / desc / readback / error / verified / dup / detail"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    try:
        success, result = _rcon_str(port, '%s %s %s %s' % (CMD_RENAME_DINO, dino_id1, dino_id2, new_name))
    except Exception as e:
        return {'ok': False, 'server': server, 'dino_id': '%s_%s' % (dino_id1, dino_id2), 'error': str(e)}
    detail = {}
    if success and result:
        try:
            j = json.loads(result)
            if isinstance(j, dict):
                detail = j
        except Exception:
            _sexc('rename_dino')
            pass
    r = {'ok': bool(success), 'server': server, 'dino_id': '%s_%s' % (dino_id1, dino_id2),
         'dino_id1': dino_id1, 'dino_id2': dino_id2, 'name': new_name,
         'detail': detail, 'result': str(result)[:800], 'ts': str(datetime.now())}
    return r


def rename_container(server, obj, new_name):
    """容器箱改名（v1326）：RCON TransferIdentityFix.RenameContainer <objName|实例尾号> <新名>（tif.operator 权限）。

    - 仅 APrimalStructureItemContainer 及子类（储物箱/保险柜/低温冰箱/展示台/泰克专储/工业熔炉/化学台…）可改；
      床 / 棺材 / 牌子无官方同步通道 ⇒ DLL 返回 container not found + hint。
    - 名字限制：非空、≤60 UTF-8 字节、不含控制字符（前端已拦截，这里兜底）。
    - 返回：DLL 的 JSON 原样透传（ok / objName / class / field / old / new / readback / verified / dup / detail），
      解析失败时返回 {ok, server, obj, name, result}。
    """
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    obj_s = str(obj or '').strip()
    name = (new_name or '').strip()
    if not obj_s:
        return {'ok': False, 'server': server, 'error': 'usage: RenameContainer <objName|instanceSuffix> <new name>'}
    if not name:
        return {'ok': False, 'server': server, 'error': 'name empty'}
    nbytes = len(name.encode('utf-8'))
    if nbytes > 60:
        return {'ok': False, 'server': server, 'error': 'name too long (%d bytes, max 60)' % nbytes}
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in name):
        return {'ok': False, 'server': server, 'error': 'name contains control char'}
    try:
        success, result = _rcon_str(port, '%s %s %s' % (CMD_RENAME_CONTAINER, obj_s, name))
    except Exception as e:
        return {'ok': False, 'server': server, 'obj': obj_s, 'error': str(e)}
    detail = {}
    if result:
        try:
            j = json.loads(result)
            if isinstance(j, dict):
                detail = j
        except Exception:
            _sexc('rename_container')
            pass
    if detail:
        out = dict(detail)
        out.setdefault('server', server)
        out.setdefault('obj', obj_s)
        out.setdefault('name', name)
        out.setdefault('ts', str(datetime.now()))
        return out
    return {'ok': bool(success), 'server': server, 'obj': obj_s, 'name': name,
            'result': str(result)[:800], 'ts': str(datetime.now())}


def set_sign_text(server, obj, text):
    """牌子/墓碑写文字（2026-09-19 插件 v0.4.0）：RCON TransferIdentityFix.SetSignText <objName|实例尾号> <文字>。

    - 覆盖 Sign_*/HangingSign*/Gravestone_*；**床/棺材不在本命令**（走 set_bed_name）。
    - 文字限制：DLL 按 maxChars（Unicode 码点，实测 160）校验；且 **RCON 单包上限**：
      整条命令 >300 字节时客户端会**完全无响应**（实测 543 字节无响应）⇒ 这里先行拦截并返回 JSON 错误，
      避免前端空等（前端也应按 maxChars 与 300B 双条件自行截断）。
    - 传单个 '-' 表示清空（RCON 无法传空参）。
    - 客户端刷新：SignText **无官方 net RPC** ⇒ 需重进视野/重连（返回 clientRefresh 字段）。
    """
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    obj_s = str(obj or '').strip()
    txt = (text or '').strip()
    if not obj_s:
        return {'ok': False, 'server': server, 'error': 'usage: SetSignText <objName|instanceSuffix> <text>'}
    if not txt:
        return {'ok': False, 'server': server, 'error': 'text empty'}
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in txt):
        return {'ok': False, 'server': server, 'error': 'text contains control char'}
    full = '%s %s %s' % (CMD_SET_SIGN_TEXT, obj_s, txt)
    _nm = len(full.encode('utf-8'))
    if _nm > 300:
        return {'ok': False, 'server': server, 'obj': obj_s, 'error': 'command too long (RCON single packet)', 'bytes': _nm, 'max_bytes': 300}
    try:
        success, result = _rcon_str(port, full)
    except Exception as e:
        return {'ok': False, 'server': server, 'obj': obj_s, 'error': str(e)}
    detail = {}
    if result:
        try:
            j = json.loads(result)
            if isinstance(j, dict):
                detail = j
        except Exception:
            _sexc('set_sign_text')
            pass
    if detail:
        out = dict(detail)
        out.setdefault('server', server)
        out.setdefault('obj', obj_s)
        out.setdefault('text', txt)
        out.setdefault('ts', str(datetime.now()))
        return out
    return {'ok': bool(success), 'server': server, 'obj': obj_s, 'text': txt,
            'result': str(result)[:800], 'ts': str(datetime.now())}


def set_bed_name(server, obj, new_name):
    """床/棺材/睡眠舱改名（2026-09-19 插件 v0.4.0）：RCON TransferIdentityFix.SetBedName <objName|实例尾号> <名字>。

    - 覆盖 SimpleBed/ModernBed…、StructureBP_Coffin_*、SleepingPod*；**显式排除乐器台**（SeatingMusic，与床共享基类）。
    - ⚠️ 旧版用 RenameContainer 改床/棺写的是 **BoxName**，该族游戏不读 ⇒ 返回 ok 但游戏内不变；本命令写 **BedName**。
    - 名字限制：非空、≤ **60 UTF-8 字节**、不含控制字符；传单个 '-' 表示清空。
    - 客户端刷新：BedName **无官方 net RPC** ⇒ 需重进视野/重连（返回 clientRefresh 字段）。
    """
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    obj_s = str(obj or '').strip()
    name = (new_name or '').strip()
    if not obj_s:
        return {'ok': False, 'server': server, 'error': 'usage: SetBedName <objName|instanceSuffix> <name> (- to clear)'}
    if not name:
        return {'ok': False, 'server': server, 'error': 'name empty'}
    nbytes = len(name.encode('utf-8'))
    if nbytes > 60:
        return {'ok': False, 'server': server, 'error': 'name too long (%d bytes, max 60)' % nbytes}
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in name):
        return {'ok': False, 'server': server, 'error': 'name contains control char'}
    full = '%s %s %s' % (CMD_SET_BED_NAME, obj_s, name)
    _nm = len(full.encode('utf-8'))
    if _nm > 300:
        return {'ok': False, 'server': server, 'obj': obj_s, 'error': 'command too long (RCON single packet)', 'bytes': _nm, 'max_bytes': 300}
    try:
        success, result = _rcon_str(port, full)
    except Exception as e:
        return {'ok': False, 'server': server, 'obj': obj_s, 'error': str(e)}
    detail = {}
    if result:
        try:
            j = json.loads(result)
            if isinstance(j, dict):
                detail = j
        except Exception:
            _sexc('set_bed_name')
            pass
    if detail:
        out = dict(detail)
        out.setdefault('server', server)
        out.setdefault('obj', obj_s)
        out.setdefault('name', name)
        out.setdefault('ts', str(datetime.now()))
        return out
    return {'ok': bool(success), 'server': server, 'obj': obj_s, 'name': name,
            'result': str(result)[:800], 'ts': str(datetime.now())}


def inv_probe(server, filter_s, tribe_id, max_n):
    """库存扫描：RCON TransferIdentityFix.InvProbe <filter> <tribeId> <maxContainers>（tif.operator）。
    2026-09-04 新增：前端「关注未成年→食物源」读取 饲料槽/泰克槽(Trough)/风行蜥(Maelizard)/未成年背包 物品。
    注意：RCON 响应约 8KB 上限 → 单次 maxContainers 建议 ≤5；解析失败视为结果过大截断。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    try:
        flt = (filter_s or '_C').strip()
        success, result = _rcon_str(port, '%s %s %s %s' % (CMD_INV_PROBE, flt, tribe_id or 0, int(max_n) if str(max_n).isdigit() else 5))
    except Exception as e:
        return {'ok': False, 'server': server, 'error': str(e)}
    if not success or not result:
        return {'ok': False, 'server': server, 'error': 'rcon empty'}
    try:
        j = json.loads(result)
    except Exception:
        return {'ok': False, 'server': server, 'error': 'result too large (truncated)'}
    if not isinstance(j, dict) or not j.get('ok'):
        return {'ok': False, 'server': server, 'error': ((j or {}).get('error')) or 'inv probe failed', 'raw': str(result)[:200]}
    return {'ok': True, 'server': server, 'filter': j.get('filter'), 'tribeId': j.get('tribeId'),
            'containers': j.get('containers'), 'items': j.get('items'), 'list': j.get('list') or [],
            'ts': str(datetime.now())}


def crafting_cost(server, item_cls):
    """单蓝图制作材料：RCON TransferIdentityFix.CraftingCost <itemClass>（只读、无副作用）。
    2026-09-13 新增：前端蓝图卡「关注 / 待制作」按需单查；配方为类默认值 ⇒ 前端可永久缓存。
    注意：类名需为运行时类名（去掉 _C_<数字> 实例后缀）；目标类需在服务器上存在实例才命中。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    if server not in CRAFTING_COST_SERVERS:
        return {'ok': False, 'server': server, 'error': 'server not ready (crafting_cost: %s)' % server}
    cls = (item_cls or '').strip()
    i = cls.rfind('_C_')
    if i > 0 and cls[i + 3:].isdigit():
        cls = cls[:i + 2]   # 2145841018 → PrimalItemXxx_C
    if not cls:
        return {'ok': False, 'server': server, 'error': 'missing cls'}
    try:
        success, result = _rcon_str(port, '%s %s' % (CMD_CRAFTING_COST, cls))
    except Exception as e:
        return {'ok': False, 'server': server, 'error': str(e)}
    if not success or not result:
        return {'ok': False, 'server': server, 'error': 'rcon empty'}
    try:
        j = json.loads(result)
    except Exception:
        return {'ok': False, 'server': server, 'error': 'bad json', 'raw': str(result)[:200]}
    if not isinstance(j, dict) or not j.get('ok'):
        return {'ok': False, 'server': server, 'cls': cls,
                'error': (j or {}).get('error') or 'crafting cost failed'}
    return {'ok': True, 'server': server, 'cls': cls, 'itemClass': j.get('itemClass'),
            'foundIn': j.get('foundIn'), 'costs': j.get('costs') or [], 'count': j.get('count'),
            'ts': str(datetime.now())}


def volcano_anchor_get(server):
    """v1096：读火山锚点（全用户共享）。POST {server} 即读。"""
    if server not in VOLCANO_SERVERS:
        return {'ok': False, 'server': server, 'error': 'server not ready (volcano: %s)' % server}
    try:
        with open(VOLCANO_FILE, 'r', encoding='utf-8') as f:
            j = json.load(f)
    except Exception:
        j = {}
    a = (j or {}).get(server) if isinstance(j, dict) else None
    return {'ok': True, 'server': server, 'anchor': a, 'ts': str(datetime.now())}


def volcano_anchor_set(server, node, by):
    """v1096：写火山锚点（任何已登录用户均可）。node 为校准事件；anchorMs = 服务器当前现实时间戳。"""
    if server not in VOLCANO_SERVERS:
        return {'ok': False, 'server': server, 'error': 'server not ready (volcano: %s)' % server}
    try:
        with open(VOLCANO_FILE, 'r', encoding='utf-8') as f:
            j = json.load(f)
    except Exception:
        j = {}
    if not isinstance(j, dict):
        j = {}
    anchor = {'node': node or 'erupt_start', 'anchorMs': int(datetime.now().timestamp() * 1000),
              'by': (by or '')[:40], 'ts': str(datetime.now())}
    j[server] = anchor
    tmp = VOLCANO_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(j, f, ensure_ascii=False, indent=2)
    os.replace(tmp, VOLCANO_FILE)
    return {'ok': True, 'server': server, 'anchor': anchor}


def volcano_state(server, fresh=False):
    """2026-09-14：火山喷发权威状态（RCON TransferIdentityFix.Volcano，插件 v0.5.0，只读）。
    替代旧方案（人工校准锚点 + 前端拟合周期）：数据直接来自游戏内常驻喷发装置本体，
    与玩家是否在线、是否有人校准无关。
    架构（插件文档 §4）：后端单点查询 + 内存 TTL（默认 3s）⇒ N 个浏览器轮询也只产生
    3s 一次 RCON（RCON 命令在游戏线程执行，多客户端直连会挤占游戏主线程）。"""
    if server not in VOLCANO_SERVERS:
        return {'ok': False, 'server': server, 'error': 'server not ready (volcano: %s)' % server}
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    now_ms = int(time.time() * 1000)
    c = _VOLC_STATE_CACHE.get(server)
    if (not fresh) and c and (now_ms - c['ts'] < VOLC_STATE_TTL_MS):
        d = dict(c['data'])
        d['cacheAgeMs'] = now_ms - c['ts']
        d['serverNowMs'] = now_ms
        return d
    try:
        success, result = _rcon_str(port, CMD_VOLCANO + (' fresh' if fresh else ''), timeout=8)
    except Exception as e:
        return {'ok': False, 'server': server, 'error': 'rcon: ' + str(e), 'serverNowMs': now_ms}
    if not success or not result:
        return {'ok': False, 'server': server, 'error': 'rcon empty', 'serverNowMs': now_ms}
    try:
        j = json.loads(result)
    except Exception:
        return {'ok': False, 'server': server, 'error': 'bad json', 'raw': str(result)[:200], 'serverNowMs': now_ms}
    if not isinstance(j, dict):
        return {'ok': False, 'server': server, 'error': 'bad payload', 'serverNowMs': now_ms}
    j['server'] = server
    _VOLC_STATE_CACHE[server] = {'ts': now_ms, 'data': j}   # 失败结果也缓存 3s，避免异常时压打 RCON
    out = dict(j)
    out['cacheAgeMs'] = 0
    out['serverNowMs'] = now_ms
    return out


_VOLC_LOG_CACHE = {}   # v1146：事件台账缓存（独立槽位，与状态槽互不影响）


def volcano_log(server):
    """v1146（用户定稿）：火山**事件台账**——RCON `TransferIdentityFix.Volcano log`。
    返回 `history[]`（`{kind, cls, worldSec, durSec}`，kind ∈ begin/end/warmupOn/warmupOff/activeOn/activeOff）
    与 `hooks`。台账为插件内存态（64 条上限，插件重载/服务器重启清空）。
    前端调用时机：开窗 / 切服 / 重启恢复 ⇒ 立即一次；之后每 30s 兜底一次；hooks.events 变化时顺手一次。"""
    if server not in VOLCANO_SERVERS:
        return {'ok': False, 'server': server, 'error': 'server not ready (volcano: %s)' % server}
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    now_ms = int(time.time() * 1000)
    c = _VOLC_LOG_CACHE.get(server)
    if c and (now_ms - c['ts'] < VOLC_LOG_TTL_MS):
        d = dict(c['data'])
        d['cacheAgeMs'] = now_ms - c['ts']
        d['serverNowMs'] = now_ms
        return d
    try:
        success, result = _rcon_str(port, CMD_VOLCANO + ' log', timeout=8)
    except Exception as e:
        return {'ok': False, 'server': server, 'error': 'rcon: ' + str(e), 'serverNowMs': now_ms}
    if not success or not result:
        return {'ok': False, 'server': server, 'error': 'rcon empty', 'serverNowMs': now_ms}
    try:
        j = json.loads(result)
    except Exception:
        return {'ok': False, 'server': server, 'error': 'bad json', 'raw': str(result)[:200], 'serverNowMs': now_ms}
    if not isinstance(j, dict):
        return {'ok': False, 'server': server, 'error': 'bad payload', 'serverNowMs': now_ms}
    j['server'] = server
    _VOLC_LOG_CACHE[server] = {'ts': now_ms, 'data': j}
    out = dict(j)
    out['cacheAgeMs'] = 0
    out['serverNowMs'] = now_ms
    return out


# ---- WorldProbe 公共设施实时查询（2026-09-30，插件 v9；只读、无副作用）----
def _wp_trim(cache, now_ms):
    """宽松上限：超 _WP_CACHE_MAX 时按 ts 清掉最旧一半（防 key 泄漏）。"""
    if len(cache) <= _WP_CACHE_MAX:
        return
    try:
        items = sorted(cache.items(), key=lambda kv: kv[1].get('ts', 0))
        for k, _ in items[:len(items) // 2]:
            cache.pop(k, None)
    except Exception:
        pass


def _wp_lock(key):
    """同键并发合并锁（锁自身泄漏防线：>2000 清空重建，最坏多跑一次 RCON）。"""
    with _WP_LOCKS_GUARD:
        lk = _WP_LOCKS.get(key)
        if lk is None:
            if len(_WP_LOCKS) > 2000:
                _WP_LOCKS.clear()
            lk = _WP_LOCKS[key] = threading.Lock()
        return lk


def _wp_rcon_json(port, cmd, server, type_s, now_ms, timeout=8):
    """执行 WorldProbe 命令并解析 JSON；失败返回 (None, err_dict)。"""
    try:
        success, result = _rcon_str(port, cmd, timeout=timeout)
    except Exception as e:
        return None, {'ok': False, 'server': server, 'type': type_s, 'error': 'rcon: ' + str(e), 'serverNowMs': now_ms}
    if not success or not result:
        return None, {'ok': False, 'server': server, 'type': type_s, 'error': 'rcon empty', 'serverNowMs': now_ms}
    try:
        j = json.loads(result)
    except Exception:
        return None, {'ok': False, 'server': server, 'type': type_s, 'error': 'bad json', 'raw': str(result)[:200], 'serverNowMs': now_ms}
    if not isinstance(j, dict):
        return None, {'ok': False, 'server': server, 'type': type_s, 'error': 'bad payload', 'serverNowMs': now_ms}
    return j, None


def worldprobe_types(server):
    """类别字典。TTL 600s（极稳定）。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    now_ms = int(time.time() * 1000)
    c = _WP_TYPES_CACHE.get(server)
    if c and (now_ms - c['ts'] < WP_TYPES_TTL_MS):
        d = dict(c['data'])
        d['cacheAgeMs'] = now_ms - c['ts']
        d['serverNowMs'] = now_ms
        return d
    j, err = _wp_rcon_json(port, CMD_WORLDPROBE + ' types', server, None, now_ms)
    if err:
        return err
    j['server'] = server
    _WP_TYPES_CACHE[server] = {'ts': now_ms, 'data': j}
    out = dict(j)
    out['cacheAgeMs'] = 0
    out['serverNowMs'] = now_ms
    return out


def worldprobe_query(server, type_s, limit, fresh=False):
    """单服单类实时查询。短时缓存共用（5s）+ 同键并发合并：
    N 个客户端在 TTL 窗口内也只产生 1 条 RCON（插件文档 §4：RCON 在游戏线程执行）。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    if not re.match(r'^[a-z_]{1,32}$', str(type_s or '')):
        return {'ok': False, 'server': server, 'type': str(type_s or ''), 'error': 'bad type'}
    try:
        limit_n = int(limit)
    except Exception:
        limit_n = WP_LIMIT_DEFAULT
    limit_n = max(1, min(WP_LIMIT_MAX, limit_n))
    key = (server, str(type_s), limit_n)
    now_ms = int(time.time() * 1000)
    if not fresh:
        c = _WP_QUERY_CACHE.get(key)
        if c and (now_ms - c['ts'] < WP_QUERY_TTL_MS):
            d = dict(c['data'])
            d['cacheAgeMs'] = now_ms - c['ts']
            d['serverNowMs'] = now_ms
            return d
    with _wp_lock(key):
        now_ms = int(time.time() * 1000)
        if not fresh:
            c = _WP_QUERY_CACHE.get(key)
            if c and (now_ms - c['ts'] < WP_QUERY_TTL_MS):
                d = dict(c['data'])
                d['cacheAgeMs'] = now_ms - c['ts']
                d['serverNowMs'] = now_ms
                return d
        cmd = '%s query %s limit=%d' % (CMD_WORLDPROBE, str(type_s), limit_n)
        j, err = _wp_rcon_json(port, cmd, server, str(type_s), now_ms)
        if err:
            return err
        j['server'] = server
        _WP_QUERY_CACHE[key] = {'ts': now_ms, 'data': j}
        _wp_trim(_WP_QUERY_CACHE, now_ms)
        out = dict(j)
        out['cacheAgeMs'] = 0
        out['serverNowMs'] = now_ms
        return out


def _wx_ttl_ms(server):
    """v4409：weather 缓存 TTL（分档）——已推送新 dll 的图 3s，其余 60s。"""
    return WP_WX_TTL_FAST.get(server, WP_WEATHER_TTL_MS)


def worldprobe_weather(server, limit=1, slim=True):
    """天气（v4367 升级：full=1 limit=N [slim=1]；TTL 60s + 同键并发合并）。

    slim 默认开（仅保留前端契约键 current/last/next/prev/remaining 等）；
    slim=False 返回插件全量字段。历史参考块前端自 v4299 起零引用。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    try:
        limit_n = max(1, min(8, int(limit)))
    except Exception:
        limit_n = 1
    cmd = CMD_WORLDPROBE + ' weather full=1 limit=%d' % limit_n + (' slim=1' if slim else '')
    key = (server, cmd)
    now_ms = int(time.time() * 1000)
    c = _WP_WEATHER_CACHE.get(key)
    if c and (now_ms - c['ts'] < _wx_ttl_ms(server)):
        d = dict(c['data'])
        d['cacheAgeMs'] = now_ms - c['ts']
        d['serverNowMs'] = now_ms
        return d
    with _wp_lock(key):
        now_ms = int(time.time() * 1000)
        c = _WP_WEATHER_CACHE.get(key)
        if c and (now_ms - c['ts'] < _wx_ttl_ms(server)):
            d = dict(c['data'])
            d['cacheAgeMs'] = now_ms - c['ts']
            d['serverNowMs'] = now_ms
            return d
        j, err = _wp_rcon_json(port, cmd, server, None, now_ms)
        if err:
            return err
        j['server'] = server
        _WP_WEATHER_CACHE[key] = {'ts': now_ms, 'data': j}
        _wp_trim(_WP_WEATHER_CACHE, now_ms)
        out = dict(j)
        out['cacheAgeMs'] = 0
        out['serverNowMs'] = now_ms
        return out


def worldprobe_zones(server, fresh=False):
    """天气区域（WorldProbe zones，2026-10-03 新增）。
    分层：插件侧「区域名单」长缓存（切图 / 15min / 指针复验自动失效；fresh=1 强制重扫）；
    天气 / 温度 / state / settings 每次调用实时重读 ⇒ 不存在旧天气。本层 TTL 60s + 同键并发合并
    （N 客户端在窗口内只产生 1 条 RCON；zones 冷调用约 1.2s）。只有 Isl(4 区)/Cen(6 区) 有区域。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    key = (server, 'zones')
    now_ms = int(time.time() * 1000)
    if not fresh:
        c0 = _WP_ZONES_CACHE.get(server)
        if c0 and (now_ms - c0['ts'] < WP_ZONES_TTL_MS):
            d0 = dict(c0['data'])
            d0['cacheAgeMs'] = now_ms - c0['ts']
            d0['serverNowMs'] = now_ms
            return d0
    with _wp_lock(key):
        now_ms = int(time.time() * 1000)
        if not fresh:
            c0 = _WP_ZONES_CACHE.get(server)
            if c0 and (now_ms - c0['ts'] < WP_ZONES_TTL_MS):
                d0 = dict(c0['data'])
                d0['cacheAgeMs'] = now_ms - c0['ts']
                d0['serverNowMs'] = now_ms
                return d0
        cmd = CMD_WORLDPROBE + ' zones' + (' fresh=1' if fresh else '')
        j, err = _wp_rcon_json(port, cmd, server, None, now_ms)
        if err:
            return err
        j['server'] = server
        _WP_ZONES_CACHE[server] = {'ts': now_ms, 'data': j}
        out = dict(j)
        out['cacheAgeMs'] = 0
        out['serverNowMs'] = now_ms
        return out


def worldprobe_biometemps(server, skip=0, count=64, brief=False, filt=''):
    """区域温度（WorldProbe biometemps，v86/v87；ABiomeZoneVolume 绝对温度 ℃）。2026-10-04 新增。
    与 zones（Weather_Override_Volume）是两套对象；覆盖 Cen 130 区 / Gen 530 区；
    顶层 globalBase=全图基准温度 / globalWind=全图风力（区级 wind 恒 0 请用 globalWind）；
    参数透传 skip / count / brief(1=精简 约-70%体积) / filter(区名子串，ASCII，推荐替代翻页)。
    本层 TTL 60s + 同键并发合并（缓存键含查询参数）。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    try:
        skip_n = max(0, min(int(skip), 100000))
    except Exception:
        skip_n = 0
    try:
        count_n = max(1, min(int(count), 512))
    except Exception:
        count_n = 64
    filt_s = re.sub(r'[^0-9A-Za-z_\-]', '', str(filt or ''))[:40]   # 区名子串：仅 ASCII（RCON 参数以空格分隔）
    brief_b = bool(brief)
    key = (server, 'biometemps', skip_n, count_n, brief_b, filt_s)
    now_ms = int(time.time() * 1000)
    c0 = _WP_BIOMET_CACHE.get(key)
    if c0 and (now_ms - c0['ts'] < WP_BIOMET_TTL_MS):
        d0 = dict(c0['data'])
        d0['cacheAgeMs'] = now_ms - c0['ts']
        d0['serverNowMs'] = now_ms
        return d0
    with _wp_lock(key):
        now_ms = int(time.time() * 1000)
        c0 = _WP_BIOMET_CACHE.get(key)
        if c0 and (now_ms - c0['ts'] < WP_BIOMET_TTL_MS):
            d0 = dict(c0['data'])
            d0['cacheAgeMs'] = now_ms - c0['ts']
            d0['serverNowMs'] = now_ms
            return d0
        cmd = CMD_WORLDPROBE + ' biometemps count=%d skip=%d' % (count_n, skip_n)
        if brief_b:
            cmd += ' brief=1'
        if filt_s:
            cmd += ' filter=' + filt_s
        j, err = _wp_rcon_json(port, cmd, server, None, now_ms)
        if err:
            return err
        j['server'] = server
        _wp_trim(_WP_BIOMET_CACHE, now_ms)
        _WP_BIOMET_CACHE[key] = {'ts': now_ms, 'data': j}
        out = dict(j)
        out['cacheAgeMs'] = 0
        out['serverNowMs'] = now_ms
        return out


def _ingame_lock(server):
    """同键并发合并锁（与 _wp_lock 同范式）。"""
    with _INGAME_LOCKS_GUARD:
        lk = _INGAME_LOCKS.get(server)
        if lk is None:
            if len(_INGAME_LOCKS) > 64:
                _INGAME_LOCKS.clear()
            lk = _INGAME_LOCKS[server] = threading.Lock()
        return lk


def ingame_time(server, fresh=False):
    """游戏内时间（原生 RCON GetInGameTime → 'Day N, HH:MM:SS'）。
    60s TTL + 同键并发合并 ⇒ N 客户端合计每图 ≤1 次 RCON/分钟。
    注：Bob（俱乐部）实服对该命令无响应（'Server received, But no response!!'）⇒ ok=false + raw。
    解析前必须剥离控制字符（list_players 实测：响应带 b':\\x00 垃圾前缀）。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    now_ms = int(time.time() * 1000)
    c = _INGAME_CACHE.get(server)
    if (not fresh) and c and (now_ms - c['ts'] < INGAME_TTL_MS):
        d = dict(c['data'])
        d['cacheAgeMs'] = now_ms - c['ts']
        d['serverNowMs'] = now_ms
        return d
    with _ingame_lock(server):
        now_ms = int(time.time() * 1000)
        c = _INGAME_CACHE.get(server)
        if (not fresh) and c and (now_ms - c['ts'] < INGAME_TTL_MS):
            d = dict(c['data'])
            d['cacheAgeMs'] = now_ms - c['ts']
            d['serverNowMs'] = now_ms
            return d
        try:
            raw = rcon_command(RCON_HOST, port, RCON_PASSWORD, CMD_INGAME_TIME)
        except Exception as e:
            return {'ok': False, 'server': server, 'error': 'rcon: ' + str(e), 'serverNowMs': now_ms}
        text = (raw or b'').decode('utf-8', errors='ignore')
        clean = re.sub(r'[\x00-\x1f]', '', text).strip()
        m = _INGAME_RE.search(clean)
        if not m:
            err = 'no response' if not clean else 'unparsable'
            return {'ok': False, 'server': server, 'error': err, 'raw': clean[:200], 'serverNowMs': now_ms}
        day = int(m.group(1)); hh = int(m.group(2)); mm = int(m.group(3)); ss = int(m.group(4))
        r = {'ok': True, 'server': server,
             'raw': 'Day %d, %02d:%02d:%02d' % (day, hh, mm, ss),
             'day': day, 'clock': '%02d:%02d:%02d' % (hh, mm, ss),
             'secOfDay': hh * 3600 + mm * 60 + ss,
             'ttlMs': INGAME_TTL_MS, 'cacheAgeMs': 0, 'serverNowMs': now_ms}
        _INGAME_CACHE[server] = {'ts': now_ms, 'data': r}
        return r


def worldprobe_scan(type_s, servers, limit, fresh=False):
    """聚合路由：逐图并行 query（复用单图 5s 缓存/同键合并），按图分组返回。
    并发 ≤4（_WP_SCAN_EXECUTOR）；聚合结果 TTL 10s。"""
    if not re.match(r'^[a-z_]{1,32}$', str(type_s or '')):
        return {'ok': False, 'type': str(type_s or ''), 'error': 'bad type'}
    if isinstance(servers, str):
        servers = [s.strip() for s in servers.split(',') if s.strip()]
    if not isinstance(servers, (list, tuple)) or not servers:
        servers = list(SERVERS.keys())
    seen = set()
    clean = []
    for s in servers:
        if s in SERVERS and s not in seen:
            seen.add(s)
            clean.append(s)
    if not clean:
        return {'ok': False, 'type': str(type_s), 'error': 'no valid servers'}
    clean = clean[:WP_SERVER_MAX]
    try:
        limit_n = int(limit)
    except Exception:
        limit_n = WP_LIMIT_DEFAULT
    limit_n = max(1, min(WP_LIMIT_MAX, limit_n))
    key = (str(type_s), tuple(clean), limit_n)
    now_ms = int(time.time() * 1000)
    if not fresh:
        c = _WP_SCAN_CACHE.get(key)
        if c and (now_ms - c['ts'] < WP_SCAN_TTL_MS):
            d = dict(c['data'])
            d['cacheAgeMs'] = now_ms - c['ts']
            d['serverNowMs'] = now_ms
            return d
    futures = {}
    for s in clean:
        futures[s] = _WP_SCAN_EXECUTOR.submit(worldprobe_query, s, str(type_s), limit_n, fresh)
    by_server = {}
    total_matched = 0
    for s in clean:
        try:
            r = futures[s].result(timeout=12)
        except Exception as e:
            r = {'ok': False, 'server': s, 'error': 'agg timeout: %r' % (e,), 'serverNowMs': now_ms}
        by_server[s] = r
        if r.get('ok') and isinstance(r.get('matched'), int):
            total_matched += r.get('matched') or 0
    out = {'ok': True, 'type': str(type_s), 'servers': clean, 'byServer': by_server,
           'totalMatched': total_matched, 'serverNowMs': now_ms, 'cacheAgeMs': 0}
    _WP_SCAN_CACHE[key] = {'ts': int(time.time() * 1000), 'data': out}
    _wp_trim(_WP_SCAN_CACHE, now_ms)
    return out


def worldprobe_class(cls_s, servers, fresh=False):
    """类级计数（scan filter=<全类名> top=1，classes 精确匹配求和）。
    cls_s 支持 'A|B' 多类（如 Santiago 的两段箱类）；TTL 10s + 同键并发合并。
    适用：探险者笔记箱 19 类 / 河狸坝 3 实体——跨图统一类名者。"""
    cls_list = [c.strip() for c in str(cls_s or '').split('|') if c.strip()]
    if not cls_list or len(cls_list) > 4 or any(not re.match(r'^[A-Za-z0-9_]{1,64}$', c) for c in cls_list):
        return {'ok': False, 'cls': str(cls_s or ''), 'error': 'bad cls'}
    if isinstance(servers, str):
        servers = [s.strip() for s in servers.split(',') if s.strip()]
    if not isinstance(servers, (list, tuple)) or not servers:
        servers = list(SERVERS.keys())
    seen = set()
    clean = []
    for s in servers:
        if s in SERVERS and s not in seen:
            seen.add(s)
            clean.append(s)
    if not clean:
        return {'ok': False, 'cls': cls_list, 'error': 'no valid servers'}
    clean = clean[:WP_SERVER_MAX]
    key = ('cls', tuple(cls_list), tuple(clean))
    now_ms = int(time.time() * 1000)
    if not fresh:
        c = _WP_CLASS_CACHE.get(key)
        if c and (now_ms - c['ts'] < WP_CLASS_TTL_MS):
            d = dict(c['data'])
            d['cacheAgeMs'] = now_ms - c['ts']
            d['serverNowMs'] = now_ms
            return d
    with _wp_lock(key):
        now_ms = int(time.time() * 1000)
        if not fresh:
            c = _WP_CLASS_CACHE.get(key)
            if c and (now_ms - c['ts'] < WP_CLASS_TTL_MS):
                d = dict(c['data'])
                d['cacheAgeMs'] = now_ms - c['ts']
                d['serverNowMs'] = now_ms
                return d

        def _one(server):
            port = SERVERS.get(server)
            total = 0
            counts = {}
            for cl in cls_list:
                cmd = '%s scan filter=%s top=1' % (CMD_WORLDPROBE, cl)
                j, err = _wp_rcon_json(port, cmd, server, None, now_ms)
                if err:
                    return err
                got = 0
                for item in (j.get('classes') or []):
                    if item.get('class') == cl:
                        got += int(item.get('count') or 0)
                counts[cl] = got
                total += got
            return {'ok': True, 'server': server, 'cls': cls_list, 'counts': counts, 'total': total, 'serverNowMs': now_ms}

        futures = {}
        for s in clean:
            futures[s] = _WP_SCAN_EXECUTOR.submit(_one, s)
        by_server = {}
        tot = 0
        for s in clean:
            try:
                r = futures[s].result(timeout=14)
            except Exception as e:
                r = {'ok': False, 'server': s, 'error': 'agg timeout: %r' % (e,), 'serverNowMs': now_ms}
            by_server[s] = r
            if r.get('ok'):
                tot += r.get('total') or 0
        out = {'ok': True, 'cls': cls_list, 'servers': clean, 'byServer': by_server,
               'total': tot, 'serverNowMs': now_ms, 'cacheAgeMs': 0}
        _WP_CLASS_CACHE[key] = {'ts': int(time.time() * 1000), 'data': out}
        _wp_trim(_WP_CLASS_CACHE, now_ms)
        return out


# ---- v4367（2026-10-06）：WorldProbe 事件扩展路由 ----
def _wp_arg(s, maxlen=64):
    """WorldProbe 命令参数净化：仅保留字母/数字/下划线/逗号/点/短横。"""
    return re.sub(r'[^A-Za-z0-9_,\.\-]', '', str(s or ''))[:maxlen]


def _wp_simple(server, sub, cache, ttl_ms):
    """无参子命令通用包装（wave/sandstorm/meteor 共用）：TTL + 同键并发合并。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    key = (server, sub)
    now_ms = int(time.time() * 1000)
    c = cache.get(key)
    if c and (now_ms - c['ts'] < ttl_ms):
        d = dict(c['data'])
        d['cacheAgeMs'] = now_ms - c['ts']
        d['serverNowMs'] = now_ms
        return d
    with _wp_lock(key):
        now_ms = int(time.time() * 1000)
        c = cache.get(key)
        if c and (now_ms - c['ts'] < ttl_ms):
            d = dict(c['data'])
            d['cacheAgeMs'] = now_ms - c['ts']
            d['serverNowMs'] = now_ms
            return d
        j, err = _wp_rcon_json(port, CMD_WORLDPROBE + ' ' + sub, server, None, now_ms)
        if err:
            return err
        j['server'] = server
        cache[key] = {'ts': now_ms, 'data': j}
        _wp_trim(cache, now_ms)
        out = dict(j)
        out['cacheAgeMs'] = 0
        out['serverNowMs'] = now_ms
        return out


def worldprobe_wave(server):
    """Gen 巨浪（WorldProbe wave）。TTL 60s + 同键并发合并。"""
    return _wp_simple(server, 'wave', _WP_WAVE_CACHE, WP_WAVE_TTL_MS)


def worldprobe_sandstorm(server):
    """Rag 沙尘暴（WorldProbe sandstorm，插件 v122b3+）。TTL 60s + 同键并发合并。"""
    return _wp_simple(server, 'sandstorm', _WP_SAND_CACHE, WP_SAND_TTL_MS)


def worldprobe_meteor(server):
    """Ext 陨石雨（WorldProbe meteor）。TTL 2s + 同键并发合并。"""
    return _wp_simple(server, 'meteor', _WP_METEOR_CACHE, WP_METEOR_TTL_MS)


def worldprobe_actor(server, filt, propsidx='0', probe='', top='1', slim='1', fields=''):
    """通用 actor 读取（Rag 火山 / Gen 流星雨 / 人工观测）。TTL 30s + 同键并发合并。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    f = _wp_arg(filt)
    if not f:
        return {'ok': False, 'server': server, 'error': 'missing filter'}
    parts = ['actor', 'filter=' + f]
    pr = _wp_arg(probe, 200)
    if pr:
        parts.append('probe=' + pr)
    parts.append('props=1')
    parts.append('propsIdx=' + (_wp_arg(propsidx, 4) or '0'))
    parts.append('top=' + (_wp_arg(top, 4) or '1'))
    if str(slim) in ('0', '1'):
        parts.append('slim=' + str(slim))
    fl = _wp_arg(fields, 200)
    if fl:
        parts.append('fields=' + fl)
    cmd = CMD_WORLDPROBE + ' ' + ' '.join(parts)
    key = (server, cmd)
    now_ms = int(time.time() * 1000)
    c = _WP_ACTOR_CACHE.get(key)
    if c and (now_ms - c['ts'] < WP_ACTOR_TTL_MS):
        d = dict(c['data'])
        d['cacheAgeMs'] = now_ms - c['ts']
        d['serverNowMs'] = now_ms
        return d
    with _wp_lock(key):
        now_ms = int(time.time() * 1000)
        c = _WP_ACTOR_CACHE.get(key)
        if c and (now_ms - c['ts'] < WP_ACTOR_TTL_MS):
            d = dict(c['data'])
            d['cacheAgeMs'] = now_ms - c['ts']
            d['serverNowMs'] = now_ms
            return d
        j, err = _wp_rcon_json(port, cmd, server, None, now_ms)
        if err:
            return err
        j['server'] = server
        _WP_ACTOR_CACHE[key] = {'ts': now_ms, 'data': j}
        _wp_trim(_WP_ACTOR_CACHE, now_ms)
        out = dict(j)
        out['cacheAgeMs'] = 0
        out['serverNowMs'] = now_ms
        return out


def _wind_prop(ap, name):
    """从 actorProps.props 柔性取字段（实测形=[{name,value}]；兼容直接键形/数字键形）。"""
    try:
        p = ap.get('props') if isinstance(ap, dict) else None
        if p is None:
            return None
        if isinstance(p, list):
            for it in p:
                if isinstance(it, dict) and it.get('name') == name:
                    return it.get('value')
            return None
        if isinstance(p, dict):
            v = p.get(name)
            if v is not None:
                return v
            for k in p:
                it = p[k]
                if isinstance(it, dict) and it.get('name') == name:
                    return it.get('value')
        return None
    except Exception:
        return None


def _wind_f(v):
    try:
        return float(v) if v is not None else None
    except Exception:
        return None


def wind_status(server, fresh=False):
    """风力发电机耐久（v4670·2026-10-16）。1 条清单 + N 条逐台（4-token），60s 缓存 + 同键并发合并。
    ⚠️ 类名官方错拼 WindTrubine（写 WindTurbine 会 matched=0）；fields= 必须与 props=1 同给且总参数 ≤4
    （actor 子命令只解析 a1..a4，第 5 起静默丢弃）⇒ byname 形式恰好 4 token，勿再追加其它参数。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    key = (server, 'wind')
    now_ms = int(time.time() * 1000)
    if not fresh:
        c = _WIND_CACHE.get(key)
        if c and (now_ms - c['ts'] < WIND_TTL_MS):
            d = dict(c['data'])
            d['cacheAgeMs'] = now_ms - c['ts']
            d['serverNowMs'] = now_ms
            return d
    with _wp_lock(key):
        now_ms = int(time.time() * 1000)
        if not fresh:
            c = _WIND_CACHE.get(key)
            if c and (now_ms - c['ts'] < WIND_TTL_MS):
                d = dict(c['data'])
                d['cacheAgeMs'] = now_ms - c['ts']
                d['serverNowMs'] = now_ms
                return d
        j1, err = _wp_rcon_json(port, CMD_WORLDPROBE + ' actor filter=WindTrubine top=60', server, None, now_ms)
        if err:
            return err
        acts = j1.get('actors') or []
        world_time = j1.get('worldTime')
        turbines = []
        for a in acts:
            obj = a.get('objectName')
            if not obj:
                continue
            t = {'objectName': obj, 'x': a.get('x'), 'y': a.get('y'), 'z': a.get('z')}
            fo = _wp_arg(obj, 96)
            if not fo:
                t['error'] = 'bad name'
                turbines.append(t)
                continue
            cmd2 = CMD_WORLDPROBE + ' actor byname=1 filter=' + fo + ' props=1 fields=' + WIND_FIELDS
            j2, err2 = _wp_rcon_json(port, cmd2, server, None, now_ms)
            if err2:
                t['error'] = str(err2.get('error', 'rcon fail'))
                turbines.append(t)
                continue
            wt = j2.get('worldTime')
            if wt is not None:
                world_time = wt
            ap = j2.get('actorProps') or {}
            h = _wind_f(_wind_prop(ap, 'Health'))
            mh = _wind_f(_wind_prop(ap, 'MaxHealth'))
            ps = _wind_f(_wind_prop(ap, 'PoweredBatteryDurabilityToDecreasePerSecond'))
            dp = _wind_f(_wind_prop(ap, 'DecayDestructionPeriod'))
            t['health'] = h
            t['maxHealth'] = mh
            t['perSecond'] = ps
            t['pct'] = round(h / mh * 100.0, 2) if (h is not None and mh) else None
            t['depleteHours'] = round(h / (ps * WIND_DECAY_MULT) / 3600.0, 2) if (h is not None and ps and ps > 0) else None
            t['decayHours'] = round(dp / 3600.0, 2) if (dp and dp > 0) else None
            t['wind'] = _wind_prop(ap, 'CurrentWind')
            turbines.append(t)
        turbines.sort(key=lambda x: (x.get('depleteHours') is None, x.get('depleteHours') or 0.0))
        matched = j1.get('matched') or 0
        returned = j1.get('returned') or len(acts)
        out = {'ok': True, 'server': server, 'worldTime': world_time, 'count': len(turbines),
               'truncated': matched > returned,
               'generatedAt': time.strftime('%Y-%m-%dT%H:%M:%S') + '+08:00',
               'turbines': turbines, 'serverNowMs': now_ms, 'cacheAgeMs': 0}
        _WIND_CACHE[key] = {'ts': now_ms, 'data': out}
        _wp_trim(_WIND_CACHE, now_ms)
        return dict(out)


def world_clock(server, fresh=False):
    """存档世界时钟逆推（v5714·2026-10-30）。
    存档本身不含世界时钟（插件定论：GameState/GameMode/WorldSettings 不持久化），
    改用 RCON 实时 worldTime 锚点 + 存档文件 mtime 逆推：
        fileWorldTime = rconWorldTime - (锚点现实时刻 - 存档 mtime)   （世界钟与真实秒 1:1）
    一次 RCON 即可锚定该服任意时刻的存档；TTL 3 分钟 + 同键并发合并 + 跳变检测。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    key = (server, 'wclock')
    now_ms = int(time.time() * 1000)
    if not fresh:
        c = _WORLD_CLOCK_CACHE.get(key)
        if c and (now_ms - c['ts'] < WORLD_CLOCK_TTL_MS):
            d = dict(c['data'])
            d['cacheAgeMs'] = now_ms - c['ts']
            d['serverNowMs'] = now_ms
            return d
    with _wp_lock(key):
        now_ms = int(time.time() * 1000)
        if not fresh:
            c = _WORLD_CLOCK_CACHE.get(key)
            if c and (now_ms - c['ts'] < WORLD_CLOCK_TTL_MS):
                d = dict(c['data'])
                d['cacheAgeMs'] = now_ms - c['ts']
                d['serverNowMs'] = now_ms
                return d
        # 1) 存档文件 mtime（item 优先：每次存档都导出，最新鲜；cryo 兜底）
        file_ms = None
        file_name = None
        for sfx in ('_item.json.gz', '_item.json', '_cryo.json.gz', '_cryo.json'):
            p = os.path.join(DINO_DATA, server + sfx)
            try:
                if os.path.isfile(p):
                    file_ms = int(os.path.getmtime(p) * 1000)
                    file_name = server + sfx
                    break
            except Exception:
                continue
        if not file_ms:
            return {'ok': False, 'server': server, 'error': 'save file not found', 'serverNowMs': now_ms}
        # 2) RCON 取实时世界时间（weather 轻查询；full=1 limit=1）
        j, err = _wp_rcon_json(port, CMD_WORLDPROBE + ' weather full=1 limit=1', server, None, now_ms)
        if err:
            return err
        anchor_ms = int(time.time() * 1000)   # 取响应后时刻，最接近读值时刻
        wt = j.get('worldTime')
        try:
            wt = float(wt)
        except Exception:
            wt = None
        if wt is None or wt <= 0:
            return {'ok': False, 'server': server, 'error': 'no worldTime in RCON',
                    'worldTimeRaw': j.get('worldTime'), 'serverNowMs': now_ms}
        src = j.get('worldTimeSource')
        # 3) 逆推存档对应的世界时间
        age_sec = max(0.0, (anchor_ms - file_ms) / 1000.0)
        file_world = round(wt - age_sec, 2)
        # 4) 跳变检测（重启/回档 ⇒ 旧锚点失效）
        jumped = False
        prev = _WORLD_CLOCK_CACHE.get(key)
        if prev:
            try:
                pd = prev['data']
                expect = float(pd['rconWorldTime']) + (anchor_ms - int(pd['anchorMs'])) / 1000.0
                if abs(wt - expect) > WORLD_CLOCK_JUMP_SEC:
                    jumped = True
            except Exception:
                jumped = True
        out = {'ok': True, 'server': server,
               'fileWorldTime': file_world,       # ← 前端直接用：这份存档对应的世界时间
               'fileMtimeMs': file_ms,
               'file': file_name,
               'rconWorldTime': wt,
               'worldTimeSource': src,
               'anchorMs': anchor_ms,
               'ageSec': round(age_sec, 1),
               'jumped': jumped,
               'generatedAt': time.strftime('%Y-%m-%dT%H:%M:%S') + '+08:00',
               'serverNowMs': now_ms, 'cacheAgeMs': 0}
        _WORLD_CLOCK_CACHE[key] = {'ts': now_ms, 'data': out}
        _wp_trim(_WORLD_CLOCK_CACHE, now_ms)
        return dict(out)


def worldprobe_badwx(server, filt='WeatherSystem'):
    """坏天气权重因子（WorldProbe badwx [filter=]）。TTL 300s + 同键并发合并。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    f = _wp_arg(filt, 80)
    cmd = CMD_WORLDPROBE + ' badwx' + ((' filter=' + f) if f else '')
    key = (server, cmd)
    now_ms = int(time.time() * 1000)
    c = _WP_BADWX_CACHE.get(key)
    if c and (now_ms - c['ts'] < WP_BADWX_TTL_MS):
        d = dict(c['data'])
        d['cacheAgeMs'] = now_ms - c['ts']
        d['serverNowMs'] = now_ms
        return d
    with _wp_lock(key):
        now_ms = int(time.time() * 1000)
        c = _WP_BADWX_CACHE.get(key)
        if c and (now_ms - c['ts'] < WP_BADWX_TTL_MS):
            d = dict(c['data'])
            d['cacheAgeMs'] = now_ms - c['ts']
            d['serverNowMs'] = now_ms
            return d
        j, err = _wp_rcon_json(port, cmd, server, None, now_ms)
        if err:
            return err
        j['server'] = server
        _WP_BADWX_CACHE[key] = {'ts': now_ms, 'data': j}
        _wp_trim(_WP_BADWX_CACHE, now_ms)
        out = dict(j)
        out['cacheAgeMs'] = 0
        out['serverNowMs'] = now_ms
        return out


# uds 图的天气 actor 类名（Isl/Cen 由 2026-09-26/10-05 实测文档 & tmp 实测 JSON 固化）
_WP_UDS_FILTERS = {
    'Isl': 'UDS_Island_Weather',
    'Sco': 'UDS_SE_Weather',
    'Cen': 'UDS_TheCenter_Weather',
}
# ext_gen 图主天气系统（Ext/Rag/Val/Los 2026-10-05 实测；Ast 待验证）
_WP_EXTGEN_FILTERS = {
    'Ext': 'EXT_WeatherSystem',
    'Ast': 'AST_DayWeather_WeatherSystem',
    'Rag': 'RAG_DayWeather_WeatherSystem',
    'Val': 'RAG_DayWeather_WeatherSystem',
    'Los': 'LC_DayWeather_WeatherSystem',
}


def _wp_hex_vals(probes, name):
    """探针值数组。v125i+（2026-10-13）：优先 asDouble（TArray<double> 正确口径；asFloat 半读已删）；
    回退 asArray.dataHex / dataHex（8 字节 double 解码，兼容旧版）。"""
    import struct as _struct
    p = probes.get(name) if isinstance(probes, dict) else None
    if not isinstance(p, dict):
        return [], 0
    num = int(p.get('num') or 0)
    _ad = p.get('asDouble')
    if isinstance(_ad, list) and _ad:
        vals = [(float(v) if isinstance(v, (int, float)) else 0.0) for v in _ad]
        if num and len(vals) > num:
            vals = vals[:num]
        return vals, (num or len(vals))
    a = p.get('asArray')
    hx = ''
    if isinstance(a, dict):
        hx = a.get('dataHex') or ''
        num = int(a.get('num') or 0) or num
    if not hx:
        hx = p.get('dataHex') or ''
        num = num or int(p.get('num') or 0)
    if not hx:
        return [], num
    try:
        b = bytes.fromhex(hx)
        vals = list(_struct.unpack('<%dd' % (len(b) // 8), b)) if (b and len(b) % 8 == 0) else []
    except Exception:
        vals = []
    if num and len(vals) > num:
        vals = vals[:num]
    return vals, (num or len(vals))


def _wp_norm(vals):
    """权重数组 -> [{i, weight, pct}]（pct = 正权重占比 %，一位小数）。"""
    pos = sum(v for v in vals if v > 0)
    out = []
    for i, v in enumerate(vals):
        out.append({'i': i, 'weight': round(v, 4),
                    'pct': round(v / pos * 100.0, 1) if (pos > 0 and v > 0) else 0.0})
    return out


def _wp_wprobs_cmd(server, idx='0'):
    """按图族返回 (rcon命令, family)；不支持返回 (None, None)。"""
    if server in _WP_UDS_FILTERS:
        f = _WP_UDS_FILTERS[server]
        return (CMD_WORLDPROBE + ' actor filter=%s props=1 probe=WeatherWeights_Day,WeatherWeights_Night,'
                'WeatherEventLengths top=1' % f), 'uds'
    f2 = _WP_EXTGEN_FILTERS.get(server)
    if f2:
        return (CMD_WORLDPROBE + ' actor filter=%s props=1 propsIdx=%s probe=WeatherChances,'
                'PossibleWeatherChances,WeatherPresetList top=1' % (f2, _wp_arg(idx, 4) or '0')), 'ext_gen'
    return None, None


def worldprobe_wprobs(server, idx='0'):
    """全服天气概率聚合（读天气 actor 权重数组 -> dataHex 解析 -> 归一化）。TTL 300s。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    now_ms = int(time.time() * 1000)
    c = _WP_WPROBS_CACHE.get(server)
    if c and (now_ms - c['ts'] < WP_WPROBS_TTL_MS):
        d = dict(c['data'])
        d['cacheAgeMs'] = now_ms - c['ts']
        d['serverNowMs'] = now_ms
        return d
    with _wp_lock((server, 'wprobs', idx)):
        now_ms = int(time.time() * 1000)
        c = _WP_WPROBS_CACHE.get(server)
        if c and (now_ms - c['ts'] < WP_WPROBS_TTL_MS):
            d = dict(c['data'])
            d['cacheAgeMs'] = now_ms - c['ts']
            d['serverNowMs'] = now_ms
            return d
        cmd, fam = _wp_wprobs_cmd(server, idx)
        if not cmd:
            return {'ok': False, 'server': server, 'reason': 'unsupported', 'serverNowMs': now_ms}
        j, err = _wp_rcon_json(port, cmd, server, None, now_ms)
        if err:
            return err
        out = {'ok': True, 'server': server, 'family': fam, 'cacheAgeMs': 0, 'serverNowMs': now_ms}
        try:
            probes = j.get('probes') or {}
            out['probeKeys'] = list(probes.keys()) if isinstance(probes, dict) else None
            if fam == 'uds':
                dv, dn = _wp_hex_vals(probes, 'WeatherWeights_Day')
                nv, nn = _wp_hex_vals(probes, 'WeatherWeights_Night')
                lv, _ = _wp_hex_vals(probes, 'WeatherEventLengths')
                out['day'] = _wp_norm(dv)
                out['night'] = _wp_norm(nv)
                out['lengths'] = [round(v, 2) for v in lv]
                out['num'] = max(dn, nn)
            else:
                cv, cn = _wp_hex_vals(probes, 'WeatherChances')
                out['slots'] = _wp_norm(cv)
                out['num'] = cn
            out['worldTime'] = j.get('worldTime')
        except Exception as e:
            return {'ok': False, 'server': server, 'reason': 'parse: %r' % (e,), 'serverNowMs': now_ms}
        _WP_WPROBS_CACHE[server] = {'ts': int(time.time() * 1000), 'data': out}
        _wp_trim(_WP_WPROBS_CACHE, now_ms)
        return out


def get_dino(server, dino1, dino2):
    """单龙实时查询：RCON ArkGetDino。返回 {found, tribeId, babyAge, ...}。
    v14（2026-09-02）：扩展返回完整实时字段（babyAge/isBaby/level/name/坐标等）——
    前端「关注未成年」浮窗周期轮询此接口刷新成长进度（ArkGetDino 实时返回 babyAge 推进值）。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    try:
        success, result = _rcon_str(port, '%s %s %s' % (CMD_GET_DINO, dino1, dino2))
    except Exception as e:
        return {'ok': False, 'server': server, 'error': str(e)}
    ok = False
    found = None
    tribe_id = None
    err = None
    extra = {}
    if success and result:
        try:
            j = json.loads(result)
            ok = bool(j.get('found'))  # v15（2026-09-02）：ArkGetDino 响应无 ok 字段（JSON 以 {"found":.. 开头），以 found 为准——v14 误用 j.get('ok') 致 ok 恒 false、extra 永不透传
            found = j.get('found')
            tribe_id = j.get('tribeId') if 'tribeId' in j else j.get('tribe_id')
            err = j.get('error')
            if ok and found:
                # v16（2026-09-02）：+ 实时属性字段（statValues/currentStatValues/statPoints/statMutations/saddle/colors）——前端关注浮窗每 5s 需刷新当前属性值，v15 仅透传成长字段导致只刷成长度
                # v17（2026-09-08）：+ worldSecondsNow / nextAllowedMatingTime（ArkGetDino 纯追加输出）——路线浮窗「交配倒计时手动刷新」用
                for k in ['babyAge', 'isBaby', 'level', 'name', 'dinoClass', 'gender',
                          'x', 'y', 'z', 'stasised', 'dinoId1', 'dinoId2', 'randomMutationsMale',
                          'saddle', 'colors', 'statValues', 'currentStatValues', 'statPoints', 'statMutations',
                          'worldSecondsNow', 'nextAllowedMatingTime']:
                    if k in j:
                        extra[k] = j[k]
        except Exception:
            ok = True
    r = {'ok': ok, 'server': server, 'dino': '%s_%s' % (dino1, dino2),
         'found': found, 'tribeId': tribe_id, 'error': err,
         'result': str(result)[:200], 'ts': str(datetime.now())}
    r.update(extra)
    mem_status('sensor.get_dino_status', 'ok' if ok else 'error', r)
    return r


def player_pos(server, player):
    """玩家位置：RCON PlayerPos（带 1.5s 共享缓存，多客户端复用同一份点位数据）。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    key = (server, player)
    now = time.time()
    hit = _POS_CACHE.get(key)
    if hit and hit[0] > now:
        # 缓存命中：复用 RCON 结果，仅刷新 ts（前端靠 attrs.ts !== baseTs 识别新结果，ts 不变会被误判"该服未找到"）
        r = dict(hit[1])
        r['ts'] = str(datetime.now())
        write_status_file('player_pos_status.json', 'ok' if r['ok'] else 'error', r)
        write_status_file('player_pos_status_%s.json' % server, 'ok' if r['ok'] else 'error', r)
        mem_status('sensor.player_pos_status', 'ok' if r['ok'] else 'error', r)
        return r
    try:
        success, result = _rcon_str(port, '%s %s' % (CMD_PLAYER_POS, player))
    except Exception as e:
        return {'ok': False, 'server': server, 'player': player, 'error': str(e)}
    ok = False
    found = None
    x = y = z = None
    err = None
    if success and result:
        try:
            j = json.loads(result)
            ok = bool(j.get('ok'))
            found = j.get('found')
            err = j.get('error')
            if ok:
                x = j.get('x')
                y = j.get('y')
                z = j.get('z')
        except Exception:
            ok = True
    r = {'ok': ok, 'server': server, 'player': player, 'found': found,
         'x': x, 'y': y, 'z': z, 'error': err,
         'result': str(result)[:200], 'ts': str(datetime.now())}
    # 2026-08-28 优化：同时写每台独立状态文件 player_pos_status_{server}.json（对齐 refresh_status/wild_status 独立文件方案）——
    # 前端 lbFindPlayerPos 并行查多服位置时，单 sensor/单文件会被并发覆盖误判"找不到玩家"（v342 曾因此被迫串行）。
    # 独立文件让前端可安全并行查询（各自轮询自己文件，found 即返回）。
    write_status_file('player_pos_status.json', 'ok' if ok else 'error', r)
    write_status_file('player_pos_status_%s.json' % server, 'ok' if ok else 'error', r)
    mem_status('sensor.player_pos_status', 'ok' if ok else 'error', r)
    # 存入共享缓存（TTL 1.5s）；超上限清空重建
    if len(_POS_CACHE) >= _POS_CACHE_MAX:
        _POS_CACHE.clear()
    _POS_CACHE[key] = [time.time() + _POS_TTL, r]
    return r


def _rcon_str(port, command, timeout=None):
    """执行 RCON 命令并提取 JSON。timeout 覆盖默认 RCON_TIMEOUT（搜野生大物种用 60s）。
    v6（2026-08-30）：先剥离 NUL/控制字符——大响应时 RCON 保活包（Keep Alive）字节混入，
    find('{') 会命中保活包中的错误位置导致 json.loads 失败 → 后端误判失败（数据实际已写入）。"""
    if timeout is None:
        timeout = RCON_TIMEOUT
    raw = rcon_command(RCON_HOST, port, RCON_PASSWORD, command, timeout=timeout)
    if not raw:
        return False, None
    text = raw.decode('utf-8', errors='ignore')
    # v7：剥离控制字符后，遍历所有 { 位置尝试 json.loads，取第一个有效 JSON——
    # 保活包（Keep Alive）非控制字节可能含 {，v6 的 find('{') 命中后变成 {{... 仍解析失败
    clean = re.sub(r'[\x00-\x1f]', '', text)
    idx = 0
    while True:
        idx = clean.find('{', idx)
        if idx < 0:
            break
        chunk = clean[idx:].rstrip('\x00\r\n\t ')
        try:
            obj = json.loads(chunk)
            if isinstance(obj, dict):
                return True, chunk
        except Exception:
            pass
        idx += 1
    return True, text


def read_saved_marker(server):
    """读取 tamed.json 更新标记：优先 savedAt，否则 mtime。"""
    path = os.path.join(DINO_DATA, server + '_tamed.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            j = json.load(f)
        saved = j.get('savedAt')
        if saved:
            return ('savedAt', str(saved))
    except Exception:
        _sexc('saved_marker')
        pass
    try:
        return ('mtime', str(os.path.getmtime(path)))
    except Exception:
        return ('mtime', '0')


def poll_until_updated(server, old_marker, timeout=30):
    kind, old_val = old_marker
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(1.0)
        new_marker = read_saved_marker(server)
        if new_marker != old_marker:
            return True, new_marker
    return False, old_marker


def write_status_file(name, state, attrs):
    """写免认证静态状态文件到 ASA_DATA（前端轮询读取）。"""
    try:
        path = os.path.join(ASA_DATA, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = {'state': state, 'attributes': attrs}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False)
    except Exception as e:
        print('[warn] write status file %s failed: %s' % (name, e))


def safe_join(base, rel):
    """防目录穿越。"""
    full = os.path.normpath(os.path.join(base, rel))
    if not full.startswith(os.path.normpath(base)):
        return None
    return full


# ===== v6121：公网 IP 监视（只观察 + 通知，**不做任何自动动作**）=====
# 背景（用户 2026-11-05）：家宽为动态公网 IP；IP 一变，已启动的游戏进程仍向 EOS 注册旧地址
#   ⇒ 游戏内服务器列表能刷出但连不上，只能 open 新IP:端口 进。
#   RCON 实测**无**重注册命令（Reconnect/ReconnectEOS 与乱写命令同样返回
#   "Server received, But no response!!"，而 TransferIdentityFix.Volcano 正常返回 JSON，
#   ListPlayers 也正常 ⇒ 对照实验已排除）。⇒ 只能靠重启进程，本阶段先只做监视+通知。
# 探测源：解析 work.whiterober.cn（TTL=1s 的 DDNS A 记录 = 当前公网 IP）。
IPWATCH_DOMAIN = (os.environ.get('IPWATCH_DOMAIN') or 'work.whiterober.cn').strip()
def _ipwatch_domain():
    """v6141（用户口径）：探测域名**不再硬编码** —— 优先级：
         环境变量 IPWATCH_DOMAIN > 系统配置 server_config.json 的 server_domain > 内置兜底
       每次调用都读配置 ⇒ 后台改了 server_domain，下一轮探测自动生效（不用重启后端）"""
    env = (os.environ.get('IPWATCH_DOMAIN') or '').strip()
    if env:
        return env
    try:
        v = _srv_domain_norm((_srv_cfg_read() or {}).get('server_domain') or '')
        if v:
            return v
    except Exception:
        _sexc('ipwatch_domain')
    return IPWATCH_DOMAIN
try:
    IPWATCH_INTERVAL = max(30, int(os.environ.get('IPWATCH_INTERVAL') or 60))
except Exception:
    IPWATCH_INTERVAL = 60
IPWATCH_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'public_ip_state.json')
IPWATCH_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ipwatch.log')
_IPWATCH = {'domain': _ipwatch_domain(), 'domainIp': '', 'lastIp': '', 'changedAt': '',
            'initAt': '',   # v6161：首次建立监视的时刻（与 changedAt 严格区分，后者只表示「真发生过 IP 变化」）
            'mode': 'notify', 'checks': 0, 'errs': 0, 'lastCheckAt': '', 'lastErr': '',
            'history': []}
_IPWATCH_LOCK = threading.Lock()


def _ipwatch_resolve():
    """解析域名拿当前公网 IPv4：优先 DoH（绕开本地 DNS 缓存），失败回落系统解析。"""
    import json as _j
    import urllib.request as _u
    _e1 = ''
    try:
        _dom = _ipwatch_domain()
        req = _u.Request('https://cloudflare-dns.com/dns-query?name=%s&type=A' % _dom,
                         headers={'accept': 'application/dns-json', 'User-Agent': 'dino-backend/ipwatch'})
        with _u.urlopen(req, timeout=8) as r:
            d = _j.loads(r.read().decode('utf-8', 'replace'))
        ips = [a.get('data') for a in (d.get('Answer') or []) if a.get('type') == 1 and a.get('data')]
        ips = [x for x in ips if x and str(x).count('.') == 3]
        if ips:
            return sorted(ips)[0], ''
        _e1 = 'doh empty'
    except Exception as e:
        _e1 = 'doh %s: %s' % (type(e).__name__, e)
        # v6219（P2-2）：DoH 失败**必须留痕** —— 原来 _e1 只在系统 DNS 也失败时才被用到，
        #   只要系统 DNS 成功返回就没任何记录 ⇒ 2026-11-07 排查「IP 变了 9 分钟才识别」时
        #   无法判断到底走的是 DoH 还是系统 DNS（openclash + AdGuard 环境下尤其需要）。
        try:
            _ipwatch_log('DoH failed -> fallback system DNS: %s' % _e1[:200])
        except Exception:
            pass
    try:
        import socket as _s
        infos = _s.getaddrinfo(_dom, None, _s.AF_INET)
        ips2 = sorted({x[4][0] for x in infos if x and x[4]})
        if ips2:
            return ips2[0], ''
        return '', '%s; dns empty' % _e1
    except Exception as e:
        return '', '%s; dns %s: %s' % (_e1, type(e).__name__, e)


def _ipwatch_save():
    try:
        with _IPWATCH_LOCK:
            snap = dict((k, _IPWATCH[k]) for k in _IPWATCH)
            snap['history'] = list(_IPWATCH['history'])[-20:]
        tmp = IPWATCH_STATE_FILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(snap, f, ensure_ascii=False, indent=1)
        os.replace(tmp, IPWATCH_STATE_FILE)
    except Exception:
        _sexc('ipwatch_save')


def _ipwatch_log(line):
    try:
        with open(IPWATCH_LOG, 'a', encoding='utf-8') as f:
            f.write('[%s] %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), line))
    except Exception:
        pass


def _ipwatch_notify(text):
    """可选通知：环境变量 IPWATCH_WEBHOOK 或 server_config.json 的 ipwatch_webhook。"""
    url = ''
    try:
        url = str(os.environ.get('IPWATCH_WEBHOOK') or '')
        if not url:
            url = str((_srv_cfg_read() or {}).get('ipwatch_webhook') or '')
    except Exception:
        url = ''
    if not url:
        return
    try:
        import urllib.request as _u
        body = json.dumps({'content': text}).encode('utf-8')
        req = _u.Request(url, data=body, headers={'Content-Type': 'application/json',
                                                  'User-Agent': 'dino-backend/ipwatch'}, method='POST')
        with _u.urlopen(req, timeout=10) as r:
            r.read()
    except Exception as e:
        _ipwatch_log('notify failed: %s: %s' % (type(e).__name__, e))


def _ipwatch_loop():
    """守护线程：每 IPWATCH_INTERVAL 秒解析一次；连续 2 次一致且与记录不同 ⇒ 判定变更。"""
    try:
        if os.path.isfile(IPWATCH_STATE_FILE):
            with open(IPWATCH_STATE_FILE, 'r', encoding='utf-8') as f:
                d = json.load(f) or {}
            with _IPWATCH_LOCK:
                _IPWATCH['lastIp'] = str(d.get('lastIp') or '')
                _IPWATCH['history'] = list(d.get('history') or [])[-20:]
                _IPWATCH['mode'] = str(d.get('mode') or 'notify')
                _IPWATCH['initAt'] = str(d.get('initAt') or '')
                # v6161：兼容清洗 —— 旧版把「初始化时刻」也写进 changedAt。只有当历史里确实存在
                #   event=changed 记录时，才承认 changedAt；否则视为「从未发生过 IP 变化」。
                _chg = [x for x in _IPWATCH['history']
                        if isinstance(x, dict) and x.get('event') == 'changed']
                _IPWATCH['changedAt'] = (str(_chg[-1].get('at') or '') if _chg else '')
                if not _IPWATCH['initAt']:
                    _ini = [x for x in _IPWATCH['history']
                            if isinstance(x, dict) and x.get('event') == 'init']
                    if _ini:
                        _IPWATCH['initAt'] = str(_ini[-1].get('at') or '')
    except Exception:
        _sexc('ipwatch_load')
    _ipwatch_log('ipwatch started: domain=%s interval=%ss lastIp=%s'
                 % (_ipwatch_domain(), IPWATCH_INTERVAL, _IPWATCH['lastIp'] or '(none)'))
    pending = ''
    while True:
        ip, err = _ipwatch_resolve()
        now_s = time.strftime('%Y-%m-%d %H:%M:%S')
        try:
            with _IPWATCH_LOCK:
                _IPWATCH['domain'] = _ipwatch_domain()
        except Exception:
            pass
        with _IPWATCH_LOCK:
            _IPWATCH['checks'] += 1
            _IPWATCH['lastCheckAt'] = now_s
            if ip:
                _IPWATCH['domainIp'] = ip
                _IPWATCH['lastErr'] = ''
            else:
                _IPWATCH['errs'] += 1
                _IPWATCH['lastErr'] = err
            cur = _IPWATCH['lastIp']
        if err:
            _ipwatch_log('resolve error: %s' % err)
        elif not cur:
            with _IPWATCH_LOCK:
                _IPWATCH['lastIp'] = ip
                # v6161：初始化**不再**写 changedAt —— 否则「ipwatch 首次启动时刻」会被前端当成
                #   「IP 变化时刻」，导致所有服被误标 IP 失效（v6160 实测 11 台全亮）。
                _IPWATCH['initAt'] = now_s
                _IPWATCH['history'].append({'at': now_s, 'ip': ip, 'event': 'init'})
                _IPWATCH['history'] = _IPWATCH['history'][-20:]
            _ipwatch_save()
            _ipwatch_log('init: lastIp=%s' % ip)
        elif pending == ip and ip != cur:
            with _IPWATCH_LOCK:
                prev = _IPWATCH['lastIp']
                _IPWATCH['lastIp'] = ip
                _IPWATCH['changedAt'] = now_s
                _IPWATCH['history'].append({'at': now_s, 'ip': ip, 'prev': prev, 'event': 'changed'})
                _IPWATCH['history'] = _IPWATCH['history'][-20:]
            _ipwatch_save()
            _ipwatch_log('CHANGED %s -> %s' % (prev, ip))
            _ipwatch_notify('[dino] 公网 IP 变化：%s → %s（域名 %s）。游戏服需重启才能恢复服务器列表。'
                            % (prev, ip, _ipwatch_domain()))
            # v6129（M3）：开关开启时启动重启编排（默认 dry-run）
            if _restart_enable_now():
                try:
                    _restart_start('ip-change %s->%s' % (prev, ip))
                except Exception:
                    _sexc('restart_start')
        if ip:
            pending = ip
        time.sleep(IPWATCH_INTERVAL)


# ===== v6129（M3）：IP 切换自动重启编排器 + 中英双语公告（默认 dry-run）=====
#   开关：环境变量 IPWATCH_RESTART=1 才会在 IP 变化时启动编排；
#         IPWATCH_RESTART_DRY=1（默认）只走状态机 + 公告，**不**执行存档/停服/起服。
RESTART_ENABLE = str(os.environ.get('IPWATCH_RESTART') or '0').strip() == '1'
RESTART_DRY = str(os.environ.get('IPWATCH_RESTART_DRY') or '1').strip() == '1'
RESTART_ROUND = 600            # 每 10 分钟一轮公告
# v6440（用户口径「更新一次只能一台 仅限于 缓存覆盖文件的步骤，别的步骤正常放行」）：
#   更新/回滚批次的**复制（sync）步骤**严格串行（避免两台各 11 GB 抢磁盘 IO），
#   但 savekill / startq / verify 正常按 RESTART_PARALLEL 并行。
_RESTART_SYNC_SERIAL = threading.Lock()
RESTART_ANN_WINDOW = 60        # 每轮只公告前 1 分钟
RESTART_ANN_OFFSETS = (0, 30)  # 00:00 中文，00:30 英文
RESTART_EMPTY_SAMPLES = 3
RESTART_EMPTY_SPAN = 180
# v6177（用户 2026-11-06 决定）：这些服**不做在线人数判断**，公告后直接进入空置确认。
#   原因：Bob（俱乐部）是独立区域（不通过集群传送进入），ASA 侧在线列表不刷新（游戏侧已知 BUG），
#   永远读到「有人在线」⇒ 空置判断永不通过 ⇒ 自动重启永久卡在 announce 阶段。
RESTART_SKIP_EMPTY = {'Bob'}

# v6179（用户口径）：savekill 任务的分步圆点 —— 复用自动重启 steps 机制（{key,label,state}），
#   前端 lbTaskStepsHtml() 直接渲染，不新增任何前端渲染代码。
SAVEKILL_STEPS = (('saveworld', u'存档'), ('verify', u'存档校验'), ('kill', u'终止'))


# ===== v6338（用户口径「5 个步骤点的 tips 都是 ////」）：分步圆点真正着色 =====
#   背景：MOD/API 分发、MOD/API 清理、本地包下载共 5 处 steps 原本是**纯字符串**，
#   前端只认 {key,label,state} ⇒ 名字丢失（tips 成 " /  /  / "）、圆点恒灰。
#   统一改为 _steps_apply() 生成带 state 的数组，零调用点改动（按 pct + phase + msg 自动推断）。
STEP_5_DEPLOY = (('stop', u'停服'), ('bak', u'备份'), ('copy', u'复制'),
                 ('verify', u'校验'), ('start', u'起服'))
STEP_3_CLEAN = (('scan', u'扫差异'), ('move', u'移入备份'), ('refresh', u'刷新状态'))
STEP_4_PKG = (('query', u'查询最新版本'), ('dl', u'下载'),
              ('unpack', u'解压'), ('verify', u'校验入库'))
STEP_4_ZH = (('remote', u'读云端清单'), ('dl', u'下载'),
             ('unpack', u'解压'), ('manifest', u'写清单'))

# pct 阈值 -> 「前 N 步已 ok、第 N+1 步进行中」
_STEP_PCT_TABLE = {
    'deploy': ((100, 5), (90, 4), (70, 3), (45, 2), (20, 1), (0, 0)),
    'clean': ((100, 3), (6, 1), (0, 0)),
    'pkg': ((100, 4), (90, 3), (70, 2), (10, 1), (0, 0)),
    'zh': ((100, 4), (70, 3), (10, 1), (0, 0)),
}


def _steps_apply(defs, pct, phase, msg, kind):
    """按进度算出 [{'key','label','state'}]。
       · phase ok/done ⇒ 全 ok
       · phase fail ⇒ 用 msg 关键词定位失败步（该步 fail、之前 ok、之后 wait），
         找不到关键词就用 pct 推断的当前步标 fail
       · 其余 ⇒ 前 N 步 ok、第 N+1 步 run、余 wait"""
    its = [{'key': str(k), 'label': str(lab), 'state': 'wait'} for k, lab in (defs or ())]
    n = len(its)
    if not n:
        return its
    if phase in ('ok', 'done'):
        for x in its:
            x['state'] = 'ok'
        return its
    p = int(pct or 0)
    tab = _STEP_PCT_TABLE.get(kind) or ((100, n), (0, 0))
    done_n = 0
    for lim, k2 in tab:
        if p >= lim:
            done_n = k2
            break
    done_n = max(0, min(n, done_n))
    if phase == 'fail':
        M = msg or u''
        idx = -1
        for i, x in enumerate(its):
            lab = x['label']
            if not lab:
                continue
            if (lab in M) or (len(lab) > 2 and lab[:2] in M):
                idx = i
                break
        if idx < 0:
            idx = min(n - 1, done_n)
        for i, x in enumerate(its):
            x['state'] = 'fail' if i == idx else ('ok' if i < idx else 'wait')
        return its
    for i, x in enumerate(its):
        x['state'] = 'ok' if i < done_n else ('run' if i == done_n else 'wait')
    return its



def _savekill_steps_obj(states):
    _s = states or {}
    return [{'key': k, 'label': lab, 'state': _s.get(k, 'wait')} for k, lab in SAVEKILL_STEPS]


def _savekill_states_by_pct(pct):
    """按进度阈值推断三步状态（与自动重启一致：wait/run/ok）"""
    p = int(pct or 0)
    if p >= 100:
        return {'saveworld': 'ok', 'verify': 'ok', 'kill': 'ok'}
    if p >= 90:
        return {'saveworld': 'ok', 'verify': 'ok', 'kill': 'run'}
    if p >= 58:
        return {'saveworld': 'ok', 'verify': 'run'}
    if p >= 10:
        return {'saveworld': 'run'}
    return {}
RESTART_CLUSTER_QUIET = 180
RESTART_MAX_ATTEMPTS = 3   # v6345（用户口径）：与启动队列口径一致，最多重试 3 次
# v6164（计划 §16 第 6~7 项）
RESTART_START_COOLDOWN = 600        # C7：同一批编排 10 分钟内不重复启动（只更新公告）；手动演练不拦
# v6200（A+C，用户口径）：换 IP 后玩家会瞬间全掉线，但「掉线」≠「走光」。
#   若在掉线空档里就判定空置通过 ⇒ 玩家随后陆续重连时正撞上停服/起服。
#   A：宽限期内不计空置、不发「即将重启」公告（玩家还看不到）。
#   C：宽限期内若从未见到玩家 ⇒ 宽限结束再确认 PROBE 秒仍无人
#      ⇒ 判定「玩家进不来」，直接按空置推进；见到过玩家 ⇒ 走正常等空置。
RESTART_IP_GRACE = 300              # A：换 IP 后宽限期（秒）
RESTART_IP_GRACE_PROBE = 120        # C：宽限结束后「无回归」确认窗口（秒）
RESTART_TOTAL_TIMEOUT = 28800       # v6219（O4）：6h -> 8h。最坏单台 saveworld180+savekill300+
                                    #   startq1200+verify600=2280s，×11 台≈7h > 6h 会被总超时误杀。
RESTART_STARTQ_IDLE_RETRY = 45      # v6219（R1）：入队后 N 秒仍 idle ⇒ 判为「被跳过/未登记」并重入队
RESTART_PARALLEL = 2                # v6221（P2-1，用户 2026-11-07 拍板）：存档→校验→停服段并发上限。
                                    #   依据：存档写 Servers\<srv>\，不写共用集群目录（clusters\9102），
                                    #   多台并行存档不会互相破坏 L3 静默判定；风险仅在「停服窗口重叠」。
                                    #   静默窗口 RESTART_CLUSTER_QUIET 保持 180s 不变。
# v6152（计划 §16 第 1~3 项）：真执行链路的超时与判据
RESTART_SAVEKILL_TIMEOUT = 300     # savekill 单步超时（秒）
# v6173（用户反馈 2026-11-06「中文公告立刻被英文盖住」）：
#   游戏广播提示条只保留最新一条 ⇒ 中英连发必然互盖；
#   中文立即发，英文延后这么多秒再发。
RESTART_ANN_GAP = 10               # 中→英 公告间隔（秒）
RESTART_SAVEWORLD_TIMEOUT = 180    # v6157（C5）：saveworld + DinoData 落盘屏障超时（秒）
RESTART_STARTQ_TIMEOUT = 1200      # 起服单步超时（秒）
RESTART_VERIFY_TIMEOUT = 600       # 起服后等 advertising 的超时（秒）
RESTART_VERIFY_NEEDLE = 'advertising for join'
RESTART_SAMPLE_PER_TICK = 3          # 每 tick 最多采 3 台在线人数（避免 11 台 RCON 打满）
# v6201（用户口径 2026-11-06）：「公告里最好给出预估安全回到服务器的时间（动态）」
#   各步骤耗时取自实测：SaveWorld+DinoData 落盘 12~32s、停服 <30s、起服 ~120s、verify ~30s。
#   每次公告按该服**当前 phase** 重算一次 ⇒ 玩家看到的剩余时间会随时间递减（动态）。
RESTART_ETA_SAVEWORLD = 30          # 存档 + DinoData 落盘屏障（实测 12~32s）
RESTART_ETA_SAVEKILL = 30           # 停服（进程终止）
RESTART_ETA_STARTQ = 120            # 起服到可连接
RESTART_ETA_VERIFY = 30             # 起服后等 advertising for join
RESTART_ETA_TAIL = (RESTART_ETA_SAVEWORLD + RESTART_ETA_SAVEKILL
                    + RESTART_ETA_STARTQ + RESTART_ETA_VERIFY)   # 空置通过后仍需 ≈210s
# v6197：`RESTART_LOG_KEYWORDS` 已随 L2（日志关键字版）删除 —— ASA 实测零命中，从未生效。
# v6204：`RESTART_LOG_QUIET` 常量同批删除（0 引用）。
RESTART_LOG_SCAN_LINES = 400
# L3：集群目录（分号分隔），**留空 = 不启用 L3**
RESTART_CLUSTER_DIRS = [x.strip() for x in (os.environ.get('IPWATCH_CLUSTER_DIRS') or '').split(';') if x.strip()]


def _restart_cluster_dirs():
    """v6136：集群目录解析优先级：
       server_config.json 的 ipwatch_cluster_dirs（列表或分号串）> 环境变量 > 内置默认（D:\\ARK Server\\Servers\\csbbClusters\\clusters\\9102）"""
    out = list(RESTART_CLUSTER_DIRS)
    try:
        v = (_srv_cfg_read() or {}).get('ipwatch_cluster_dirs')
        if isinstance(v, list):
            out = [str(x).strip() for x in v if str(x).strip()]
        elif isinstance(v, str) and v.strip():
            out = [x.strip() for x in v.split(';') if x.strip()]
    except Exception:
        pass
    if not out:
        d = os.path.join(os.path.dirname(DINO_DATA), 'Servers', 'csbbClusters', 'clusters', '9102')
        if os.path.isdir(d):
            out = [d]
    return out
RESTART_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'restart.log')
RESTART_LOG_MAX = 2 * 1024 * 1024        # v6204：日志超过 2MB 转 .1（原无上限）
RESTART_STEPS = (('ann', u'公告'), ('empty', u'等待空置'),
                 ('quiet', u'静默校验'), ('saveworld', u'存档屏障'), ('savekill', u'存档停服'),
                 ('startq', u'起服'), ('verify', u'校验'))
# ===== v6228（P1）：服务器更新模式 =====
#   方案：计划\服务器更新_任务总线复用_实施方案_v1_20261107.md §1.1 / §17.1
#   运行中的服走 8 步（含 sync）；原本停服的服走 3 步（检查->复制->完成，不启动）
UPDATE_STEPS = (('ann', u'公告'), ('empty', u'等待空置'), ('quiet', u'静默校验'),
                ('saveworld', u'存档屏障'), ('savekill', u'停服'),
                ('sync', u'复制差异'), ('startq', u'起服'), ('verify', u'校验'))
UPDATE_STEPS_STOPPED = (('check', u'检查'), ('sync', u'复制差异'), ('done', u'完成'))
UPDATE_SYNC_TIMEOUT = 900        # 单台复制差异超时（秒）：HDD 96s x 3 倍余量 + 停服开销
_RESTART_LOCK = threading.Lock()
_RESTART = {'running': False, 'pendingReason': '', 'reason': '', 't0': 0, 'dry': RESTART_DRY,
            'servers': {}, 'done': [], 'current': '',
            'lastStartAt': 0,   # v6164（C7）：上次真正启动编排的时刻，用于 10 分钟冷却
            # v6228（P1）：编排模式与更新相关上下文
            'mode': 'restart',  # restart | update | rollback
            'verKind': '',      # forced | patch | same | unknown（仅 update/rollback 有意义）
            'srcRoot': ''}      # rollback 时的回滚包目录（空=用 UPDATE_CACHE_PATH）


def _restart_enable_now():
    """v6132：编排开关可热切 —— 环境变量优先，其次 server_config.json 的 ipwatch_restart"""
    if RESTART_ENABLE:
        return True
    try:
        return bool((_srv_cfg_read() or {}).get('ipwatch_restart'))
    except Exception:
        return False


def _restart_dry_now():
    """v6132：演练开关同样可热切（server_config.json 的 ipwatch_restart_dry，默认演练）"""
    try:
        v = (_srv_cfg_read() or {}).get('ipwatch_restart_dry')
        if v is None:
            return RESTART_DRY
        return bool(v)
    except Exception:
        return RESTART_DRY


# v6217b：进程启动时以配置为准同步快照 —— _RESTART['dry'] 原先取模块常量 RESTART_DRY
#   （环境变量 IPWATCH_RESTART_DRY 未设时为 True），所以配置里 dry=false 时，
#   /api/ipwatch 的 restart.dry 与任务条 meta.dry 仍报 true；真跑时前端显示「演练」会误导验收。
#   实际执行以 _restart_start 内的 _restart_dry_now() 为准，此处只修显示。
try:
    _RESTART['dry'] = bool(_restart_dry_now())
except Exception:
    pass


# ===== v6135：服务器级独占锁 =====
#   hard：回档/撤销回档 —— 不可被人工打断（仅管理员强制终止）
#   soft：IP 重启编排 / 启动队列成员 —— **允许人工操作打断**（需 interrupt=1）
SRV_LOCK_HARD = ('rollback', 'restore')
SRV_LOCK_SOFT = ('restart', 'queue', 'refresh')   # v6141：刷新数据也是软锁（可被人工操作打断）
SRV_LOCK_TTL = 1800
SRV_LOCK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server_locks.json')
_SRV_LOCK = {}
_SRV_LOCK_LOCK = threading.Lock()


def _srv_lock_save_locked():
    try:
        tmp = SRV_LOCK_FILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(_SRV_LOCK, f, ensure_ascii=False)
        os.replace(tmp, SRV_LOCK_FILE)
    except Exception:
        _sexc('srv_lock_save')


def _srv_lock_gc():
    now = time.time()
    with _SRV_LOCK_LOCK:
        dead = [s for s, v in _SRV_LOCK.items() if now - float(v.get('beat') or 0) > SRV_LOCK_TTL]
        for s in dead:
            _SRV_LOCK.pop(s, None)
        if dead:
            _srv_lock_save_locked()
    return len(dead)


def _srv_lock_set(server, kind, owner, label, user='', ttl=None):
    now = time.time()
    with _SRV_LOCK_LOCK:
        _SRV_LOCK[server] = {'server': server, 'kind': kind, 'owner': owner,
                             'label': label, 'user': str(user or ''),
                             'ts': now, 'beat': now, 'ttl': int(ttl or SRV_LOCK_TTL)}
        _srv_lock_save_locked()


def _srv_lock_beat(server, owner=None):
    now = time.time()
    with _SRV_LOCK_LOCK:
        v = _SRV_LOCK.get(server)
        if v and (owner is None or v.get('owner') == owner):
            v['beat'] = now


def _srv_lock_clear(server, owner=None):
    with _SRV_LOCK_LOCK:
        v = _SRV_LOCK.get(server)
        if v and (owner is None or v.get('owner') == owner):
            _SRV_LOCK.pop(server, None)
            _srv_lock_save_locked()


def _srv_lock_get(server):
    with _SRV_LOCK_LOCK:
        return dict(_SRV_LOCK.get(server) or {})


def _srv_lock_snapshot():
    _srv_lock_gc()
    with _SRV_LOCK_LOCK:
        return dict((s, dict(v)) for s, v in _SRV_LOCK.items())


_RESTART_LOG_LOCK = threading.Lock()


def _restart_log(line):
    """v6204：① 加锁（tick 主线程 + 执行器线程并发 append）
              ② 按大小轮转（RESTART_LOG_MAX，转成 .1）—— 原来无上限，长期无限增长。"""
    try:
        with _RESTART_LOG_LOCK:
            try:
                if os.path.getsize(RESTART_LOG) > RESTART_LOG_MAX:
                    _bak = RESTART_LOG + '.1'
                    try:
                        if os.path.isfile(_bak):
                            os.remove(_bak)
                    except Exception:
                        pass
                    os.replace(RESTART_LOG, _bak)
            except Exception:
                pass
            with open(RESTART_LOG, 'a', encoding='utf-8') as f:
                f.write('[%s] %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), line))
    except Exception:
        pass


def _restart_cn(srv):
    try:
        return (SERVER_THEMES.get(srv) or {}).get('name') or srv
    except Exception:
        return srv


def _restart_steps_def(st):
    """v6228：按编排模式与「进入时是否在运行」选步骤集
       · restart                    -> RESTART_STEPS（7 步）
       · update/rollback + 在运行    -> UPDATE_STEPS（8 步，含 sync）
       · update/rollback + 原本停服  -> UPDATE_STEPS_STOPPED（3 步：检查->复制->完成）"""
    _mode = str(_RESTART.get('mode') or 'restart')
    if _mode in ('update', 'rollback'):
        # v6239（B3）：按 targets 动态改 sync 步骤标签（实现上仍是单阶段内串行两项，
        #   故无需新增 sync_zh 独立阶段 —— 方案 §4 的 9 步在此收敛为「sync 标签变化」）
        _tg = _RESTART.get('targets') or ['server']
        _has_sv = ('server' in _tg)
        _has_zh = ('zh' in _tg)
        _labsync = (u'复制本体+汉化' if (_has_sv and _has_zh)
                    else (u'复制汉化' if _has_zh else u'复制差异'))
        _steps = list(UPDATE_STEPS if st.get('wasRunning', True) else UPDATE_STEPS_STOPPED)
        return tuple([((k, _labsync) if k == 'sync' else (k, lab)) for k, lab in _steps])
    return RESTART_STEPS


def _restart_steps_obj(st):
    phases = st.get('steps') or {}
    return [{'key': k, 'label': lab, 'state': phases.get(k, 'wait')}
            for k, lab in _restart_steps_def(st)]


def _restart_label(dry=None):
    """v6228：任务标签按 mode（+verKind）生成"""
    _mode = str(_RESTART.get('mode') or 'restart')
    _d = bool(_RESTART.get('dry')) if dry is None else bool(dry)
    if _mode in ('update', 'rollback'):
        _vk = str(_RESTART.get('verKind') or '')
        _tg = _RESTART.get('targets') or ['server']
        # v6335（用户口径）：只有本次真的分发了服务器本体，才谈得上「强制更新」——
        #   原实现只看 verKind，没勾本体也会写「·强制」，与自动重启「按实际动作取名」不一致。
        _suf = ((u'·强制' if _vk == 'forced' else (u'·补丁' if _vk == 'patch' else ''))
                if ('server' in _tg) else '')
        _base = (u'回滚（分发）' if _mode == 'rollback' else u'更新（分发）')
        # v6340（方案 A）：四类目标全部列出（本体/汉化/MOD/API）
        _pname = {'server': u'本体', 'zh': u'汉化', 'mod': u'MOD', 'api': u'API'}
        _parts = [_pname[k] for k in ('server', 'zh', 'mod', 'api') if k in _tg]
        _zsuf = (u'·' + u'+'.join(_parts)) if _parts else u''
        return _base + _suf + _zsuf + (u'·演练' if _d else '')
    return (u'重启（IP 切换·演练）' if _d else u'重启（IP 切换）')


def _restart_push(srv):
    """把单台重启状态镜像到统一任务总线（action=restart / operator=ipwatch ⇒ 「自动」）

    v6204（复核 P1-5）：**状态指纹去重** —— 原来每台每 tick 无条件写，
      11 台 x 4 次/分钟 = 44 次/分钟 频繁落盘 tasks_state.json。
      指纹含 phase/pct/msg/attempts/err/steps，任一变化才写（宽限期倒计时在 msg 里，仍会实时更新）。"""
    # v6260（用户口径「一个服一个任务条 · 不同服不合并」）：**恢复登记 restart|<srv> 单台条**。
    #   v6259 曾误删此条、只留 restart|__batch 汇总条 ⇒ 界面把每台服合并成「全服」，
    #   与用户口径相反。现每台服各写一条，批次汇总条由前端隐藏（见 app_core.js lbTaskRender v6260）。
    st = (_RESTART.get('servers') or {}).get(srv) or {}
    _steps_def = _restart_steps_def(st)
    _sig = '%s|%s|%s|%s|%s|%s' % (
        st.get('phase'), st.get('pct'), st.get('msg'), st.get('attempts'),
        st.get('err'), u','.join(str((st.get('steps') or {}).get(_k, '')) for _k, _ in _steps_def))
    if st.get('_pushSig') == _sig:
        return
    st['_pushSig'] = _sig
    ph = str(st.get('phase') or 'queue')
    phase = 'ok' if ph == 'done' else ('fail' if ph == 'fail' else 'run')
    _utask_put('restart|%s' % srv, srv, 'restart', 'ipwatch',
               label=_restart_label(),
               msg=(st.get('msg') or ''), pct=int(st.get('pct') or 0), phase=phase,
               steps=_restart_steps_obj(st), err=(st.get('err') or ''),
               meta={'attempts': int(st.get('attempts') or 0), 'dry': bool(_RESTART.get('dry')),
                     'reason': _RESTART.get('reason') or '',
                     'mode': str(_RESTART.get('mode') or 'restart'),
                     'wasRunning': bool(st.get('wasRunning', True)),
                     'finalStatus': (st.get('finalStatus') or '')})
    _restart_push_batch()


def _restart_push_batch():
    """v6219（O1）：编排**汇总行** —— 原来 11 台各一条 restart|<srv>，一次编排最多 33 条任务行
       （11 重启 + N 存档 + N 启动）。这里额外维护一条 restart|__batch 表达整体进度，
       单台明细仍保留（前端默认折叠）。指纹化，只在变化时写盘。"""
    try:
        svs = _RESTART.get('servers') or {}
        if not svs:
            return
        tot = len(svs)
        dn = sum(1 for v in svs.values() if v.get('phase') == 'done')
        fl = sum(1 for v in svs.values() if v.get('phase') == 'fail')
        run = bool(_RESTART.get('running'))
        cur = _RESTART.get('current') or ''
        dry = bool(_RESTART.get('dry'))
        if not run and (dn + fl) >= tot:
            phase = 'fail' if fl else 'ok'
        else:
            phase = 'run'
        # v6259（用户口径「进度条一直看不到进度」）：pct 按每台**真实进度**加权。
        #   原来 pct = 已完成台数/总数 ⇒ 单台分发时恒为 0 ⇒ 前端 (pct>0?pct%:'等待中') 永远「等待中」。
        _acc = 0.0
        for _v in svs.values():
            if str(_v.get('phase') or '') in ('done', 'fail'):
                _acc += 100.0
            else:
                _acc += float(_v.get('pct') or 0)
        pct = int(round(_acc / max(1, tot)))
        msg = u'已完成 %d/%d 台' % (dn + fl, tot)
        if fl:
            msg += u'（失败 %d）' % fl
        _sk_now = [k for k, v in svs.items() if v.get('phase') == 'savekill']
        if _sk_now and run:
            msg += u' · 处理中 %s' % u','.join(_sk_now)
        elif cur and run:
            msg += u' · 当前 %s' % cur
        _stopped_n = sum(1 for v in svs.values()
                         if not bool(v.get('wasRunning', True)))
        if _stopped_n and str(_RESTART.get('mode') or '') in ('update', 'rollback'):
            msg += u'（其中 %d 台保持停服）' % _stopped_n
        # v6259（用户口径「任务过程中状态就没有刷新过」）：指纹**必须含 pct + msg**。
        #   原指纹只含 tot/dn/fl/cur/run/dry —— 单台分发时 dn+fl 恒 0、cur 只在进入 savekill 时才变，
        #   于是指纹长时间不变 ⇒ 批次条永不更新 ⇒ 前端永远停在最初那一眼（「等待中 / 0/1 台」）。
        _sig2 = '%d|%d|%d|%s|%s|%s|%d|%s' % (tot, dn, fl, cur, run, dry, pct, msg)
        if _RESTART.get('_batchSig') == _sig2:
            return
        _RESTART['_batchSig'] = _sig2
        # v6335（用户口径）：批次条也要带实际服务器名 —— 原 server/srvName 都空，
        #   前端 fallback 成「全服」，单台分发时被读成「全服在更新」。
        _bnm = u'、'.join(_restart_cn(k) for k in sorted(svs.keys()))
        _utask_put('restart|__batch', '', 'restart', 'ipwatch',
                   label=_restart_label(dry), srv_name=_bnm[:60],
                   msg=msg, pct=pct, phase=phase,
                   meta={'batch': True, 'done': dn, 'fail': fl, 'total': tot,
                         'dry': dry, 'reason': _RESTART.get('reason') or '',
                         'mode': str(_RESTART.get('mode') or 'restart'),
                         'stopped': _stopped_n})
    except Exception:
        pass


# v6171（计划 §16 第 8 项验收）：英文公告需用英文地图名
#   （原先 _restart_targets() 返回中文名，直接拼进英文句 ⇒ Transfer targets: 孤岛 / 焦土）
SRV_EN = {'Isl': 'The Island', 'Sco': 'Scorched Earth', 'Cen': 'The Center',
          'Abe': 'Aberration', 'Ext': 'Extinction', 'Ast': 'Astraeos',
          'Rag': 'Ragnarok', 'Val': 'Valguero', 'Bob': 'Club ARK',
          'Los': 'Lost Colony', 'Gen': 'Genesis'}


def _restart_targets():
    """已重启完成的服务器 key 列表（v6171：原返回中文名，改为 key 以便按语言取名）"""
    return list(_RESTART.get('done') or [])


def _restart_ann_names(lang, keys, limit=3):
    """目标服名串：最多列 limit 台，余下折叠成「等 N 台」/ 「+N more」
       —— 200 字节上限下 11 台全量中文名会超限（实测 274 字节）"""
    ks = list(keys or [])
    out = []
    for k in ks[:limit]:
        out.append(SRV_EN.get(k, k) if lang == 'en' else _restart_cn(k))
    s = u' / '.join(out)
    if len(ks) > limit:
        s += (u' +%d more' % (len(ks) - limit)) if lang == 'en' else (u' 等 %d 台' % len(ks))
    return s


def _restart_eta_sec(srv):
    """v6201（用户口径）：预估「该服重新可进」还需多少秒 —— 让公告能说「约 X 分钟后可回」。

    按该服**各自**的 phase 独立计算（11 台并行推进，进度各不相同）。
    返回 int 秒数；返回 None = 无法预估（已失败），此时公告不写时间。

    | phase    | 剩余构成                                            |
    |----------|-----------------------------------------------------|
    | announce | 宽限期剩余 / 空置剩余 / 满额 180s，再 + 尾部 210s    |
    | ready    | 尾部 210s（空置+静默已通过，即将存档停服）           |
    | savekill | 停服 30 + 起服 120 + 校验 30 = 180s                  |
    | startq   | 起服 120 + 校验 30 = 150s                            |
    | verify   | 30s                                                 |
    | done     | 0（已可进）                                          |

    ⚠ 宽限期内按「之后仍满额等空置」保守估 —— 若玩家始终不回归会自动跳过空置（v6200 C 分支），
      实际比预估更快，玩家看到的是**上界**，不会产生「说好了却还没好」的抱怨。"""
    st = (_RESTART.get('servers') or {}).get(srv) or {}
    ph = str(st.get('phase') or u'')
    now = time.time()
    if ph == 'done':
        return 0
    if ph == 'fail':
        return None
    if ph == 'verify':
        return RESTART_ETA_VERIFY
    if ph == 'startq':
        return RESTART_ETA_STARTQ + RESTART_ETA_VERIFY
    if ph == 'savekill':
        return RESTART_ETA_SAVEKILL + RESTART_ETA_STARTQ + RESTART_ETA_VERIFY
    # ---- announce / ready：还要先过「空置」这道关 ----
    _wait = float(RESTART_EMPTY_SPAN)
    if ph == 'ready':
        _wait = 0.0
    else:
        gu = float(st.get('graceUntil') or 0)
        if gu and now < gu:
            _wait = (gu - now) + RESTART_EMPTY_SPAN      # v6200 A：宽限期内保守估满额空置
        else:
            es = float(st.get('firstEmptyTs') or 0)
            if es:
                _wait = max(0.0, RESTART_EMPTY_SPAN - (now - es))
    return int(_wait) + RESTART_ETA_TAIL


def _restart_ann_text(lang, players, targets, eta=None):
    """v6175（用户 2026-11-06「言简意赚，扫一眼就能了解」）：
       按「发生什么 → 会怎样 → 你要做什么」三段式重写，删掉客套话。
       旧版：中文 65 字 / 英文 143 字符；新版：约 28 字 / 70 字符。
       v6201（用户口径）：插入**动态** ETA「预计约 X 分钟后可重新进入」（粗粒度取整到分钟）。
         eta=None ⇒ 不写时间（phase=fail 时）；eta 由 _restart_eta_sec(srv) 每次公告重算。"""
    tg = _restart_ann_names(lang, targets)
    _m = 0
    if eta is not None:
        try:
            # 四舍五入到分钟（+30s 再整除）；**不能用 round()** —— 它是银行家舍入，
            #   round(150/60)=round(2.5)=2 ⇒ 150s 会报「约 2 分钟」，偏差明显。
            _m = int((float(eta) + 30.0) // 60.0)
        except Exception:
            _m = 0
        if _m < 1:
            _m = 1                      # 已进入 verify 等尾段 ⇒ 至少报 1 分钟，不报 0
    _ba_cn = (u'预计约 %d 分钟后可重新进入。' % _m) if _m else u''
    _ba_en = (u'Back in ~%d min. ' % _m) if _m else u''
    if lang == 'cn':
        s = u'【维护】公网IP变更，玩家下线后自动重启。' + _ba_cn
        s += ((u'可传送至：' + tg) if targets else u'请尽快下线。')
        s += u'（在线%d人）' % players
    else:
        s = u'[Maintenance] IP changed. Restart when empty. ' + _ba_en
        s += ((u'Transfer to: ' + tg) if targets else u'Please log off. ')
        s += u'(online: %d)' % players
    return s[:200]


def _restart_announce_real_now():
    """v6169（计划 §16 第 8 项验收）：dry 模式下**是否也真发广播**。
       仅用于验收「公告文案 + 200 字符/字节上限」，默认关；
       开启后 dry 仍不会停服/起服（savekill / startq 受 dry 保护不变）。"""
    try:
        v = (_srv_cfg_read() or {}).get('ipwatch_announce_real')
        return bool(v)
    except Exception:
        return False


def _restart_ann_send(srv, txt):
    """v6173：单条广播发送（从 _restart_announce 抽出，供延时回调复用）"""
    try:
        _rcon_exec(srv, 'broadcast %s' % txt, timeout=8)
    except Exception as e:
        _restart_log('announce fail %s: %s' % (srv, e))


def _restart_announce_done(srv):
    """v6204（复核 P1-8）：该服重启完成 → 发一条「已恢复」公告。
       原来只发「即将重启」，玩家不知道什么时候能进（尤其换 IP 场景等了几十分钟）。
       dry 且未开 announce_real 时只记日志，不真发广播（与 _restart_announce 同口径）。"""
    if bool(_RESTART.get('dry')):
        _restart_log('DRY announce-done %s' % srv)
        if not _restart_announce_real_now():
            return
    _restart_ann_send(srv, u'【维护】本服已完成重启，可重新进入。')


def _restart_announce(srv, players, lang=None):
    """v6174（用户 2026-11-06「中文很快被英文盖住」「10 秒不太够」）：
       真因不是“连发”，而是 **_restart_announce() 每次都把中英两条全发**，
       而上游 `_restart_tick()` 每轮会调它 **2 次**（cn 槽 + en 槽，见 RESTART_ANN_OFFSETS=(0,30)）
       ⇒ 实际每轮每台发 **4 条**，中文自然被连续盖住。
       现按槽只发单语言：cn 槽 → 只发中文，en 槽 → 只发英文，间隔天然 = 槽间距 30s。
       参数 lang 为 None 时保持旧行为（中英都发），供其他调用方兼容。"""
    targets = _restart_targets()
    _eta = _restart_eta_sec(srv)      # v6201：动态 ETA（每台按自身阶段算，每次公告刷新）
    _dry_an = bool(_RESTART.get('dry'))
    _real_an = (not _dry_an) or _restart_announce_real_now()   # v6169
    langs = (lang,) if lang in ('cn', 'en') else ('cn', 'en')
    for lg in langs:
        txt = _restart_ann_text(lg, players, targets, eta=_eta)
        if _dry_an:
            _restart_log('DRY announce %s [%s] %s' % (srv, lg, txt))
            if not _real_an:
                continue
        _restart_ann_send(srv, txt)


def _restart_players(srv):
    """RCON ListPlayers 计数；不可用返回 None"""
    try:
        ok, txt = _rcon_exec(srv, 'ListPlayers', timeout=8)
        if not ok:
            return None
        n = 0
        for ln in (txt or '').splitlines():
            s = ln.strip()
            if not s or 'No Players Connected' in s:
                continue
            head = s.split('.')[0]
            if head.isdigit():
                n += 1
        return n
    except Exception:
        return None


def _restart_snapshot():
    with _RESTART_LOCK:
        return {'running': bool(_RESTART.get('running')), 'reason': _RESTART.get('reason') or '',
                'dry': bool(_RESTART.get('dry')), 'enable': _restart_enable_now(),
                'current': _RESTART.get('current') or '',
                'done': list(_RESTART.get('done') or []),
                # v6204（复核 P1-4）：补 steps / 宽限倒计时 / 动态 ETA / 在线人数 ——
                #   原来只有 phase/pct/msg/attempts，前端拿不到宽限期剩余与预计可回时间
                #   （任务条走 steps，/api/ipwatch 没有 ⇒ 两套数据源不一致）。
                'pendingReason': _RESTART.get('pendingReason') or '',
                'elapsed': (int(time.time() - float(_RESTART.get('t0') or 0))
                            if _RESTART.get('t0') else 0),
                'servers': dict((k, {'phase': v.get('phase'), 'pct': v.get('pct'),
                                     'msg': v.get('msg'), 'attempts': v.get('attempts') or 0,
                                     'steps': _restart_steps_obj(v),
                                     'ipMode': bool(v.get('ipMode')),
                                     'sawPlayer': bool(v.get('sawPlayer')),
                                     'players': v.get('players'),
                                     'graceLeft': (max(0, int(float(v.get('graceUntil') or 0) - time.time()))
                                                   if v.get('graceUntil') else 0),
                                     'eta': _restart_eta_sec(k),
                                     'err': v.get('err') or ''})
                                for k, v in (_RESTART.get('servers') or {}).items())}


def _batch_busy_probe():
    """v6276（用户口径 2026-11-08「同时只允许一个批次在运行（防止混乱）」）：
    探测当前是否有批次占用。返回 (busy, owner, remaining, kind)。

    优先级：编排（restart）> 启动队列（startq）。
    · kind='restart' → owner 恒为 'ipwatch'
    · kind='startq'  → owner 为发起人（_SRVCTL_STARTQ['user']）
    """
    try:
        if bool(_RESTART.get('running')):
            _sv = _RESTART.get('servers') or {}
            _left = sum(1 for _v in _sv.values()
                        if str(_v.get('phase') or '') not in ('done', 'fail'))
            return True, 'ipwatch', _left, 'restart'
    except Exception:
        pass
    try:
        _q = _SRVCTL_STARTQ or {}
        if bool(_q.get('running')):
            _left = len(_q.get('queue') or []) + len(_q.get('active') or {})
            return True, str(_q.get('user') or ''), _left, 'startq'
    except Exception:
        pass
    return False, '', 0, ''


def _batch_busy_error(busy, owner, left, kind):
    """v6276：互斥拒绝时返回给前端的统一文案（前端已有透出逻辑，无需改渲染）。"""
    _k = u'重启编排' if kind == 'restart' else u'启动队列'
    return (u'当前有批次正在进行中（%s · 发起人 %s · 剩余 %d 台），'
            u'请等它跑完再启动' % (_k, owner or u'未知', int(left or 0)))


def _restart_start(reason, dry_override=None, force=False, mode='restart',
                   servers=None, ver_kind='', src_root='', targets=None, deploy_plans=None):
    """v6228（P1）：支持 mode / servers
       · servers=None   => 全部 11 台（restart 原行为完全不变）
       · servers=[...]  => **只调度这些台**（需求 ①：只对选中服分发）
       · mode='update'  => savekill 段走 stop -> sync（见 _restart_tick）
       · mode='rollback'=> 同上，但 src_root 指向回滚包目录
       · 每台记录 wasRunning（进入时是否在运行）=> 停服批走 3 步快速通道（§17.1）"""
    _dry = _restart_dry_now() if dry_override is None else bool(dry_override)
    _mode = str(mode or 'restart')
    # v6276（用户口径「同时只允许一个批次在运行」）：已有**别人**的启动队列在跑时，不允许再起编排。
    #   编排自己的 startq 调用不走这里（走 _srvctl_startq_new），故不会自锁。
    #   演练（dry）不受限，方便反复验证流程。
    if not _dry:
        try:
            _bb, _bo, _bl, _bk = _batch_busy_probe()
            if _bb and _bk == 'startq' and str(_bo or '') != 'ipwatch':
                _restart_log('start REJECTED mode=%s: 启动队列占用中（发起人 %s · 剩余 %d 台）'
                             % (_mode, _bo or '?', _bl))
                return False
        except Exception:
            _sexc('restart_busy_probe')
    _picked = None
    if servers is not None:
        _picked = []
        for _s in servers:
            _s2 = str(_s or '').strip()
            if _s2 and (_s2 in SERVERS) and (_s2 not in _picked):
                _picked.append(_s2)
        if not _picked:
            _restart_log('start REJECTED mode=%s: servers 列表为空或全部无效 %r'
                         % (_mode, servers))
            return False
    # 运行状态快照：**在锁外取**（内部有 HTTP，不能持 _RESTART_LOCK）
    # v6272（用户原则 2026-11-08「本来就是停服状态的，任务后也必须是停服状态」）：
    #   原来只在 update/rollback 取快照 ⇒ restart 模式完全不知道谁在跑，
    #   已停服的服仍去 saveworld（RCON 10061）⇒ 必然报「存档屏障失败」（2026-11-08 实测 6 台）。
    #   现改为**所有 mode 都取**，供下方统一的 `if not wasRunning` 判定使用。
    _psnap = {}
    try:
        _psnap = _srvctl_proc_snapshot(10) or {}
    except Exception:
        _psnap = {}
    with _RESTART_LOCK:
        if _RESTART.get('running'):
            # v6204（复核 P0-2）：**不能静默丢弃** —— 公网 IP 抖动/重拨时会连发两次 CHANGED，
            #   原实现第二次直接 return False，编排跑完就结束 ⇒ 服务器仍绑旧 IP。
            #   改为记待处理，本轮收尾后自动再跑一轮（跳过冷却）。
            _RESTART['pendingReason'] = str(reason or '')
            _restart_log('skip start (%s): already running -> 记为待续跑' % reason)
            return False
        # v6164（C7）：10 分钟冷却 —— 自动 / 真触发才拦；手动演练（dry_override 非 None）不拦，方便反复演练
        _last = float(_RESTART.get('lastStartAt') or 0)
        if _last and dry_override is None and not force and (time.time() - _last) < RESTART_START_COOLDOWN:
            _restart_log('skip start (cooldown %ds left): %s'
                         % (int(RESTART_START_COOLDOWN - (time.time() - _last)), reason))
            return False
        _tg_list = []
        for _t in (targets if isinstance(targets, (list, tuple)) else ['server']):
            _t2 = str(_t or '').strip().lower()
            # v6340：MOD / API 也是合法目标（方案 A）
            if _t2 in ('server', 'zh', 'mod', 'api') and (_t2 not in _tg_list):
                _tg_list.append(_t2)
        if not _tg_list:
            _tg_list = ['server']
        _RESTART.update({'running': True, 'reason': str(reason or ''), 't0': time.time(),
                         'dry': _dry, 'servers': {}, 'done': [], 'current': '',
                         'lastStartAt': time.time(),
                         'mode': _mode, 'verKind': str(ver_kind or ''),
                         'srcRoot': str(src_root or ''), 'targets': _tg_list,
                         'deployPlans': dict(deploy_plans or {}),
                         '_batchSig': None})
        now = time.time()
        # v6200（A）：换 IP 触发 ⇒ 开启宽限期（不计空置），并记录「是否见到过玩家」
        _is_ip = ('ip-change' in str(reason or '').lower())
        _targets = _picked if _picked is not None else sorted(SERVERS.keys())
        for srv in _targets:
            # v6272（用户原则 + 保守判定）：
            #   快照明确 running/starting ⇒ 在运行
            #   快照明确返回其它值（stopped 等）⇒ 已停服
            #   快照查不到该服 / 快照失败（_psnap 为空）⇒ **当作在运行**
            #     —— 宁可按完整流程慢一点，也绝不误判「已停服」而跳过存档导致丢档。
            _raw_run = str(_psnap.get(srv) or '').strip().lower()
            if _raw_run in ('running', 'starting'):
                _was_run = True
            elif _raw_run:
                _was_run = False
            else:
                _was_run = True
            _RESTART['servers'][srv] = {'phase': 'announce', 'pct': 5,
                                        'msg': (u'线路切换宽限期，等待玩家回归' if _is_ip
                                                else u'公告期，等待空置'),
                                        'attempts': 0, 'steps': {'ann': 'run'}, 'empty': [],
                                        'firstEmptyTs': 0, 'err': '', 'annStart': now,
                                        'lastAnnRound': -1, 'annSlot': '',
                                        'ipMode': _is_ip,
                                        'graceUntil': (now + RESTART_IP_GRACE) if _is_ip else 0,
                                        'probeUntil': 0,
                                        'sawPlayer': False,
                                        'wasRunning': bool(_was_run),
                                        'finalStatus': '',
                                        'syncDone': False, 'syncOk': False, 'syncMsg': '',
                                        'syncAt': 0, 'syncBytes': 0, 'syncFiles': 0}
    _restart_log('START mode=%s reason=%s dry=%s servers=%d/%d%s'
                 % (_mode, reason, _dry, len(_RESTART.get('servers') or {}), len(SERVERS),
                    (u' picked=%s' % u','.join(_picked)) if _picked else ''))
    # v6274（用户口径 2026-11-08「原本停服状态的基点是启动批次任务时为准」）：
    #   基点即为**批次开始那一刻**的进程快照（servers 每次 start 都重建，不跨批次继承）。
    #   这里把每台的判定落盘，便于事后核对「谁被当成原本停服」。
    try:
        _wr_txt = ', '.join(
            '%s=%d' % (_s5, 1 if (_RESTART['servers'][_s5].get('wasRunning')) else 0)
            for _s5 in (_targets or []) if _s5 in (_RESTART.get('servers') or {}))
        _restart_log('START wasRunning@batch-start: %s' % _wr_txt)
    except Exception:
        pass
    for srv in list((_RESTART.get('servers') or {}).keys()):
        try:
            _restart_push(srv)
        except Exception:
            _sexc('restart_push')
    return True


def _restart_line_ts(ln):
    """从 ShooterGame.log 行首 `[YYYY.MM.DD-HH.MM.SS:mmm]` 取时间戳；失败返回 None
       v6176（排查「用户退出却不被拦」时发现）：日志时间戳是 **UTC**，
       而首行括号内 `MM/DD/YY HH:MM:SS` 才是本地（实测差 8h）。
       原用 time.mktime（按本地时区解析 UTC 串）⇒ epoch 比真实时刻早 8 小时
       ⇒ L2 的 lq 恒 ≥ 28800 秒、`_srv_boot_at` 同样偏 8h（前端「IP 失效」判定也受影响）。
       改用 calendar.timegm 按 UTC 解析。"""
    try:
        if len(ln) < 19 or ln[0] != '[':
            return None
        s = ln[1:19]
        return _cal.timegm((int(s[0:4]), int(s[5:7]), int(s[8:10]),
                            int(s[11:13]), int(s[14:16]), int(s[17:19]), 0, 0, 0))
    except Exception:
        return None


def _srv_boot_at(srv):
    """v6160：该服**本次进程启动时刻**（ShooterGame.log 首行时间戳）；取不到返回 0。
       用途：IP 失效判定 —— 启动时间早于「公网 IP 变化时间」⇒ 该服还跑在旧 IP 环境 ⇒ 玩家搜不到。"""
    try:
        p = os.path.join(CFG_SERVERS_DIR, srv, SRVCTL_LOG_REL)
        if not os.path.isfile(p):
            return 0
        with open(p, 'r', encoding='utf-8', errors='ignore') as f:
            for _i in range(3):
                ln = f.readline()
                if not ln:
                    break
                t = _restart_line_ts(ln)
                if t:
                    return int(t)
        return 0
    except Exception:
        return 0


def _restart_cluster_quiet_sec():
    """L3：集群目录最近一次写入距今秒数；未配置或无文件返回 None（=不启用）"""
    dirs = _restart_cluster_dirs()
    if not dirs:
        return None
    newest = 0.0
    for d in dirs:
        try:
            for root, dirs, files in os.walk(d):
                if root[len(d):].count(os.sep) >= 3:
                    dirs[:] = []
                for fn in files:
                    # v6137：实测集群目录里的文件无扩展名 ⇒ 不再拒绝后缀，任意文件写入都算
                    mt = os.path.getmtime(os.path.join(root, fn))
                    if mt > newest:
                        newest = mt
        except Exception:
            continue
    if not newest:
        return None
    return max(0.0, time.time() - newest)


def _restart_sample(now, limit=None):
    """轮转采样在线人数：优先采「最久未采」的几台"""
    lim = int(limit or RESTART_SAMPLE_PER_TICK)
    items = []
    for srv, st in (_RESTART.get('servers') or {}).items():
        if st.get('phase') in ('done', 'fail'):
            continue
        items.append((float(st.get('lastSample') or 0), srv, st))
    items.sort()
    # v6197（用户口径）：**并行采样** —— 原串行 3 台 x RCON timeout 8s = 最坏 24s > tick 15s，
    #   会把 tick 拉长（公告时点漂移、起服/verify 判定延迟）。
    #   `_rcon_exec` 每次新建 TCP 连接、无共享状态 ⇒ 并发安全。
    _picks = [x[1] for x in items[:lim]]
    _nmap = {}
    if _picks:
        try:
            _Ex = __import__('concurrent.futures', fromlist=['ThreadPoolExecutor']).ThreadPoolExecutor
            _ex = _Ex(max_workers=min(4, len(_picks)))
            try:
                _futs = [(_ex.submit(_restart_players, _s), _s) for _s in _picks]
                for _f, _s in _futs:
                    try:
                        _nmap[_s] = _f.result(timeout=12)
                    except Exception:
                        _nmap[_s] = None
            finally:
                try:
                    _ex.shutdown(wait=False)
                except Exception:
                    pass
        except Exception:
            # 兜底：线程池创建失败 -> 回退串行（行为与旧版一致）
            for _s in _picks:
                try:
                    _nmap[_s] = _restart_players(_s)
                except Exception:
                    _nmap[_s] = None
    for _t, srv, st in items[:lim]:
        _prev = st.get('players')
        n = _nmap.get(srv)
        st['lastSample'] = now
        st['players'] = n
        st['sampled'] = (n is not None)   # v6133：区分「未采样」与「RCON 不可用」
        # v6176：L2 改用「人数由 >0 变 0」的时刻（原日志关键字方案失效）
        if n is not None:
            _n = int(n)
            _p = None if _prev is None else int(_prev)
            if _n > 0:
                st['emptySince'] = 0
            elif _p is not None and _p > 0:
                st['emptySince'] = now
            elif not st.get('emptySince'):
                st['emptySince'] = now


def _restart_startq_state(srv):
    """该服在启动队列中的状态：ok / fail / run / queue / idle"""
    q = _SRVCTL_STARTQ or {}
    # v6195（用户口径）：**先判「正在跑 / 排队中」，再判历史结果** ——
    #   原来 done 优先，若该服既有历史记录又在 queue/active 里，
    #   编排会立刻误判 ok（假成功）或 fail。
    if srv in (q.get('active') or {}):
        return 'run'
    if srv in (q.get('queue') or []):
        return 'queue'
    for x in (q.get('done') or []):
        if x.get('server') == srv:
            return 'ok' if x.get('ok') else 'fail'
    return 'idle'


def _restart_log_has_after(server, needles, since_ts):
    """ShooterGame.log 末 N 行里是否存在「含 needle 且行首时间戳 >= since_ts」的行"""
    try:
        p = os.path.join(CFG_SERVERS_DIR, server, SRVCTL_LOG_REL)
        if not os.path.isfile(p):
            return False
        with open(p, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()[-RESTART_LOG_SCAN_LINES:]
    except Exception:
        return False
    nl = [str(n).lower() for n in needles]
    for ln in lines:
        low = ln.lower()
        if not any(n in low for n in nl):
            continue
        t = _restart_line_ts(ln)
        if t is not None and t >= float(since_ts or 0):
            return True
    return False


def _restart_has_save(srv):
    """C4（v6157）：该服是否存在**非空**主存档（.ark）—— 有存档的服优先重启"""
    try:
        base = os.path.join(CFG_SERVERS_DIR, srv, SRVCTL_ARKS_REL)
        if not os.path.isdir(base):
            return False
        for d in os.listdir(base):
            dp = os.path.join(base, d)
            if not os.path.isdir(dp):
                continue
            try:
                fns = os.listdir(dp)
            except Exception:
                continue
            for f in fns:
                if f.lower().endswith('.ark'):
                    try:
                        if os.path.getsize(os.path.join(dp, f)) > 0:
                            return True
                    except Exception:
                        pass
        return False
    except Exception:
        return False


def _restart_exec_saveworld(srv):
    """C5（v6157）：后台真执行 saveworld；_srvctl_run 自带 DinoData 落盘稳定屏障。
       屏障未过（ok=False 或 data.ok=False）⇒ 调用方回 ready，**不重启**。"""
    def _job():
        ok, msg = False, ''
        try:
            res = _srvctl_run('ipwatch', [srv], 'saveworld', None, silent=True)
            r0 = (res[0] if res else {}) or {}
            ok = bool(r0.get('ok'))
            msg = (r0.get('message') or u'无回执')
            dw = r0.get('data') or {}
            if ok and dw and dw.get('ok') is False:
                ok = False
                msg = u'DinoData 未稳定：%s' % (dw.get('reason') or 'unknown')
        except Exception as e:
            ok, msg = False, repr(e)
        st = (_RESTART.get('servers') or {}).get(srv)
        if st:
            st['swDone'] = True
            st['swOk'] = bool(ok)
            st['swMsg'] = msg
        _restart_log('saveworld %s %s -> %s' % ('ok' if ok else 'FAIL', srv, str(msg)[:80]))
    try:
        _RCON_EXECUTOR.submit(_job)
    except Exception:
        threading.Thread(target=_job, daemon=True).start()


def _restart_exec_savekill(srv):
    """C1：后台真执行 settle 动作；完成后回填状态位（绝不在 tick 里同步等待）
       C6（v6157）：Bob（俱乐部）该图不落盘 ⇒ 走 kill 而不是 savekill"""
    act = 'kill' if srv == 'Bob' else 'savekill'
    def _job():
        ok, msg = False, ''
        try:
            # v6196（用户口径）：**去掉 force=True** ——
            #   v6189 起 savekill 的护栏已改为「保存通过后、kill 前复检」，而 force 会**跳过这次复检**
            #   ⇒ 编排在 T1（0 人）判静默通过后，保存的约 20 秒里若有玩家进服，仍会被 kill。
            #   v6191 后 Bob 也不再拦截，v6180 留 force 的理由已消失。
            #   ⇒ 交给正常护栏：有人就拦，按 RESTART_MAX_ATTEMPTS 重试（超限则该台判 fail）。
            res = _srvctl_run('ipwatch', [srv], act, None, silent=True)
            ok = bool(res and res[0].get('ok'))
            msg = (res[0].get('message') or '') if res else u'无回执'
        except Exception as e:
            ok, msg = False, repr(e)
        st = (_RESTART.get('servers') or {}).get(srv)
        if st:
            st['execDone'] = True
            st['execOk'] = bool(ok)
            st['execMsg'] = msg
        _restart_log('exec %s %s -> ok=%s %s' % (act, srv, ok, str(msg)[:80]))
    try:
        _RCON_EXECUTOR.submit(_job)
    except Exception:
        threading.Thread(target=_job, daemon=True).start()


def _sync_finish(srv, st, now):
    """v6228（§17.1）：sync 成功后的收尾分流
       · 运行中的服 -> startq（起服）
       · 原本停服的服 -> done（**保持停服**，finalStatus='stopped'，不走 startq/verify）"""
    if st.get('wasRunning', True):
        st['steps']['startq'] = 'run'
        st['phase'] = 'startq'
        st['pct'] = 85
        st['msg'] = u'复制完成，准备起服'
    else:
        st['steps']['done'] = 'ok'
        st['phase'] = 'done'
        st['pct'] = 100
        st['finalStatus'] = 'stopped'
        st['msg'] = u'复制完成（本服原本停服，保持停服）'
        try:
            _srv_lock_clear(srv, 'restart|%s' % srv)
        except Exception:
            pass
        if srv not in _RESTART['done']:
            _RESTART['done'].append(srv)
    _restart_push(srv)


def _zh_local_ver():
    """扫描 D:\\Cache-zh 下的版本目录，返回版本号最大者（不依赖远端）"""
    best, bt = '', None
    try:
        with os.scandir(ZH_CACHE_ROOT) as it:
            for e in it:
                try:
                    if not e.is_dir():
                        continue
                except Exception:
                    continue
                vt = _zh_ver_tuple(e.name)
                if not vt:
                    continue
                if bt is None or vt > bt:
                    best, bt = e.name, vt
    except Exception:
        return ''
    return best


def _zh_cache_ready():
    """读本地缓存 manifest -> (ok, ver, man, paks_dir, err)"""
    try:
        rem = _zh_remote()
        ver = rem.get('ver') or ''
        if not ver:
            return False, '', {}, '', u'云端版本未知（需先刷新清单）'
        base = os.path.join(ZH_CACHE_ROOT, ver)
        paks_dir = os.path.join(base, 'paks')
        manp = os.path.join(base, 'manifest.json')
        if not os.path.isfile(manp):
            return False, ver, {}, paks_dir, u'本地包未就绪（请先「下载并解压」）'
        with open(manp, encoding='utf-8') as f:
            man = json.load(f) or {}
        if not (man.get('paks') or []):
            return False, ver, man, paks_dir, u'manifest 无文件清单'
        return True, ver, man, paks_dir, ''
    except Exception as e:
        return False, '', {}, '', ('%s: %s' % (type(e).__name__, e))[:200]


def _zh_prewrite(srv):
    """停服前预写 <目标>.dinozh.tmp（游戏不加载该后缀，可在服务器运行时安全写）
       -> (ok, msg)；失败不影响主流程（停服后会退化为直接复制）"""
    ok, ver, man, paks_dir, err = _zh_cache_ready()
    if not ok:
        return False, err
    try:
        tgt_paks = _zh_paks_dir(srv)
        if not os.path.isdir(tgt_paks):
            return False, u'目标 Paks 目录不存在'
        scan = _zh_scan_paks(srv)
        base_name = 'ShooterGame-Windows_P'
        for b in (scan.get('bases') or []):
            if 'WindowsServer' in b:
                base_name = b
                break
        n = 0
        for it in (man.get('paks') or []):
            srcn = it.get('name') or ''
            sp = os.path.join(paks_dir, srcn)
            if not os.path.isfile(sp):
                continue
            dstn = srcn
            if base_name != 'ShooterGame-Windows_P':
                dstn = base_name + srcn[len('ShooterGame-Windows_P'):]
            tmp = os.path.join(tgt_paks, dstn + '.dinozh.tmp')
            if os.path.isfile(tmp) and os.path.getsize(tmp) == int(it.get('size') or 0):
                n += 1
                continue
            shutil.copy2(sp, tmp)
            n += 1
        return True, u'预写 %d 个文件' % n
    except Exception as e:
        return False, ('%s: %s' % (type(e).__name__, e))[:160]


def _zh_exec_apply(srv, st=None):
    """把缓存里的 3 个 _P 落到目标服（停服后调用）-> (ok, msg)
       方案 §3.7 / §14 B1 B2 C4 C6：优先用预写 .tmp 只做 rename；备份到 D:\\Cache-zh\\backup；
       sidecar 写服务器根；不改 acf/buildId；不删任何目标端额外文件。"""
    try:
        ok, ver, man, paks_dir, err = _zh_cache_ready()
        if not ok:
            return False, err
        tgt_paks = _zh_paks_dir(srv)
        if not os.path.isdir(tgt_paks):
            return False, u'目标 Paks 目录不存在'
        # 磁盘余量（只做汉化时阈值 1 GB）
        try:
            freeb = shutil.disk_usage(UPDATE_SERVERS_ROOT).free
            if freeb < 1 * 2 ** 30:
                return False, u'磁盘剩余 %.1f GB < 1 GB' % (freeb / 2 ** 30)
        except Exception:
            pass
        scan = _zh_scan_paks(srv)
        base_name = 'ShooterGame-Windows_P'
        for b in (scan.get('bases') or []):
            if 'WindowsServer' in b:
                base_name = b
                break
        paks_list = man.get('paks') or []
        tot = len(paks_list)
        # 备份现有文件（回滚用，保留最近 3 份）
        bkroot = os.path.join(ZH_CACHE_ROOT, 'backup', srv)
        bkdir = os.path.join(bkroot, time.strftime('%Y%m%d_%H%M%S'))
        n_bk = 0
        try:
            olds = sorted([d for d in os.listdir(bkroot) if os.path.isdir(os.path.join(bkroot, d))]) \
                if os.path.isdir(bkroot) else []
            for old in olds[:-2]:
                shutil.rmtree(os.path.join(bkroot, old), True)
        except Exception:
            pass
        for it in paks_list:
            srcn = it.get('name') or ''
            cur = os.path.join(tgt_paks, srcn)
            if os.path.isfile(cur):
                try:
                    os.makedirs(bkdir, exist_ok=True)
                    shutil.copy2(cur, os.path.join(bkdir, srcn))
                    n_bk += 1
                except Exception:
                    _sexc('zh_backup')
        # 落盘
        n_ok = 0
        for i, it in enumerate(paks_list):
            srcn = it.get('name') or ''
            sp = os.path.join(paks_dir, srcn)
            if not os.path.isfile(sp):
                return False, u'缓存缺文件 %s' % srcn
            dstn = srcn
            if base_name != 'ShooterGame-Windows_P':
                dstn = base_name + srcn[len('ShooterGame-Windows_P'):]
            dp = os.path.join(tgt_paks, dstn)
            tmp = dp + '.dinozh.tmp'
            need = int(it.get('size') or 0)
            if not (os.path.isfile(tmp) and os.path.getsize(tmp) == need):
                try:
                    shutil.copy2(sp, tmp)
                except Exception as e:
                    return False, u'写入失败 %s：%s' % (dstn, e)
            # v6255：清只读 + 重试 3 次 × 500ms（与本体分发同一套加固）
            try:
                if os.path.exists(dp):
                    try:
                        os.chmod(dp, _stat.S_IWRITE)
                    except Exception:
                        pass
                _le = None
                for _t3 in range(3):
                    try:
                        os.replace(tmp, dp)
                        _le = None
                        break
                    except (PermissionError, OSError) as _e3:
                        _le = _e3
                        if _t3 < 2:
                            time.sleep(0.5)
                if _le is not None:
                    raise _le
            except Exception as e:
                return False, u'覆盖失败 %s：%s' % (dstn, e)
            if os.path.getsize(dp) != need:
                return False, u'校验失败 %s（%d != %d）' % (dstn, os.path.getsize(dp), need)
            n_ok += 1
            if st is not None:
                st['msg'] = u'复制汉化 %d/%d：%s' % (i + 1, tot, dstn[-52:])
                st['pct'] = 88 + int(2.0 * (i + 1) / max(1, tot))
        # sidecar（§14 C6：放服务器根）
        try:
            sc = {'ver': ver, 'variant': man.get('variant') or '',
                  'asset': (man.get('source') or {}).get('name') or '',
                  'at': time.strftime('%Y-%m-%d %H:%M:%S'),
                  'paksBase': base_name,
                  'files': [{'name': it.get('name') or '', 'size': it.get('size') or 0,
                             'sha256': it.get('sha256') or ''} for it in paks_list]}
            with open(os.path.join(UPDATE_SERVERS_ROOT, srv, ZH_SIDECAR_NAME),
                      'w', encoding='utf-8') as f:
                json.dump(sc, f, ensure_ascii=False, indent=1)
        except Exception:
            _sexc('zh_sidecar')
        return True, u'%d 个文件，备份 %d 份，版本 %s' % (n_ok, n_bk, ver)
    except Exception as e:
        return False, ('%s: %s' % (type(e).__name__, e))[:200]


def _restart_exec_sync(srv, src_root=None):
    """v6228（P1 核心）：后台真执行「复制差异 + 改 acf」
       方案 §5.2 / §13 O2 O3 O8 / §11.3：
         · 只复制 add/update，**绝不删除目标端额外文件**（AsaApi/PDB/白名单/汉化包自动安全）
         · 复制顺序：先小文件（<100MB）再大文件按大小降序（O8）
         · shutil.copy2 拿 Windows 文件系统级优化（CopyFileExW）；进度按文件推进（O2 折中）
         · acf 原子写 .tmp + os.replace（O3）"""
    _mode = str(_RESTART.get('mode') or 'update')
    _src = src_root or str(_RESTART.get('srcRoot') or '') or UPDATE_CACHE_PATH
    st = (_RESTART.get('servers') or {}).get(srv) or {}
    _cur = {'rel': ''}

    def _prog():
        # O2：旁路轮询「当前正在复制的目标文件大小」，让大文件复制期间进度也动
        try:
            if not _cur['rel']:
                return
            tp = os.path.join(UPDATE_SERVERS_ROOT, srv, _cur['rel'])
            sz = os.stat(tp).st_size
            _cur['cur'] = sz
        except Exception:
            pass
    def _job_inner():
        ok, msg = False, ''
        n_ok = n_total = 0
        bytes_tot = 0
        _tg = _RESTART.get('targets') or ['server']
        _do_sv = ('server' in _tg)
        _do_zh = ('zh' in _tg)
        _do_mod = ('mod' in _tg)      # v6340：MOD / API 分发并入本编排
        _do_api = ('api' in _tg)
        _msgs = []
        _fail_files = []      # v6255：失败文件清单 [{rel, err}]
        try:
            tgt = os.path.join(UPDATE_SERVERS_ROOT, srv)
            if not os.path.isdir(tgt):
                raise RuntimeError(u'目标目录不存在：%s' % tgt)
            if _do_sv:
                skip_l = _upd_skip_set()
                # 1) 磁盘预检（§6：全盘一次判定，阈值 13 GB）
                try:
                    freeb = shutil.disk_usage(UPDATE_SERVERS_ROOT).free
                except Exception:
                    freeb = None
                if freeb is not None and freeb < 13 * 2 ** 30:
                    raise RuntimeError(u'磁盘剩余 %.1f GB < 13 GB，拒绝复制' % (freeb / 2 ** 30))
                # 1.5) v6255（权限加固·步骤 260.7 第 1 条）：**探针写测**
                #   目标目录 ACL 常见为 Users:(RX)（只读），覆盖已存在文件会 WinError 5。
                #   这里在目标根先写一个探针再删，失败立刻整批中止 ——
                #   绝不出现「11 台已停服、复制才报没权限」的半路翻车。
                _probe = os.path.join(tgt, '.dino_write_probe')
                try:
                    with open(_probe, 'wb') as _pf:
                        _pf.write(b'dino')
                    os.remove(_probe)
                except Exception as _pe:
                    raise RuntimeError(
                        u'目标目录不可写（权限不足）：%s —— 探针写入失败 %s；'
                        u'请把 dino_backend 计划任务改为「以最高权限运行」'
                        u'（RunLevel Highest），或给该目录授予写权限后重试'
                        % (tgt, repr(_pe)[:120]))
                # 2) 差异清单
                # v6438（Bob 2026-11-09 事故）：**不能只比 size** ——
                #   97.17 与 97.16 的 35 个 paks 字节数完全相同（实测 35/35），
                #   但内容不同（sha256：global.utoc / pakchunk11.utoc/.ucas 全不同）。
                #   只比 size ⇒ paks 全判「无变化」⇒ 只复制了 exe（差 17,920 字节）
                #   ⇒ 「新 exe + 旧 paks」= AsyncLoading2.cpp:8438 Assert 启动崩溃。
                #   ⇒ 加 mtime 判据（copy2 保留源 mtime；容差 2 秒防 FS 粒度差异）。
                plan = []
                for rel, sz, mt in _upd_walk(_src, skip_l):
                    tp = os.path.join(tgt, rel)
                    try:
                        _tst = os.stat(tp)
                        tsz = _tst.st_size
                        tmt = int(_tst.st_mtime)
                    except Exception:
                        tsz = -1
                        tmt = -1
                    if tsz == sz and abs(tmt - mt) <= 2:
                        continue
                    plan.append((rel, sz))
                n_total = len(plan)
                bytes_tot = sum(p[1] for p in plan)
                st['syncFiles'] = n_total
                st['syncBytes'] = bytes_tot
                _restart_log('sync %s src=%s files=%d bytes=%d'
                             % (srv, _src, n_total, bytes_tot))
                # 3) 排序：小文件先（快速验证路径/权限），大文件按大小降序
                small = [p for p in plan if p[1] < 100 * 2 ** 20]
                large = sorted([p for p in plan if p[1] >= 100 * 2 ** 20],
                               key=lambda x: -x[1])
                ordered = small + large
                # 4) 逐个复制（copy2 不删任何东西）
                for i, (rel, _sz) in enumerate(ordered):
                    _cur['rel'] = rel
                    sp = os.path.join(_src, rel)
                    tp = os.path.join(tgt, rel)
                    _d = os.path.dirname(tp)
                    if _d and not os.path.isdir(_d):
                        os.makedirs(_d, exist_ok=True)
                    # v6255：覆盖前清只读（目标带 ReadOnly 会 WinError 5）
                    if os.path.exists(tp):
                        try:
                            os.chmod(tp, _stat.S_IWRITE)
                        except Exception:
                            pass
                    # v6255：单文件重试 3 次 × 500ms（覆盖杀软扫描 / 句柄未释放窗口）
                    _last_e = None
                    for _try in range(3):
                        try:
                            shutil.copy2(sp, tp)
                            _last_e = None
                            break
                        except (PermissionError, OSError) as _ce:
                            _last_e = _ce
                            if _try < 2:
                                time.sleep(0.5)
                    if _last_e is not None:
                        _fail_files.append({'rel': rel,
                                            'err': '%s: %s' % (type(_last_e).__name__, _last_e)})
                        raise RuntimeError(u'复制失败 %s（%s）' % (rel, _last_e))
                    n_ok += 1
                    st['pct'] = (55 + int(30.0 * (i + 1) / max(1, len(ordered))) if _do_zh
                                 else 55 + int(35.0 * (i + 1) / max(1, len(ordered))))
                    st['msg'] = (u'复制本体 %d/%d：%s' if _do_zh else u'复制 %d/%d：%s') \
                        % (i + 1, len(ordered), rel[-54:])
                _cur['rel'] = ''
                # 5) acf 原子改写
                _aok, _amsg = _upd_apply_acf_from_src(tgt)
                if not _aok:
                    raise RuntimeError(u'acf 改写失败：%s' % _amsg)
                # 6) 清理 ASAM 残留临时文件（O6）
                try:
                    _w64 = os.path.join(tgt, 'ShooterGame', 'Binaries', 'Win64')
                    if os.path.isdir(_w64):
                        for _f in os.listdir(_w64):
                            if '~RF' in _f or _f.upper().endswith('.TMP'):
                                try:
                                    os.remove(os.path.join(_w64, _f))
                                except Exception:
                                    pass       # 被进程占用就跳过，不中断
                except Exception:
                    pass
                _msgs.append(u'本体 %d 个文件 / %.2f GB，acf 已更新'
                             % (n_ok, bytes_tot / 2 ** 30))
            # v6239（B3）：汉化补丁 —— 只复制 3 个 _P + 写 sidecar，不碰 acf / buildId
            if _do_zh:
                st['msg'] = u'准备复制汉化…'
                st['pct'] = 88
                _zok, _zmsg = _zh_exec_apply(srv, st)
                _msgs.append(u'汉化 %s' % _zmsg)
                if not _zok:
                    raise RuntimeError(u'汉化失败：%s' % _zmsg)
            # v6340：MOD / API 分发（同一条融合任务条内完成，失败走 _restart_step_fail 重试）
            if _do_mod:
                st['msg'] = u'准备复制 MOD…'
                st['pct'] = 92
                _mok, _mmsg = _deploy_mod_apply(srv, st)
                _msgs.append(u'MOD %s' % _mmsg)
                if not _mok:
                    raise RuntimeError(u'MOD 分发失败：%s' % _mmsg)
            if _do_api:
                st['msg'] = u'准备复制 API…'
                st['pct'] = 94
                _aok2, _amsg2 = _deploy_api_apply(srv, st)
                _msgs.append(u'API %s' % _amsg2)
                if not _aok2:
                    raise RuntimeError(u'API 分发失败：%s' % _amsg2)
            ok = True
            msg = u'；'.join([x for x in _msgs if x]) or u'无变更'
        except Exception as e:
            ok, msg = False, repr(e)
            # v6255：带上失败文件清单（不再只说"失败"）
            if _fail_files:
                st['syncFails'] = _fail_files[:50]
                msg = (u'%s；失败 %d 个文件：%s'
                       % (msg, len(_fail_files),
                          '、'.join(x['rel'] for x in _fail_files[:5])))
        st['syncDone'] = True
        st['syncOk'] = bool(ok)
        st['syncMsg'] = msg
        _restart_log('exec sync %s mode=%s -> ok=%s %d/%d %s'
                     % (srv, _mode, ok, n_ok, n_total, str(msg)[:140]))

    def _job():
        # v6440：更新/回滚的**复制步骤串行** —— 抢不到锁就本轮让路，下个 tick 再来
        _lk = (_RESTART_SYNC_SERIAL
               if str(_mode or '').lower() in ('update', 'rollback') else None)
        if _lk is not None:
            if not _lk.acquire(blocking=False):
                try:
                    st['syncAt'] = 0            # 重置 => 下个 tick 重新进 sync 分支
                    st['syncDone'] = False
                    st['msg'] = u'等待其它服完成缓存复制（复制步骤严格串行）'
                    st['pct'] = 80
                except Exception:
                    pass
                try:
                    _restart_log('SYNC WAIT %s（其它服正在复制，本 tick 让路）' % srv)
                except Exception:
                    pass
                return
        try:
            _job_inner()
        finally:
            if _lk is not None:
                try:
                    _lk.release()
                except Exception:
                    pass

    try:
        _RCON_EXECUTOR.submit(_job)
    except Exception:
        threading.Thread(target=_job, daemon=True).start()


# ===== v6340（用户口径「改走方案 A」）：MOD / API 分发并入编排 ----------
#   目标：游戏本体 / 汉化 / MOD / API 四类分发全部走同一条 `restart|<srv>` 融合任务条，
#   共享公告→空置→存档→停服→复制→起服→校验 + 失败重试。
#   计划由 /api/update/apply 预先算好存入 _RESTART['deployPlans']。
def _deploy_mod_apply(srv, st=None):
    """把该服待分发的 MOD 复制进服（备份旧目录 -> copytree -> 文件数校验）。
       计划元素：{srv, pid, want, src, cur}。返回 (ok, msg)。"""
    pl = [x for x in ((_RESTART.get('deployPlans') or {}).get('mod') or []) if x.get('srv') == srv]
    if not pl:
        return True, u'无待分发 MOD'
    ts = time.strftime('%Y%m%d_%H%M%S')
    bak_root = os.path.join(_upd_cache_dir(), '_modbak', ts, srv)
    tgt_base = _mods_dir_of(srv)
    done, fails = 0, []
    for p in pl:
        pid = str(p.get('pid') or '')
        want = str(p.get('want') or '')
        src = str(p.get('src') or '')
        nm = u'%s_%s' % (pid, want)
        try:
            if not src or not os.path.isdir(src):
                fails.append(u'%s：源不存在' % nm)
                continue
            if not os.path.isdir(tgt_base):
                os.makedirs(tgt_base)
            # 备份同 pid 的旧目录
            for x in os.scandir(tgt_base):
                if x.is_dir() and x.name.split('_')[0] == pid:
                    if not os.path.isdir(bak_root):
                        os.makedirs(bak_root)
                    try:
                        _mods_strip_ls(x.path)
                    except Exception:
                        pass
                    shutil.move(x.path, os.path.join(bak_root, x.name))
            dst = os.path.join(tgt_base, nm)
            if os.path.isdir(dst):
                shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(src, dst)
            src_n = sum(len(fs) for _, _, fs in os.walk(src))
            dst_n = sum(len(fs) for _, _, fs in os.walk(dst))
            if src_n != dst_n or src_n <= 0:
                fails.append(u'%s：校验失败 %d/%d' % (nm, dst_n, src_n))
            else:
                done += 1
        except Exception as e:
            fails.append(u'%s：%s' % (nm, repr(e)[:120]))
    if fails:
        return False, u'；'.join(fails[:3])
    return True, (u'%d 个 MOD 已复制' % done)


def _deploy_api_apply(srv, st=None):
    """把该服待分发的 API 文件复制进服（备份 -> copy2 -> md5 校验，失败回滚）。
       计划元素来自 _api_deploy_plan3：{srv,name,rel,src,wantMd5}。返回 (ok, msg)。"""
    pl = [x for x in ((_RESTART.get('deployPlans') or {}).get('api') or []) if x.get('srv') == srv]
    if not pl:
        return True, u'无待分发 API'
    ts = time.strftime('%Y%m%d_%H%M%S')
    bdir = os.path.join(_upd_cache_dir(), '_apibak', ts, srv)
    win = _srv_win64(srv)
    fails, n_ok = [], 0
    for it in pl:
        try:
            dp = os.path.join(win, it['rel'])
            d2 = os.path.dirname(dp)
            if d2 and not os.path.isdir(d2):
                os.makedirs(d2)
            if os.path.isfile(dp):
                bp = os.path.join(bdir, it['rel'])
                bd = os.path.dirname(bp)
                if bd and not os.path.isdir(bd):
                    os.makedirs(bd)
                shutil.copy2(dp, bp)
            try:
                os.chmod(dp, _stat.S_IWRITE)
            except Exception:
                pass
            shutil.copy2(it['src'], dp)
            if it.get('wantMd5') and _md5_of(dp) != it['wantMd5']:
                fails.append(u'%s：md5 不一致' % (it.get('name') or it['rel']))
            else:
                n_ok += 1
        except Exception as e:
            fails.append(u'%s：%s' % (it.get('name') or it.get('rel'), repr(e)[:120]))
    if fails:
        try:
            for it in pl:
                dp = os.path.join(win, it['rel'])
                bp = os.path.join(bdir, it['rel'])
                if os.path.isfile(bp):
                    try:
                        os.chmod(dp, _stat.S_IWRITE)
                    except Exception:
                        pass
                    shutil.copy2(bp, dp)
        except Exception:
            _sexc('deploy_api_rollback')
        return False, u'；'.join(fails[:3]) + u'（已回滚）'
    # v6441（用户口径「config version 分发 API 后没有改啊？」）：
    #   v6400 只在旧独立路径 `_api_deploy_run2` 里同步了 config.json 的 version，
    #   而 v6340 把 API 分发并入本编排后走的是这里 —— 只复制 dll/PluginInfo + md5 校验，
    #   **从未同步 config.json** ⇒ 插件自报仍旧版（如 Bob 卡在 0.8.2 而 dll 已是 0.84）。
    #   失败不影响分发结果（dll/PluginInfo 已就位）。
    try:
        _sync_sok_cfg_ver(srv, pl)
    except Exception:
        _sexc('deploy_api_sync_cfg_ver')
    return True, (u'%d 项已更新' % n_ok)


def _restart_step_fail(srv, st, why):
    """C3：单步失败 -> attempts+1 -> 未超限回 ready 重排队；超限置 fail 并清锁"""
    st['attempts'] = int(st.get('attempts') or 0) + 1
    st['err'] = str(why or '')
    # v6273（用户口径 2026-11-08）：**任务中途已停服的服，重试时跳过存档屏障直接起服** ——
    #   场景：本台初始在运行（wasRunning=True）、savekill 已成功（steps.savekill=='ok'），
    #         但 startq/verify 失败 ⇒ 服务器当前是**停的**。
    #   原逻辑重试会退回 saveworld → RCON 10061（端口无人监听）⇒ 必然失败 ⇒ 3 次后判死。
    #   2026-11-08 实测六台（Isl/Sco/Abe/Rag/Val/Los）全部卡死于此。
    #   ⚠️ 与 v6272「原本停服 ⇒ 保持停服」不冲突：那条针对**初始**状态，这条针对**任务中途**。
    try:
        if bool(st.get('wasRunning', True)) and str((st.get('steps') or {}).get('savekill')) == 'ok':
            st['skipSaveOnRetry'] = True
    except Exception:
        pass
    st['execAt'] = 0
    st['execDone'] = False
    st['execOk'] = False
    st['swAt'] = 0                        # v6157（C5）：存档屏障状态一并复位
    st['swDone'] = False
    st['swOk'] = False
    # v6228：停服批（skipToSync）重试时仍直达 sync，不要退回 saveworld
    if (str(_RESTART.get('mode') or 'restart') in ('update', 'rollback')
            and st.get('skipToSync')):
        st['skStage'] = 'sync'
        st['syncAt'] = 0
        st['syncDone'] = False
    else:
        st['skStage'] = ('savekill' if srv == 'Bob' else 'saveworld')
    st['startqAt'] = 0
    st['verifyAt'] = 0
    for k in ('saveworld', 'savekill', 'sync', 'startq', 'verify'):
        if (st.get('steps') or {}).get(k) == 'run':
            st['steps'][k] = 'wait'
    if st['attempts'] > RESTART_MAX_ATTEMPTS:
        st['phase'] = 'fail'
        st['msg'] = u'重试 %d 次仍失败：%s' % (st['attempts'], why)
        for k in ('saveworld', 'savekill', 'startq', 'verify'):
            if (st.get('steps') or {}).get(k) in ('run', 'wait'):
                st['steps'][k] = 'fail'
        _srv_lock_clear(srv, 'restart|%s' % srv)
        _restart_log('FAIL %s attempts=%d %s' % (srv, st['attempts'], why))
    else:
        st['phase'] = 'ready'
        st['readyAt'] = time.time()
        # v6270：退回 ready 时进度回落到 45 —— 原残留 75 让人误以为「还在起服」，
        #   与「第 N 次重试（等待重新调度）」自相矛盾。
        st['pct'] = 45
        st['msg'] = u'第 %d 次重试（%s）' % (st['attempts'], why)
        _restart_log('RETRY %s attempts=%d %s' % (srv, st['attempts'], why))
    _restart_push(srv)


def _restart_abort(server, by_user=''):
    """v6135：人工操作打断自动重启 —— 本台标记中止，同批其他服继续跑"""
    st = (_RESTART.get('servers') or {}).get(server)
    if not st or st.get('phase') in ('done', 'fail'):
        return False
    st['phase'] = 'fail'
    st['err'] = u'被 %s 手动操作中止' % (by_user or u'用户')
    st['msg'] = st['err']
    steps = st.get('steps') or {}
    for k in list(steps.keys()):
        if steps[k] == 'run':
            steps[k] = 'fail'
        elif steps[k] == 'wait':
            steps[k] = 'skip'
    _srv_lock_clear(server, 'restart|%s' % server)   # v6152：owner 必须与 set 时一致，否则锁清不掉
    _restart_push(server)
    _restart_log('ABORT %s by %s' % (server, by_user))
    return True


def _restart_tick():
    if not _RESTART.get('running'):
        return
    now = time.time()
    dry = bool(_RESTART.get('dry'))
    servers = _RESTART.get('servers') or {}

    # ---- 1) 在线人数采样（节流）----
    _restart_sample(now)

    # ---- 2) 公告：每轮前 60s，00:00 中文 / 00:30 英文 ----
    for srv, st in servers.items():
        if st.get('phase') in ('done', 'fail'):
            continue
        # v6200（A）：宽限期内不发「即将重启」公告 —— 玩家此刻多数还连不上，发了也看不到，
        #   且会让「刚回来就看到即将重启」的玩家以为马上要关服。宽限结束后再正常发。
        if st.get('graceUntil') and now < float(st.get('graceUntil') or 0):
            continue
        el = now - float(st.get('annStart') or now)
        off = el % RESTART_ROUND
        if off < RESTART_ANN_WINDOW:
            slot = 'cn' if off < RESTART_ANN_OFFSETS[1] else 'en'
            tag = '%d:%s' % (int(el // RESTART_ROUND), slot)
            if st.get('annSlot') != tag:
                # v6173（用户反馈 2026-11-06「我在 Cen 里却报 0 人」）：
                #   公告要报「当前在线 N 人」，不能直接用 _restart_sample 的缓存值
                #   —— 它每 tick 只轮转采 3 台，编排刚起时多数服 players=None ⇒ 误报 0 人。
                #   现场实时查一次；RCON 不可用时才回退到上次采样值。
                # v6204（复核 P2-11）：**刚采过就复用**，省一次 RCON ——
                #   原来每轮公告都现场查，而 _restart_sample 可能同 tick 刚采过同一台。
                #   40s 时效判据保证「复用的一定是新鲜值」（v6173 的教训是「采样轮转导致值过期」）。
                _ls = float(st.get('lastSample') or 0)
                if st.get('sampled') and _ls and (now - _ls) < 40:
                    pn = st.get('players')
                else:
                    pn = _restart_players(srv)
                    if pn is None:
                        pn = st.get('players')
                _restart_announce(srv, 0 if pn is None else int(pn), slot)   # v6174：按槽只发单语言
                st['annSlot'] = tag

    # ---- 3) 空置 + 静默校验 -> ready ----
    for srv, st in servers.items():
        if st.get('phase') != 'announce':
            continue
        # ---- v6272（用户原则 2026-11-08）：**统一「进入时已停服」判定，目的地按 mode 分叉** ----
        #   原则：「本来就是停服状态的，任务后也必须是停服状态 ——
        #          可以做其他启动前能做的一切，但绝不允许改变当前状态」。
        #   · update / rollback：跳过存档/停服 → 直接排队**复制差异**（复制后不起服，见 _sync_finish）
        #   · restart          ：重启对它无意义 → 直接判**完成并保持停服**，绝不进 startq
        #   判定**只有这一处** —— 以后修 wasRunning，两条通道同时受益。
        if not st.get('wasRunning', True):
            if str(_RESTART.get('mode') or 'restart') in ('update', 'rollback'):
                st['phase'] = 'ready'
                st['readyAt'] = now
                st['pct'] = 45
                st['hasSave'] = False
                st['skipToSync'] = True
                st['steps'].update({'check': 'ok', 'sync': 'wait'})
                st['msg'] = u'本服已停服，直接排队复制'
            else:
                st['phase'] = 'done'
                st['pct'] = 100
                st['steps'].update({'ann': 'skip', 'empty': 'skip', 'quiet': 'skip',
                                    'saveworld': 'skip', 'savekill': 'skip',
                                    'startq': 'skip', 'verify': 'skip'})
                st['msg'] = u'原本停服，保持停服（未做任何启停）'
                st['skippedStopped'] = True
                try:
                    _srv_lock_clear(srv, 'restart|%s' % srv)
                except Exception:
                    pass
                if srv not in _RESTART['done']:
                    _RESTART['done'].append(srv)
                _restart_log('HOLD-STOPPED %s 保持停服（wasRunning=False，未做任何启停）' % srv)
            _restart_push(srv)
            continue
        n = st.get('players')
        # v6177：RESTART_SKIP_EMPTY 中的服（Bob）不参与在线人数判断，直接视为 0 人
        if srv in RESTART_SKIP_EMPTY:
            n = 0
        # ---- v6200（A+C）：换 IP 场景的宽限期与玩家回归信号 ----
        if st.get('ipMode'):
            if isinstance(n, int) and n > 0:
                st['sawPlayer'] = True          # C：整个 announce 阶段记录是否见到过玩家
            _gu = float(st.get('graceUntil') or 0)
            if _gu and now < _gu:
                st['steps']['empty'] = 'run'
                # v6219（P1-1）：宽限期内**不抬进度** —— 原来 max(...,8) 让人误以为已在重启。
                st['pct'] = 0
                st['msg'] = u'线路切换宽限期剩 %ds（等玩家回归）' % int(_gu - now)
                _restart_push(srv)
                continue                        # 宽限期内**不累计空置**
            # v6204（复核 P0-1）：**宽限结束必须重置公告计时**。
            #   公告段用 el = now - annStart，宽限 300s 内被 continue 跳过但 el 照常增长
            #   ⇒ 宽限结束时 el=300、off=300%600=300 ∉ [0,60) ⇒ **再等 300s 才发第一条公告**。
            #   玩家正好在这 5 分钟回归时完全看不到「即将重启」，与 v6200 的保护意图相反。
            if _gu and not st.get('graceEnded'):
                st['graceEnded'] = True
                st['annStart'] = now
                st['annSlot'] = ''
                _restart_log('GRACE %s 宽限期结束 -> 公告计时重启' % srv)
            if _gu and now >= _gu and not st.get('sawPlayer'):
                # C：宽限结束仍从未见到玩家 ⇒ 再确认 PROBE 秒
                _pu = float(st.get('probeUntil') or 0)
                if not _pu:
                    st['probeUntil'] = now + RESTART_IP_GRACE_PROBE
                    _pu = st['probeUntil']
                    _restart_log('GRACE %s 宽限结束仍无玩家，确认 %ds' % (srv, int(RESTART_IP_GRACE_PROBE)))
                if now < _pu:
                    st['msg'] = u'无玩家回归，确认中剩 %ds' % int(_pu - now)
                    st['pct'] = max(int(st.get('pct') or 0), 12)
                    _restart_push(srv)
                    continue
                # 确认完毕仍无人 ⇒ 判定「玩家进不来」⇒ 直接按空置推进
                st['empty'] = [now] * RESTART_EMPTY_SAMPLES
                st['firstEmptyTs'] = now - RESTART_EMPTY_SPAN
                st['msg'] = u'无玩家回归（玩家无法接入），按空置推进'
                _restart_log('GRACE %s 无回归 ⇒ 跳过空置等待' % srv)
                _restart_push(srv)
            elif st.get('sawPlayer'):
                st['msg'] = u'玩家已回归，等待下线…'

        # v6204（复核 P0-3）：**RCON 不可用要告警** —— 原来 n=None 走 n != 0 分支静默清零空置，
        #   某台 RCON 挂掉时该服永远过不了空置，一路静默卡到 6 小时总超时，restart.log 零异常记录。
        #   仍保持「None ⇒ 重置空置」的保守语义，但连续失败要留痕 + 通知。
        if n is None and srv not in RESTART_SKIP_EMPTY:
            _rf = int(st.get('rconFail') or 0) + 1
            st['rconFail'] = _rf
            if _rf in (1, 5):
                _restart_log('WARN %s RCON 不可用，在线人数无法判定（连续 %d 次）' % (srv, _rf))
            elif _rf % 20 == 0:
                _restart_log('WARN %s RCON 仍不可用（连续 %d 次，约 %d 分钟）'
                             % (srv, _rf, _rf))
                try:
                    _ipwatch_notify('[dino] 自动重启：%s 连续 %d 次探测在线人数失败（RCON 不可用），'
                                    u'该服重启被阻塞' % (srv, _rf))
                except Exception:
                    pass
        else:
            st['rconFail'] = 0
        if n != 0:
            st['empty'] = []
            st['firstEmptyTs'] = 0
            st['steps']['empty'] = 'run'
            st['pct'] = max(int(st.get('pct') or 0), 10)
            if n is None:
                st['msg'] = (u'公告中（RCON 不可用）' if st.get('sampled')
                             else u'公告中，等待采样在线人数…')
            else:
                st['msg'] = u'公告中，当前在线 %d 人' % n
            _restart_push(srv)
            continue
        st.setdefault('empty', []).append(now)
        if not st.get('firstEmptyTs'):
            st['firstEmptyTs'] = now
        if not (len(st['empty']) >= RESTART_EMPTY_SAMPLES
                and now - float(st['firstEmptyTs']) >= RESTART_EMPTY_SPAN):
            st['msg'] = u'空置确认中 %d/%d（跨度 %ds）' % (
                min(len(st['empty']), RESTART_EMPTY_SAMPLES), RESTART_EMPTY_SAMPLES,
                int(now - float(st['firstEmptyTs'])))   # v6134：计数封顶，不再出现 6/3
            _restart_push(srv)
            continue
        # v6197（用户口径）：**删除 L2「变空静默」** —— 测（步骤 207）实测它与 L1 空置判定起点几乎相同、
        #   从不拦截，纯冗余。保留 L3（集群目录静默）作为跨服传送保护。
        bad = []
        cq = _restart_cluster_quiet_sec()          # v6204：lq 残留已删（L2 判定 v6197 移除）
        if cq is not None and cq < RESTART_CLUSTER_QUIET:
            bad.append(u'集群目录 %ds 内有写入' % int(cq))
        # v6170（计划 §16 第 9 项 9a 验收）：把 L2/L3 的**输入**也记日志 ——
        #   否则「为什么没拦住」只能猜（cq=None 表示目录未配/无文件）
        _restart_log('QUIET %s cq=%s dirs=%s bad=%s'
                     % (srv, ('-' if cq is None else int(cq)),
                        '|'.join(_restart_cluster_dirs()), (';'.join(bad) or 'ok')))
        if bad:
            st['steps']['quiet'] = 'run'
            st['msg'] = u'静默校验未过：' + u' / '.join(bad)
            _restart_push(srv)
            continue
        st['phase'] = 'ready'
        st['readyAt'] = now
        st['pct'] = 45
        st['hasSave'] = _restart_has_save(srv)          # v6157（C4）：排序依据，只算一次
        st['steps'].update({'ann': 'ok', 'empty': 'ok', 'quiet': 'ok'})
        st['msg'] = (u'三重静默通过，排队等待重启' if st['hasSave']
                     else u'三重静默通过，排队等待重启（无主存档，排后）')
        _restart_push(srv)

    # ---- 4) 并发门：最多 RESTART_PARALLEL 台同时在**整条执行链**内 ----
    #   v6270（用户口径 2026-11-07「重压到 0/2，一堆排队的一个都没开始启动」「启动失败后不会自动重试」）：
    #   原实现 `busy` 只要**任意一台**处于 savekill/sync/startq/verify 就整体停止调度，
    #   而名额 `_in_sk` 只统计 savekill/sync ⇒ 两个判据不一致。
    #   后果：某台进入 startq（等起服 + MOD 自动更新，常 10~20 分钟）时，全场停止调度 ——
    #     · 界面显示「0/2 有空位却没人启动」
    #     · _restart_step_fail 退回 ready 的失败台永远等不到重试
    #   修法：名额按整条链统计，两个判据统一；不再有「全局 busy」这个门。
    _CHAIN_PH = ('savekill', 'sync', 'startq', 'verify')
    _in_chain = [k for k, v in servers.items() if v.get('phase') in _CHAIN_PH]
    # v6440（用户口径「更新一次只能一台 仅限于 缓存覆盖文件的步骤」）：
    #   原来 update/rollback 把 _par_now 压成 1 ⇒ savekill→sync→startq→verify
    #   整条链只能 1 台（实测 Cen 走完 5 分 19 秒，Los 全程 ready 干等）。
    #   现统一按 RESTART_PARALLEL；真正的串行只由 _RESTART_SYNC_SERIAL 在
    #   复制（sync）这一步把住。
    _par_now = int(RESTART_PARALLEL)
    busy = len(_in_chain) >= _par_now
    if not busy:
        # v6157（C4/C6）：锚点排序 = (Bob 永远最后, 有存档优先, 在线人数升序, readyAt 先到先得)
        _cands = []
        for srv, st in servers.items():
            if st.get('phase') != 'ready':
                continue
            if _srv_lock_get(srv).get('kind') in SRV_LOCK_HARD:
                continue
            _pn = st.get('players')
            _cands.append(((1 if srv == 'Bob' else 0,
                            0 if st.get('hasSave') else 1,
                            9999 if _pn is None else int(_pn),
                            float(st.get('readyAt') or 0)), srv))
        _cands.sort()
        # v6221（P2-1）：允许最多 RESTART_PARALLEL 台**同时**进入 savekill 段。
        #   原实现每 tick 只取 _cands[0] ⇒ 11 台严格串行（45~60 分钟）。
        #   并发安全性依据：存档写 Servers\<srv>\，不写共用集群目录 ⇒ 两台并行存档
        #   不会互相破坏 L3 静默判定；且每台在「保存通过后、终止前」仍会**复检**
        #   _srvctl_terminal_gate（v6189），停服前那一刻的静默状态依然有效。
        # v6228（O5 / §15.1）：更新/回滚是**纯磁盘 IO**，强制串行（与 ASAM 一致且极快）
        _is_upd_m = str(_RESTART.get('mode') or 'restart') in ('update', 'rollback')
        _par = 1 if _is_upd_m else int(RESTART_PARALLEL)
        _in_sk = [k for k, v in servers.items()
                  if v.get('phase') in ('savekill', 'sync')]
        # v6270：名额按**整条执行链**（含 startq/verify）统计，与上面的 busy 判据保持一致
        _free_slots = max(0, _par_now - len(_in_chain))
        for _pick in (_cands[:_free_slots] if _free_slots > 0 else []):
            srv = _pick[1]
            st = servers[srv]
            # v6273（用户口径）：任务中途已停服的服 —— 跳过存档/停服，**直接重新起服**
            #   否则重试必然撞 RCON 10061（见 _restart_step_fail 注释）。
            if (not _is_upd_m) and st.get('skipSaveOnRetry'):
                st['phase'] = 'startq'
                st['pct'] = 75
                st['startqAt'] = 0
                st['skipSaveOnRetry'] = False      # 用一次即清，避免「永远跳过存档」
                st['steps'].update({'saveworld': 'ok', 'savekill': 'ok', 'startq': 'run'})
                st['msg'] = u'已停服（上次启动失败），直接重新起服'
                try:
                    _srv_lock_set(srv, 'restart', 'restart|%s' % srv,
                                  u'自动重启（IP 切换）', 'ipwatch')
                except Exception:
                    pass
                _restart_log('RETRY-STARTQ %s 跳过存档屏障直接起服（savekill 已完成）' % srv)
                _restart_push(srv)
                continue
            st['phase'] = 'savekill'
            st['pct'] = 60
            # C6：Bob 不落盘 ⇒ 跳过存档屏障，直接走 kill
            if _is_upd_m and st.get('skipToSync'):
                # 停服批：直接进 sync（不存档 / 不停服 / 不起服）
                st['skStage'] = 'sync'
                st['steps']['sync'] = 'run'
            else:
                st['skStage'] = ('savekill' if srv == 'Bob' else 'saveworld')
                st['steps']['saveworld'] = ('skip' if srv == 'Bob' else 'run')
                st['steps']['savekill'] = ('run' if srv == 'Bob' else 'wait')
            st['swAt'] = 0; st['swDone'] = False; st['swOk'] = False
            st['execAt'] = 0; st['execDone'] = False; st['execOk'] = False   # v6152（C1）：真执行状态位
            st['startqAt'] = 0; st['verifyAt'] = 0
            _RESTART['current'] = srv
            _srv_lock_set(srv, 'restart', 'restart|%s' % srv,
                          u'自动重启（IP 切换）', 'ipwatch')   # v6135：soft 锁
            if dry:
                st['msg'] = (u'[演练] 跳过存档停服' if srv != 'Bob'
                             else u'[演练] 跳过停服（本图不落盘）')
            else:
                st['msg'] = u'存档并停服（等待）'
            _restart_log('enter savekill %s (parallel %d/%d)'
                         % (srv, len(_in_sk) + 1, int(RESTART_PARALLEL)))
            _restart_push(srv)

    # ---- 5) 推进执行链（dry：即时推进；真执行：按执行器回执 / 日志判据推进）----
    #   v6152（计划 §16 第 1~3 项）：dry 分支与改造前**逐字等价**，真执行分支全新
    for srv, st in servers.items():
        ph = st.get('phase')
        if ph == 'savekill':
            if (st.get('skStage') == 'sync'
                    and str(_RESTART.get('mode') or 'restart') in ('update', 'rollback')):
                # v6228：停服批直通复制（跳过存档/停服）
                st['phase'] = 'sync'
                st['pct'] = 80
                st['syncAt'] = 0
                st['steps']['sync'] = 'run'
                st['msg'] = u'准备复制差异（本服原本停服）'
                _restart_push(srv)
            elif dry:
                # v6228：演练模式下 update/rollback 把 sync 也标 ok（不复制任何文件）
                if str(_RESTART.get('mode') or 'restart') in ('update', 'rollback'):
                    _wr = bool(st.get('wasRunning', True))
                    st['steps'].update({'saveworld': ('ok' if _wr else 'skip'),
                                        'savekill': ('ok' if _wr else 'skip'),
                                        'sync': 'ok'})
                else:
                    st['steps'].update({'saveworld': ('skip' if srv == 'Bob' else 'ok'),
                                        'savekill': 'ok', 'startq': 'run'})
                st['phase'] = 'startq'
                st['pct'] = 75
                st['msg'] = u'[演练] 跳过起服'          # v6204：此处已在 if dry 内，三元恒真
                _restart_push(srv)
            elif (st.get('skStage') or 'saveworld') == 'saveworld':
                # v6157（C5）：savekill 前先 saveworld + DinoData 落盘屏障；未过 ⇒ 回 ready，不重启
                if not st.get('swAt'):
                    st['swAt'] = now
                    st['swDone'] = False
                    st['msg'] = u'存档并等待落盘（屏障）'
                    _restart_log('saveworld start %s' % srv)
                    _restart_exec_saveworld(srv)
                    _restart_push(srv)
                elif st.get('swDone'):
                    if st.get('swOk'):
                        st['steps']['saveworld'] = 'ok'
                        st['steps']['savekill'] = 'run'
                        st['skStage'] = 'savekill'
                        st['swAt'] = 0
                        st['swDone'] = False
                        # v6204（复核 P1-6）：**同一 tick 直接下发** —— 原来只切 skStage，
                        #   真正下发要等下一 tick（15s）⇒ 11 台累计白等约 3 分钟。
                        st['execAt'] = now
                        st['execDone'] = False
                        st['msg'] = u'存档已落盘，开始停服（执行中）'
                        _restart_log('exec savekill %s (same-tick)' % srv)
                        _restart_exec_savekill(srv)
                        _restart_push(srv)
                    else:
                        st['steps']['saveworld'] = 'fail'
                        _restart_step_fail(srv, st, u'存档屏障未过：%s' % (st.get('swMsg') or u'无回执'))
                elif now - float(st['swAt']) > RESTART_SAVEWORLD_TIMEOUT:
                    _restart_step_fail(srv, st, u'存档屏障超时 %ds' % RESTART_SAVEWORLD_TIMEOUT)
            elif not st.get('execAt'):
                # C1：首次进入 —— 下发 savekill（丢线程池），本 tick 只记账
                st['execAt'] = now
                st['execDone'] = False
                st['msg'] = u'存档并停服（执行中）'
                _restart_log('exec savekill %s' % srv)          # C1 验收标志
                _restart_exec_savekill(srv)
                _restart_push(srv)
            elif st.get('execDone'):
                if st.get('execOk'):
                    st['steps']['savekill'] = 'ok'
                    st['execAt'] = 0
                    st['execDone'] = False
                    if str(_RESTART.get('mode') or 'restart') in ('update', 'rollback'):
                        st['steps']['sync'] = 'run'
                        st['phase'] = 'sync'
                        st['pct'] = 80
                        st['syncAt'] = 0
                        st['msg'] = u'已停服，准备复制差异'
                    else:
                        st['steps']['startq'] = 'run'
                        st['phase'] = 'startq'
                        st['pct'] = 75
                        st['msg'] = u'已停服，准备起服'
                    _restart_push(srv)
                else:
                    _restart_step_fail(srv, st, u'savekill 失败：%s' % (st.get('execMsg') or u'无回执'))
            elif now - float(st['execAt']) > RESTART_SAVEKILL_TIMEOUT:
                _restart_step_fail(srv, st, u'savekill 超时 %ds' % RESTART_SAVEKILL_TIMEOUT)
        elif ph == 'sync':
            # v6228：复制差异 + 改 acf（后台线程，回填 syncDone/syncOk/syncMsg）
            if dry:
                st['steps']['sync'] = 'ok'
                _sync_finish(srv, st, now)
            elif not st.get('syncAt'):
                st['syncAt'] = now
                st['syncDone'] = False
                st['msg'] = u'正在复制差异…'
                _restart_log('exec sync %s mode=%s' % (srv, _RESTART.get('mode')))
                _restart_exec_sync(srv)
                _restart_push(srv)
            elif st.get('syncDone'):
                if st.get('syncOk'):
                    st['steps']['sync'] = 'ok'
                    st['syncAt'] = 0
                    st['syncDone'] = False
                    _sync_finish(srv, st, now)
                else:
                    st['steps']['sync'] = 'fail'
                    _restart_step_fail(srv, st,
                                       u'复制差异失败：%s' % (st.get('syncMsg') or u'无回执'))
            elif now - float(st['syncAt']) > UPDATE_SYNC_TIMEOUT:
                _restart_step_fail(srv, st, u'复制差异超时 %ds' % UPDATE_SYNC_TIMEOUT)
        elif ph == 'startq':
            if dry:
                st['steps'].update({'startq': 'ok', 'verify': 'run'})
                st['phase'] = 'verify'
                st['pct'] = 90
                st['verifyAt'] = now
                st['msg'] = u'等待服务器对外开放加入'
                _restart_push(srv)
            elif not st.get('startqAt'):
                # C1：加入启动队列（_srvctl_startq_new 非阻塞，立即返回）
                st['startqAt'] = now
                st['msg'] = u'已入启动队列（等待起服）'
                _restart_log('exec startq %s' % srv)            # C1 验收标志
                try:
                    _srvctl_startq_new('ipwatch', [srv])
                    _restart_push(srv)
                except Exception as e:
                    _restart_step_fail(srv, st, u'startq 下发失败：%r' % e)
            else:
                qs = _restart_startq_state(srv)
                if qs == 'ok':
                    st['steps'].update({'startq': 'ok', 'verify': 'run'})
                    st['phase'] = 'verify'
                    st['pct'] = 90
                    st['startqAt'] = 0
                    st['verifyAt'] = now
                    st['msg'] = u'等待服务器对外开放加入'
                    _restart_push(srv)
                elif qs == 'fail':
                    # v6274（用户口径 2026-11-08「把真实原因透出来」）：
                    #   原来这里写死「启动队列报失败」⇒ 真正的崩溃原因被丢掉。
                    #   实际原因（含 ShooterGame.log 尾部，如 `Failed to load package ...`）
                    #   存在 _SRVCTL_STARTQ['done'][].err 里 —— 完整透出，不截断。
                    _qerr = ''
                    try:
                        for _xq in (_SRVCTL_STARTQ.get('done') or []):
                            if _xq.get('server') == srv and not _xq.get('ok'):
                                _qerr = str(_xq.get('err') or '')
                                break
                    except Exception:
                        _qerr = ''
                    _restart_step_fail(srv, st,
                                       u'启动队列报失败：%s' % (_qerr.strip() or u'（队列无详情）'))
                elif qs == 'idle' and (now - float(st['startqAt'])) > RESTART_STARTQ_IDLE_RETRY:
                    # v6219（R1）：队列里查不到该服 —— 最常见原因是入队时「进程已存在」被静默跳过
                    #   （_srvctl_startq_new 的幂等判据）。不处理会永远等不到 ok ⇒ 卡满超时。
                    if int(st.get('bootReqs') or 0) < 2:
                        st['bootReqs'] = int(st.get('bootReqs') or 0) + 1
                        st['startqAt'] = now
                        st['msg'] = u'队列未登记，重新入队（第 %d 次）' % st['bootReqs']
                        _restart_log('startq idle -> re-enqueue %s (#%d)' % (srv, st['bootReqs']))
                        try:
                            _srvctl_startq_new('ipwatch', [srv])
                        except Exception as _e:
                            _restart_step_fail(srv, st, u'重新入队失败：%r' % _e)
                        _restart_push(srv)
                    else:
                        _restart_step_fail(srv, st, u'队列始终未登记该服（疑似进程残留），已重试 %d 次'
                                           % int(st.get('bootReqs') or 0))
                elif now - float(st['startqAt']) > RESTART_STARTQ_TIMEOUT:
                    _restart_step_fail(srv, st, u'起服超时 %ds' % RESTART_STARTQ_TIMEOUT)
        elif ph == 'verify':
            if dry:
                st['steps']['verify'] = 'ok'
                st['phase'] = 'done'
                st['pct'] = 100
                st['msg'] = u'[演练] 完成'                # v6204：此处已在 if dry 内，三元恒真
                _srv_lock_clear(srv, 'restart|%s' % srv)   # v6135：释放 soft 锁
                if srv not in _RESTART['done']:
                    _RESTART['done'].append(srv)
                _restart_push(srv)
            elif _restart_startq_state(srv) == 'ok':
                # v6219（P0-1 方案 B）：**不再自己扫日志** —— 直接信任启动队列的 advertising 判定。
                #   原实现用「日志行时间戳 >= verifyAt」，而 verifyAt 是队列收割时刻（天然晚于
                #   advertising 那一行）⇒ 判定恒不成立 ⇒ 每台必卡 600s（2026-11-07 实测 Abe）。
                st['steps']['verify'] = 'ok'
                st['phase'] = 'done'
                st['pct'] = 100
                st['msg'] = u'重启完成（已上线）'
                _srv_lock_clear(srv, 'restart|%s' % srv)
                if srv not in _RESTART['done']:
                    _RESTART['done'].append(srv)
                _restart_log('advertising OK %s' % srv)        # C2 验收标志
                try:
                    _restart_announce_done(srv)                # v6204：告知玩家可以进了
                except Exception:
                    _sexc('announce_done')
                _restart_push(srv)
            elif _restart_startq_state(srv) == 'fail':
                # v6219（R1）：队列已判死 ⇒ 立即失败，不必空等到超时
                _restart_step_fail(srv, st, u'起服后启动队列判失败')
            elif now - float(st.get('verifyAt') or now) > RESTART_VERIFY_TIMEOUT:
                _restart_step_fail(srv, st, u'起服后 %ds 未见 advertising（队列=%s）'
                                   % (RESTART_VERIFY_TIMEOUT, _restart_startq_state(srv)))

    # v6164（C8 配套）：整批总超时收尾 —— 防「某台一直有人在线」让 running 永远 true
    _t0t = float(_RESTART.get('t0') or 0)
    if _t0t and (now - _t0t) > RESTART_TOTAL_TIMEOUT:
        _left = 0
        for srv, st in servers.items():
            if st.get('phase') in ('done', 'fail'):
                continue
            st['phase'] = 'fail'
            st['err'] = u'编排超时（超过 %d 分钟）未完成' % (RESTART_TOTAL_TIMEOUT // 60)
            st['msg'] = st['err']
            _stps = st.get('steps') or {}
            for _k in list(_stps.keys()):
                if _stps[_k] == 'run':
                    _stps[_k] = 'fail'
                elif _stps[_k] == 'wait':
                    _stps[_k] = 'skip'
            try:
                _srv_lock_clear(srv, 'restart|%s' % srv)
            except Exception:
                pass
            _restart_push(srv)
            _left += 1
        with _RESTART_LOCK:
            _RESTART['running'] = False
            _RESTART['current'] = ''
        _restart_log('TIMEOUT reason=%s left=%d elapsed=%ds'
                     % (_RESTART.get('reason'), _left, int(now - _t0t)))
        _restart_rerun_pending()
        return

    try:
        _restart_push_batch()
    except Exception:
        pass

    if servers and all(v.get('phase') in ('done', 'fail') for v in servers.values()):
        _RESTART['running'] = False
        _RESTART['current'] = ''
        _restart_log('ALL DONE reason=%s dry=%s' % (_RESTART.get('reason'), _RESTART.get('dry')))
        # v6335（用户口径）：收尾后**再**推一次批次条 ——
        #   原顺序是「先 push 再 running=False」，push 时 running 仍 True ⇒ 批次条永远 phase=run
        #   ⇒ 永不消失；后端重启时还会被 _utask_load 判成「中断失败」。
        try:
            _restart_push_batch()
        except Exception:
            pass
        _restart_rerun_pending()


def _restart_rerun_pending():
    """v6204（复核 P0-2）：本轮收尾后若期间又有 IP 变化，自动再跑一轮。
       ⚠ 必须在**不持 _RESTART_LOCK** 的地方调用（_restart_start 内部要取同一把锁）。"""
    try:
        _pend = str(_RESTART.get('pendingReason') or '')
        if not _pend:
            return
        with _RESTART_LOCK:
            _RESTART['pendingReason'] = ''
        _restart_log('RERUN pending: %s' % _pend)
        _restart_start(_pend, force=True)      # force：跳过 10 分钟冷却
    except Exception:
        _sexc('restart_rerun_pending')


# ===== v6206：SteamCMD Cache 接入（只读状态 + 一键分发）=====
#   背景（2026-11-07 实测）：ASAM 的 `Cache Manager` 窗口 = WPF 原生，方法不暴露成 HTTP 端点，
#     其内部结构（从程序集还原）：
#       CacheUpdateManager.EnsureSteamCmdReadyAsync   -> 按钮「Reinstall SteamCMD」
#       CacheUpdateManager.UpdateCacheAsync           -> 按钮「Update local cache from steam」
#       CacheUpdateManager.ApplyCacheToProfileAsync   -> 按钮「Update the selected profile from the cache」
#       CacheUpdateManager.DirectoryCopyAsync         -> 内部 EnumerateFiles + CopyFileWithProgress
#     其「分发到 profile」的做法 = 复制文件 + **改写目标 appmanifest 的 manifest 值**
#       （程序集字符串：`-app 2430930 -depot 2430931 -manifest <id>` /
#         `Manifest updated successfully in appmanifest_2430930.acf to:`）
#     这解释了为什么 11 台的 buildid 全同（26334129）—— 都是从缓存复制来的。
#   → 本模块照它的做法**等价实现**，并补上它没有的：批量 / 在线护栏 / 任务总线 / 存档保障。
UPDATE_CACHE_PATH = r'D:\Cache'
UPDATE_APP_ID = '2430930'
UPDATE_DEPOT_ID = '2430931'
UPDATE_ACF_NAME = 'appmanifest_2430930.acf'
UPDATE_SERVERS_ROOT = r'D:\ARK Server\Servers'
# 复制时**不覆盖**的目标子目录（存档/配置/日志/备份/profile/Steam 自管）
UPDATE_SKIP_DIRS = ('Saved', 'Config', 'Logs', 'ConfigBackups', 'Profile',
                    'Cache', 'steamapps', 'steamcmd', 'dumps')


def _upd_read_acf(fp):
    """读 appmanifest 的关键字段（Steam 的 acf 是 Valve KeyValues 文本格式）"""
    d = {'buildid': '', 'manifest': '', 'lastUpdated': '', 'sizeOnDisk': '',
         'bytesToDownload': '', 'name': '', 'ok': False}
    try:
        # v6206b：后端**没有 import io**（只导入了 json/os/re/socket/...）⇒ 用内置 open
        t = open(fp, encoding='utf-8', errors='replace').read()
    except Exception:
        return d
    def _g(k):
        m = re.search(r'"%s"\s*"([^"]*)"' % k, t)
        return m.group(1) if m else ''
    d['buildid'] = _g('buildid')
    d['lastUpdated'] = _g('LastUpdated')
    d['sizeOnDisk'] = _g('SizeOnDisk')
    d['bytesToDownload'] = _g('BytesToDownload')
    d['name'] = _g('name')
    # 挂载的 depot manifest（形如 "2430931" { "manifest" "6604340029022292600" }）
    m = re.search(r'"%s"\s*\{[^}]*?"manifest"\s*"([^"]*)"' % UPDATE_DEPOT_ID, t, re.S)
    if m:
        d['manifest'] = m.group(1)
    d['ok'] = bool(d['buildid'])
    return d


def _upd_fmt_ts(v):
    """Steam 的 LastUpdated 是 unix 秒 → 本地时间串"""
    try:
        iv = int(str(v or '').strip())
        if iv > 0:
            return time.strftime('%Y-%m-%d %H:%M', time.localtime(iv))
    except Exception:
        pass
    return ''


def _upd_dir_gb(d):
    """目录占用（GB，仅一层文件累加，避免全盘遍历太慢）"""
    tot = 0
    try:
        for root, dirs, files in os.walk(d):
            for f in files:
                try:
                    tot += os.path.getsize(os.path.join(root, f))
                except Exception:
                    pass
            if len(dirs) > 400:
                break
    except Exception:
        pass
    return round(tot / 1073741824.0, 2)


# ===== v6402（用户口径 2026-11-09）：版本更新缓存 → **可拉取指定版本** =====
#   需求：卡片上给下拉选历史版本；按时间新→旧；只列当前主版本（如 97.x）
#   下载：走用户已验证的命令
#         steamcmd +login <账号> <密码> +download_depot 2430930 2430931 <manifestGID> +quit
#   数据源（不碰外站）：
#     ① Steam 官方 public 分支实时值（保证「最新版」一定在列表里）
#     ② 本机扫描：各服 / 缓存 的 appmanifest_2430930.acf（Steam 自己写的 buildid+manifest）
#        + SteamCMD 的 depotcache\2430931_<GID>.manifest（每下载过一个版本就留一份档）
#     ③ 手工补录库 depot_history.json（SteamDB 上抄到的 GID 录一次，永久复用）
#   凭据：按账号缓存，密码用 _srvctl_secret() 派生密钥加密落盘；读取接口**永不回明文**
DEPOT_HIST_FILE = os.path.join(os.path.dirname(ACCOUNTS_FILE), 'depot_history.json')
STEAM_CRED_FILE = os.path.join(os.path.dirname(ACCOUNTS_FILE), 'steam_creds.json')
STEAMCMD_EXE = r'D:\ASADedicatedManager\SteamCMDInstall\steamcmd.exe'
STEAMCMD_CONTENT = os.path.join(r'D:\ASADedicatedManager\SteamCMDInstall', 'steamapps',
                                'content', 'app_' + UPDATE_APP_ID,
                                'depot_' + UPDATE_DEPOT_ID)
DEPOT_SAME_GEN_GAP = 120000   # 无版本号时的兜底：buildId 与最新相差小于此值 ⇒ 同大版本


def _depot_hist_load():
    try:
        with open(DEPOT_HIST_FILE, 'r', encoding='utf-8') as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _depot_hist_save(d):
    try:
        with open(DEPOT_HIST_FILE + '.tmp', 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(DEPOT_HIST_FILE + '.tmp', DEPOT_HIST_FILE)
        return True
    except Exception:
        _sexc('depot_hist_save')
        return False


def _depot_put(out, man, bid, at, size, src, srv):
    """往版本池里并入一条（按 manifest 去重，字段取并集）"""
    man = str(man or '').strip()
    if not man:
        return
    k = man
    it = out.get(k) or {'manifest': man, 'buildId': '', 'at': 0, 'size': 0,
                        'src': [], 'srv': [], 'ver': ''}
    if bid and not it.get('buildId'):
        it['buildId'] = str(bid)
    try:
        it['at'] = max(int(it.get('at') or 0), int(at or 0))
    except Exception:
        pass
    try:
        it['size'] = max(int(it.get('size') or 0), int(size or 0))
    except Exception:
        pass
    if src and src not in it['src']:
        it['src'].append(src)
    if srv and srv not in it['srv']:
        it['srv'].append(srv)
    out[k] = it


def _depot_scan_local():
    """本机已存在的 depot manifest（各服 acf + 缓存 acf + SteamCMD depotcache）"""
    out = {}
    _roots = [(UPDATE_CACHE_PATH, 'cache')]
    for _s in sorted(SERVERS.keys()):
        try:
            _roots.append((os.path.normpath(os.path.join(_srv_win64(_s), '..', '..', '..')), _s))
        except Exception:
            pass
    for _root, _tag in _roots:
        _fp = os.path.join(_root, 'steamapps', UPDATE_ACF_NAME)
        if not os.path.isfile(_fp):
            continue
        _a = _upd_read_acf(_fp)
        if not _a.get('manifest'):
            continue
        try:
            _at = int(_a.get('lastUpdated') or 0)
        except Exception:
            _at = 0
        try:
            _sz = int(_a.get('sizeOnDisk') or 0)
        except Exception:
            _sz = 0
        _depot_put(out, _a['manifest'], _a.get('buildid'), _at, _sz, 'acf',
                   ('' if _tag == 'cache' else _tag))
    for _dc in (os.path.join(os.path.dirname(STEAMCMD_EXE), 'depotcache'),
                os.path.join(UPDATE_CACHE_PATH, 'steamapps', 'depotcache')):
        try:
            if not os.path.isdir(_dc):
                continue
            _pre = UPDATE_DEPOT_ID + '_'
            for _fn in os.listdir(_dc):
                _low = _fn.lower()
                if not _low.startswith(_pre) or not _low.endswith('.manifest'):
                    continue
                _gid = _fn[len(_pre):-len('.manifest')]
                try:
                    _mt = int(os.path.getmtime(os.path.join(_dc, _fn)))
                except Exception:
                    _mt = 0
                _depot_put(out, _gid, '', _mt, 0, 'depotcache', '')
        except Exception:
            _sexc('depot_scan_cache')
    return out


def _discord_ver_timeline():
    """v6406（用户口径「通过 Discord 的 PC 版本 来对照判定」）：
       从资讯广场 `patch_pc` 缓存解析「游戏版本号 + 公告时间」时间线。
       · 版本号：卡片 `<h3>` 标题（`v97.16 - …` / `## v97 - …`），口径与 _news_official_version 一致
       · 时间：`cards[].mid` 反查 `messages[]` 里对应 Discord 消息的 `timestamp`（UTC）
       返回按时间升序的 [{'ver': '97.16', 'ts': 1794xxxxxx}, …]"""
    out = []
    try:
        d = _news_read('patch_pc') or {}
        _mt = {}
        for _m in (d.get('messages') or []):
            try:
                _mt[str(_m.get('id') or '')] = str(_m.get('timestamp') or '')
            except Exception:
                pass
        for _c in (d.get('cards') or []):
            _txt = str(_c.get('content') or '')
            _mh = re.search(r'<h3>(.*?)</h3>', _txt, re.S)
            if not _mh:
                continue
            _head = _mh.group(1)
            _low = _head.lower()
            if not (re.search(r'servers?\b', _low) or re.search(r'\bsteam\b', _low)):
                continue
            _vm = re.search(r'(?<![\d.])v?(\d+)(?:\.(\d+))?', _head, re.I)
            if not _vm:
                continue
            _ver = '%d.%d' % (int(_vm.group(1)), int(_vm.group(2) or 0))
            _ts = 0
            _tstr = _mt.get(str(_c.get('mid') or ''), '')
            if _tstr:
                try:
                    _ts = int(_cal.timegm(time.strptime(_tstr[:19], '%Y-%m-%dT%H:%M:%S')))
                except Exception:
                    _ts = 0
            out.append({'ver': _ver, 'ts': _ts})
        out.sort(key=lambda x: (int(x.get('ts') or 0), _ver_seg(x.get('ver')) or (0, '0')))
    except Exception:
        _sexc('discord_ver_timeline')
    return out


STEAMDB_RSS_URL = 'https://steamdb.info/api/PatchnotesRSS/?appid=2430930'
STEAMDB_BUILDS_FILE = os.path.join(os.path.dirname(ACCOUNTS_FILE), 'steamdb_builds.json')
STEAMDB_RSS_TTL = 3600          # RSS 自带 <ttl>3600</ttl>
_STEAMDB_CACHE = {'ts': 0.0, 'list': []}


def _steamdb_builds():
    """v6407（用户口径「从 SteamDB 取列表」）：走 **SteamDB 官方 RSS**（站点自带订阅接口，
    不是猜端点/爬页面）。返回 [{buildId, at}]，按 buildId 降序。

    · RSS 只给最近 10 条 ⇒ **持久累积**到 steamdb_builds.json，跑得越久列表越全
    · 时间戳不解析 pubDate 文本（受系统 locale 影响），改用
      `<media:thumbnail ... ?_=<epoch>>` 里的 epoch 秒，稳定可靠
    """
    now = time.time()
    if _STEAMDB_CACHE['list'] and (now - float(_STEAMDB_CACHE['ts'] or 0)) < STEAMDB_RSS_TTL:
        return _STEAMDB_CACHE['list']
    store = {}
    try:
        with open(STEAMDB_BUILDS_FILE, 'r', encoding='utf-8') as f:
            d = json.load(f)
        if isinstance(d, dict):
            # v6409：结构升级为 {buildId: {'at': ts, 'man': gid}}；兼容旧的纯时间戳写法
            # v6415：再留 auto 字段 —— 区分「官方自动配对」与「人工手填」
            for _k, _v in (d.get('builds') or {}).items():
                if isinstance(_v, dict):
                    store[str(_k)] = {'at': int(_v.get('at') or 0),
                                      'man': str(_v.get('man') or ''),
                                      'auto': bool(_v.get('auto')),
                                      'verified': bool(_v.get('verified'))}
                else:
                    store[str(_k)] = {'at': int(_v or 0), 'man': '',
                                      'auto': False, 'verified': False}
    except Exception:
        store = {}
    try:
        import urllib.request as _u2
        req = _u2.Request(STEAMDB_RSS_URL, headers={
            'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                           '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'),
            'Accept': 'application/rss+xml, application/xml, text/xml, */*'})
        raw_xml = _u2.urlopen(req, timeout=25).read().decode('utf-8', 'replace')
        for m in re.finditer(r'<item>(.*?)</item>', raw_xml, re.S):
            it = m.group(1)
            g = re.search(r'<guid[^>]*>\s*build#(\d+)', it)
            if not g:
                continue
            bid = g.group(1)
            ts = 0
            mt = re.search(r'patchnotes/\d+\.png\?_=(\d+)', it)
            if mt:
                ts = int(mt.group(1))
            _old = store.get(bid) or {}
            store[bid] = {'at': ts or int(_old.get('at') or 0),
                          'man': str(_old.get('man') or ''),
                          'auto': bool(_old.get('auto')),
                          'verified': bool(_old.get('verified'))}
    except Exception:
        _sexc('steamdb_rss')
    try:
        if store:
            with open(STEAMDB_BUILDS_FILE + '.tmp', 'w', encoding='utf-8') as f:
                json.dump({'builds': store,
                           'updated': time.strftime('%Y-%m-%d %H:%M:%S')},
                          f, ensure_ascii=False, indent=1)
            os.replace(STEAMDB_BUILDS_FILE + '.tmp', STEAMDB_BUILDS_FILE)
    except Exception:
        _sexc('steamdb_save')
    lst = []
    for bid, rec in store.items():
        try:
            rec = rec if isinstance(rec, dict) else {'at': int(rec or 0), 'man': ''}
            lst.append({'buildId': str(bid), 'at': int(rec.get('at') or 0),
                        'man': str(rec.get('man') or ''),
                        'auto': bool(rec.get('auto')),
                        'verified': bool(rec.get('verified'))})
        except Exception:
            pass
    lst.sort(key=lambda x: -int(x['buildId']))
    _STEAMDB_CACHE['ts'] = now
    _STEAMDB_CACHE['list'] = lst
    return lst


def _steamdb_set_manifest(bid, man):
    """v6409（用户口径）：按 buildId **永久记录** depot manifest —— 用户从 SteamDB
    详情页抄一次，之后该版本一直可拉，永不过期、无需再填。"""
    bid = str(bid or '').strip()
    man = str(man or '').strip()
    if not bid.isdigit():
        return {'ok': False, 'code': 'bad_buildid', 'error': u'buildId 需为纯数字'}
    if not man.isdigit() or len(man) < 8:
        return {'ok': False, 'code': 'bad_manifest',
                'error': u'manifest GID 需为纯数字（通常 19 位）'}
    store = {}
    try:
        with open(STEAMDB_BUILDS_FILE, 'r', encoding='utf-8') as f:
            d = json.load(f)
        if isinstance(d, dict):
            for _k, _v in (d.get('builds') or {}).items():
                if isinstance(_v, dict):
                    store[str(_k)] = {'at': int(_v.get('at') or 0),
                                      'man': str(_v.get('man') or '')}
                else:
                    store[str(_k)] = {'at': int(_v or 0), 'man': ''}
    except Exception:
        store = {}
    rec = store.get(bid) or {'at': 0, 'man': ''}
    rec['man'] = man
    store[bid] = rec
    try:
        with open(STEAMDB_BUILDS_FILE + '.tmp', 'w', encoding='utf-8') as f:
            json.dump({'builds': store,
                       'updated': time.strftime('%Y-%m-%d %H:%M:%S')},
                      f, ensure_ascii=False, indent=1)
        os.replace(STEAMDB_BUILDS_FILE + '.tmp', STEAMDB_BUILDS_FILE)
    except Exception as e:
        _sexc('steamdb_set_man')
        return {'ok': False, 'code': 'save_failed', 'error': repr(e)[:200]}
    # 让下一次查询立刻生效
    _STEAMDB_CACHE['list'] = []
    _STEAMDB_CACHE['ts'] = 0.0
    try:
        _depot_ver_cache_clear()
    except Exception:
        pass
    return {'ok': True, 'buildId': bid, 'manifest': man}


# ===== v6415（用户口径「97 的历史版本你直接给配上，反正后续的新版本都能对应上，无需手动了」）=====
#   结论：**不需要跑 steamcmd**。`_steam_latest_build()`（v6397 已有）走 api.steamcmd.net，
#   一次 1.2 秒就同时返回
#       depots.branches.public.buildid            = 26528593
#       depots.2430931.manifests.public.gid       = 1403008564163147406
#   与 `steamcmd +app_info_print`（19.5 秒起进程）结果逐位一致 —— 实测交叉验证过。
#   ⇒ 只要把这对值**落库**，之后每个新版本都会自动有 manifest，不用再手填。
STEAMDB_PAIR_INTERVAL = 1800      # 30 分钟一轮（Steam 不会 30 分钟内连发两个 build）
STEAMDB_PAIR_FIRST_DELAY = 45     # 启动后 45 秒先跑一次
_STEAMDB_PAIR_LAST = {'at': 0.0, 'bid': '', 'man': '', 'err': ''}


DEPOT_VER_TTL = 30.0          # v6425：版本池短缓存（并发时只算一次；拉取/改库后主动清）
_DEPOT_VER_CACHE = {'ts': 0.0, 'data': None}


def _depot_ver_cache_clear():
    _DEPOT_VER_CACHE['ts'] = 0.0
    _DEPOT_VER_CACHE['data'] = None


def _steamdb_remember(bid, man, at=0, verified=False):
    """把**官方来源**的 buildId + depot manifest 配对落库。
       · `verified=True`（SteamCMD 官方日志）⇒ **权威**，可覆盖库中非权威值
       · `verified=False`（api.steamcmd.net 的 latest）⇒ 只填空，不覆盖已有值
       · 就地更新 _STEAMDB_CACHE，**不清空缓存**（避免下一次调用重复拉 RSS）
    """
    bid = str(bid or '').strip()
    man = str(man or '').strip()
    if not bid.isdigit():
        return {'ok': False, 'code': 'bad_buildid'}
    if not man.isdigit() or len(man) < 8:
        return {'ok': False, 'code': 'bad_manifest'}
    store = {}
    try:
        with open(STEAMDB_BUILDS_FILE, 'r', encoding='utf-8') as f:
            d = json.load(f)
        if isinstance(d, dict):
            for _k, _v in (d.get('builds') or {}).items():
                if isinstance(_v, dict):
                    store[str(_k)] = {'at': int(_v.get('at') or 0),
                                      'man': str(_v.get('man') or ''),
                                      'auto': bool(_v.get('auto')),
                                      'verified': bool(_v.get('verified'))}
                else:
                    store[str(_k)] = {'at': int(_v or 0), 'man': '',
                                      'auto': False, 'verified': False}
    except Exception:
        store = {}
    rec = store.get(bid) or {}
    _cur = str(rec.get('man') or '')
    if _cur and _cur == man:
        if verified and not rec.get('verified'):
            rec['verified'] = True
            store[bid] = rec
            try:
                with open(STEAMDB_BUILDS_FILE + '.tmp', 'w', encoding='utf-8') as f:
                    json.dump({'builds': store,
                               'updated': time.strftime('%Y-%m-%d %H:%M:%S')},
                              f, ensure_ascii=False, indent=1)
                os.replace(STEAMDB_BUILDS_FILE + '.tmp', STEAMDB_BUILDS_FILE)
            except Exception:
                _sexc('steamdb_remember_verify_save')
        return {'ok': True, 'buildId': bid, 'skipped': 'same'}
    if _cur and not verified:
        return {'ok': True, 'buildId': bid, 'skipped': 'already'}
    store[bid] = {'at': int(rec.get('at') or 0) or int(at or 0),
                  'man': man, 'auto': True, 'verified': bool(verified)}
    try:
        with open(STEAMDB_BUILDS_FILE + '.tmp', 'w', encoding='utf-8') as f:
            json.dump({'builds': store,
                       'updated': time.strftime('%Y-%m-%d %H:%M:%S')},
                      f, ensure_ascii=False, indent=1)
        os.replace(STEAMDB_BUILDS_FILE + '.tmp', STEAMDB_BUILDS_FILE)
    except Exception as e:
        _sexc('steamdb_remember_save')
        return {'ok': False, 'code': 'save_failed', 'error': repr(e)[:200]}
    try:
        for _r in (_STEAMDB_CACHE.get('list') or []):
            if str(_r.get('buildId')) == bid:
                if not _r.get('man'):
                    _r['man'] = man
                _r['auto'] = True
                break
    except Exception:
        pass
    return {'ok': True, 'buildId': bid, 'manifest': man, 'auto': True}


STEAMCMD_LOG_FILE = os.path.join(os.path.dirname(STEAMCMD_EXE), 'logs', 'content_log.txt')
_STEAMDB_LOG_CACHE = {'ts': 0.0, 'map': {}, 'err': ''}


def _steamdb_scan_content_log():
    """v6416（用户口径「如果要去除推断风险 有别的方案么」）：
    从 **SteamCMD 官方日志** `logs/content_log.txt` 提取 `BuildID -> depot manifest` **权威配对**。
    Steam 落盘时自己打印这一行，不存在任何推断：
        AppID 2430930 finished update, 2 mounted depots (BuildID 26515168) :
              1004 (7604377918839582995),2430931 (3083367148300701914),
    ⚠ 局限：只覆盖本机实际更新过的版本（且受日志轮转限制）。
    """
    now = time.time()
    if (now - float(_STEAMDB_LOG_CACHE.get('ts') or 0)) < 300 and _STEAMDB_LOG_CACHE.get('map'):
        return dict(_STEAMDB_LOG_CACHE['map'])
    out = {}
    try:
        with open(STEAMCMD_LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
            txt = f.read()
        _pat = re.compile(r'\(BuildID\s+(\d{5,})\)\s*:\s*([^\n]*)')
        _dpat = re.compile(r'(?<![\d])' + str(UPDATE_DEPOT_ID) + r'\s*\((\d{10,})\)')
        for m in _pat.finditer(txt):
            _bid, _seg = m.group(1), m.group(2)
            _dm = _dpat.search(_seg)
            if _dm:
                out[_bid] = _dm.group(1)
        _STEAMDB_LOG_CACHE['err'] = ''
    except Exception as e:
        _STEAMDB_LOG_CACHE['err'] = '%s:%s' % (type(e).__name__, str(e)[:120])
        out = {}
    _STEAMDB_LOG_CACHE['ts'] = now
    if out:
        _STEAMDB_LOG_CACHE['map'] = dict(out)
    return out


def _steamdb_sync_content_log():
    """把日志里的权威配对同步进库（verified=True），并顺手校验已有值是否一致。"""
    res = {'ok': True, 'n': 0, 'fixed': 0, 'confirmed': 0}
    try:
        pairs = _steamdb_scan_content_log()
    except Exception:
        _sexc('steamdb_log_scan')
        return res
    for _bid, _man in (pairs or {}).items():
        try:
            r = _steamdb_remember(_bid, _man, 0, verified=True)
            res['n'] += 1
            if r.get('skipped') == 'same':
                res['confirmed'] += 1
            elif r.get('ok'):
                res['fixed'] += 1
        except Exception:
            _sexc('steamdb_log_remember')
    return res


def _steamdb_pair_loop():
    """后台守护：定时把「当前最新 buildId ↔ manifest」配对落库。
       只在新版本发布时才会有新 buildId，30 分钟一轮足够；单轮开销 = 1 次 HTTP（约 1.2 秒）。
    """
    time.sleep(STEAMDB_PAIR_FIRST_DELAY)
    while True:
        try:
            st = _steam_latest_build(force=True)
            bid = str(st.get('buildid') or '')
            man = str(st.get('manifest') or '')
            _STEAMDB_PAIR_LAST.update({'at': time.time(), 'bid': bid, 'man': man,
                                       'err': str(st.get('err') or '')})
            if bid.isdigit() and man.isdigit():
                _steamdb_remember(bid, man, st.get('timeupdated'))
            # v6416：顺手把 SteamCMD 日志里的权威配对同步进来
            _steamdb_sync_content_log()
        except Exception:
            _sexc('steamdb_pair_loop')
        time.sleep(STEAMDB_PAIR_INTERVAL)


def _depot_versions(force=False):
    """版本池（v6407）：
       · **主列表 = SteamDB 官方 RSS 的 buildId 序列**（不再以本机 acf 为主）
       · 合并本机事实：manifest / 在用服 / 大小（各服 acf + SteamCMD depotcache）
       · **大版本过滤 = 纯 buildId 数值**：`最新 buildId - 该 buildId <= 120000`
       · `v97.x` 版本号**只用于显示**，不参与过滤与排序
    """
    # v6425：30 秒短缓存 —— 原来每次调用都重扫全部服务器 acf，6 并发时 1.7s -> 4.6s
    _now0 = time.time()
    if (not force) and _DEPOT_VER_CACHE['data'] is not None \
            and (_now0 - float(_DEPOT_VER_CACHE['ts'] or 0)) < DEPOT_VER_TTL:
        return _DEPOT_VER_CACHE['data']
    out = {'ok': True, 'major': '', 'items': [], 'latest': {}, 'err': '',
           'rssCount': 0, 'maxBuildId': ''}
    # ① 本机事实
    local = {}
    try:
        local = _depot_scan_local()
    except Exception:
        _sexc('depot_local')
    latest_bid, latest_man, latest_at = '', '', 0
    try:
        _st = _steam_latest_build()
        latest_bid = str(_st.get('buildid') or '')
        latest_man = str(_st.get('manifest') or '')
        latest_at = int(_st.get('timeupdated') or 0)
    except Exception as e:
        out['err'] = '%s:%s' % (type(e).__name__, str(e)[:100])
    # ② SteamDB RSS
    rss = []
    try:
        rss = _steamdb_builds()
    except Exception:
        _sexc('steamdb_rss2')
    out['rssCount'] = len(rss)
    # ②b v6415：官方 latest 配对自动落库（放在 RSS 之后，就地更新缓存，不重复拉 RSS）
    if str(latest_bid).isdigit() and str(latest_man).isdigit():
        try:
            _steamdb_remember(latest_bid, latest_man, latest_at)
        except Exception:
            _sexc('steamdb_remember_caller')
    # ②c v6416：SteamCMD 官方日志的权威配对（零推断）同步进库
    try:
        _steamdb_sync_content_log()
        for _e6 in rss:
            _b6 = str(_e6.get('buildId') or '')
            _m6 = (_STEAMDB_LOG_CACHE.get('map') or {}).get(_b6)
            if _m6 and not _e6.get('man'):
                _e6['man'] = _m6
                _e6['auto'] = True
                _e6['verified'] = True
            elif _m6 and str(_e6.get('man')) == _m6:
                _e6['verified'] = True
    except Exception:
        _sexc('steamdb_log_sync_caller')
    # ③ 版本号来源（仅显示）
    _srvver = {}
    try:
        _cfg_sv = _srvctl_cfg()
        if _cfg_sv.get('token'):
            _c_sv, _t_sv = _asa_http('GET', _cfg_sv['base'] + '/server-status',
                                     _cfg_sv['token'], None,
                                     timeout=min(8, int(_cfg_sv.get('timeout') or 8)),
                                     verify=_cfg_sv.get('verify'))
            if 200 <= _c_sv < 300:
                _doc_sv = json.loads(_t_sv) or {}
                _rev_sv = {}
                for _k_sv, _v_sv in SERVER_THEMES.items():
                    _rev_sv[(_v_sv or {}).get('name') or ''] = _k_sv
                for _it_sv in (_doc_sv.get('servers') or []):
                    _pn_sv = str(_it_sv.get('ProfileName') or '')
                    _sid_sv = _pn_sv if _pn_sv in SERVERS else _rev_sv.get(_pn_sv, '')
                    _sv_sv = _extract_ver(str(_it_sv.get('ServerVersion') or ''))
                    if _sid_sv and _sv_sv:
                        _srvver[_sid_sv] = _sv_sv
    except Exception:
        _sexc('depot_srvver')
    _offver = ''
    try:
        _offver = str(_official_version_ex().get('ver') or '')
    except Exception:
        _offver = ''
    # ④ 组装（buildId 为唯一键）
    items_map = {}

    def _mk(bid, at, at_rss=False):
        k = str(bid)
        it = items_map.get(k)
        if not it:
            it = {'buildId': k, 'at': 0, 'atRss': 0, 'manifest': '', 'inferred': False,
                  'sizeGB': 0, 'srv': [], 'ver': '', 'major': '',
                  'latest': False, 'hasManifest': False}
            items_map[k] = it
        try:
            it['at'] = max(int(it['at'] or 0), int(at or 0))
        except Exception:
            pass
        # v6407b：显示的「日期」优先用 **SteamDB/Steam 官方发布时间**，
        #   本机 acf 的 LastUpdated（= 实际下载时间）放 tips，避免两个时间混排看起来乱序
        if at_rss:
            try:
                it['atRss'] = max(int(it.get('atRss') or 0), int(at or 0))
            except Exception:
                pass
        return it

    for e in rss:
        if str(e.get('buildId') or '').isdigit():
            _e = _mk(e['buildId'], e.get('at'), True)
            if e.get('man') and not _e.get('manifest'):
                _e['manifest'] = str(e['man'])
                if e.get('verified'):
                    _e['verified'] = True
                elif e.get('auto'):
                    _e['autoMan'] = True
                else:
                    _e['manual'] = True
    if latest_bid.isdigit():
        _x = _mk(latest_bid, latest_at, True)
        _x['latest'] = True
        if latest_man:
            _x['manifest'] = latest_man
    _orphan = []
    for man, lit in local.items():
        bid = str(lit.get('buildId') or '')
        if bid.isdigit():
            _x = _mk(bid, lit.get('at'))
            if man and not _x.get('manifest'):
                _x['manifest'] = man
            for s in (lit.get('srv') or []):
                if s and s not in _x['srv']:
                    _x['srv'].append(s)
            try:
                _x['sizeGB'] = max(float(_x.get('sizeGB') or 0),
                                   round(int(lit.get('size') or 0) / 1073741824.0, 2))
            except Exception:
                pass
        else:
            _orphan.append((man, lit))
    # 孤立留档（无 buildId）：按时间就近推断（±6 小时），标 inferred（用户口径 A）
    for man, lit in _orphan:
        _at = int(lit.get('at') or 0)
        if not _at or not rss:
            continue
        best, bestd = '', None
        for e in rss:
            _ea = int(e.get('at') or 0)
            if not _ea:
                continue
            d = abs(_at - _ea)
            if bestd is None or d < bestd:
                best, bestd = str(e.get('buildId') or ''), d
        if not best or bestd is None or bestd > 6 * 3600:
            continue
        _x = items_map.get(best)
        if not _x or _x.get('manifest'):
            continue
        _x['manifest'] = man
        _x['inferred'] = True
        try:
            _x['sizeGB'] = max(float(_x.get('sizeGB') or 0),
                               round(int(lit.get('size') or 0) / 1073741824.0, 2))
        except Exception:
            pass
    # ⑤ 版本号（仅显示）
    for k, it in items_map.items():
        _v = ''
        for s in (it.get('srv') or []):
            if _srvver.get(s):
                _v = _srvver[s]
                break
        if not _v and it.get('latest') and _offver:
            _v = _offver
        it['ver'] = _v
        _sg = _ver_seg(_v) if _v else None
        it['major'] = str(_sg[0]) if _sg else ''
    # ⑤b v6410（用户口径「buildId 26515168 对应的 v 应该也能推断吧？」）：
    #     版本号**夹逼推断** —— buildId 与版本号同序递增，若两个已知版本号之间
    #     恰好夹着 gap 个未知点且版本号差正好 gap+1 ⇒ 依次填中间值。
    #     例：26509035=97.16（Cen/Los 实跑）、26528593=97.18（官方实时），
    #         中间 26515168 唯一 ⇒ 必为 97.17。
    #     ⚠ 仅用于**显示**，不参与任何过滤（过滤仍纯 buildId）。
    try:
        _seq = sorted(items_map.keys(), key=lambda k: int(k))
        _known = []
        for _i4 in range(len(_seq)):
            _v4 = str(items_map[_seq[_i4]].get('ver') or '')
            if _v4:
                _g4 = _ver_seg(_v4)
                if _g4:
                    _known.append((_i4, _g4))
        for _j4 in range(len(_known) - 1):
            _ia, _ga = _known[_j4]
            _ib, _gb = _known[_j4 + 1]
            if str(_ga[0]) != str(_gb[0]):
                continue
            _na, _nb2 = int(_ga[1]), int(_gb[1])
            _gap = _ib - _ia - 1
            if _gap <= 0 or _gap > 3:
                continue
            if _nb2 - _na == _gap + 1:
                for _m4 in range(_gap):
                    _k4 = _seq[_ia + 1 + _m4]
                    items_map[_k4]['ver'] = '%s.%d' % (_ga[0], _na + 1 + _m4)
                    items_map[_k4]['verGuess'] = True
    except Exception:
        _sexc('depot_verguess')
    # ⑥ **纯 buildId 数值过滤**（主版本窗口）
    _bids = []
    for k in items_map.keys():
        try:
            _bids.append(int(k))
        except Exception:
            pass
    _maxb = max(_bids) if _bids else 0
    items = []
    for k, it in items_map.items():
        try:
            _b = int(k)
        except Exception:
            continue
        if _maxb and (_maxb - _b) > DEPOT_SAME_GEN_GAP:
            continue
        _show_at = int(it.get('atRss') or 0) or int(it['at'] or 0)
        it['atTxt'] = (time.strftime('%Y-%m-%d %H:%M', time.localtime(_show_at))
                       if _show_at else '')
        it['atLocalTxt'] = (time.strftime('%Y-%m-%d %H:%M', time.localtime(int(it['at'])))
                            if int(it['at'] or 0) else '')
        it['hasManifest'] = bool(it.get('manifest'))
        items.append(it)
    items.sort(key=lambda x: -int(x.get('buildId') or 0))
    out['items'] = items
    out['maxBuildId'] = str(_maxb or '')
    for it in items:
        if it.get('major'):
            out['major'] = it['major']
            break
    out['latest'] = {'buildId': latest_bid, 'manifest': latest_man, 'at': latest_at}
    out['cacheBuildId'] = ''
    try:
        out['cacheBuildId'] = str(_upd_cache_status().get('buildId') or '')
    except Exception:
        pass
    _DEPOT_VER_CACHE['ts'] = time.time()
    _DEPOT_VER_CACHE['data'] = out
    return out


def _steam_cred_key():
    return _hashlib.pbkdf2_hmac('sha256', _srvctl_secret().encode('utf-8'),
                                b'dino-steam-cred-v1', 120000, 32)


def _steam_cred_enc(pwd):
    """加密：随机 IV + HMAC-SHA256 密钥流 XOR + 16B MAC（encrypt-then-MAC）"""
    try:
        key = _steam_cred_key()
        iv = os.urandom(16)
        data = str(pwd).encode('utf-8')
        ks = b''
        ctr = 0
        while len(ks) < len(data):
            ks += _hmac.new(key, iv + struct.pack('>I', ctr), _hashlib.sha256).digest()
            ctr += 1
        ct = bytes(a ^ b for a, b in zip(data, ks))
        mac = _hmac.new(key, iv + ct, _hashlib.sha256).digest()[:16]
        return _b64.b64encode(iv + ct + mac).decode('ascii')
    except Exception:
        _sexc('steam_cred_enc')
        return ''


def _steam_cred_dec(tok):
    try:
        raw = _b64.b64decode(str(tok or '').encode('ascii'))
        if len(raw) < 33:
            return ''
        iv, rest = raw[:16], raw[16:]
        ct, mac = rest[:-16], rest[-16:]
        key = _steam_cred_key()
        if not _hmac.compare_digest(
                mac, _hmac.new(key, iv + ct, _hashlib.sha256).digest()[:16]):
            return ''
        ks = b''
        ctr = 0
        while len(ks) < len(ct):
            ks += _hmac.new(key, iv + struct.pack('>I', ctr), _hashlib.sha256).digest()
            ctr += 1
        return bytes(a ^ b for a, b in zip(ct, ks)).decode('utf-8', 'replace')
    except Exception:
        return ''


def _steam_cred_load():
    try:
        with open(STEAM_CRED_FILE, 'r', encoding='utf-8') as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _steam_cred_save(d):
    try:
        with open(STEAM_CRED_FILE + '.tmp', 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(STEAM_CRED_FILE + '.tmp', STEAM_CRED_FILE)
        return True
    except Exception:
        _sexc('steam_cred_save')
        return False


def _steam_cred_list():
    d = _steam_cred_load()
    out = []
    for u, it in (d.get('accounts') or {}).items():
        it = it or {}
        out.append({'user': u, 'hasPwd': bool(it.get('enc')), 'at': it.get('at') or ''})
    out.sort(key=lambda x: str(x.get('user') or '').lower())
    return out


def _steam_cred_set(user, pwd):
    u = str(user or '').strip()
    if not u:
        return {'ok': False, 'error': 'need user'}
    d = _steam_cred_load()
    acc = d.get('accounts')
    if not isinstance(acc, dict):
        acc = {}
    it = acc.get(u) or {}
    if pwd:
        it['enc'] = _steam_cred_enc(pwd)
        if not it['enc']:
            return {'ok': False, 'error': 'encrypt failed'}
    it['at'] = time.strftime('%Y-%m-%d %H:%M:%S')
    acc[u] = it
    d['accounts'] = acc
    if not _steam_cred_save(d):
        return {'ok': False, 'error': 'save failed'}
    return {'ok': True, 'accounts': _steam_cred_list()}


def _steam_cred_get(user):
    d = _steam_cred_load()
    it = (d.get('accounts') or {}).get(str(user or '')) or {}
    return _steam_cred_dec(it.get('enc') or '')


def _cache_force_rm(p):
    """Windows 下强制删除（先摘只读再删）"""
    def _onerr(func, path, exc):
        try:
            os.chmod(path, _stat.S_IWRITE)
            func(path)
        except Exception:
            pass
    if os.path.isdir(p) and not os.path.islink(p):
        shutil.rmtree(p, onerror=_onerr)
    else:
        try:
            os.chmod(p, _stat.S_IWRITE)
        except Exception:
            pass
        os.remove(p)


def _cache_purge_dir(path, keep=()):
    r"""清空目录内容（`keep` 内名字大小写不敏感保留）。返回 (删除数, 失败名列表)。
    v6417（用户口径「先备份 acf → 清空 D:\Cache → 再复制」）：只覆盖不删除会让旧版本
    **多出来的文件**残留（如降级时新版新增的 pak/utoc），这里做彻底清理。
    """
    n, fail = 0, []
    if not os.path.isdir(path):
        return n, fail
    keep_l = set(str(k).lower() for k in keep)
    try:
        names = os.listdir(path)
    except Exception:
        return n, [path]
    for _name in names:
        if _name.lower() in keep_l:
            continue
        try:
            _cache_force_rm(os.path.join(path, _name))
            n += 1
        except Exception as e:
            fail.append(u'%s(%s)' % (_name, type(e).__name__))
    return n, fail


def _cache_count_files(root):
    n = 0
    try:
        for _r, _ds, _fs in os.walk(root):
            n += len(_fs)
    except Exception:
        pass
    return n


def _cache_copy_tree(src, dst, skip=('steamapps',)):
    """把 depot 目录内容复制进缓存目录（跳过 steamapps，保留原 acf）"""
    n = 0
    for _name in os.listdir(src):
        if _name.lower() in skip:
            continue
        _sp = os.path.join(src, _name)
        _dp = os.path.join(dst, _name)
        if os.path.isdir(_sp):
            for _r, _ds, _fs in os.walk(_sp):
                _rel = os.path.relpath(_r, _sp)
                _t = os.path.join(_dp, _rel) if _rel != '.' else _dp
                if not os.path.isdir(_t):
                    os.makedirs(_t)
                for _f in _fs:
                    _sf = os.path.join(_r, _f)
                    _tf = os.path.join(_t, _f)
                    try:
                        shutil.copy2(_sf, _tf)
                        n += 1
                    except Exception:
                        try:
                            os.chmod(_tf, _stat.S_IWRITE)
                            shutil.copy2(_sf, _tf)
                            n += 1
                        except Exception:
                            pass
        else:
            try:
                shutil.copy2(_sp, _dp)
                n += 1
            except Exception:
                pass
    return n


def _sc_dl_ok(buf):
    """v6429（用户实测取证）：判定 steamcmd 是否**真的已完成 depot 下载**。

    成功日志实证：
        Waiting for user info...OK
        Downloading depot 2430931 (221 files, 8946 MB) ...
        Depot download complete : ".../depot_2430931" (manifest 3083367148300701914)
        Unloading Steam API...OK
        Redirecting stderr to '.../logs/stderr.txt'
        Logging directory: '.../logs'
        [ 0%] 正在检查            <-- steamcmd 自更新，可能卡住 / 非零退出
    ⇒ 只要出现 `Depot download complete`，说明下载早已完成，
      后续自更新阶段的非零退出码**不能**当作失败。
    """
    try:
        low = u'\n'.join(buf).lower()
    except Exception:
        return False
    return ('depot download complete' in low) or ('download complete :' in low)


def _sc_noise_lines():
    """v6429：steamcmd 自更新 / 日志重定向产生的噪声行关键词（不得当错误行展示）"""
    return (u'redirecting stderr', u'logging directory', u'正在检查',
            u'正在验证', u'正在安装更新', u'unloading steam api',
            u'update state', u'[----]')


def _sc_err_lines(buf, n=10):
    """v6421：从 SteamCMD 输出里挑出**关键错误行**。
    背景：steamcmd 每次启动都会刷 6 行「正在安装更新...」自更新提示，
    原来只截尾部 8 行 ⇒ 真正的 `ERROR (Timeout)` 被挤出窗口，用户只看到无意义的自更新。
    v6429：额外剔除自更新 / 日志重定向噪声（如 `[ 0%] 正在检查`）。
    """
    keys = ('error', 'failed', 'timeout', 'invalid', 'denied', 'guard',
            'logging in', 'logged in', 'unable', 'cannot', 'no subscription',
            'not logged', 'no app', 'missing', 'expired', 'rate limit')
    _noise = _sc_noise_lines()

    def _is_noise(_x):
        _l = _x.lower()
        return any(_k in _l for _k in _noise)

    hit = [x for x in buf if (not _is_noise(x)) and any(k in x.lower() for k in keys)]
    if not hit:
        _clean = [x for x in buf if not _is_noise(x)]
        hit = _clean[-n:] if _clean else buf[-n:]
    return u'\n'.join(hit[-n:])


def _sc_wait_auth(buf):
    """v6425（用户口径「等待授权不要报失败而是等待才对啊」）：
    判断这次失败是不是**在等 Steam 设备批准**（手机 App 里点批准那种）。
    明确的密码错 / 被拒 / 限流 才算真失败，其余一律视为「还在等待授权」。
    """
    low = u'\n'.join(buf).lower()
    for k in ('invalid password', 'logon denied', 'account disabled',
              'rate limit exceeded', 'no subscription'):
        if k in low:
            return False
    # v6430（用户实测取证「这次又报错，并且报错后手机反而弹批准了」）：
    #   steamcmd 走**设备批准模式时根本不打印 Guard 字样**，只会
    #     Logging in user ... -> Retrying... -> Retrying... -> ERROR (Timeout) -> Unloading
    #   而 Steam App 的推送取决于手机网络（开代理常延迟数分钟）⇒ 常出现
    #   「后端已判失败退出，手机才弹批准」的时序倒挂。
    #   ⇒ 只要登录行已出现、且没有明确的密码/权限错误，Timeout/Retrying 一律
    #     视为**仍在等批准**，保持任务 run 并继续重试（用户口径：等待不报错）。
    if (('error (timeout)' in low) or ('retrying' in low)) \
            and (('logging in' in low) or ('logged in' in low) or ('logging in user' in low)):
        return True
    for k in ('steam guard', 'waiting for', 'auth code', 'two-factor',
              'please enter the auth code', 'confirmation'):
        if k in low:
            return True
    return False


def _sc_login_failed(buf):
    low = u'\n'.join(buf).lower()
    for k in ('error (timeout)', 'logging in', 'logged in', 'invalid password',
              'steam guard', 'rate limit', 'denied'):
        if k in low:
            return True
    return False


def _cache_pull_run(srvuser, manifest, buildid, cred_user):
    """后台：steamcmd download_depot → 落 D:\\Cache → 写 acf"""
    key = 'cachepull|%s' % manifest

    def _t(msg, pct, phase='run', err=''):
        try:
            _utask_put(key, 'Cache', 'update', srvuser,
                       label=(u'拉取缓存 · ' + (u'v' + str(buildid) if buildid else str(manifest)[-8:])),
                       msg=msg, pct=pct, phase=phase, err=err)
        except Exception:
            pass

    try:
        _pwd = _steam_cred_get(cred_user)
        if not _pwd:
            _t(u'缺少 Steam 密码', 100, 'fail',
               u'账号 %s 没有缓存密码，请先在浮窗里填写并保存' % cred_user)
            return
        if not os.path.isfile(STEAMCMD_EXE):
            _t(u'SteamCMD 不存在', 100, 'fail', STEAMCMD_EXE)
            return
        _t(u'正在请求 Steam…', 3)
        # v6417：下载前先清空 SteamCMD 暂存区（download_depot 只增量补，不删旧文件）
        try:
            _pn0, _ = _cache_purge_dir(STEAMCMD_CONTENT)
            if _pn0:
                _t(u'已清理下载暂存区 %d 项' % _pn0, 4)
        except Exception:
            _sexc('cache_pull_purge_staging')
        _last = [0.0]
        _SCLOG = os.path.join(os.path.dirname(STEAMCMD_EXE), 'logs', 'console_log.txt')

        def _run_sc(login_args):
            """跑一次 steamcmd download_depot，返回 (rc, 输出行list)

            v6428（用户口径「我点了好几次批准，任务条还在等待」）实测根因：
              **steamcmd 把 stdout 写进管道时是块缓冲**，readline() 长时间拿不到新行
              ⇒ 任务条文案停更在「等批准」，而实际早已登录成功并在下载 3.8 GB。
              ⇒ 改为读 `logs/console_log.txt` 增量（steamcmd 自己实时落盘，不受管道缓冲影响）。
            """
            _cmd = [STEAMCMD_EXE] + list(login_args) + [
                '+download_depot', UPDATE_APP_ID, UPDATE_DEPOT_ID, str(manifest), '+quit']
            try:
                _pos = os.path.getsize(_SCLOG) if os.path.isfile(_SCLOG) else 0
            except Exception:
                _pos = 0
            _p = subprocess.Popen(_cmd, cwd=os.path.dirname(STEAMCMD_EXE),
                                  stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            _t1 = time.time()
            _login_t = [0.0]
            _dl_on = [False]
            _ok_at = [0.0]          # v6429：记录「Depot download complete」出现时刻
            _dep_tot = [0]          # v6432：depot 声明总字节（用于磁盘占用推算进度）
            _b = []

            def _feed(_s):
                # v6424：把 steamcmd 每个阶段翻译成任务条可见的中文提示
                _b.append(_s)
                if len(_b) > 400:
                    del _b[:-200]
                _low = _s.lower()
                _pm = re.search(r'progress:\s*[\d.]+ \((\d+)/(\d+)\)', _s)
                if _pm:
                    try:
                        _a, _bt = int(_pm.group(1)), max(1, int(_pm.group(2)))
                        _pc = 40 + int(45.0 * _a / _bt)
                        if _pc > 85:
                            _pc = 85
                        _dl_on[0] = True
                        if time.time() - _last[0] > 2.0:
                            _last[0] = time.time()
                            _t(u'下载中 %d%%（%.1f / %.1f GB）'
                               % (_pc, _a / 1073741824.0, _bt / 1073741824.0), _pc)
                        return
                    except Exception:
                        pass
                if 'logging in user' in _low:
                    _login_t[0] = time.time()
                    _t(u'正在登录 Steam…（若账号开了 Steam Guard，请先关闭手机代理/VPN，'
                       u'再到 Steam App 点「批准」）', 8)
                elif ('steam guard' in _low) or ('auth code' in _low):
                    _login_t[0] = _login_t[0] or time.time()
                    _t(u'需要 Steam Guard 验证 —— 请先关闭手机代理/VPN，'
                       u'再在 Steam App「确认」列表点「批准」', 10)
                elif ('waiting for' in _low) or ('confirmation' in _low):
                    _login_t[0] = _login_t[0] or time.time()
                    _t(u'等待 Steam 确认 —— 请先关闭手机代理/VPN，再点「批准」', 12)
                elif 'retrying' in _low:
                    _login_t[0] = _login_t[0] or time.time()
                    _t(u'Steam 登录重试中…（手机若开着代理请先关闭，再去 App 批准）', 14)
                elif 'error (timeout)' in _low:
                    _t(u'Steam 登录超时 —— 手机请先关闭代理/VPN，再到 App「确认」列表批准', 14)
                elif ('logged in ok' in _low) or ('logged in user' in _low):
                    _t(u'Steam 登录成功，准备下载…', 20)
                elif 'depot download complete' in _low:
                    # v6429：下载完成标记 —— 此后 steamcmd 只剩自更新/退出，不能再算失败
                    _ok_at[0] = time.time()
                    _t(u'下载完成，正在收尾…', 86)
                elif 'missing license' in _low:
                    _t(u'该 depot 需要账号订阅权限 —— 请确认登录账号拥有 ARK: Survival Ascended', 22)
                elif 'downloading' in _low:
                    _dl_on[0] = True
                    # v6432：解析 `Downloading depot 2430931 (221 files, 8946 MB)` 的声明总大小
                    try:
                        # v6435：_low 已 lower() ⇒ 单位是 'mb'/'gb'，不能写大写 MB（v6432 因此永不命中）
                        _dm = re.search(r'downloading depot \d+ \(\d+ files,\s*([\d.]+)\s*(mb|gb)\)', _low)
                        if _dm:
                            _uv = float(_dm.group(1))
                            _uu = _dm.group(2)
                            _dep_tot[0] = int(_uv * (1073741824.0 if _uu == 'gb' else 1048576.0))
                    except Exception:
                        pass
                    if time.time() - _last[0] > 2.0:
                        _last[0] = time.time()
                        _t(u'下载中… ' + _s[:110], 40)

            while True:
                _chunk = u''
                try:
                    _sz = os.path.getsize(_SCLOG) if os.path.isfile(_SCLOG) else 0
                    if _sz < _pos:
                        _pos = 0                     # 文件被重写
                    if _sz > _pos:
                        with open(_SCLOG, 'rb') as _f:
                            _f.seek(_pos)
                            _raw = _f.read()
                        _pos += len(_raw)
                        _chunk = _raw.decode('utf-8', 'replace')
                except Exception:
                    _chunk = u''
                for _s in _chunk.splitlines():
                    _s = _s.strip()
                    if _s:
                        _feed(_s)
                if _p.poll() is not None:
                    break
                # v6432（用户口径「下载阶段进度条完全不跑」）：
                #   steamcmd 的 `progress: x (a/b)` 只写 stdout（且 \r 原地刷新，块缓冲读不到），
                #   console_log.txt 只有阶段里程碑 ⇒ 进度卡死 40%。改用**磁盘真实占用**推算。
                if _dl_on[0] and _dep_tot[0] > 0:
                    try:
                        _cur = 0
                        for _rr, _dd, _ff in os.walk(STEAMCMD_CONTENT):
                            for _fn in _ff:
                                try:
                                    _cur += os.path.getsize(os.path.join(_rr, _fn))
                                except Exception:
                                    pass
                        if time.time() - _last[0] > 2.0:
                            _last[0] = time.time()
                            _pc = 40 + int(45.0 * _cur / _dep_tot[0])
                            if _pc > 85:
                                _pc = 85
                            _t(u'下载中 %d%%（%.1f / %.1f GB）'
                               % (_pc, _cur / 1073741824.0,
                                  _dep_tot[0] / 1073741824.0), _pc)
                    except Exception:
                        pass
                # v6429：出现「Depot download complete」后 steamcmd 只剩自更新（`[ 0%] 正在检查`），
                #   该阶段可能长时间不动 / 非零退出 ⇒ 再给 15 秒收尾即主动结束，避免误判失败。
                if _ok_at[0] and (time.time() - _ok_at[0] > 15):
                    try:
                        _p.kill()
                    except Exception:
                        pass
                    _b.append(u'[完成] 下载已完成，跳过自更新阶段')
                    break
                if time.time() - _t1 > 5400:
                    try:
                        _p.kill()
                    except Exception:
                        pass
                    _b.append(u'[超时] 已终止（90 分钟）')
                    break
                time.sleep(2)
            _rc = _p.wait()
            # v6429：只要取到「Depot download complete」，无论退出码如何一律判成功
            try:
                if _rc != 0 and _sc_dl_ok(_b):
                    _b.append(u'[已修正] 下载已完成，忽略 steamcmd 退出码 %d' % _rc)
                    _rc = 0
            except Exception:
                pass
            return _rc, _b

        # v6429（用户口径「anonymous 优先逻辑要去掉」）：
        #   一律用**自己的账号**登录 —— anonymous 对本 depot 无订阅权限，
        #   还会把真实的登录问题掩盖成「权限不足」。
        _t(u'⚠ 即将登录 Steam —— 若账号开了 Steam Guard：请**先关闭手机的代理/VPN**，'
           u'再打开手机 Steam App，在「确认 / 批准」列表里点「批准」登录（约 60 秒内有效）', 10)
        _rc, _buf = _run_sc(['+login', str(cred_user), _pwd])
        # v6425（用户口径「等待授权不要报失败而是等待才对啊」）：
        #   steamcmd 登录超时通常是「在等手机 App 批准」。这不是失败，是**还没批**。
        #   ⇒ 保持任务 run（不写 fail），自动重新拉起 steamcmd 再等一轮。
        _guard_round = 0
        _GUARD_MAX = 6          # 最多 6 轮（每轮约 105 秒 ≈ 总计 11 分钟等待窗）
        # v6430（用户实测「报错后手机才弹批准」）：手机推送常晚于单轮 105 秒，
        #   轮间距缩短到 10 秒 —— 让批准弹窗到达时尽快有一轮 steamcmd 在线接住。
        _GUARD_GAP = 10
        while (_rc != 0 and _guard_round < _GUARD_MAX and _sc_wait_auth(_buf)):
            _guard_round += 1
            # 倒计时（每 5 秒刷一次任务条，让用户看到确实在等而不是卡死）
            _seg = _GUARD_GAP // 5
            for _k in range(_seg):
                _left = _GUARD_GAP - _k * 5
                _t(u'等待设备批准 —— %d 秒后发起第 %d/%d 次登录。'
                   u'手机请**先关闭代理/VPN**，再打开 Steam App 底部「确认」列表找待批记录点「批准」'
                   u'（没弹推送时列表里通常仍有记录）'
                   % (_left, _guard_round, _GUARD_MAX), 15)
                time.sleep(5)
            _t(u'正在发起第 %d/%d 次 Steam 登录 —— 手机先关闭代理/VPN，'
               u'再立刻在 Steam App 点「批准」' % (_guard_round, _GUARD_MAX), 16)
            _rc, _buf = _run_sc(['+login', str(cred_user), _pwd])
            if _rc == 0:
                _t(u'设备批准通过，Steam 登录成功', 20)
                break
        _tail = u'\n'.join(_buf[-8:])
        if _rc != 0:
            # v6424：登录类失败一律附「用 Steam 客户端/手机 App 批准」的具体指引
            _hint = u''
            _lowf = u'\n'.join(_buf).lower()
            if ('error (timeout)' in _lowf) and (not _sc_wait_auth(_buf)) \
                    and ('invalid password' not in _lowf) and ('logon denied' not in _lowf):
                _hint = (u'【判断】登录请求发出后 Steam 长时间无回应（每轮约 105 秒 × 多轮）。\n'
                         u'最常见原因是**手机端的批准弹窗来得太晚**（推送要过手机网络；'
                         u'手机开着代理/VPN 时常常延迟数分钟，甚至后端已放弃才到）。\n'
                         u'请这样做：① 手机**先关掉代理/VPN**（系统代理 / Clash / Shadowrocket 等）；\n'
                         u'② 打开 Steam App 底部「确认」->「登录请求」列表，找待批记录点「批准」；\n'
                         u'③ 批准后**立刻**再点一次「开始拉取」（新开一轮 105 秒窗口），'
                         u'不要等弹窗提示再点。\n\n')
            elif _sc_login_failed(_buf):
                _hint = (u'【需要你做什么】账号开启了 Steam Guard，需要你在手机上批准这次登录：\n'
                         u'  1) 打开手机 Steam App -> 底部「确认」（盾牌）图标 -> 「登录请求」列表\n'
                         u'  2) 找到本次登录并点「批准」（**手机没弹推送时，列表里通常仍有记录**）\n'
                         u'  3) 批准后立刻回到本页再点一次「开始拉取」—— 全程只有这次登录需要批准\n'
                         u'  4) 一旦成功登录过一次，steamcmd 会把授权缓存到本机（ConnectCache），\n'
                         u'     之后拉取就不会再要求批准了\n'
                         u'注意：批准只在 steamcmd 登录的那个 60 秒窗口内有效，'
                         u'错过了就要重新点一次「开始拉取」再批。\n\n')
            _t(u'Steam 登录/下载失败', 100, 'fail', _hint + _sc_err_lines(_buf, 10)[:900])
            return
        if not os.path.isdir(STEAMCMD_CONTENT):
            _t(u'下载目录不存在', 100, 'fail', STEAMCMD_CONTENT + u'\n' + _tail[:300])
            return
        # v6417：清空缓存前先校验下载内容，避免「rc=0 但目录空」把缓存清成空
        # v6431（用户实测 2026-11-09）：steamcmd 报 `221 files` 是**下载条目数**，
        #   落盘实际只有 152 个（条目合并/共享），但 11.41 GB 内容完全正确、日志有
        #   `Depot download complete`。硬编码 500 会把好数据判成坏数据 ⇒ 缓存永远落不了地。
        #   ⇒ 权威判据改为 steamcmd 自己的完成标记；文件数/大小只做兜底底线。
        _got = _cache_count_files(STEAMCMD_CONTENT)
        _size_gb = 0.0
        try:
            _tb = 0
            for _r2, _d2, _f2 in os.walk(STEAMCMD_CONTENT):
                for _fn2 in _f2:
                    try:
                        _tb += os.path.getsize(os.path.join(_r2, _fn2))
                    except Exception:
                        pass
            _size_gb = _tb / 1073741824.0
        except Exception:
            pass
        _dl_done = False
        try:
            _dl_done = _sc_dl_ok(_buf)
        except Exception:
            _dl_done = False
        _ok_content = (_dl_done and _got >= 20 and _size_gb >= 1.0) or (_got >= 500)
        if not _ok_content:
            _t(u'下载内容异常（%d 个文件 / %.2f GB），已中止 —— 缓存未做任何改动'
               % (_got, _size_gb), 100, 'fail',
               (u'steamcmd 完成标记=%s\n' % (u'有' if _dl_done else u'无')) + _tail[:400])
            return
        _acf = os.path.join(UPDATE_CACHE_PATH, 'steamapps', UPDATE_ACF_NAME)
        # ① 备份 acf
        _bak = ''
        try:
            if os.path.isfile(_acf):
                _bak = _acf + '.bak_' + time.strftime('%Y%m%d_%H%M%S')
                shutil.copy2(_acf, _bak)
                _t(u'已备份 acf → ' + os.path.basename(_bak), 82)
        except Exception as e:
            _sexc('cache_pull_acf_bak')
            _t(u'acf 备份失败，已中止（缓存未清空）', 100, 'fail', repr(e)[:300])
            return
        # ② 清空 D:\Cache（保留 steamapps 与其中 acf）
        _t(u'清空缓存目录…', 84)
        try:
            _dn1, _df1 = _cache_purge_dir(UPDATE_CACHE_PATH, keep=('steamapps',))
            _dn2, _df2 = _cache_purge_dir(
                os.path.join(UPDATE_CACHE_PATH, 'steamapps', 'downloading'))
            _t(u'已清空缓存 %d 项（暂存 %d 项）' % (_dn1, _dn2), 86)
            if _df1 or _df2:
                _sexc('cache_pull_purge_cache',
                      u'部分残留: ' + u','.join((_df1 + _df2)[:6]))
        except Exception as e:
            _sexc('cache_pull_purge_cache')
            _t(u'缓存清空失败，已中止（acf 已备份：%s）'
               % (os.path.basename(_bak) or '-'), 100, 'fail', repr(e)[:300])
            return
        # ③ 再复制
        _t(u'回写缓存目录…（复制文件）', 88)
        _n = _cache_copy_tree(STEAMCMD_CONTENT, UPDATE_CACHE_PATH)
        _t(u'回写完成，正在写 acf…（%d 个文件）' % _n, 94)
        try:
            _t2 = open(_acf, encoding='utf-8', errors='replace').read()
            _t3 = _upd_patch_acf_text(_t2, buildid or '', str(manifest), '', int(time.time()))
            open(_acf + '.tmp', 'w', encoding='utf-8').write(_t3)
            os.replace(_acf + '.tmp', _acf)
        except Exception as e:
            _sexc('cachepull_acf')
            _t(u'文件已落，但 acf 写入失败', 95, 'fail', repr(e)[:300])
            return
        try:
            _depot_ver_cache_clear()      # v6425：拉完立刻让版本池反映新缓存
        except Exception:
            pass
        _t(u'完成：已拉到该版本（复制 %d 个文件）' % _n, 100, 'ok')
    except Exception as e:
        _sexc('cachepull')
        try:
            _t(u'异常', 100, 'fail', repr(e)[:400])
        except Exception:
            pass


def _cache_pull_start(srvuser, manifest, buildid, cred_user):
    key = 'cachepull|%s' % manifest
    try:
        _utask_put(key, 'Cache', 'update', srvuser,
                   label=u'拉取缓存 · ' + (u'v' + str(buildid) if buildid else str(manifest)[-8:]),
                   msg=u'排队中…', pct=1)
    except Exception:
        pass
    th = threading.Thread(target=_cache_pull_run,
                          args=(srvuser, str(manifest), str(buildid or ''), str(cred_user)),
                          daemon=True)
    th.start()
    return {'ok': True, 'key': key}


def _upd_cache_status():
    """缓存状态：ASAM 的 Cache Manager 顶部那一栏 + 「是否可以分发」"""
    d = UPDATE_CACHE_PATH
    acf = os.path.join(d, 'steamapps', UPDATE_ACF_NAME)
    sg = os.path.join(d, 'ShooterGame')
    paks = os.path.join(sg, 'Content', 'Paks')
    a = _upd_read_acf(acf)
    has_sg = os.path.isdir(sg)
    # 光有 ShooterGame 目录不算有内容 —— 必须有 Paks 文件（Clear Cache 会留空壳）
    has_paks = False
    if os.path.isdir(paks):
        try:
            has_paks = any(x.lower().endswith(('.pak', '.ucas', '.utoc'))
                           for x in os.listdir(paks))
        except Exception:
            has_paks = False
    return {'path': d, 'appId': UPDATE_APP_ID, 'depotId': UPDATE_DEPOT_ID,
            'exists': os.path.isdir(d), 'hasContent': bool(has_sg and has_paks),
            'buildId': a.get('buildid') or '', 'manifest': a.get('manifest') or '',
            'updatedAt': _upd_fmt_ts(a.get('lastUpdated')),
            'sizeGB': (round(int(a['sizeOnDisk']) / 1073741824.0, 2)
                       if str(a.get('sizeOnDisk') or '').isdigit() else 0),
            'realGB': _upd_dir_gb(d) if os.path.isdir(d) else 0,
            'name': a.get('name') or ''}


# ===== v6212（用户口径「要能抓到 ASAM 正在从 steam 更新的所有进度」）=====
#   ASAM 调 SteamCMD 更新缓存时，SteamCMD 自己写日志（实测样本 2026-10-31）：
#     SteamCMDInstall/logs/console_log.txt
#        [2026-10-31 08:21:17]  Update state (0x61) downloading, progress: 1.08 (132235281 / 12227543642)
#     SteamCMDInstall/logs/content_log.txt
#        Downloading 11017 chunks for depot 2430931 (6604340029022292600)
#        AppID 2430930 App update changed : Running Update,Downloading,Staging,
#        AppID 2430930 starting commit from "d:/cache/steamapps/downloading/2430930" to "d:/cache" : 248 updated
#   状态机实测全集：0x3 reconfiguring -> 0x5 verifying install -> 0x61 downloading
#                  -> 0x81 verifying update -> 0x0 unknown -> "Success! App '2430930' fully installed."
#   **纯只读**：只 open(...).read()，不写 ASAM 任何文件。
UPDATE_STEAM_LOG_DIRS = (
    r'D:\ASADedicatedManager\SteamCMDInstall\logs',
    r'C:\ASADedicatedManager\SteamCMDInstall\logs',
    r'E:\ASADedicatedManager\SteamCMDInstall\logs',
    r'\\localhost\ASADedicatedManager\SteamCMDInstall\logs',
    r'\\127.0.0.1\ASADedicatedManager\SteamCMDInstall\logs',
    r'\\SERVER\ASADedicatedManager\SteamCMDInstall\logs',
)
UPDATE_STEAM_IDLE_SEC = 120      # 最后一条状态行距今超过这么久 => 判定「没在更新」
UPDATE_STEAM_OK_HOLD = 12        # 完成后在任务列表里再留多少秒
_UPD_SPD = {'at': 0.0, 'done': 0}
_UPD_STAGE_ZH = {'0x3': u'重配置', '0x5': u'校验已装',
                 '0x61': u'下载', '0x81': u'校验下载', '0x0': u'收尾'}


def _upd_steam_logdir():
    # 依次探测候选目录（ASAM 与后端同机 192.168.199.3，正常情况下第一条即命中）
    for _d in UPDATE_STEAM_LOG_DIRS:
        try:
            if os.path.isdir(_d):
                return _d
        except Exception:
            pass
    return ''


def _upd_tail(fp, nbytes=32768):
    # 读文件尾部（日志可能很大，只取尾部）；失败返回空串
    try:
        _sz = os.path.getsize(fp)
        with open(fp, 'rb') as f:
            if _sz > nbytes:
                f.seek(_sz - nbytes)
            return f.read().decode('utf-8', 'replace')
    except Exception:
        return ''


def _upd_steam_steps(code, state):
    # 把 Steam 的 Update state code 映射成任务子步骤（与前端 lbTaskStepsHtml 的 steps 结构一致）
    order = ['0x3', '0x5', '0x61', '0x81', 'commit']
    labels = [u'重配置', u'校验已装', u'下载', u'校验下载', u'落盘']
    cur = code if code in order else ('commit' if state == 'commit' else '')
    idx = order.index(cur) if cur in order else -1
    out = []
    for i, k in enumerate(order):
        if idx < 0:
            st = 'ok' if state == 'done' else 'wait'
        elif i < idx:
            st = 'ok'
        elif i == idx:
            st = 'run' if state == 'run' else ('ok' if state == 'done' else 'fail')
        else:
            st = 'wait'
        out.append({'key': k, 'label': labels[i], 'state': st})
    return out


def _upd_steam_progress():
    # 返回 SteamCMD 缓存更新进度摘要（**不含日志正文**）
    # {found,phase,pct,done,total,speed,stage,stageZh,msg,chunks,idleSec,steps}
    _d = _upd_steam_logdir()
    r = {'found': bool(_d), 'phase': 'na', 'pct': 0, 'done': 0, 'total': 0, 'speed': 0,
         'stage': '', 'stageZh': '', 'msg': u'', 'chunks': 0, 'idleSec': -1, 'steps': []}
    if not _d:
        r['msg'] = u'未找到 SteamCMD 日志目录'
        return r
    _con = _upd_tail(os.path.join(_d, 'console_log.txt'))
    if not _con:
        r['phase'] = 'idle'
        r['msg'] = u'尚无 SteamCMD 日志'
        return r

    _pat = (r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s+Update state '
            r'\((0x[0-9a-fA-F]+)\)\s*([^,]*),\s*progress:\s*([\d.]+)\s*\((\d+) / (\d+)\)')
    _st = re.findall(_pat, _con)
    _okpos = _con.rfind(u"Success! App '2430930' fully installed")
    _lastpos = _con.rfind(u'Update state (%s)' % _st[-1][1]) if _st else -1
    _errm = re.findall(r'(?i)(error|failed|failure)', _con[-4000:])

    code = stage_en = tslast = ''
    pct = 0.0
    bdone = btotal = 0
    if _st:
        tslast, code, stage_en, _p, _bd, _bt = _st[-1]
        try:
            pct = float(_p)
        except Exception:
            pct = 0.0
        try:
            bdone, btotal = int(_bd), int(_bt)
        except Exception:
            bdone, btotal = 0, 0

    _idle = -1
    if tslast:
        try:
            _idle = int(max(0, time.time() - time.mktime(time.strptime(tslast, '%Y-%m-%d %H:%M:%S'))))
        except Exception:
            _idle = -1
    r['idleSec'] = _idle

    _cnt = _upd_tail(os.path.join(_d, 'content_log.txt'), 16384)
    _m = re.search(r'Downloading (\d+) chunks for depot', _cnt)
    if _m:
        r['chunks'] = int(_m.group(1))
    _tail_app = _cnt[_cnt.rfind(u'AppID 2430930'):] if _cnt else u''
    _commit = u'starting commit from' in _tail_app

    _sp = 0.0
    _now = time.time()
    if stage_en.startswith('download') and bdone > 0:
        if _UPD_SPD['at'] > 0 and (_now - _UPD_SPD['at']) > 0.4:
            _db = bdone - _UPD_SPD['done']
            if _db > 0:
                _sp = _db / (_now - _UPD_SPD['at'])
        _UPD_SPD['at'] = _now
        _UPD_SPD['done'] = bdone
    else:
        _UPD_SPD['at'] = 0.0
        _UPD_SPD['done'] = 0
    r['speed'] = int(_sp)

    if _okpos > 0 and _okpos >= _lastpos:
        r['phase'] = 'ok'
        r['pct'] = 100
        r['msg'] = u'缓存已更新到最新（SteamCMD: fully installed）'
    elif _idle >= 0 and _idle > UPDATE_STEAM_IDLE_SEC:
        r['phase'] = 'idle'
        r['msg'] = u'空闲（上次活动 %d 分钟前）' % (_idle // 60)
    elif _errm and _idle >= 0 and _idle <= UPDATE_STEAM_IDLE_SEC:
        r['phase'] = 'fail'
        r['msg'] = u'更新失败：' + (_errm[-1] or 'error')
    elif _commit and (pct >= 99.0 or code == '0x0'):
        r['phase'] = 'run'
        r['pct'] = 99
        r['stage'] = 'commit'
        r['stageZh'] = u'落盘'
        r['msg'] = u'落盘提交中（把下载内容写入 D:\\Cache）'
    elif code and code != '0x0':
        r['phase'] = 'run'
        r['pct'] = int(round(pct))
        r['stage'] = code
        r['stageZh'] = _UPD_STAGE_ZH.get(code, stage_en)
        if stage_en.startswith('download'):
            r['msg'] = u'下载中 %.1f%% · %.1f MB/s · %.2f / %.2f GB' % (
                pct, _sp / 1048576.0, bdone / 1073741824.0, btotal / 1073741824.0)
        else:
            r['msg'] = u'%s %.1f%%' % (r['stageZh'] or stage_en, pct)
    else:
        r['phase'] = 'idle'
        r['msg'] = u'空闲'

    r['done'] = bdone
    r['total'] = btotal
    r['stage'] = r['stage'] or code
    r['stageZh'] = r['stageZh'] or _UPD_STAGE_ZH.get(code, '')
    r['steps'] = _upd_steam_steps(code,
                                  'done' if r['phase'] == 'ok'
                                  else 'fail' if r['phase'] == 'fail'
                                  else 'commit' if r['stage'] == 'commit' else 'run')
    return r


def _upd_server_status(srv):
    """单台状态：自己的 acf + 是否落后于缓存"""
    d = os.path.join(UPDATE_SERVERS_ROOT, srv)
    acf = os.path.join(d, 'steamapps', UPDATE_ACF_NAME)
    a = _upd_read_acf(acf)
    return {'srv': srv, 'path': d, 'exists': os.path.isdir(d),
            'hasAcf': os.path.isfile(acf),
            'buildId': a.get('buildid') or '', 'manifest': a.get('manifest') or '',
            'updatedAt': _upd_fmt_ts(a.get('lastUpdated')),
            'sizeGB': (round(int(a['sizeOnDisk']) / 1073741824.0, 2)
                       if str(a.get('sizeOnDisk') or '').isdigit() else 0)}


# ===== v6397（用户口径「4 个卡片的本地包要加一个 待升级状态，只跟权威线上最新版本号对比」）=====
#   缓存卡的「权威线上最新版本号」= Steam 官方最新 buildId。
#   数据源 api.steamcmd.net（公开、免 key、实测可用）：
#     data.<appid>.depots.branches.public.buildid
#     data.<appid>.depots.<depotid>.manifests.public.gid
#   ⚠ Steam 官方 ISteamApps/UpToDateCheck 对 ASA(2430930) 直接返回
#     {"success":false,"error":"Couldn't get app info for the app specified."} —— 已实测不可用。
STEAM_INFO_URL = 'https://api.steamcmd.net/v1/info/%s' % UPDATE_APP_ID
STEAM_INFO_TTL = 600.0
_STEAM_INFO = {'at': 0.0, 'buildid': '', 'manifest': '', 'timeupdated': 0, 'err': ''}


def _steam_latest_build(force=False):
    """Steam 官方最新 buildId / depot manifest（10 分钟缓存；失败保留旧值不抛）"""
    now = time.time()
    if (not force) and _STEAM_INFO.get('buildid') \
            and (now - float(_STEAM_INFO.get('at') or 0) < STEAM_INFO_TTL):
        return dict(_STEAM_INFO)
    try:
        # v6397c：模块级没有 _ur（那是 _offi_get 里的局部 import），照抄会 NameError。
        #   直接复用 _offi_get —— 它已内置 UA 头 + 证书校验失败时降级不校验。
        j = json.loads(_offi_get(STEAM_INFO_URL, timeout=15))
        d = ((j.get('data') or {}).get(UPDATE_APP_ID) or {})
        br = ((d.get('depots') or {}).get('branches') or {}).get('public') or {}
        dp = (d.get('depots') or {}).get(UPDATE_DEPOT_ID) or {}
        _STEAM_INFO.update({'at': now,
                            'buildid': str(br.get('buildid') or ''),
                            'manifest': str((((dp.get('manifests') or {}).get('public')) or {}).get('gid') or ''),
                            'timeupdated': int(br.get('timeupdated') or 0),
                            'err': ''})
    except Exception as e:
        _STEAM_INFO.update({'at': now,
                            'err': '%s:%s' % (type(e).__name__, str(e)[:120])})
    return dict(_STEAM_INFO)


def _upd_status(include_players=False):
    """完整状态：缓存 + 11 台对比 + 落后清单
    include_players=True 时逐台查在线人数（慢，仅前端点「刷新」时用）"""
    cache = _upd_cache_status()
    cbuild = cache.get('buildId') or ''
    # v6397：缓存卡的「本地包待升级」判据 —— 本地缓存 buildId vs Steam 官方最新 buildId
    try:
        _st = _steam_latest_build()
        _lb = str(_st.get('buildid') or '')
        cache['latestBuildId'] = _lb
        cache['latestManifest'] = str(_st.get('manifest') or '')
        cache['latestAt'] = (time.strftime('%Y-%m-%d %H:%M', time.localtime(int(_st.get('timeupdated') or 0)))
                             if int(_st.get('timeupdated') or 0) else '')
        cache['latestErr'] = str(_st.get('err') or '')
        cache['needUpgrade'] = bool(_lb and cbuild and _lb != str(cbuild))
    except Exception as e:
        cache['latestBuildId'] = ''
        cache['latestErr'] = '%s:%s' % (type(e).__name__, str(e)[:120])
        cache['needUpgrade'] = False
    out = []
    for srv in sorted(SERVERS.keys()):
        s = _upd_server_status(srv)
        s['same'] = bool(cbuild and s.get('buildId') == cbuild)
        if include_players:
            try:
                s['players'] = _restart_players(srv)
            except Exception:
                s['players'] = None
        out.append(s)
    behind = [x['srv'] for x in out if not x['same']]
    # 能不能分发：缓存必须有真实内容 + 必须能读到缓存的 buildid
    can = bool(cache.get('hasContent') and cbuild)
    return {'cache': cache, 'servers': out, 'behind': behind,
            'canApply': can,
            'applyBlockReason': (u'' if can else
                                 (u'缓存没有实际文件（可能已被 ASAM 的 Clear Cache 清空），'
                                  u'请先在 ASAM 的 Cache Manager 里点「Update local cache from steam」')),
            'ts': time.strftime('%Y-%m-%d %H:%M:%S')}


def _upd_status_snapshot():
    """给前端用的轻量版（不含在线人数，秒回）"""
    return _upd_status(include_players=False)


# ===== v6228（P1.5）：版本档位判定 + AsaApi 缓存就绪判定 =====
#   方案 §16（版本号是「档位」不是小数）/ §14.3（精确串判据）
# v6230（用户纠正口径）：版本号可能**没有小数部分**（`v97` = 97.0）
_VER_RE = re.compile(r'^(\d+)(?:\.(\d+))?$')
_AS_TAG = re.compile(r'<[^>]+>')
_AS_MD = re.compile(r'[*_`]+')
_AS_WS = re.compile(r'\s+')
_AS_READY = 'automated cache build: success'
_OFF_VER_RE = re.compile(r'(\d+\.\d+)')


def _extract_ver(s):
    """从 ASAM 原始串里抽版本号：'Official Server Network Status: Online (v96.6)' -> '96.6'"""
    m = _OFF_VER_RE.search(str(s or ''))
    return m.group(1) if m else ''


def _ver_seg(v):
    m = _VER_RE.match(str(v or '').strip().lstrip('vV'))
    if not m:
        return None
    return (int(m.group(1)), m.group(2) or '0')      # v97 -> (97, '0')


def _vnum(s):
    try:
        return int(str(s))
    except Exception:
        return 0


def _ver_kind(old, new):
    """v6230（**用户纠正后的最终口径，只从版本号判断**）
       · **主版本整数部分**变化：96.x -> 97.x  => forced（强制，不更新玩家进不来）
       · **仅小数部分**变化：96.9 -> 96.13     => patch （非强制，客户端仍可进）
       · 完全一致                              => same
       · 无法解析                              => unknown
       ⚠ 已废除两版旧规则：
         ① v6228「小数点后首字符」判据 —— 用户明确说「小数变化全是非强制」，
            故 96.8 -> 96.9 也是 patch，不再算 forced
         ② buildId 兜底 —— 用户明确「只从版本号判断」，不再拿 acf buildId 反推"""
    a, b = _ver_seg(old), _ver_seg(new)
    if not a or not b:
        return 'unknown'
    if a[0] != b[0]:
        return 'forced'
    if a[1] == b[1]:
        return 'same'
    return 'patch'


def _asaapi_state(cards=None):
    """v6228（§14.3）：AsaApi 缓存就绪判定 —— **唯一精确判据**
       规范化（剥 HTML -> 去 markdown -> 小写 -> 压空白）后文本包含
       `automated cache build: success` 即就绪；其余一律 building/unknown。
       ⚠ 不做任何关键词猜测（旧方案在 'once completed' / 'cache-ready message' 上踩过 2 次坑）。
       返回 (state, raw, meta)；raw 是**英文原文**，前端浮窗必须原样展示不翻译。"""
    try:
        meta = {'updated': '', 'fetchedAt': 0, 'total': 0, 'hit': False}
        if cards is None:
            # v6395（真根因收尾 · 用户口径「补上」）：
            #   api_cache 缓存只有资讯广场前端按需请求时才刷新，本函数却**直接 open 文件**、
            #   绕开 _news_read ⇒ 不开资讯就永远读旧内容（分发确认浮窗的
            #   「Automated Cache Build」原文与 officialCacheState 一起滞后）。
            #   lbUpdFetch 并发打 /api/update/status 与 /api/api/status，谁先返回不确定，
            #   光靠 _api_discord_latest 刷新会出现首帧读旧值。这里补一次按需刷新，
            #   _news_refresh 自带 60s 全局冷却 + 全局锁，冷却期内零网络开销、失败不抛。
            try:
                _news_refresh('api_cache')
            except Exception:
                pass
            doc = {}
            try:
                with open(_news_path('api_cache'), encoding='utf-8') as f:
                    doc = json.load(f) or {}
            except Exception:
                doc = {}
            cards = doc.get('cards') or []
            meta['updated'] = doc.get('updated') or ''
            try:
                meta['fetchedAt'] = int(doc.get('fetched_at') or 0)
            except Exception:
                meta['fetchedAt'] = 0
        meta['total'] = len(cards)
        if not cards:
            return 'unknown', '', meta
        raw = cards[-1].get('content') or ''
        t = _AS_TAG.sub(' ', raw)
        t = _AS_MD.sub('', t)
        t = _AS_WS.sub(' ', t).strip().lower()
        meta['hit'] = (_AS_READY in t)
        return ('ready' if meta['hit'] else 'building'), raw, meta
    except Exception:
        return 'unknown', '', {'updated': '', 'fetchedAt': 0, 'total': 0, 'hit': False}


# ===== v6283（用户口径 Round 1）：MOD / API 只读状态（服务器更新浮窗两张卡）=====
MODS_GAMEID = '83374'          # CurseForge gameId（ARK: Survival Ascended，固定）
# v6284（用户口径）：MOD 策略 —— Bob 固定自己那套；其他 10 服用「统一列表」（默认为空，由系统管理配置）
MODS_POLICY_DEFAULT = {'bob': '1005639', 'common': []}
# v6284（用户口径）：API 只保留这三样，其余一律判为「多余 · 应清理」
API_REQUIRED_LIB = 'AsaApi'                      # 库本体
API_REQUIRED_PLUGINS = ('Permissions', 'ServerOpsKitAPI')
# v6298（用户口径）：AsaApi.dll 没有 PE 版本资源（GetFileVersionInfo 返回空），
#   用**文件大小指纹**映射版本号；新增版本时在此补一行即可（人工核对官方 release 的 dll 大小）。
ASA_API_VER_BY_SIZE = {
    7308288: '2.03',
    7335424: '2.1',   # 2026-11-08 官方 2.1 包（_apipkg/2.1/ArkApi/AsaApi.dll 同指纹）
}
_MODS_CACHE = {'at': 0.0, 'data': None}
_API_CACHE = {'at': 0.0, 'data': None}
MODS_TTL = 30.0
API_TTL = 30.0


def _mods_policy():
    """MOD 策略：{bob: str, common: [str]}；Bob 固定，其余服共用 common 列表"""
    out = {'bob': MODS_POLICY_DEFAULT['bob'], 'common': list(MODS_POLICY_DEFAULT['common'])}
    try:
        d = _srv_cfg_read()
        raw = d.get('mods_policy')
        if isinstance(raw, dict):
            bob = str(raw.get('bob') or '').strip()
            if bob:
                out['bob'] = bob
            cm = raw.get('common')
            if isinstance(cm, list):
                out['common'] = [str(x).strip() for x in cm if str(x).strip()]
            elif isinstance(cm, str):
                out['common'] = [x.strip() for x in cm.replace(u'，', ',').split(',') if x.strip()]
    except Exception:
        pass
    return out


def _mods_expect_of(srv, policy=None):
    """该服「应该装哪些 ProjectId」——Bob 只认 bob，其他服认 common"""
    po = policy or _mods_policy()
    if srv == 'Bob':
        return ([po['bob']] if po.get('bob') else [])
    return list(po.get('common') or [])


def _read_text(p, enc='utf-8-sig'):
    """安全读文本（后端无 import io，统一走内置 open）"""
    try:
        with open(p, encoding=enc, errors='replace') as fh:
            return fh.read()
    except Exception:
        return ''


def _srv_win64(srv):
    return os.path.join(CFG_SERVERS_DIR, srv, 'ShooterGame', 'Binaries', 'Win64')


def _dir_size(p):
    t = 0
    try:
        for root, ds, fs in os.walk(p):
            for x in fs:
                try:
                    t += os.path.getsize(os.path.join(root, x))
                except Exception:
                    pass
    except Exception:
        pass
    return t


def _mt_str(p):
    try:
        return time.strftime('%Y-%m-%d %H:%M', time.localtime(os.stat(p).st_mtime))
    except Exception:
        return ''


def _mt_epoch(p):
    try:
        return os.stat(p).st_mtime
    except Exception:
        return 0.0


def _mod_infos_of(srv):
    """Profile\\modInfos.json → {pid: dict}（仅展示补充；实测滞后，不作判定依据）"""
    p = os.path.join(CFG_SERVERS_DIR, srv, 'Profile', 'modInfos.json')
    out = {}
    try:
        arr = json.loads(_read_text(p) or '[]')
        for it in (arr or []):
            if not isinstance(it, dict):
                continue
            pid = str(it.get('ProjectId') or '').strip()
            if pid:
                out[pid] = it
    except Exception:
        pass
    return out


def mods_status():
    """MOD 卡数据：以磁盘 83374\\<pid>_<fid> 为唯一判定源（纯只读）"""
    now = time.time()
    if _MODS_CACHE['data'] is not None and (now - _MODS_CACHE['at']) < MODS_TTL:
        return _MODS_CACHE['data']
    t0 = time.time()
    servers, groups = {}, {}
    policy = _mods_policy()
    total = 0
    ls_cnt, ls_size = 0, 0
    for srv in SERVERS.keys():
        base = os.path.join(_srv_win64(srv), 'ShooterGame', 'Mods', MODS_GAMEID)
        infos = _mod_infos_of(srv)
        items = []
        if os.path.isdir(base):
            try:
                # v6352（用户口径「怎么还残留 .temp 这行」）：CFCore 下载残留的 .temp 等**点目录不是 MOD**，
                #   扫进来会变成一条假的「MOD 版本组」（界面显示：.temp　1 台）。
                keys = sorted([x.name for x in os.scandir(base)
                               if x.is_dir() and not x.name.startswith(u'.')])
            except Exception:
                keys = []
            for k in keys:
                kp = os.path.join(base, k)
                roots = []
                try:
                    roots = sorted([x.name for x in os.scandir(kp) if x.is_dir()])
                except Exception:
                    pass
                rt = roots[0] if roots else ''
                name, desc, murl = rt, '', ''
                if rt:
                    try:
                        j = json.loads(_read_text(os.path.join(kp, rt, rt + '.uplugin')) or '{}')
                        name = str(j.get('FriendlyName') or rt)
                        desc = str(j.get('Description') or '')
                        murl = str(j.get('MarketplaceURL') or '')
                    except Exception:
                        pass
                pid, _, fid = k.partition('_')
                info = infos.get(pid) or {}
                sz = _dir_size(kp)
                lsb = 0
                if rt:
                    lsp = os.path.join(kp, rt, 'Content', 'Movies', 'LoadingScreen.bk2')
                    if os.path.isfile(lsp):
                        try:
                            lsb = os.path.getsize(lsp)
                        except Exception:
                            lsb = 0
                if lsb:
                    ls_cnt += 1
                    ls_size = max(ls_size, lsb)
                items.append({'dir': k, 'pid': pid, 'fid': fid, 'root': rt,
                              'name': name, 'desc': desc[:200], 'url': murl,
                              'size': sz, 'mtime': _mt_str(kp), 'lsSize': lsb,
                              'summary': str(info.get('Summary') or '')[:200],
                              'author': str(info.get('AuthorName') or ''),
                              'downloads': int(info.get('DownloadCount') or 0),
                              'image': str(info.get('ImageUrl') or ''),
                              'registeredFileId': str(info.get('FileId') or '')})
                total += sz
                # v6284（用户口径）：分组按「前段 ProjectId」——后段 FileId 只是版本，不算不同 MOD
                groups.setdefault(pid, {}).setdefault(fid, []).append(srv)
        # 期望 vs 实际（策略判定）
        expect = _mods_expect_of(srv, policy)
        actual = dict((it['pid'], it['fid']) for it in items)
        missing = [x for x in expect if x not in actual]
        extra = [x for x in actual.keys() if x not in expect]
        servers[srv] = {'exists': os.path.isdir(base), 'items': items,
                        'expect': expect, 'actual': actual,
                        'missing': missing, 'extra': extra,
                        'conform': (not missing) and (not extra)}
    reclaim = (ls_size * (ls_cnt - 1)) if (ls_cnt > 1 and ls_size) else 0
    # 基准版本（每个 pid 取「最新 fid」，判据=目录 mtime 最新者）——分发时用
    base_fid = {}
    for pid, fmap in groups.items():
        best, best_ts = '', -1
        for fid, svs in fmap.items():
            for sv in svs:
                for it in (servers.get(sv, {}).get('items') or []):
                    if it['pid'] == pid:
                        kp = os.path.join(_srv_win64(sv), 'ShooterGame', 'Mods', MODS_GAMEID, it['dir'])
                        tsv = _mt_epoch(kp)
                        if tsv > best_ts:
                            best_ts, best = tsv, fid
        base_fid[pid] = best
    conform_n = sum(1 for sv in servers.values() if sv.get('conform'))
    # v6397（用户口径「不光要加进面板，还要影响对于最新版的判断」）：
    #   每个 pid 查 **CurseForge 最新文件**（走 _mods_cf_files，10 分钟缓存；未配 cf_key 时为空）。
    #   前端「最新版」判定与「本地包待升级」都以它为准，不再拿「已装服里 mtime 最新的 fid」当最新。
    cf_latest = {}
    for _pid in groups.keys():
        try:
            _fl = _mods_cf_files(_pid)
            if _fl:
                _f0 = _fl[0]
                cf_latest[_pid] = {
                    'fid': str(_f0.get('id') or ''),
                    'name': str(_f0.get('displayName') or _f0.get('fileName') or ''),
                    'at': str(_f0.get('fileDate') or '')[:19].replace('T', ' '),
                    'dl': int(_f0.get('downloadCount') or 0),
                }
        except Exception:
            _sexc('mods_cf_latest')
    data = {'ok': True, 'gameId': MODS_GAMEID, 'servers': servers, 'groups': groups,
            'policy': policy, 'baseFid': base_fid, 'cfLatest': cf_latest,
            'localPack': _mods_local_pack(),
            'conformCount': conform_n, 'serverCount': len(SERVERS),
            'totalBytes': total, 'reclaimableBytes': reclaim,
            'loadingScreen': {'count': ls_cnt, 'size': ls_size},
            'ms': int((time.time() - t0) * 1000)}
    _MODS_CACHE['at'] = now
    _MODS_CACHE['data'] = data
    return data


def _plugin_scan(dirp):
    """扫一个插件目录 → [{name, version, minApi, dll, dllSize, dllMtime}]"""
    out = []
    try:
        names = sorted([x.name for x in os.scandir(dirp) if x.is_dir()], key=lambda s: s.lower())
    except Exception:
        return out
    for nm in names:
        dp = os.path.join(dirp, nm)
        info, ierr = {}, ''
        ip = os.path.join(dp, 'PluginInfo.json')
        try:
            info = json.loads(_read_text(ip) or '{}')
        except Exception as _e:
            ierr = '%s: %s' % (type(_e).__name__, _e)
            info = {}
        dll, dsz, dmt, derr = '', 0, '', ''
        try:
            for f in os.scandir(dp):
                if f.is_file() and f.name.lower().endswith('.dll'):
                    dll = f.name
                    dsz = f.stat().st_size
                    dmt = _mt_str(f.path)
                    break
            if not dll:
                derr = 'no_dll'
        except Exception as _e2:
            derr = '%s: %s' % (type(_e2).__name__, _e2)
        out.append({'name': nm, 'version': str(info.get('Version') or ''),
                    'minApi': str(info.get('MinApiVersion') or ''),
                    'fullName': str(info.get('FullName') or ''),
                    'dll': dll, 'dllSize': dsz, 'dllMtime': dmt,
                    'err': ierr, 'derr': derr, 'dp': dp})
    return out


def _dc_ts_local(ts):
    """Discord ISO 时间（UTC）-> 本地 'YYYY-MM-DD HH:MM'"""
    try:
        e = _cal.timegm(time.strptime(str(ts)[:19], '%Y-%m-%dT%H:%M:%S'))
        return time.strftime('%Y-%m-%d %H:%M', time.localtime(e))
    except Exception:
        return ''


def _dc_msg_text(m):
    """Discord message -> 纯文本（content + embeds.title/description/fields）"""
    parts = []
    try:
        c = (m.get('content') or '').strip()
        if c:
            parts.append(c)
        for e in (m.get('embeds') or []):
            if not isinstance(e, dict):
                continue
            au = ((e.get('author') or {}).get('name') or '').strip()
            if au:
                parts.append(au)
            for k in ('title', 'description'):
                v = (e.get(k) or '').strip()
                if v:
                    parts.append(v)
            for fld in (e.get('fields') or []):
                nm = (fld.get('name') or '').strip()
                vl = (fld.get('value') or '').strip()
                if nm or vl:
                    parts.append((nm + ': ' + vl).strip())
    except Exception:
        pass
    return '\n'.join(parts)


def _api_discord_latest():
    """v6288（用户口径）：最新 API 信息取自 Discord 接口抓取缓存（api_ver / api_cache），零网络"""
    out = {}
    # v6393（真根因 · 用户口径「不是应该找到为啥你拉到的 Discord 官方公告号是旧的么」
    #        「官方缓存 后面的 已就绪，也滞后，应该也是同一个根因」「我发现我必须手动打开过资讯 你才更新」）：
    #   api_ver / api_cache 两份缓存**只有资讯广场前端按需请求时**才会调 _news_refresh 去 Discord 抓，
    #   不开资讯就永远读旧文件 ⇒「库」最新版（latest.verNum）与「官方缓存」状态（officialCacheState）
    #   一起滞后（用户本地包已 2.11，这里还返回 2.1）。
    #   ⇒ 读数前先按需刷新一次。_news_refresh 自带全局冷却（NEWS_COOL_SEC=60s）与全局锁，
    #     冷却期内零网络开销；抓取失败不抛（保留旧缓存，行为与原来一致）。
    #   成本上界：api_status() 自身 _API_CACHE TTL=30s ⇒ 最多每 60s 打 2 个频道各一次。
    for _tid in ('api_ver', 'api_cache'):
        try:
            _news_refresh(_tid)
        except Exception:
            pass
    try:
        d = _news_read('api_ver') or {}
        ms = [x for x in (d.get('messages') or []) if isinstance(x, dict)]
        if ms:
            t = _dc_msg_text(ms[-1])
            out['verAt'] = _dc_ts_local(ms[-1].get('timestamp'))
            out['verText'] = t[:600]
            # v6393（真根因 · 第二层）：Discord 公告标题格式已从「AsaApi v2.1 released」
            #   变成「[ASA: Server API v2.11] released」—— 只认 AsaApi 的老正则抓不到 ⇒ verNum 为空，
            #   前端「库」行变 v?、库需升级判定全失效。放宽为三种常见写法，再兜底取首个 vX.Y+。
            mv = (re.search(r'(?i)(?:AsaApi|Server\s*API|ASA[:\s\-]*API)\s*[:\-]?\s*v?([0-9]+(?:\.[0-9]+)+)', t)
                  or re.search(r'(?i)\bv([0-9]+(?:\.[0-9]+)+)', t))
            out['verNum'] = mv.group(1) if mv else ''
    except Exception as e:
        out['verErr'] = repr(e)
    try:
        d2 = _news_read('api_cache') or {}
        ms2 = [x for x in (d2.get('messages') or []) if isinstance(x, dict)]
        if ms2:
            t2 = _dc_msg_text(ms2[-1])
            low = t2.lower()
            out['cacheAt'] = _dc_ts_local(ms2[-1].get('timestamp'))
            out['cacheText'] = t2[:600]
            if 'success' in low:
                out['cacheState'] = 'ready'
            elif ('longer than usual' in low) or ('running' in low):
                out['cacheState'] = 'building'
            elif 'detected' in low:
                out['cacheState'] = 'detected'
            else:
                out['cacheState'] = 'unknown'
    except Exception as e:
        out['cacheErr'] = repr(e)
    return out


def _lib_needs_upgrade(_dc, lib):
    """v6297：本地 AsaApi.dll 是否落后于官方最新版本（用 dll 文件时间 vs Discord 发布公告时间判定）"""
    try:
        _va = str((_dc or {}).get('verAt') or '')
        if not _va:
            return False
        for _sv in lib.values():
            _dm = str(_sv.get('dllMtime') or '')
            if not _dm:
                return False            # 有服没装 dll -> 不标"需升级"（属缺库，另有展示）
            if _dm < _va:
                return True
        return False
    except Exception:
        return False


def _asa_lib_ver_map():
    """v6399（真根因）：dll size -> AsaApi 版本号。
       **以本地包目录名（_upd_cache/_apipkg/<版本>/ArkApi/AsaApi.dll）为准动态生成**，
       硬编码 ASA_API_VER_BY_SIZE 仅作兜底。
       根因：Bob 分发 2.11 后 dll=7351808 字节，硬编码表没有这一项 ⇒ dllVer='' ⇒
             前端 `_libGrp` 把它归进「未检测到 dll」灰段（用户报「AsaApi 显示 Bob 未检测到 dll」）。
       以后本地包一升级就会自动识别，不再需要人工补表。"""
    m = dict(ASA_API_VER_BY_SIZE)
    try:
        root = _asa_pkg_root()
        if os.path.isdir(root):
            for x in os.scandir(root):
                if not x.is_dir():
                    continue
                p = os.path.join(x.path, 'ArkApi', 'AsaApi.dll')
                if os.path.isfile(p):
                    try:
                        m[os.path.getsize(p)] = x.name      # 目录名即版本号（如 2.11）
                    except Exception:
                        pass
    except Exception:
        _sexc('asa_lib_ver_map')
    return m


def api_status():
    """API 卡数据：库一致性 + 缓存就绪 + 插件矩阵（纯只读）"""
    now = time.time()
    if _API_CACHE['data'] is not None and (now - _API_CACHE['at']) < API_TTL:
        return _API_CACHE['data']
    t0 = time.time()
    lib, cache, plugs = {}, {}, {}
    lib_sig = {}
    _diag2 = {}
    _lib_vermap = _asa_lib_ver_map()          # v6399：本地包优先，硬编码兜底
    for srv in SERVERS.keys():
        win = _srv_win64(srv)
        dll = os.path.join(win, 'ArkApi', 'AsaApi.dll')
        ld = os.path.join(win, 'AsaApiLoader.exe')
        cfg = os.path.join(win, 'config.json')
        dsz, dmt = 0, ''
        if os.path.isfile(dll):
            dsz = os.path.getsize(dll)
            dmt = _mt_str(dll)
        lib[srv] = {'dllExists': os.path.isfile(dll), 'dllSize': dsz, 'dllMtime': dmt,
                    'dllVer': _lib_vermap.get(dsz, ''),
                    'loaderSize': (os.path.getsize(ld) if os.path.isfile(ld) else 0),
                    'loaderMtime': _mt_str(ld), 'hasCfg': os.path.isfile(cfg)}
        lib_sig.setdefault('%s|%s' % (dsz, dmt), []).append(srv)
        exe = os.path.join(win, 'ArkAscendedServer.exe')
        co = os.path.join(win, 'ArkApi', 'Cache', 'cached_offsets.cache')
        ck = os.path.join(win, 'ArkApi', 'Cache', 'cached_key.cache')
        gen, gen_at = '', 0.0
        try:
            gd = os.path.join(win, 'ArkApi', 'Cache', 'generations')
            gens = [(os.stat(os.path.join(gd, x.name)).st_mtime, x.name)
                    for x in os.scandir(gd) if x.is_dir()]
            if gens:
                gens.sort(reverse=True)
                gen_at, gen = gens[0][0], gens[0][1]
        except Exception:
            gen, gen_at = '', 0.0
        exe_at, co_at, ck_at = _mt_epoch(exe), _mt_epoch(co), _mt_epoch(ck)
        # v6289（用户实测口径）：AsaApi 2.x 把偏移缓存写进 Cache\generations\<分代>\，
        #   根目录 cached_offsets.cache 停在旧版（2026-07-04）不再更新 ⇒ 老判据永远 0/11。
        #   新判据：根目录 offsets 或最新分代 任一 >= 服务端 exe 即视为就绪。
        _best_at = max(co_at or 0.0, gen_at or 0.0)
        cache[srv] = {'offsetsSize': (os.path.getsize(co) if os.path.isfile(co) else 0),
                      'offsetsAt': _mt_str(co), 'keyAt': _mt_str(ck), 'generation': gen,
                      'genAt': (time.strftime('%Y-%m-%d %H:%M', time.localtime(gen_at)) if gen_at else ''),
                      'exeAt': _mt_str(exe),
                      'ready': bool(_best_at and exe_at and _best_at >= exe_at)}
        act = _plugin_scan(os.path.join(win, 'ArkApi', 'Plugins'))
        dis = _plugin_scan(os.path.join(win, '_disabled_plugins'))
        if srv == list(SERVERS.keys())[0]:
            _diag2['pluginsRaw'] = act
            _diag2['pluginsDisabledRaw'] = dis
        for p in act:
            _pe = plugs.get(p['name'])
            if _pe is None:
                _pe = {'version': p['version'], 'minApi': p['minApi'],
                       'dllSize': p['dllSize'], 'dllMtime': p['dllMtime'],
                       'servers': [], 'missing': [], 'disabled': [], 'vers': {}}
                plugs[p['name']] = _pe
            # v6334（用户口径）：原 setdefault 只保留首个服的版本，
            #   Bob \u5347\u5230 0.8 \u540e\u4ecd\u663e\u793a v0.7\uff08\u53d6\u5230 Isl\uff09\u3002\u8fd9\u91cc\u6309 PluginInfo \u5206\u7ec4\u3002
            _pv = str(p['version'] or '')
            _pe['vers'].setdefault(_pv, []).append(srv)
            _pe['servers'].append(srv)
        for p in dis:
            key = p['name'].split('_')[0] if '_' in p['name'] else p['name']
            # v6286（用户口径）：启用目录里没有的插件**不登记** —— _disabled_plugins 只是历史残留，
            #   不能因为它存在就把「0/11 台」的插件列进卡片（用户：明明一台都没有为什么显示）
            if key not in plugs:
                continue
            plugs[key]['disabled'].append({'srv': srv, 'dir': p['name']})
    all_srv = list(SERVERS.keys())
    for nm, p in plugs.items():
        p['missing'] = [s for s in all_srv if s not in p['servers']]
        # v6334：版本取「台数最多的非空版本」（缺 PluginInfo 的空值不参与）
        _cand = [(len(v), k) for k, v in (p.get('vers') or {}).items() if k]
        if _cand:
            _cand.sort(reverse=True)
            p['version'] = _cand[0][1]
        else:
            p['version'] = ''
        p['required'] = (nm in API_REQUIRED_PLUGINS)   # v6284：只保留 Permissions / ServerOpsKitAPI
    lib_consistent = (len(lib_sig) == 1)
    ready_cnt = sum(1 for s in all_srv if (cache.get(s) or {}).get('ready'))
    _extras = sorted([nm for nm in plugs.keys() if nm not in API_REQUIRED_PLUGINS])
    # v6287：自研源目录只读探测；v6312（用户口径）改用 UNC 网络地址
    try:
        _ps_p = SOK_SRC_UNC
        _ps_e = os.path.isdir(_ps_p)
        _diag2['pluginSrc'] = {'path': _ps_p, 'exists': _ps_e,
                               'items': (sorted(os.listdir(_ps_p))[:40] if _ps_e else None)}
    except Exception as _e_ps:
        _diag2['pluginSrc'] = {'path': SOK_SRC_UNC, 'err': repr(_e_ps)}
    _dc = _api_discord_latest()
    _oc_state = str(_dc.get('cacheState') or 'unknown')
    # v6301：自研源版本兜底 —— 插件 dll 本身不含任何版本信息（实测无 FileVersion/PluginInfo 资源），
    #   版本号只在同目录 PluginInfo.json。源目录常只放了 dll ⇒ 用「dll 大小与已装插件比对」给出判断。
    _lp_fix = _api_local_pack()
    _sok = plugs.get('ServerOpsKitAPI') or {}
    _inst_ver = str(_sok.get('version') or '')
    _inst_sz = int(_sok.get('dllSize') or 0)
    _src_sz = int(_lp_fix.get('srcDllSize') or 0)
    _lp_fix['srcInstalledVer'] = _inst_ver
    _lp_fix['srcSameAsInstalled'] = bool(_inst_sz and _src_sz and _inst_sz == _src_sz)
    if not _lp_fix.get('srcVer') and _lp_fix['srcSameAsInstalled'] and _inst_ver:
        _lp_fix['srcVer'] = _inst_ver
        _lp_fix['srcVerSrc'] = 'same_size_as_installed'
    try:
        _need_map = _api_need_by_srv(_asa_targets())
    except Exception:
        _sexc('api_need_by_srv')
        _need_map = {}
    # v6397（用户口径「4 个卡片的本地包要加一个 待升级状态，只跟权威线上最新版本号对比」）：
    #   API 卡本地包 —— 只与**权威线上最新**（Discord 公告 latest.verNum）比，
    #   不与「SOK 自研源版本」或「各服已装版本」比（那两个是分发源 / 现状，不是线上最新）。
    try:
        _nv = lambda x: str(x or '').strip().lstrip('vV')
        _alp_v = str(_lp_fix.get('ver') or '')
        _lat_v = str(_dc.get('verNum') or '')
        _lp_fix['latestVer'] = _lat_v
        _lp_fix['needUpgrade'] = bool(_alp_v and _lat_v and _nv(_alp_v) != _nv(_lat_v))
    except Exception:
        _lp_fix['latestVer'] = ''
        _lp_fix['needUpgrade'] = False
    data = {'ok': True,
            'apiNeed': _need_map,          # v6349：每服插件是否需要分发（与分发同源）
            'requiredPlugins': list(API_REQUIRED_PLUGINS),
            'latest': _dc,
            'officialCacheState': _oc_state,
            'officialCacheAt': _dc.get('cacheAt') or '',
            'officialCacheText': _dc.get('cacheText') or '',
            # v6290（用户口径）：就绪/分发门控 = 官方针对「最新游戏版本」的缓存是否已构建完成
            #   （Discord api_cache 出 SUCCESS）；同时要求各服本地当前版本分代缓存齐备，
            #   否则换 dll 会 offsets 不匹配、服务器起不来。
            'deployReady': bool(_oc_state == 'ready' and ready_cnt >= len(all_srv)),
            'localPack': _lp_fix,
            # v6297（用户口径）：库是否需要升级 —— 本地 dll 文件时间早于官方最新版本发布公告时间
            'libNeedsUpgrade': _lib_needs_upgrade(_dc, lib),
            'extras': _extras,
            'lib': lib, 'libConsistent': lib_consistent,
            'libGroups': dict((k, v) for k, v in lib_sig.items()),
            'cache': cache, 'cacheReadyCount': ready_cnt, 'serverCount': len(all_srv),
            'plugins': plugs,
            'diag': _diag2,
            'ms': int((time.time() - t0) * 1000)}
    _API_CACHE['at'] = now
    _API_CACHE['data'] = data
    return data


# ===== v6284（用户口径）：MOD / API 分发（Round 2/3） =====
def _upd_cache_dir():
    """批次共享缓存根：<ARK Server>\\_upd_cache\\<batchId>\\..."""
    return os.path.join(os.path.dirname(CFG_SERVERS_DIR), '_upd_cache')


def _mods_new_batch():
    return 'mb' + time.strftime('%Y%m%d%H%M%S') + ('%03d' % int((time.time() * 1000) % 1000))


def _mods_local_pack():
    """v6293（用户口径）：MOD 本地包 = _upd_cache 下 批次/mods/ 已缓存的版本（pid_fid）
    v6353（方案 A）：把 _upd_cache/_modpkg/ 下的「真·本地包」（CurseForge 下载）一并统计"""
    root = _upd_cache_dir()
    items, tot, bat = [], 0, ''
    _pkg_root = os.path.join(root, MODS_PKG_ROOT_NAME)
    try:
        if os.path.isdir(_pkg_root):
            for y in os.scandir(_pkg_root):
                if not y.is_dir() or y.name.endswith('.tmp'):
                    continue
                sz = _dir_size(y.path)
                tot += sz
                items.append({'key': y.name, 'bytes': sz, 'at': _mt_str(y.path), 'src': 'pkg'})
    except Exception:
        _sexc('mods_local_pack_pkg')
    try:
        cands = []
        for x in os.scandir(root):
            if not x.is_dir() or not x.name.startswith('mb'):
                continue
            md = os.path.join(x.path, 'mods')
            if os.path.isdir(md):
                cands.append((os.path.getmtime(x.path), x.name, md))
        cands.sort(reverse=True)
        if cands:
            bat = cands[0][1]
            md = cands[0][2]
            for y in os.scandir(md):
                if not y.is_dir():
                    continue
                sz = _dir_size(y.path)
                tot += sz
                items.append({'key': y.name, 'bytes': sz, 'at': _mt_str(y.path)})
        items.sort(key=lambda z: z['key'])
    except Exception:
        _sexc('mods_local_pack')
    return {'batchId': bat, 'count': len(items), 'bytes': tot, 'items': items}


def _mods_prefetch_plan():
    """v6293：把策略基准版本从现有服复制进新批次缓存（=更新本地包），纯只读计算"""
    st = mods_status()
    base = st.get('baseFid') or {}
    svmap = st.get('servers') or {}
    out, seen = [], set()
    for pid in sorted(base.keys()):
        want = str(base.get(pid) or '')
        if not want or pid in seen:
            continue
        seen.add(pid)
        src_srv, src_dir, nb = '', '', 0
        for cand, ci in svmap.items():
            if str((ci.get('actual') or {}).get(pid) or '') != want:
                continue
            for it in (ci.get('items') or []):
                if it.get('pid') == pid and it.get('fid') == want:
                    src_srv = cand
                    src_dir = os.path.join(_srv_win64(cand), 'ShooterGame', 'Mods',
                                           MODS_GAMEID, it.get('dir') or '')
                    nb = int(it.get('size') or 0)
                    break
            if src_srv:
                break
        out.append({'pid': pid, 'fid': want, 'key': '%s_%s' % (pid, want),
                    'srcSrv': src_srv, 'srcDir': src_dir, 'bytes': nb,
                    'ok': bool(src_dir and os.path.isdir(src_dir))})
    return out


# v6305（用户口径·无感回收）：MOD 开场视频 Content/Movies/LoadingScreen.bk2 服务端根本不读
#   （不在 Manifest_NonUFS/UFS 清单里；dedicated 无渲染设备）⇒ 分发与更新本地包一律跳过，
#   分发前把目标旧目录里已有的删掉，用户无感、不用任何按钮。
MODS_LS_NAME = 'LoadingScreen.bk2'


def _mods_strip_ls(dirp):
    """删除 <ModRoot>/Content/Movies/LoadingScreen.bk2；返回 (删除个数, 释放字节)"""
    n, tot = 0, 0
    try:
        if not os.path.isdir(dirp):
            return 0, 0
        for root, _ds, _fs in os.walk(dirp):
            if os.path.basename(root).lower() != 'movies':
                continue
            if os.path.basename(os.path.dirname(root)).lower() != 'content':
                continue
            p = os.path.join(root, MODS_LS_NAME)
            if os.path.isfile(p):
                try:
                    sz = os.path.getsize(p)
                    os.remove(p)
                    n += 1
                    tot += sz
                except Exception:
                    _sexc('mods_strip_ls')
    except Exception:
        _sexc('mods_strip_ls_walk')
    return n, tot


def _mods_prefetch_run(user, batch_id, plans):
    """v6293：复制到 _upd_cache/新批次/mods/（只写缓存，不动任何服务器）
    v6323（用户口径）：接入任务总线 —— 一个实例一条（key 固定，重复点击复用同一条）"""
    cache_base = os.path.join(_upd_cache_dir(), batch_id, 'mods')
    ok_n, bad_n, tot = 0, 0, 0
    _pk = u'modprefetch|' + str(batch_id)
    _ps = [u'扫描基准版本', u'复制到缓存', u'校验']
    _pn = max(1, len(plans))

    def _pt(msg, pct, phase='run', err=''):
        try:
            _utask_put(_pk, '', 'update', user, label=u'更新本地包',
                       msg=msg, pct=pct, phase=phase, steps=_ps, err=err,
                       srv_name=u'%d 个 MOD' % _pn)
        except Exception:
            _sexc('mods_prefetch_utask')
    _pt(u'准备复制 %d 个基准 MOD…' % _pn, 5)
    try:
        if not os.path.isdir(cache_base):
            os.makedirs(cache_base)
    except Exception:
        _sexc('mods_prefetch_mkdir')
    _pi = 0
    for p in plans:
        _pi += 1
        dst = os.path.join(cache_base, p['key'])
        try:
            if os.path.isdir(dst):
                ok_n += 1
                _pt(u'第 %d/%d 个：%s 已在缓存，跳过' % (_pi, _pn, p.get('key') or u''),
                    5 + int(85.0 * _pi / _pn))
                continue
            _pt(u'第 %d/%d 个：复制 %s …' % (_pi, _pn, p.get('key') or u''),
                5 + int(85.0 * _pi / _pn))
            shutil.copytree(p['srcDir'], dst, ignore=shutil.ignore_patterns(MODS_LS_NAME))
            ok_n += 1
            tot += int(p.get('bytes') or 0)
        except Exception:
            _sexc('mods_prefetch_copy')
            bad_n += 1
    try:
        _admin_log('MODS prefetch by %s batch=%s ok=%d bad=%d bytes=%d'
                   % (user, batch_id, ok_n, bad_n, tot))
    except Exception:
        pass
    try:
        if bad_n:
            _pt(u'完成：成功 %d 个，失败 %d 个' % (ok_n, bad_n), 100, 'fail', u'部分复制失败')
        else:
            _pt(u'完成：%d 个 MOD 已进缓存（%.1f MB）· 批次 %s'
                % (ok_n, tot / 1048576.0, batch_id), 100, 'ok')
    except Exception:
        pass
    return {'ok': ok_n, 'bad': bad_n, 'bytes': tot, 'batchId': batch_id}


def _pe_file_version(p):
    """v6299：从 dll 版本资源里抠 FileVersion 字符串（无资源返回空；AsaApi 插件 dll 一般带版本资源）"""
    try:
        if os.path.getsize(p) > 32 * 1024 * 1024:
            return ''
        with open(p, 'rb') as f:
            b = f.read()
        key = 'FileVersion'.encode('utf-16-le')
        i = b.find(key)
        if i < 0:
            return ''
        txt = b[i + len(key): i + len(key) + 240].decode('utf-16-le', 'ignore')
        m = re.search(r'([0-9]+(?:\.[0-9]+){1,3})', txt)
        return m.group(1) if m else ''
    except Exception:
        return ''


def _api_local_pack():
    """v6293（用户口径）：API 本地包 = _upd_cache/_apipkg/版本/（官方 AsaApi 包 + 自研插件源）"""
    root = os.path.join(_upd_cache_dir(), '_apipkg')
    items, tot, cur = [], 0, ''
    try:
        if os.path.isdir(root):
            for x in os.scandir(root):
                if not x.is_dir():
                    continue
                sz = _dir_size(x.path)
                tot += sz
                items.append({'ver': x.name, 'bytes': sz, 'at': _mt_str(x.path)})
                if (not cur) or (x.name > cur):
                    cur = x.name
            items.sort(key=lambda z: z['ver'])
    except Exception:
        _sexc('api_local_pack')
    _sp = SOK_SRC_UNC
    _sf, _sa = [], ''
    try:
        if os.path.isdir(_sp):
            _sf = sorted(os.listdir(_sp))[:20]
            _mt = 0.0
            for _x in os.scandir(_sp):
                try:
                    _v = os.path.getmtime(_x.path)
                except Exception:
                    continue
                if _v > _mt:
                    _mt = _v
            _sa = time.strftime('%Y-%m-%d %H:%M', time.localtime(_mt)) if _mt else ''
    except Exception:
        _sf, _sa = [], ''
    # v6299（用户口径）：自研源也要显示版本号 —— 读源目录 dll 的版本资源，其次读 PluginInfo.json
    _sver, _sdll, _ssz = '', '', 0
    try:
        if os.path.isdir(_sp):
            for _f in os.scandir(_sp):
                if _f.is_file() and _f.name.lower().endswith('.dll'):
                    _sdll = _f.name
                    try:
                        _ssz = _f.stat().st_size
                    except Exception:
                        _ssz = 0
                    _sver = _pe_file_version(_f.path)
                    break
            if not _sver:
                _pj = os.path.join(_sp, 'PluginInfo.json')
                if os.path.isfile(_pj):
                    _sver = str((json.loads(_read_text(_pj) or '{}') or {}).get('Version') or '')
    except Exception:
        _sver = ''
    return {'ver': cur, 'count': len(items), 'bytes': tot, 'items': items,
            'srcPath': _sp, 'srcOk': bool(_sf), 'srcFiles': _sf, 'srcAt': _sa,
            'srcVer': _sver, 'srcDll': _sdll, 'srcDllSize': _ssz}


# ===== v6353（用户口径·方案 A）：MOD 「真·本地包」—— 直接从 CurseForge 官方下载 =====
#   背景：原「本地包」只是**从某台服 copytree 出来的副本**（_mods_prefetch_run），
#         没有源服就彻底没源；且文案写「请配置 CurseForge API Key 后再下载」但**下载功能从未实现**。
#   实测（2026-11-09）：
#     · GET /v1/mods/{id}/files  → 200，可列出该 mod 全部文件（筛 fileName 含 windowsserver = 服务端包）
#     · GET /v1/mods/{id}/files/{fid}/download-url → **403**（第三方 key 不给直链）
#     · CDN 直链必须自己拼：https://mediafilez.forgecdn.net/files/<fid 前4>/<fid 其余>/<fileName> → 206 / zip
#     · 746 MB 包 76 秒下完；解压后 <root>/<root>.uplugin + Content/Paks/WindowsServer/*.{pak,ucas,utoc}
MODS_PKG_ROOT_NAME = '_modpkg'
MODS_CF_TTL = 600.0
_MODS_CF = {'files': {}}


def _cf_key():
    try:
        return str((_srv_cfg_read() or {}).get('cf_key') or '').strip()
    except Exception:
        return ''


def _cf_api(path):
    """CurseForge API（cf_key + 浏览器 UA）。返回 (status, json)"""
    k = _cf_key()
    if not k:
        return 0, {'_error': u'未配置 CurseForge API Key'}
    try:
        import urllib.request as _ur
        req = _ur.Request('https://api.curseforge.com' + path,
                          headers={'Accept': 'application/json',
                                   'User-Agent': ASA_HTTP_UA,
                                   'x-api-key': k})
        with _ur.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode('utf-8', 'replace'))
    except Exception as e:
        return -1, {'_error': repr(e)[:200]}


def _mods_cf_files(pid, force=False):
    """该 MOD 的文件列表（发布时间倒序；缓存 10 分钟）"""
    pid = str(pid or '')
    now = time.time()
    cc = _MODS_CF['files'].get(pid)
    if cc and not force and (now - cc['at']) < MODS_CF_TTL:
        return cc['data']
    s, j = _cf_api('/v1/mods/%s/files?pageSize=50&sort=datePublished&sortOrder=desc' % pid)
    data = (j.get('data') or []) if s == 200 else []
    _MODS_CF['files'][pid] = {'at': now, 'data': data}
    return data


def _mods_cf_name(pid):
    """v6360：MOD 展示名（CurseForge name，如 Fear Ascended）—— 任务条不能拿 projectId 当名字"""
    pid = str(pid or '')
    cc = _MODS_CF.setdefault('names', {}).get(pid)
    if cc:
        return cc
    s, j = _cf_api('/v1/mods/%s' % pid)
    nm = u''
    if s == 200:
        nm = str(((j.get('data') or {}).get('name') or u'')).strip()
    if nm:
        _MODS_CF['names'][pid] = nm
    return nm


def _mods_cf_server_file(pid):
    """挑「服务端包」：fileName 含 windowsserver（不是 windows/ps5/xboxxs），取最新"""
    for f in _mods_cf_files(pid):
        if u'windowsserver' in str(f.get('fileName') or '').lower():
            return f
    return None


MODS_CF_HOSTS = (u'mediafilez.forgecdn.net', u'edge.forgecdn.net', u'mediafiles.forgecdn.net')


def _mods_cf_cdn_urls(pid):
    """v6364：CDN 候选直链（多主机）→ (urls, fid)
       实测（2026-11-09）：**同一文件不是所有主机都有** ——
         Club ARK 9418028：mediafilez=403 / mediafiles=403 / edge=200（真 zip 118,557,863 B）
         Fear Ascended 9411569：mediafilez=200 / edge=200
       ⇒ 必须按主机顺序挨个试，任一成功即停（原来写死 mediafilez ⇒ Club ARK 必然 403，
         误判成「作者不允许公开直连」）
       ⚠ edge 不支持 Range 分段（带 Range 返回 404），下载必须整包 GET。"""
    f = _mods_cf_server_file(pid)
    if not f:
        return [], u''
    fid = str(f.get('id') or '')
    fn = str(f.get('fileName') or '')
    if not fid or not fn:
        return [], fid
    return ([u'https://%s/files/%s/%s/%s' % (h, fid[:4], fid[4:], fn)
             for h in MODS_CF_HOSTS], fid)


def _mods_cf_cdn_url(pid):
    """CDN 直链（首个候选；兼容旧调用）→ (url, fid)"""
    _us, fid = _mods_cf_cdn_urls(pid)
    return (_us[0] if _us else u''), fid


def _mods_pkg_dir(pid, fid):
    return os.path.join(_upd_cache_dir(), MODS_PKG_ROOT_NAME, '%s_%s' % (pid, fid))


def _mods_pkg_fetch(pid, on_prog=None, force=False):
    """下载并解压「真·本地包」→ _upd_cache/_modpkg/<pid>_<fid>/
       · 跳过开场视频 LoadingScreen.bk2（服务端不读，与分发同策略）
       · 原子性：先下 .zip 校验大小，再解压到临时目录后改名
       返回 (ok, msg, fid, dir)"""
    import zipfile
    pid = str(pid or '')
    f = _mods_cf_server_file(pid)
    if not f:
        return False, u'CurseForge 上没有该 MOD 的服务端包（windowsserver）', u'', u''
    fid = str(f.get('id') or '')
    _urls = _mods_cf_cdn_urls(pid)[0]      # v6365：返回 (urls, fid)，必须取 [0]
    if not _urls:
        return False, u'拿不到 CDN 直链', fid, u''
    dst = _mods_pkg_dir(pid, fid)
    if os.path.isdir(dst) and not force:
        n0 = sum(len(fs) for _r, _d, fs in os.walk(dst))
        if n0 > 0:
            return True, u'已存在本地包（%d 文件，跳过下载）' % n0, fid, dst
    root = os.path.join(_upd_cache_dir(), MODS_PKG_ROOT_NAME)
    try:
        if not os.path.isdir(root):
            os.makedirs(root)
    except Exception as e:
        return False, u'建目录失败：%r' % (e,), fid, u''
    zpath = os.path.join(root, '%s_%s.zip' % (pid, fid))
    tot = int(f.get('fileLength') or 0)
    import urllib.request as _ur
    _errmap = []
    _okdl = False
    for _ui, _u in enumerate(_urls):
        try:
            if os.path.isfile(zpath):
                os.remove(zpath)
        except Exception:
            pass
        try:
            _host = str(_u).split('//')[-1].split('/')[0]
        except Exception:
            _host = u'?'
        try:
            if on_prog:
                on_prog(u'下载 %s（%.1f MB）…%s'
                        % (f.get('fileName') or u'', tot / 1048576.0,
                           (u'' if _ui == 0 else u' 换主机 %s' % _host)), 'dl', 0.0)
            req = _ur.Request(_u, headers={'User-Agent': ASA_HTTP_UA})
            got = 0
            last = 0
            # v6374（用户口径「进度平滑」）：上报粒度 8MB → 约 1%（小文件 1MB 兑底）
            #   配合前端 1.4s 线性过渡，条子视觉上连续上涨
            _step = max(1048576, int(tot / 100)) if tot else 1048576
            with _ur.urlopen(req, timeout=300) as r, open(zpath, 'wb') as fh:
                while True:
                    b = r.read(512 * 1024)
                    if not b:
                        break
                    fh.write(b)
                    got += len(b)
                    if on_prog and tot > 0 and (got - last) >= _step:
                        last = got
                        on_prog(u'下载中 %.1f / %.1f MB'
                                % (got / 1048576.0, tot / 1048576.0), 'dl',
                                float(got) / float(tot))
            if tot and got != tot:
                raise IOError(u'size mismatch %d/%d' % (got, tot))
            _okdl = True
            break
        except Exception as _e1:
            # v6364（实测）：CDN 各主机内容不同 —— Club ARK 9418028 在 mediafilez=403 / edge=200
            #   ⇒ 逐个主机回退，任一成功即停；全失败才报错（不再误称「不允许公开直连」）
            _errmap.append(u'%s %s' % (_host, repr(_e1)[:50]))
            continue
    if not _okdl:
        try:
            if os.path.isfile(zpath):
                os.remove(zpath)
        except Exception:
            pass
        return (False, u'下载失败（%d 个 CDN 主机都取不到）：%s'
                % (len(_urls), u'；'.join(_errmap)[:200]), fid, u'')
    tmpd = dst + '.tmp'
    try:
        if on_prog:
            on_prog(u'解压中…', 'unzip')
        if os.path.isdir(tmpd):
            shutil.rmtree(tmpd, ignore_errors=True)
        os.makedirs(tmpd)
        n = 0
        _keep = 0
        _skip = 0
        with zipfile.ZipFile(zpath) as z:
            for _zi in z.infolist():
                if _zi.filename.endswith('/'):
                    continue
                if _zi.filename.split('/')[-1].lower() == MODS_LS_NAME.lower():
                    # v6362：开场视频占包体积的 95%（实测 Fear Ascended：
                    #   整包 746 MB，其中 LoadingScreen.bk2 709 MB，真正 MOD 内容只有 ~5 MB）
                    _skip += int(getattr(_zi, 'file_size', 0) or 0)
                    continue
                z.extract(_zi, tmpd)
                n += 1
                _keep += int(getattr(_zi, 'file_size', 0) or 0)
        if n <= 0:
            raise IOError(u'解压后 0 文件')
        if os.path.isdir(dst):
            shutil.rmtree(dst, ignore_errors=True)
        os.replace(tmpd, dst)
    except Exception as e:
        try:
            shutil.rmtree(tmpd, ignore_errors=True)
        except Exception:
            pass
        return False, u'解压失败：%r' % (e,), fid, u''
    try:
        os.remove(zpath)
    except Exception:
        pass
    _msg = u'已下载并解压 %d 文件（%.1f MB，fid %s）' % (n, _keep / 1048576.0, fid)
    if _skip:
        _msg += u'；跳过开场视频 %.0f MB（服务端不读）' % (_skip / 1048576.0)
    return True, _msg, fid, dst


def _mods_deploy_plan(servers, policy=None):
    """MOD 分发计划：[{srv, pid, cur, want, srcSrv, srcDir, reason, ok}]（纯只读计算）"""
    po = policy or _mods_policy()
    st = mods_status()
    base = st.get('baseFid') or {}
    svmap = st.get('servers') or {}
    out = []
    for srv in servers:
        info = svmap.get(srv) or {}
        actual = info.get('actual') or {}
        for pid in _mods_expect_of(srv, po):
            want = str(base.get(pid) or '')
            cur = str(actual.get(pid) or '')
            if want and cur == want:
                continue
            src_srv, src_dir, src_kind = '', '', ''
            if want:
                for cand, ci in svmap.items():
                    if cand == srv:
                        continue
                    if str((ci.get('actual') or {}).get(pid) or '') == want:
                        for it in (ci.get('items') or []):
                            if it.get('pid') == pid and it.get('fid') == want:
                                src_srv = cand
                                src_dir = os.path.join(_srv_win64(cand), 'ShooterGame', 'Mods',
                                                       MODS_GAMEID, it.get('dir') or '')
                                src_kind = 'srv'
                                break
                    if src_srv:
                        break
                # v6353（方案 A）：**服上都没有该版本时，回落「真·本地包」**
                #   原实现直接判 ok=False ⇒ 任务条「无可用源」，本地包形同摆设
                if not src_dir:
                    _pkg = _mods_pkg_dir(pid, want)
                    if os.path.isdir(_pkg):
                        src_dir = _pkg
                        src_kind = 'pkg'
            out.append({'srv': srv, 'pid': pid, 'cur': cur, 'want': want,
                        'srcSrv': src_srv, 'srcDir': src_dir, 'srcKind': src_kind,
                        'reason': ('missing' if not cur else 'old'),
                        'ok': bool(want and src_dir)})
    return out


def _mods_dir_of(srv):
    return os.path.join(_srv_win64(srv), 'ShooterGame', 'Mods', MODS_GAMEID)


# ===== v6356（方案 A·最后一步）：CFCore library.json 条目「自建」 =====
#   实测（Los 2026-11-09）：CFCore 条目就是 CurseForge API 响应的**改名版**
#     API id / url / fileName  ->  CFCore iD / uRL / filename
#     API fileStatus 4         ->  CFCore "Approved"（数字转词）
#     API releaseType 1        ->  CFCore "Release"
#     API 2026-11-02T22:01:58.393Z  ->  CFCore 2026.11.02-22.01.58（点分）
_CF_RELEASE = {1: u'Release', 2: u'Beta', 3: u'Alpha'}
_CF_STATUS = {1: u'Processing', 2: u'ChangesRequired', 3: u'UnderReview', 4: u'Approved',
              5: u'Rejected', 6: u'DistributionDenied', 7: u'PendingRelease'}
_CF_REN = {'id': 'iD', 'url': 'uRL', 'fileName': 'filename'}
_CF_DATE_KEYS = ('dateCreated', 'dateModified', 'dateReleased', 'fileDate',
                 'gameVersionReleaseDate')


def _cf_date(v):
    """ISO → CFCore 点分格式；已是点分则原样返回"""
    s = str(v or u'')
    if not s or re.match(r'^\d{4}\.\d{2}\.\d{2}-', s):
        return s
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})', s)
    return (u'%s.%s.%s-%s.%s.%s' % m.groups()) if m else s


def _cf_rename(o):
    """递归把 API 键名改成 CFCore 的怪命名，并把日期/状态/类型转成 CFCore 表示"""
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            kk = _CF_REN.get(k, k)
            vv = _cf_rename(v)
            if kk in _CF_DATE_KEYS and not isinstance(vv, (dict, list)):
                vv = _cf_date(vv)
            elif kk in ('fileStatus', 'status') and isinstance(v, int):
                vv = _CF_STATUS.get(v, v)
            elif kk == 'releaseType' and isinstance(v, int):
                vv = _CF_RELEASE.get(v, v)
            out[kk] = vv
        return out
    if isinstance(o, list):
        return [_cf_rename(v) for v in o]
    return o


_MODS_LIB_DEF = {'at': 0.0, 'data': None}


def _mods_lib_defaults():
    """v6357：从任一台服的 library.json 借出 CFCore 自己写的默认子对象
       （premiumDetails / ratingDetails / videos / screenshots）—— 这些字段 API 不返回，
       硬编码结构有风险；借真品最安全。"""
    now = time.time()
    if _MODS_LIB_DEF['data'] is not None and (now - _MODS_LIB_DEF['at']) < 300:
        return _MODS_LIB_DEF['data']
    out = {}
    for srv in SERVERS.keys():
        p = os.path.join(_srv_win64(srv), 'ShooterGame', 'ModsUserData', MODS_GAMEID, 'library.json')
        if not os.path.isfile(p):
            continue
        try:
            j = json.loads(_read_text(p) or '{}')
        except Exception:
            continue
        for it in (j.get('installedMods') or []):
            d = it.get('details') or {}
            if d.get('premiumDetails') is not None:
                out = {'premiumDetails': d.get('premiumDetails'),
                       'ratingDetails': d.get('ratingDetails') or {},
                       'videos': d.get('videos') or [],
                       'screenshots': d.get('screenshots') or []}
                break
        if out:
            break
    _MODS_LIB_DEF['at'] = now
    _MODS_LIB_DEF['data'] = out
    return out


def _mods_cf_file_cc(pid, fid):
    """单文件详情（API）→ CFCore installedFile 结构；失败返回 {}"""
    s, j = _cf_api('/v1/mods/%s/files/%s' % (pid, fid))
    if s != 200:
        return {}
    f = (j.get('data') or {})
    if not f:
        return {}
    o = _cf_rename(f)
    for k in ('favoriteCount', 'isEarlyAccess', 'licenseType', 'featuredProjectTag',
              'hasCommentsEnabled', 'premiumDetails', 'platformFileSizesOnDisk'):
        o.pop(k, None)
    # v6357：实测 diff —— 这三项 CFCore 有、API 单文件接口不返回，按默认补
    o.setdefault('exposeAsAlternative', False)
    o.setdefault('parentProjectFileId', 0)
    o.setdefault('serverPackFileId', 0)
    if not o.get('downloadUrl'):
        # CFCore 自己存的是 edge 域名直链（我们下载用 mediafilez，两者存在差异）
        _fn = str(o.get('filename') or '')
        _fid = str(o.get('iD') or '')
        if _fn and _fid:
            o['downloadUrl'] = u'https://edge.forgecdn.net/files/%s/%s/%s' % (_fid[:4], _fid[4:], _fn)
    return o


def _mods_lib_entry_build(pid, fid):
    """用 CurseForge 元数据构造一个 CFCore `installedMods[]` 条目（不需要任何服有旧记录）"""
    import hashlib as _h2
    pid, fid = str(pid or ''), str(fid or '')
    if not pid or not fid or not _cf_key():
        return None
    s, j = _cf_api('/v1/mods/%s' % pid)
    if s != 200:
        return None
    mod = (j.get('data') or {})
    if not mod:
        return None
    fcc = _mods_cf_file_cc(pid, fid)
    if not fcc:
        return None
    det = _cf_rename(mod)
    for k in ('favoriteCount', 'featuredProjectTag', 'hasCommentsEnabled',
              'latestEarlyAccessFilesIndexes', 'licenseType',
              'supportedPlatform', 'supportsCrossPlatform', 'thumbsUpCount'):
        det.pop(k, None)
    det['mainFileId'] = int(fid)
    _def = _mods_lib_defaults()
    for _k in ('premiumDetails', 'ratingDetails', 'videos', 'screenshots'):
        if _k not in det and _k in _def:
            det[_k] = _def[_k]
    # latestFiles / latestFilesIndexes 至少要含目标 fid（CFCore 用它判断「有无更新」）
    lf = det.get('latestFiles') or []
    if not any(str((x or {}).get('iD') or '') == fid for x in lf):
        det['latestFiles'] = [fcc] + list(lf)
    lfi = det.get('latestFilesIndexes') or []
    if not any(str((x or {}).get('fileId') or '') == fid for x in lfi):
        _gvs = fcc.get('gameVersions') or [u'1.0']
        det['latestFilesIndexes'] = [{'fileId': int(fid),
                                      'filename': fcc.get('filename') or u'',
                                      'gameVersion': _gvs[0],
                                      'gameVersionTypeId': 76367,
                                      'modLoader': 'Any',
                                      'releaseType': fcc.get('releaseType') or u'Release'}] + list(lfi)
    _pod = u'%s/%s_%s' % (MODS_GAMEID, pid, fid)
    _now = time.strftime('%Y.%m.%d-%H.%M.%S')
    return {'iD': _h2.md5(_pod.encode('utf-8')).hexdigest().upper(),
            'dateInstalled': _now,
            'dateUpdated': _now,
            'details': det,
            'downloadInfo': {'canResume': False, 'downloaded': [], 'fileId': 0,
                             'fileSizeInBytes': 0,
                             'lastModified': '0001.01.01-00.00.00', 'tempFile': u''},
            'dynamicContent': False,
            'enabled': True,
            'installedFile': fcc,
            'latestUpdatedFile': fcc,
            'loadOrder': 0,
            'pathOnDisk': _pod,
            'status': 'Normal',
            'unmanaged': False,
            'users': ['local']}   # v6357：实测真品就是 ["local"]


def _mods_lib_sync(srv, pid, src_srv, fid=u''):
    """v6351（用户口径·方案 A）：把源服 ModsUserData/<gid>/library.json 里该 pid 的安装记录
       **合并**进目标服同名文件 —— CFCore 以这份记录判定「是否已安装 / 需不需要升级」：
       · 只换目录不改记录 ⇒ 起服时 `LogCFCore: Deleting mods dir ...` → `status invalid - Missing module`
         → `requires upgrade/downgrade (old -> new)` → **重新下载**（Los 2026-11-08 实测）
       · 合并粒度 = modId（各服 MOD 集合可能不同，如 Bob 是 ClubARK），**不整文件覆盖**"""
    if src_srv and src_srv == srv:
        return False, u'源服即目标服（跳过）'
    gid = MODS_GAMEID

    def _lib(s):
        return os.path.join(_srv_win64(s), 'ShooterGame', 'ModsUserData', gid, 'library.json')

    tp = _lib(srv)
    item = None
    if src_srv:
        sp = _lib(src_srv)
        if os.path.isfile(sp):
            try:
                sj = json.loads(_read_text(sp) or '{}')
            except Exception as e:
                return False, u'源 library.json 解析失败：%r' % (e,)
            for it in (sj.get('installedMods') or []):
                if str((it.get('details') or {}).get('iD') or '') == str(pid):
                    item = it
                    break
    if not item:
        # v6356（方案 A·最后一步）：源服没有该记录（或压根没源服）⇒ 用 CurseForge 元数据**自建**
        try:
            item = _mods_lib_entry_build(pid, fid)
        except Exception as _e_b:
            item = None
        if not item:
            return False, u'源记录里没有 pid=%s，CurseForge 也构造不出（检查 API Key / 网络）' % pid
    tj = {'installedMods': []}
    if os.path.isfile(tp):
        try:
            tj = json.loads(_read_text(tp) or '{}') or {'installedMods': []}
        except Exception:
            tj = {'installedMods': []}
    arr = tj.get('installedMods')
    if not isinstance(arr, list):
        arr = []
    out, done = [], False
    for it in arr:
        if str((it.get('details') or {}).get('iD') or '') == str(pid):
            out.append(item)
            done = True
        else:
            out.append(it)
    if not done:
        out.append(item)
    tj['installedMods'] = out
    try:
        d = os.path.dirname(tp)
        if not os.path.isdir(d):
            os.makedirs(d)
        tmp = tp + '.tmp_' + str(int(time.time()))
        with open(tmp, 'w', encoding='utf-8-sig', newline='') as f:
            f.write(json.dumps(tj, ensure_ascii=False))
        try:
            os.chmod(tp, _stat.S_IWRITE)
        except Exception:
            pass
        os.replace(tmp, tp)
        return True, u'pid %s 记录已同步（%s）' % (pid, (item.get('pathOnDisk') or u''))
    except Exception as e:
        return False, repr(e)[:200]


def _mods_deploy_run(user, batch_id, plans):
    """逐台执行：停服 → 备份旧目录 → 从批次缓存复制 → 校验 → 按原状态起服"""
    cfg = _srvctl_cfg()
    ts = time.strftime('%Y%m%d_%H%M%S')
    cache_base = os.path.join(_upd_cache_dir(), batch_id, 'mods')
    bak_root = os.path.join(_upd_cache_dir(), '_modbak', ts)
    # ① 预热：每个 <pid>_<fid> 只从源服取一次（用户口径：同批次共用缓存）
    pre = {}
    for p in plans:
        k = '%s_%s' % (p['pid'], p['want'])
        if k in pre:
            continue
        src = p.get('srcDir') or ''
        if not src:
            pre[k] = ''
            continue
        dst = os.path.join(cache_base, k)
        try:
            if not os.path.isdir(dst):
                if not os.path.isdir(cache_base):
                    os.makedirs(cache_base)
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns(MODS_LS_NAME))
            pre[k] = dst
        except Exception:
            _sexc('mods_prewarm')
            pre[k] = ''
    # ② 逐台执行
    for p in plans:
        srv, pid, want = p['srv'], p['pid'], p['want']
        key = '%s_%s' % (pid, want)
        # v6339（用户口径）：同服一条融合分发条（不再按版本分条）
        tkey = 'deploy|%s' % srv
        sname = (SERVER_THEMES.get(srv) or {}).get('name') or srv
        def _t(msg, pct, phase='run', err=''):
            try:
                _utask_put(tkey, srv, 'mods', user, label=u'MOD 分发 · ' + sname,
                           msg=msg, pct=pct, phase=phase,
                           steps=_steps_apply(STEP_5_DEPLOY, pct, phase, msg, 'deploy'),
                           err=err, srv_name=sname)
            except Exception:
                _sexc('mods_utask')
        src_cache = pre.get(key) or ''
        if not src_cache:
            _t(u'无可用源（该版本所有服都没有）—— 请先在系统管理配置 CurseForge API Key 后再下载',
               100, 'fail', u'no_source')
            continue
        was_run = False
        try:
            was_run = bool(_cfg_proc_start(srv, force=True))
        except Exception:
            was_run = False
        # 停服
        if was_run:
            _t(u'停服中…', 10)
            try:
                _srvctl_one(srv, 'kill', '', cfg)
            except Exception as e:
                _t(u'停服失败：%s' % e, 100, 'fail', repr(e))
                continue
            _t(u'已停服，等待进程退出', 20)
        # 备份旧目录
        tgt_base = _mods_dir_of(srv)
        bdir = os.path.join(bak_root, srv)
        backup = []
        ls_n, ls_b = 0, 0          # v6305：无感回收统计（开场视频）
        try:
            if os.path.isdir(tgt_base):
                for x in os.scandir(tgt_base):
                    if x.is_dir() and x.name.split('_')[0] == pid:
                        if not os.path.isdir(bdir):
                            os.makedirs(bdir)
                        _an_ls, _ab_ls = _mods_strip_ls(x.path)   # v6305：备份前先删开场
                        ls_n += _an_ls
                        ls_b += _ab_ls
                        shutil.move(x.path, os.path.join(bdir, x.name))
                        backup.append(x.name)
            _t(u'已备份 %d 个旧目录%s' % (len(backup),
                                          (u'，无感回收 %d 份开场（%.0f MB）'
                                           % (ls_n, ls_b / 1048576.0)) if ls_n else u''), 35)
        except Exception as e:
            _t(u'备份失败：%s' % e, 100, 'fail', repr(e))
            if was_run:
                try:
                    _srvctl_startq_new(user, [srv], 'moddeploy')
                except Exception:
                    pass
            continue
        # 复制
        _t(u'复制中…', 45)
        try:
            if not os.path.isdir(tgt_base):
                os.makedirs(tgt_base)
            dst = os.path.join(tgt_base, key)
            shutil.copytree(src_cache, dst)
        except Exception as e:
            _t(u'复制失败：%s（回滚）' % e, 100, 'fail', repr(e))
            try:
                for nm in backup:
                    shutil.move(os.path.join(bdir, nm), os.path.join(tgt_base, nm))
            except Exception:
                _sexc('mods_rollback')
            if was_run:
                try:
                    _srvctl_startq_new(user, [srv], 'moddeploy')
                except Exception:
                    pass
            continue
        # 校验
        _t(u'校验中…', 75)
        ok, detail = True, ''
        try:
            src_n = sum(len(fs) for _, _, fs in os.walk(src_cache))
            dst_n = sum(len(fs) for _, _, fs in os.walk(os.path.join(tgt_base, key)))
            ok = (src_n == dst_n and src_n > 0)
            detail = u'%d/%d 文件' % (dst_n, src_n)
        except Exception as e:
            ok, detail = False, repr(e)
        if not ok:
            _t(u'校验失败（%s）—— 已回滚' % detail, 100, 'fail', 'verify_failed')
            try:
                shutil.rmtree(os.path.join(tgt_base, key), ignore_errors=True)
                for nm in backup:
                    shutil.move(os.path.join(bdir, nm), os.path.join(tgt_base, nm))
            except Exception:
                _sexc('mods_rollback2')
            if was_run:
                try:
                    _srvctl_startq_new(user, [srv], 'moddeploy')
                except Exception:
                    pass
            continue
        # v6351（用户口径·方案 A）：同步 CFCore 安装记录
        #   否则起服时 ASA 会先删掉我们复制的目录、再自己重下一份（Los 2026-11-08 实测）
        try:
            _lib_ok, _lib_msg = _mods_lib_sync(srv, pid, p.get('srcSrv') or '', want)
        except Exception as _e_lib:
            _lib_ok, _lib_msg = False, repr(_e_lib)[:200]
        if _lib_ok:
            _t(u'已同步 CFCore 安装记录…', 82)
        else:
            _t(u'⚠ CFCore 安装记录未同步：%s' % _lib_msg, 82)
        # 起服
        _startErr = u''
        if was_run:
            _t(u'校验通过（%s），起服中…' % detail, 90)
            # v6339：起服失败自动重试（最多 3 次）
            _ok2, _startErr = _deploy_start_retry(srv, user, 'moddeploy', lambda t: _t(t, 90))
        _utask_put(tkey, srv, 'mods', user, label=u'MOD 分发 · ' + sname,
                   msg=((u'完成（%s，%s → %s）' % (detail, p.get('cur') or u'无', want))
                        + ((u' · 起服失败：' + _startErr) if _startErr else u'')),
                   pct=100, phase=('fail' if _startErr else 'done'),
                   steps=_steps_apply(STEP_5_DEPLOY, 100, 'done', '', 'deploy'), srv_name=sname,
                   meta={'pid': pid, 'fid': want, 'wasRunning': was_run, 'batch': batch_id})
    try:
        mods_status_cache_clear()
    except Exception:
        pass


# ===== v6307（用户口径）：AsaApi 官方包（GitHub ArkServerApi/AsaApi）=====
#   实测：https://api.github.com/repos/ArkServerApi/AsaApi/releases/latest → tag 2.1 / AsaApi_2.1.zip
#   包内结构（实测）：ArkApi/AsaApi.dll、ArkApi/Plugins/Permissions/{Permissions.dll,PluginInfo.json,config.json,...}
#   ==> Permissions 属于库包的一部分，分发库时一并更新（但仍单独展示版本）。
#   安全红线：Plugins/Permissions/config.json（用户配置）与 ArkDB.db*（玩家权限数据）**一律不动**。
ASA_API_GH_REPO = u'ArkServerApi/AsaApi'
ASA_HTTP_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
               '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
ASA_GH_TTL = 300.0
_ASA_GH = {'at': 0.0, 'data': None}
ASA_ZIP_SKIP_EXT = (u'.pdb', u'.lib')
ASA_ZIP_SKIP_DIR = (u'only for developers', u'lib', u'__macosx')
# 分发时**只更新**这些（包内相对路径 -> 相对 Win64 路径）
ASA_DEPLOY_FILES = (
    (u'ArkApi/AsaApi.dll', u'ArkApi\\AsaApi.dll', u'AsaApi', u'lib'),
    (u'ArkApi/Plugins/Permissions/Permissions.dll',
     u'ArkApi\\Plugins\\Permissions\\Permissions.dll', u'Permissions', u'plugin'),
    (u'ArkApi/Plugins/Permissions/PluginInfo.json',
     u'ArkApi\\Plugins\\Permissions\\PluginInfo.json', u'Permissions', u'plugin'),
)


def _asa_pkg_root():
    return os.path.join(_upd_cache_dir(), '_apipkg')


def _asa_pkg_vers():
    root = _asa_pkg_root()
    out = []
    try:
        if os.path.isdir(root):
            for x in os.scandir(root):
                if x.is_dir() and os.path.isfile(os.path.join(x.path, 'ArkApi', 'AsaApi.dll')):
                    out.append(x.name)
    except Exception:
        _sexc('asa_pkg_vers')
    out.sort()
    return out


def _asa_pkg_cur():
    v = _asa_pkg_vers()
    return v[-1] if v else u''


def _md5_of(p):
    try:
        if not os.path.isfile(p):
            return u''
        h = _hashlib.md5()
        with open(p, 'rb') as f:
            while True:
                b = f.read(1024 * 1024)
                if not b:
                    break
                h.update(b)
        return h.hexdigest()
    except Exception:
        return u''


def _gh_latest_asaapi():
    """GitHub 最新 release（缓存 5 分钟）"""
    now = time.time()
    if _ASA_GH['data'] is not None and (now - _ASA_GH['at']) < ASA_GH_TTL:
        return _ASA_GH['data']
    res = {'ok': False, 'error': u'unknown'}
    try:
        import urllib.request as _ur
        req = _ur.Request('https://api.github.com/repos/%s/releases/latest' % ASA_API_GH_REPO,
                          headers={'User-Agent': ASA_HTTP_UA, 'Accept': 'application/vnd.github+json'})
        with _ur.urlopen(req, timeout=25) as r:
            j = json.loads(r.read().decode('utf-8', 'replace'))
        res = {'ok': True, 'tag': str(j.get('tag_name') or ''),
               'published': str(j.get('published_at') or ''),
               'htmlUrl': str(j.get('html_url') or ''),
               'assets': [{'name': a.get('name'), 'size': a.get('size'),
                           'url': a.get('browser_download_url')} for a in (j.get('assets') or [])]}
    except Exception as e:
        res = {'ok': False, 'error': repr(e)[:300]}
    _ASA_GH['at'] = now
    _ASA_GH['data'] = res
    return res


def _asa_pkg_download(user):
    """下载最新 AsaApi 官方包到 _upd_cache/_apipkg/<tag>/（任务总线可见）"""
    import urllib.request as _ur
    key = u'apipkg|latest'
    # v6374（用户口径）：卡片条只表示下载 —— 同样下发 meta.items（官方包一条）
    _its = [{'key': u'asaapi', 'fid': '', 'name': u'AsaApi 官方包', 'bytes': 0,
             'state': 'wait', 'pct': 0, 'msg': u'等待中'}]

    def _t(msg, pct, phase='run', err=''):
        try:
            if phase == 'ok':
                _its[0].update({'state': 'ok', 'pct': 100, 'msg': msg})
            elif phase == 'fail':
                _its[0].update({'state': 'fail', 'msg': (err or msg)})
        except Exception:
            pass
        try:
            _utask_put(key, '', 'update', user, label=u'更新本地包',
                       msg=msg, pct=pct, phase=phase,
                       steps=_steps_apply(STEP_4_PKG, pct, phase, msg, 'pkg'), err=err,
                       meta={'items': _its},
                       srv_name=u'AsaApi')
        except Exception:
            _sexc('asa_pkg_utask')

    _t(u'查询 GitHub 最新版本…', 3)
    rel = _gh_latest_asaapi()
    if not rel.get('ok'):
        _t(u'查询 GitHub 失败', 100, 'fail', rel.get('error') or u'github_error')
        return {'ok': False, 'error': rel.get('error') or u'查询 GitHub 失败'}
    tag = rel.get('tag') or u''
    z = None
    for a in (rel.get('assets') or []):
        if str(a.get('name') or '').lower().endswith(u'.zip'):
            z = a
            break
    if not tag or not z:
        _t(u'该 release 没有 zip 资产', 100, 'fail', u'no_zip_asset')
        return {'ok': False, 'error': u'release %s 无 zip 资产' % (tag or u'?')}
    dst = os.path.join(_asa_pkg_root(), tag)
    if os.path.isfile(os.path.join(dst, 'ArkApi', 'AsaApi.dll')):
        _t(u'本地包 %s 已存在，跳过' % tag, 100, 'ok')
        return {'ok': True, 'ver': tag, 'skipped': True, 'dir': dst}
    tmpd = os.path.join(_upd_cache_dir(), '_apipkg_dl')
    zpath = os.path.join(tmpd, str(z.get('name') or 'asaapi.zip'))
    try:
        if not os.path.isdir(tmpd):
            os.makedirs(tmpd)
    except Exception:
        _sexc('asa_pkg_mkdl')
    _t(u'下载 %s（%.1f MB）…' % (z.get('name'), (int(z.get('size') or 0)) / 1048576.0), 10)
    try:
        req = _ur.Request(str(z.get('url')), headers={'User-Agent': ASA_HTTP_UA})
        total = int(z.get('size') or 0)
        got = 0
        with _ur.urlopen(req, timeout=180) as r, open(zpath, 'wb') as f:
            while True:
                b = r.read(256 * 1024)
                if not b:
                    break
                f.write(b)
                got += len(b)
                if total > 0:
                    try:
                        _its[0].update({'state': 'dl',
                                        'pct': int(round(100.0 * got / total)),
                                        'msg': u'下载中 %.1f / %.1f MB'
                                               % (got / 1048576.0, total / 1048576.0)})
                    except Exception:
                        pass
                    _t(u'下载中 %.1f / %.1f MB' % (got / 1048576.0, total / 1048576.0),
                       10 + int(55.0 * got / total))
    except Exception as e:
        _t(u'下载失败', 100, 'fail', repr(e)[:300])
        return {'ok': False, 'error': repr(e)[:300]}
    try:
        _its[0].update({'state': 'unzip', 'pct': 100, 'msg': u'解压中…'})
    except Exception:
        pass
    _t(u'解压中…', 70)
    n_ok, n_skip = 0, 0
    try:
        import zipfile
        if not os.path.isdir(dst):
            os.makedirs(dst)
        with zipfile.ZipFile(zpath) as zf:
            for nm in zf.namelist():
                low = nm.lower()
                if low.endswith(u'/'):
                    continue
                if any(low.endswith(e) for e in ASA_ZIP_SKIP_EXT):
                    n_skip += 1
                    continue
                if any((u'/' + d + u'/') in (u'/' + low) for d in ASA_ZIP_SKIP_DIR):
                    n_skip += 1
                    continue
                tgt = os.path.join(dst, nm.replace(u'/', os.sep))
                try:
                    d2 = os.path.dirname(tgt)
                    if d2 and not os.path.isdir(d2):
                        os.makedirs(d2)
                    with zf.open(nm) as src, open(tgt, 'wb') as out:
                        shutil.copyfileobj(src, out)
                    n_ok += 1
                except Exception:
                    _sexc('asa_pkg_unzip_one')
    except Exception as e:
        _t(u'解压失败', 100, 'fail', repr(e)[:300])
        return {'ok': False, 'error': repr(e)[:300]}
    _t(u'校验入库…', 90)
    dll = os.path.join(dst, 'ArkApi', 'AsaApi.dll')
    perm = os.path.join(dst, 'ArkApi', 'Plugins', 'Permissions', 'Permissions.dll')
    if not os.path.isfile(dll):
        _t(u'包内缺少 ArkApi/AsaApi.dll', 100, 'fail', u'no_dll')
        return {'ok': False, 'error': u'包内缺少 ArkApi/AsaApi.dll'}
    try:
        os.remove(zpath)
    except Exception:
        pass
    try:
        mods_status_cache_clear()
    except Exception:
        pass
    sz = os.path.getsize(dll)
    perm_sz = (os.path.getsize(perm) if os.path.isfile(perm) else 0)
    _t(u'完成：v%s（AsaApi.dll %.2f MB%s）' %
       (tag, sz / 1048576.0, (u'，Permissions %.2f MB' % (perm_sz / 1048576.0)) if perm_sz else u''),
       100, 'ok')
    return {'ok': True, 'ver': tag, 'dir': dst, 'files': n_ok, 'skipped': n_skip,
            'dllSize': sz, 'permSize': perm_sz}


# v6312（用户口径）：自研插件源改用 UNC 网络地址（后端服务器上的 Z: 映射不稳定）
SOK_SRC_UNC = r'\\Tnas\public\ServerOpsKitAPI'


def _asa_targets():
    """目标文件表：本地包（库 + Permissions）+ 自研源插件（\\\\Tnas\\public\\ServerOpsKitAPI/*.dll）"""
    ver = _asa_pkg_cur()
    files = []
    if ver:
        pdir = os.path.join(_asa_pkg_root(), ver)
        for rel, winrel, nm, kind in ASA_DEPLOY_FILES:
            src = os.path.join(pdir, rel.replace(u'/', os.sep))
            if os.path.isfile(src):
                files.append({'rel': winrel, 'src': src, 'md5': _md5_of(src),
                              'size': os.path.getsize(src), 'kind': kind, 'name': nm})
    try:
        zdir = SOK_SRC_UNC
        if os.path.isdir(zdir):
            _ents = list(os.scandir(zdir))
            _dlls = [y for y in _ents if y.is_file() and y.name.lower().endswith(u'.dll')]
            _pis = [y for y in _ents if y.is_file() and y.name.lower() == u'plugininfo.json']
            for x in _dlls:
                nm = os.path.splitext(x.name)[0]
                files.append({'rel': u'ArkApi\\Plugins\\%s\\%s' % (nm, x.name),
                              'src': x.path, 'md5': _md5_of(x.path),
                              'size': os.path.getsize(x.path), 'kind': u'plugin', 'name': nm})
            # v6342（用户口径：最新 SOK 是 0.81 而 Bob 显示 0.8）：
            #   版本号来自 PluginInfo.json。原实现只分发 *.dll ⇒ dll 已是最新但 PluginInfo 永远不更新
            #   ⇒ 界面永远显示旧版本（且「无需分发」）。此处把同级 PluginInfo.json 一并纳入。
            #   仅当源目录只有**单个** dll 时才配对，避免多插件时错配。
            if len(_dlls) == 1 and _pis:
                nm = os.path.splitext(_dlls[0].name)[0]
                for p in _pis:
                    files.append({'rel': u'ArkApi\\Plugins\\%s\\%s' % (nm, p.name),
                                  'src': p.path, 'md5': _md5_of(p.path),
                                  'size': os.path.getsize(p.path),
                                  'kind': u'plugin', 'name': nm})
    except Exception:
        _sexc('asa_plugin_src')
    return {'ver': ver, 'vers': _asa_pkg_vers(), 'files': files,
            'latest': _gh_latest_asaapi()}


# ===== v6310（用户口径）：清理备份统一挪到 NAS；v6312：改用 UNC 网络地址 =====
ASA_BAK_UNC = r'\\Tnas\public\备份\ASA'
ASA_BAK_FALLBACK = True


def _asa_bak_root(kind):
    """返回 (备份目录, 来源标记)。优先 \\\\Tnas\\public\\备份\\ASA/<kind>/<ts>，不可写则回退 _upd_cache/_bk_<kind>/<ts>"""
    ts = time.strftime('%Y%m%d_%H%M%S')
    try:
        base = os.path.join(ASA_BAK_UNC, kind)
        if not os.path.isdir(base):
            os.makedirs(base)
        _t = os.path.join(base, u'.wtest_' + ts)
        with open(_t, 'w') as _f:
            _f.write('1')
        os.remove(_t)
        return os.path.join(base, ts), u'UNC'
    except Exception:
        _sexc('asa_bak_unc')
        return os.path.join(_upd_cache_dir(), '_%s_bak' % kind, ts), u'local'


def _asa_mv(src, dst):
    """跨盘安全搬移：同盘 shutil.move；跨盘 复制 -> 校验存在 -> 删源"""
    d1 = os.path.splitdrive(os.path.abspath(src))[0].lower()
    d2 = os.path.splitdrive(os.path.abspath(dst))[0].lower()
    if os.path.isdir(src):
        if d1 == d2 and d1:
            shutil.move(src, dst)
        else:
            shutil.copytree(src, dst)
            if not os.path.isdir(dst):
                raise IOError('copy failed: %s' % dst)
            shutil.rmtree(src, ignore_errors=True)
    else:
        if d1 == d2 and d1:
            shutil.move(src, dst)
        else:
            shutil.copy2(src, dst)
            if not os.path.isfile(dst):
                raise IOError('copy failed: %s' % dst)
            try:
                os.remove(src)
            except Exception:
                pass


# ===== v6309（用户口径）：MOD 多余清理（不在策略内的 MOD）=====
def _mods_cleanup_plan():
    """MOD 多余清理计划（只读）：[{srv, pid, fid, dir, path, size, name}]
    只针对 servers[srv].extra（实际存在但不在策略 expect 内），基准/策略内一律不动。"""
    st = mods_status()
    out = []
    for srv, info in (st.get('servers') or {}).items():
        ex = info.get('extra') or []
        if not ex:
            continue
        for it in (info.get('items') or []):
            if it.get('pid') not in ex:
                continue
            p = os.path.join(_mods_dir_of(srv), it.get('dir') or u'')
            if not os.path.isdir(p):
                continue
            out.append({'srv': srv, 'pid': it.get('pid'), 'fid': it.get('fid'),
                        'dir': it.get('dir'), 'path': p,
                        'size': int(it.get('size') or 0),
                        'name': it.get('name') or it.get('pid')})
    return out


def _mods_cleanup_run(user, plans):
    """安全清理：把多余 MOD 目录 **move** 到 _upd_cache/_modcleanbak/<ts>/<srv>/（可随时移回）"""
    ts = time.strftime('%Y%m%d_%H%M%S')
    bak_root, bak_src = _asa_bak_root(u'mods')
    # v6324（用户口径）：key 不带时间戳 —— 同一功能复用同一条任务条
    key = u'modcleanup|latest'
    n = max(1, len(plans))

    def _t(msg, pct, phase='run', err=''):
        try:
            _utask_put(key, '', 'update', user, label=u'安全清理 · 多余 MOD',
                       msg=msg, pct=pct, phase=phase,
                       steps=_steps_apply(STEP_3_CLEAN, pct, phase, msg, 'clean'), err=err,
                       srv_name=u'%d 个目录' % n)
        except Exception:
            _sexc('mods_cleanup_utask')
    _t(u'准备清理 %d 个多余 MOD 目录…' % n, 5)
    ok_n, bad_n, tot = 0, 0, 0
    moved = []
    i = 0
    for p in plans:
        i += 1
        tdir = os.path.join(bak_root, p['srv'])
        try:
            _t(u'第 %d/%d：%s · %s' % (i, n, p['srv'], p['dir']), 5 + int(85.0 * i / n))
            if not os.path.isdir(tdir):
                os.makedirs(tdir)
            dst = os.path.join(tdir, p['dir'])
            if os.path.exists(dst):
                dst = dst + u'_' + str(int(time.time()))
            _asa_mv(p['path'], dst)
            ok_n += 1
            tot += int(p.get('size') or 0)
            moved.append({'srv': p['srv'], 'dir': p['dir'], 'to': dst})
        except Exception:
            _sexc('mods_cleanup_move')
            bad_n += 1
    try:
        _admin_log('MODS cleanup-extra by %s ok=%d bad=%d bytes=%d bak=%s'
                   % (user, ok_n, bad_n, tot, bak_root))
    except Exception:
        pass
    try:
        mods_status_cache_clear()
    except Exception:
        pass
    try:
        if bad_n:
            _t(u'完成：移入备份 %d 个，失败 %d 个' % (ok_n, bad_n), 100, 'fail', u'部分失败')
        else:
            _t(u'完成：已把 %d 个多余 MOD 移入备份（%.1f MB）→ %s'
               % (ok_n, tot / 1048576.0, bak_root), 100, 'ok')
    except Exception:
        pass
    return {'ok': ok_n, 'bad': bad_n, 'bytes': tot, 'backupDir': bak_root, 'moved': moved[:60]}


def _api_deploy_plan3(servers):
    """API 分发差异表：只列「当前 md5 != 目标 md5」的项（已最新自动跳过）"""
    tgt = _asa_targets()
    out = []
    for srv in servers:
        win = _srv_win64(srv)
        for f in tgt['files']:
            p = os.path.join(win, f['rel'])
            cur = _md5_of(p) if os.path.isfile(p) else u''
            if cur and cur == f['md5']:
                continue
            out.append({'srv': srv, 'name': f['name'], 'kind': f['kind'], 'rel': f['rel'],
                        'src': f['src'], 'wantMd5': f['md5'], 'curMd5': cur,
                        'size': f['size'], 'ver': tgt['ver'],
                        'reason': (u'missing' if not cur else u'old'),
                        'ok': bool(f['md5'])})
    return out


def _api_need_by_srv(tgt=None):
    """v6349（用户口径）：每服是否需要分发 **插件** —— 与 _api_deploy_plan3 同源（比 size，不读 md5）
       · 原前端拿「插件版本 = 台数最多的那个」当基准 ⇒ Bob 升到 0.82 后，10 台旧 0.7 成多数，
         Bob 反被判成「待升级」（v6348 紫点误报）。此处以后端目标文件表为准，前端直接取结果。
       · 只看 kind == 'plugin' 的文件；库（AsaApi.dll, kind='lib'）落后由 libNeedsUpgrade 单独表达，不污染 TAB 点。"""
    _t0 = tgt if tgt else _asa_targets()
    out = {}
    # v6396（用户口径「附件还是没显示 api 待升级的点」）：
    #   Bob 的库是 2.1、本地包已 2.11，却因这里只比 plugin 而被判「无需升级」⇒ TAB 无紫点。
    #   v6349 当年排除 lib 是为规避「前端按多数派判版本」的误报（Bob 升了反被报紫点）；
    #   现在判据已换成后端目标文件表（本地包 / 自研源的真实 dll size），不存在多数派问题 ——
    #   库 size 与本地包不一致就是真落后，一并纳入。
    #   防护：size 为 0（文件缺失 / 读不到）的条目跳过，避免「目标 size=0 ⇒ 全服误报」。
    fl = [f for f in (_t0.get('files') or [])
          if str(f.get('kind') or '') in ('plugin', 'lib')
          and int(f.get('size') or 0) > 0]
    for srv in SERVERS.keys():
        win = _srv_win64(srv)
        need = False
        for f in fl:
            p = os.path.join(win, f['rel'])
            if not os.path.isfile(p):
                need = True
                break
            try:
                if int(os.path.getsize(p)) != int(f.get('size') or 0):
                    need = True
                    break
            except Exception:
                pass
        out[srv] = need
    return out


def _sok_ver_key(v):
    """版本等价键：只留数字并去掉尾部 0。
       '0.84' -> '084'；'0.8.4' -> '084'（等价）；'0.7' -> '07'；'0.7.0' -> '07'（等价）"""
    try:
        s = re.sub(r'[^0-9]', '', str(v or ''))
        return (s.rstrip('0') or '0')
    except Exception:
        return str(v or '')


def _sok_ver3(v):
    """把 PluginInfo 的版本规范成 SOK config 惯用的三段式：
       '0.84' -> '0.8.4'；'0.7' -> '0.7.0'；'0.8.4' 原样；'1' -> '1.0.0'"""
    s = str(v or '').strip()
    if not s:
        return ''
    parts = [p for p in s.split('.') if p != '']
    try:
        if len(parts) >= 3:
            return s
        if len(parts) == 2:
            _mj, _mn = parts[0], parts[1]
            if len(_mn) >= 2:
                return u'%s.%s.%s' % (_mj, _mn[0], _mn[1:])
            return u'%s.%s.0' % (_mj, _mn)
        if len(parts) == 1:
            return u'%s.0.0' % parts[0]
    except Exception:
        pass
    return s


def _sync_sok_cfg_ver(srv, items):
    """v6400（用户口径「分发时 config.json 的 version 也要跟着改，不然会误判」）：
       把该服 SOK 的 config.json 里 `version` 同步为本次分发目标的 PluginInfo Version。
       根因：分发只替换 dll + PluginInfo.json，SOK 启动时**不会**回写 config 的 version
             ⇒ 插件自报仍旧版（实测 Bob 卡在 0.8.2，而 dll/PluginInfo 都已是 0.84）。
       ⚠ 只改 version 一个键：dino_data_dir / auto_parse_server_id 等每服个性化配置原样保留，
         绝不整份覆盖（源目录里也没有 config.json）。
       返回 True=已一致或已改正 / False=无法处理（不影响分发主流程）。"""
    want = ''
    for it in (items or []):
        try:
            if str(it.get('rel') or '').lower().endswith(u'plugininfo.json') \
                    and 'serveropskitapi' in str(it.get('rel') or '').lower():
                j = json.loads(_read_text(it.get('src') or '') or '{}')
                want = str((j or {}).get('Version') or '')
                break
        except Exception:
            want = ''
    if not want:
        return False
    # v6442（用户口径「version 应该写成 0.8.4」）：PluginInfo 是两段（0.84），
    #   而 SOK config 惯用三段（0.8.4）。这里先规范化，再做**等价判定** ——
    #   `0.84` 与 `0.8.4` 视为同一版本，不改写（避免把已有的 0.8.4 改成 0.84）。
    want = _sok_ver3(want)
    cfgp = os.path.join(_srv_win64(srv), 'ArkApi', 'Plugins', 'ServerOpsKitAPI', 'config.json')
    if not os.path.isfile(cfgp):
        return False
    try:
        doc = json.loads(_read_text(cfgp) or '{}')
    except Exception:
        return False
    if not isinstance(doc, dict):
        return False
    _cur_ver = str(doc.get('version') or '')
    # v6443（用户口径「config 里也不对：Sco/Rag 是 0.84，Bob/Cen/Los 是 0.8.4」）：
    #   原「等价即返回」会把 '0.84' 一直留着 ⇒ 格式长期不一致。
    #   改为**仅字符串完全相同**才跳过；写法不规范的一律统一成三段（'0.84' -> '0.8.4'）。
    if _cur_ver == want:
        return True
    doc['version'] = want
    try:
        os.chmod(cfgp, _stat.S_IWRITE)
    except Exception:
        pass
    tmp = cfgp + '.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        os.replace(tmp, cfgp)
        return True
    except Exception:
        try:
            os.remove(tmp)
        except Exception:
            pass
        return False


def _api_deploy_run2(user, plans):
    """逐台：记状态 -> 停服 -> 备份 -> 复制 -> 校验 -> 失败回滚 -> 按原状态起服（任务总线）"""
    cfg = _srvctl_cfg()
    ts = time.strftime('%Y%m%d_%H%M%S')
    bak_root = os.path.join(_upd_cache_dir(), '_apibak', ts)
    bysrv = {}
    for p in plans:
        bysrv.setdefault(p['srv'], []).append(p)
    for srv, items in bysrv.items():
        # v6339（用户口径「每个服一条融合分发条」）：key 不再带时间戳
        key = u'deploy|%s' % srv
        sname = (SERVER_THEMES.get(srv) or {}).get('name') or srv
        def _t(msg, pct, phase='run', err='', _k=key, _s=srv, _n=sname):
            try:
                _utask_put(_k, _s, 'update', user, label=u'API 分发 · ' + _n,
                           msg=msg, pct=pct, phase=phase,
                           steps=_steps_apply(STEP_5_DEPLOY, pct, phase, msg, 'deploy'),
                           err=err, srv_name=_n)
            except Exception:
                _sexc('api_deploy_utask')

        was_run = False
        try:
            was_run = bool(_cfg_proc_start(srv, force=True))
        except Exception:
            was_run = False
        if was_run:
            _t(u'停服中…', 8)
            try:
                _srvctl_one(srv, 'kill', '', cfg)
            except Exception as e:
                _t(u'停服失败：%s' % e, 100, 'fail', repr(e)[:400])
                continue
            _t(u'已停服', 18)
        bdir = os.path.join(bak_root, srv)
        try:
            for it in items:
                sp = os.path.join(_srv_win64(srv), it['rel'])
                if os.path.isfile(sp):
                    bp = os.path.join(bdir, it['rel'])
                    d2 = os.path.dirname(bp)
                    if d2 and not os.path.isdir(d2):
                        os.makedirs(d2)
                    shutil.copy2(sp, bp)
            _t(u'已备份 %d 项' % len(items), 32)
        except Exception as e:
            _t(u'备份失败：%s' % e, 100, 'fail', repr(e)[:400])
            if was_run:
                try:
                    _srvctl_startq_new(user, [srv], 'apideploy')
                except Exception:
                    pass
            continue
        _t(u'复制中…', 48)
        err = u''
        _stage = u''   # v6338：失败阶段（复制/校验），供分步圆点定位
        try:
            for it in items:
                dp = os.path.join(_srv_win64(srv), it['rel'])
                d2 = os.path.dirname(dp)
                if d2 and not os.path.isdir(d2):
                    os.makedirs(d2)
                try:
                    os.chmod(dp, _stat.S_IWRITE)
                except Exception:
                    pass
                shutil.copy2(it['src'], dp)
        except Exception as e:
            err = repr(e)[:400]
            _stage = u'复制'
        if not err:
            _t(u'校验中…', 74)
            bad = []
            for it in items:
                dp = os.path.join(_srv_win64(srv), it['rel'])
                if _md5_of(dp) != it['wantMd5']:
                    bad.append(it['name'])
            if bad:
                err = u'md5 不一致：' + u'、'.join(bad)
                _stage = u'校验'
        if not err:
            # v6400：dll/PluginInfo 已就位后，把 config.json 的 version 也同步过去，
            #   否则插件自报仍是旧版（用户实测 Bob 卡在 0.8.2）。失败不影响分发结果。
            try:
                _sync_sok_cfg_ver(srv, items)
            except Exception:
                _sexc('api_sync_cfg_ver')
        if err:
            try:
                for it in items:
                    dp = os.path.join(_srv_win64(srv), it['rel'])
                    bp = os.path.join(bdir, it['rel'])
                    if os.path.isfile(bp):
                        try:
                            os.chmod(dp, _stat.S_IWRITE)
                        except Exception:
                            pass
                        shutil.copy2(bp, dp)
                    elif not it.get('curMd5'):
                        try:
                            os.remove(dp)
                        except Exception:
                            pass
            except Exception:
                _sexc('api_rollback')
            _t(u'%s失败（%s）—— 已回滚' % (_stage or u'校验', err), 100, 'fail', err)
            if was_run:
                try:
                    _srvctl_startq_new(user, [srv], 'apideploy')
                except Exception:
                    pass
            continue
        _startErr = u''
        if was_run:
            _t(u'校验通过，起服中…', 90)
            # v6339：起服失败自动重试（最多 3 次）—— 原实现丢给启动队列后不管结果
            _ok2, _startErr = _deploy_start_retry(srv, user, 'apideploy', lambda t: _t(t, 90))
        try:
            _admin_log('API deploy srv=%s files=%s bak=%s' %
                       (srv, u','.join(x['name'] for x in items), bdir))
        except Exception:
            pass
        _utask_put(key, srv, 'update', user, label=u'API 分发 · ' + sname,
                   msg=(u'完成（更新 %d 项）' % len(items))
                       + ((u' · 起服失败：' + _startErr) if _startErr else u''),
                   pct=100, phase=('fail' if _startErr else 'ok'),
                   steps=_steps_apply(STEP_5_DEPLOY, 100, 'ok', '', 'deploy'), srv_name=sname,
                   meta={'files': [x['name'] for x in items], 'wasRunning': was_run,
                         'bak': bdir})
    try:
        mods_status_cache_clear()
    except Exception:
        pass


# ===== v6306（用户口径）：「多余插件」安全清理 =====
def _api_cleanup_plan():
    """多余插件清理计划（纯只读）：[{srv, name, path, bytes, disabled:[{dir,path,bytes}]}]
    只针对 api_status().extras（不在必需清单内的插件），必需插件绝不入列。"""
    st = api_status()
    ex = list(st.get('extras') or [])
    out = []
    if not ex:
        return out
    for srv in SERVERS.keys():
        win = _srv_win64(srv)
        dp = os.path.join(win, '_disabled_plugins')
        for nm in ex:
            p = os.path.join(win, 'ArkApi', 'Plugins', nm)
            dis = []
            try:
                if os.path.isdir(dp):
                    for x in os.scandir(dp):
                        if not x.is_dir():
                            continue
                        k = x.name.split('_')[0] if '_' in x.name else x.name
                        if k == nm:
                            dis.append({'dir': x.name, 'path': x.path, 'bytes': _dir_size(x.path)})
            except Exception:
                _sexc('api_cleanup_disabled')
            if (not os.path.isdir(p)) and (not dis):
                continue
            out.append({'srv': srv, 'name': nm, 'path': p,
                        'bytes': (_dir_size(p) if os.path.isdir(p) else 0),
                        'disabled': dis})
    return out


def _api_cleanup_run(user, plans):
    """安全清理：把插件目录 **move** 到 _upd_cache/_pluginbak/<ts>/<srv>/（同盘秒级，可随时移回）"""
    ts = time.strftime('%Y%m%d_%H%M%S')
    bak_root, bak_src = _asa_bak_root(u'plugins')
    ok_n, bad_n, tot = 0, 0, 0
    moved = []
    # v6307（用户口径）：接入任务总线 —— 单条汇总，与「存档后终止」多台汇总条同款
    # v6324（用户口径）：key 不带时间戳 —— 同一功能复用同一条任务条
    _ckey = u'apicleanup|latest'
    _cn = max(1, len(plans))

    def _ct(msg, pct, phase='run', err=''):
        try:
            _utask_put(_ckey, '', 'update', user, label=u'安全清理 · 多余插件',
                       msg=msg, pct=pct, phase=phase,
                       steps=_steps_apply(STEP_3_CLEAN, pct, phase, msg, 'clean'), err=err,
                       srv_name=u'%d 项' % _cn)
        except Exception:
            _sexc('api_cleanup_utask')
    _ct(u'准备清理 %d 项…' % _cn, 5)
    _ci = 0

    for p in plans:
        _ci += 1
        try:
            _ct(u'第 %d/%d 项：%s · %s' % (_ci, _cn, p.get('srv') or u'', p.get('name') or u''),
                5 + int(85.0 * _ci / _cn))
        except Exception:
            pass
        tdir = os.path.join(bak_root, p['srv'])
        try:
            if not os.path.isdir(tdir):
                os.makedirs(tdir)
            srcs = []
            if os.path.isdir(p['path']):
                srcs.append((p['path'], p['name'], int(p.get('bytes') or 0)))
            for d in (p.get('disabled') or []):
                srcs.append((d['path'], d['dir'], int(d.get('bytes') or 0)))
            for sp, nm, sz in srcs:
                dst = os.path.join(tdir, nm)
                if os.path.exists(dst):
                    dst = dst + '_' + str(int(time.time()))
                _asa_mv(sp, dst)
                ok_n += 1
                tot += sz
                moved.append({'srv': p['srv'], 'name': nm, 'to': dst})
        except Exception:
            _sexc('api_cleanup_move')
            bad_n += 1
    try:
        _admin_log('API cleanup-extras by %s ok=%d bad=%d bytes=%d bak=%s'
                   % (user, ok_n, bad_n, tot, bak_root))
    except Exception:
        pass
    try:
        if bad_n:
            _ct(u'完成：移入备份 %d 项，失败 %d 项' % (ok_n, bad_n), 100, 'fail',
                u'部分失败，详见 _pluginbak')
        else:
            _ct(u'完成：已把 %d 个目录移入备份（%.1f MB）→ %s'
                % (ok_n, tot / 1048576.0, bak_root), 100, 'ok')
    except Exception:
        pass
    try:
        mods_status_cache_clear()
    except Exception:
        pass
    return {'ok': ok_n, 'bad': bad_n, 'bytes': tot,
            'backupDir': bak_root, 'moved': moved[:60]}


def mods_status_cache_clear():
    _MODS_CACHE['at'] = 0.0
    _MODS_CACHE['data'] = None
    _API_CACHE['at'] = 0.0
    _API_CACHE['data'] = None


def _api_deploy_plan(servers):
    """API 分发计划（当前实现：库 + Permissions；ServerOpsKitAPI 取本地源）"""
    st = api_status()
    out = []
    lib0 = None
    for srv in servers:
        lp = (st.get('lib') or {}).get(srv) or {}
        out.append({'srv': srv, 'libSize': lp.get('dllSize') or 0,
                    'plugin': 'ServerOpsKitAPI',
                    'pluginInstalled': bool((st.get('plugins') or {}).get('ServerOpsKitAPI', {})
                                            .get('servers') and srv in
                                            (st['plugins']['ServerOpsKitAPI']['servers'] or []))})
    return out


def _upd_ver_info(picked=None):
    """v6228（§16.3）：新版本(官方) vs 旧版本(各服实跑) -> verKind
       · 新版本：优先 `_news_official_version()`（资讯广场 patch_pc 的 Server 最大版本号），
                 取不到则回退 ASA `OfficialServerVersion` 众数
       · 旧版本：各服 `ServerVersion`（实际运行版本），多台不一致时取**最旧**
       · 任一缺失 => kind='unknown'（前端浮窗提示人工确认）"""
    out = {'kind': 'unknown', 'from': '', 'to': '', 'src': '', 'err': ''}
    _to, _from = '', ''
    try:
        try:
            # v6231：改走权威取数链（官方 CDN ini 主源），不再只用资讯广场
            _oe = _official_version_ex()
            _to = str(_oe.get('ver') or '')
            out['src'] = str(_oe.get('src') or '')
        except Exception:
            _to = ''
        try:
            _cfg = _srvctl_cfg()
            if _cfg.get('token'):
                _code, _text = _asa_http('GET', _cfg['base'] + '/server-status',
                                         _cfg['token'], None,
                                         timeout=_cfg['timeout'], verify=_cfg['verify'])
                if 200 <= _code < 300:
                    _doc = json.loads(_text) or {}
                    _rev = {}
                    for _k, _v in SERVER_THEMES.items():
                        _rev[(_v or {}).get('name') or ''] = _k
                    _vs, _offs = [], []
                    for _it in (_doc.get('servers') or []):
                        _pn = str(_it.get('ProfileName') or '')
                        _sid = _pn if _pn in SERVERS else _rev.get(_pn, '')
                        if picked and _sid not in picked:
                            continue
                        _sv = str(_it.get('ServerVersion') or '')
                        if _sv:
                            _vs.append(_sv)
                        _ov = str(_it.get('OfficialServerVersion') or '')
                        if _ov:
                            _offs.append(_ov)
                    if not _to and _offs:
                        # v6231：**取最大版本**，不能取众数 —— 实测 11 台里手点过验证的
                        #   Gen 是 v97.5，其余 10 台仍缓存 v96.9；众数必然是旧的 96.9。
                        _cand = [(x, _ver_seg(_extract_ver(x))) for x in _offs]
                        _cand = [t for t in _cand if t[1]]
                        if _cand:
                            _cand.sort(key=lambda t: (t[1][0], _vnum(t[1][1])))
                            _to = _cand[-1][0]
                            out['src'] = 'asam'
                    if _vs:
                        _seg = [(x, _ver_seg(_extract_ver(x))) for x in _vs]
                        _seg = [t for t in _seg if t[1]]
                        if _seg:
                            _seg.sort(key=lambda t: (t[1][0], _vnum(t[1][1])))
                            _from = _seg[0][0]
        except Exception:
            pass
        out['from'] = _extract_ver(_from) or _from
        out['to'] = _extract_ver(_to) or _to
        out['kind'] = _ver_kind(out['from'], out['to'])
    except Exception as e:
        out['err'] = repr(e)
    return out


def _upd_dry_default():
    """v6233（用户口径 2026-11-07）：服务器更新「默认预演」开关 —— server_config.json 的 update_dry。
       为真时 `/api/update/apply` **一律强制 dry**（只出清单，不复制文件/不改 acf/不停服）。
       缺省视为 True（与接口本身 dry 默认 true 一致：宁可不跑，不可误跑）。"""
    try:
        d = _srv_cfg_read() or {}
        v = d.get('update_dry')
        if v is None:
            return True
        return str(v).lower() in ('1', 'true', 'yes', 'on')
    except Exception:
        return True


# ===== v6237（B1）：汉化补丁（Google Drive 源）—— 只读探测 =====
# 方案 §3 / §14。要点：
#   · 云端版本只认 zip 文件名里的 V<n>.<n>；Drive embeddedfolderview 的 mtime 是 "1:08 am" 无日期，不参与比较（§14 A4）
#   · 变体匹配用规范化比较，防作者改名（§14 B4）
#   · 各服扫描用 os.scandir 一次拿全（§14 B6）
#   · sidecar 放服务器根而非 Paks 内（§14 C6）
#   · 字體補丁（HLN-A/winhttp.dll）属玩家客户端，服务端完全不管（2026-11-07 用户裁决）
ZH_CACHE_ROOT = r'D:\Cache-zh'
ZH_PAKS_REL = os.path.join('ShooterGame', 'Content', 'Paks')
ZH_SIDECAR_NAME = '.dino_zh.json'
ZH_PKG_WHITELIST = ('ShooterGame-Windows_P.pak',
                    'ShooterGame-Windows_P.ucas',
                    'ShooterGame-Windows_P.utoc')
ZH_FOLDER_DEFAULT = 'https://drive.google.com/drive/folders/1SarH6KgkuQp4uev2wHf3mX-kS5xsL37S'
ZH_LS_URL = 'https://drive.google.com/embeddedfolderview?id=%s#list'
ZH_DL_URL = 'https://drive.usercontent.google.com/download?id=%s&export=download&confirm=t'
ZH_VARIANTS = ('dinoitem', 'item', 'normal')
ZH_TTL = 1800
ZH_PROBE_TIMEOUT = 3
_ZH_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
          '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
# 2026-11-07 实测基线（11 台 size+mtime 完全一致，2026-10-16 装机）—— 用于「已知旧版」判定
ZH_BASELINE_SIZES = {'ShooterGame-Windows_P.pak': 63112850,
                     'ShooterGame-Windows_P.ucas': 57328256,
                     'ShooterGame-Windows_P.utoc': 28379}
_ZH_CACHE = {'at': 0.0, 'ok': False, 'folder': '', 'ver': '', 'variant': '',
             'asset': {}, 'items': [], 'err': '', 'probe': {}}
_ZH_LOCK = threading.Lock()
# v6238（B2）：下载/解压后台任务状态（供 /api/zh/status 轮询）
_ZH_PREP = {'running': False, 'ver': '', 'phase': '', 'got': 0, 'total': 0,
            'err': '', 'at': 0.0, 'msg': '', 'skipped': False}
_ZH_PREP_LOCK = threading.Lock()
_ZH_DL = {'got': 0, 'total': 0}


def _zh_cfg_of(doc):
    """从 server_config dict 解析 zh_patch（不读盘，便于 GET 复用同一个 _sd）"""
    z = (doc or {}).get('zh_patch')
    z = z if isinstance(z, dict) else {}
    url = str(z.get('folder_url') or '').strip() or ZH_FOLDER_DEFAULT
    var = str(z.get('variant') or '').strip().lower()
    if var not in ZH_VARIANTS:
        var = 'dinoitem'
    ac = z.get('auto_check')
    return {'folder_url': url, 'variant': var,
            'auto_check': True if ac is None else (str(ac).lower() in ('1', 'true', 'yes', 'on'))}


def _zh_cfg():
    try:
        return _zh_cfg_of(_srv_cfg_read())
    except Exception:
        return _zh_cfg_of({})


def _zh_folder_id(url):
    m = re.search(r'/folders/([A-Za-z0-9_-]{10,})', str(url or ''))
    return m.group(1) if m else ''


def _zh_norm(s):
    return re.sub(r'[^a-z0-9]+', '', str(s or '').lower())


def _zh_variant_of(name):
    n = _zh_norm(name)
    if 'dinoitembilingual' in n:
        return 'dinoitem'
    if 'itembilingual' in n:
        return 'item'
    return 'normal'


def _zh_ver_of(name):
    m = re.search(r'[Vv](\d+(?:\.\d+)?)', str(name or ''))
    return m.group(1) if m else ''


def _zh_ver_tuple(v):
    m = re.match(r'^(\d+)(?:\.(\d+))?$', str(v or '').strip().lstrip('vV'))
    return (int(m.group(1)), int(m.group(2) or 0)) if m else None


def _zh_get(url, timeout=15, rng=None, maxb=4 * 1024 * 1024):
    """只读 GET -> {ok,code,ms,err,ctype,body}（不抛异常）"""
    import urllib.request as _ur
    t0 = time.time()
    hdr = {'User-Agent': _ZH_UA, 'Accept': '*/*'}
    if rng:
        hdr['Range'] = rng
    try:
        rq = _ur.Request(url, headers=hdr)
        with _ur.urlopen(rq, timeout=timeout) as r:
            b = r.read(maxb)
            return {'ok': True, 'code': int(getattr(r, 'status', 0) or 0),
                    'ms': int((time.time() - t0) * 1000), 'err': '',
                    'ctype': str(r.headers.get('Content-Type') or ''), 'body': b}
    except Exception as e:
        return {'ok': False, 'code': 0, 'ms': int((time.time() - t0) * 1000),
                'err': ('%s: %s' % (type(e).__name__, e))[:200], 'ctype': '', 'body': b''}


def _zh_html_unescape(s):
    return (str(s or '').replace('&amp;', '&').replace('&lt;', '<')
            .replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'"))


def _zh_parse_ls(html):
    """embeddedfolderview HTML -> [{id,name}]"""
    out = []
    for m in re.finditer(r'id="entry-([A-Za-z0-9_-]{10,})"[\s\S]{0,900}?'
                         r'flip-entry-title">([^<]*)<', str(html or '')):
        out.append({'id': m.group(1), 'name': _zh_html_unescape(m.group(2)).strip()})
    return out


def _zh_pick(items, variant):
    """按变体挑包（多个命中取版本号最大者）"""
    cand = []
    for it in (items or []):
        if _zh_variant_of(it.get('name')) != variant:
            continue
        vt = _zh_ver_tuple(_zh_ver_of(it.get('name')))
        if vt:
            cand.append((vt, it))
    if not cand:
        return None
    cand.sort(key=lambda t: t[0])
    return cand[-1][1]


def _zh_probe_meta(r):
    return {'ok': bool(r.get('ok')), 'code': int(r.get('code') or 0),
            'ms': int(r.get('ms') or 0), 'err': r.get('err') or '',
            'ctype': r.get('ctype') or ''}


def _zh_remote(force=False):
    """列 Google Drive 文件夹（embeddedfolderview，无需 API key/OAuth）"""
    now = time.time()
    with _ZH_LOCK:
        if (not force) and _ZH_CACHE.get('at') and (now - float(_ZH_CACHE['at']) < ZH_TTL):
            return dict(_ZH_CACHE)
    cfg = _zh_cfg()
    fid = _zh_folder_id(cfg['folder_url'])
    out = {'at': now, 'ok': False, 'folder': fid, 'ver': '', 'variant': cfg['variant'],
           'asset': {}, 'items': [], 'err': '', 'probe': {}}
    if not fid:
        out['err'] = u'下载地址里找不到 /folders/<id>'
        with _ZH_LOCK:
            _ZH_CACHE.clear(); _ZH_CACHE.update(out)
        return dict(out)
    ls_url = ZH_LS_URL % fid
    lr = _zh_get(ls_url, timeout=15)
    out['probe']['ls'] = _zh_probe_meta(lr)
    if not lr['ok']:
        out['err'] = u'无法访问 Google Drive（列目录失败）：%s' % (lr['err'] or '')
        with _ZH_LOCK:
            _ZH_CACHE.clear(); _ZH_CACHE.update(out)
        return dict(out)
    try:
        items = _zh_parse_ls(lr['body'].decode('utf-8', 'replace'))
    except Exception as e:
        items = []
        out['err'] = (u'列表解析异常：%s: %s' % (type(e).__name__, e))[:200]
    out['items'] = items
    if not items:
        if not out['err']:
            out['err'] = u'目录列表解析为空（可能被限流或页面结构变化）'
    else:
        pick = _zh_pick(items, cfg['variant'])
        if not pick:
            out['err'] = u'目录里没有匹配变体 %s 的包（共 %d 项）' % (cfg['variant'], len(items))
        else:
            out['ok'] = True
            out['ver'] = _zh_ver_of(pick['name'])
            out['asset'] = {'id': pick['id'], 'name': pick['name'],
                            'ver': out['ver'], 'variant': cfg['variant']}
            # 下载域名连通性（只取 1 KB，不下载整包）
            dr = _zh_get(ZH_DL_URL % pick['id'], timeout=ZH_PROBE_TIMEOUT,
                         rng='bytes=0-1023', maxb=4096)
            out['probe']['dl'] = _zh_probe_meta(dr)
            if dr['ok'] and dr['body'][:4] != b'PK\x03\x04':
                out['probe']['dl']['err'] = u'响应不是 zip（首 4 字节不符）'
    with _ZH_LOCK:
        _ZH_CACHE.clear(); _ZH_CACHE.update(out)
    return dict(out)


def _zh_paks_dir(srv):
    return os.path.join(UPDATE_SERVERS_ROOT, srv, ZH_PAKS_REL)


def _zh_scan_paks(srv):
    """各服 Paks 下 ShooterGame-* 文件（scandir 一次拿全）"""
    d = _zh_paks_dir(srv)
    r = {'exists': False, 'files': {}, 'bases': [], 'conflict': False, 'err': ''}
    try:
        with os.scandir(d) as it:
            r['exists'] = True
            for e in it:
                try:
                    if not e.is_file():
                        continue
                except Exception:
                    continue
                if not e.name.lower().startswith('shootergame-'):
                    continue
                try:
                    r['files'][e.name] = e.stat().st_size
                except Exception:
                    r['files'][e.name] = -1
    except Exception as e:
        r['err'] = ('%s: %s' % (type(e).__name__, e))[:160]
        return r
    bases = set()
    for n in r['files']:
        low = n.lower()
        for ext in ('.pak', '.ucas', '.utoc'):
            if low.endswith(ext):
                bases.add(n[:-len(ext)])
                break
    r['bases'] = sorted(bases)
    r['conflict'] = len(bases) > 1
    return r


def _zh_read_sidecar(srv):
    p = os.path.join(UPDATE_SERVERS_ROOT, srv, ZH_SIDECAR_NAME)
    try:
        with open(p, encoding='utf-8') as f:
            d = json.load(f) or {}
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _zh_server_status(srv, remote=None):
    """单台汉化状态（B1：纯本地判定）"""
    scan = _zh_scan_paks(srv)
    sc = _zh_read_sidecar(srv)
    out = {'srv': srv, 'exists': bool(scan['exists']), 'bases': scan['bases'],
           'conflict': bool(scan['conflict']), 'files': [], 'err': scan['err'],
           'curVer': '', 'curSrc': '', 'needUpd': False, 'reason': ''}
    if (not scan['exists']) or (not scan['files']):
        out['curSrc'] = 'none'
        out['reason'] = u'未安装汉化'
    elif sc.get('ver'):
        out['curVer'] = str(sc.get('ver') or '')
        out['curSrc'] = 'sidecar'
    else:
        hit = all(scan['files'].get(k) == v for k, v in ZH_BASELINE_SIZES.items())
        if hit:
            out['curVer'] = u'旧版'
            out['curSrc'] = 'baseline'
            out['reason'] = u'2026-10-16 装机旧版（size 指纹匹配）'
        else:
            out['curVer'] = u'?'
            out['curSrc'] = 'unknown'
            out['reason'] = u'无版本标记且与已知基线不符'
    for k in ZH_PKG_WHITELIST:
        out['files'].append({'name': k, 'size': scan['files'].get(k, -1)})
    rv = (remote or {}).get('ver') or ''
    if scan['exists'] and scan['files'] and (remote or {}).get('ok') and rv:
        if out['curSrc'] in ('none', 'baseline', 'unknown'):
            out['needUpd'] = True
            if not out['reason']:
                out['reason'] = u'云端有 %s' % rv
        elif out['curSrc'] == 'sidecar':
            a, b = _zh_ver_tuple(out['curVer']), _zh_ver_tuple(rv)
            if a and b and b > a:
                out['needUpd'] = True
                out['reason'] = u'云端 %s 高于本地 %s' % (rv, out['curVer'])
    return out


def _zh_human(n):
    try:
        n = float(n or 0)
    except Exception:
        return '0 B'
    if n < 1024:
        return '%d B' % int(n)
    for unit in ('KB', 'MB', 'GB'):
        n /= 1024.0
        if n < 1024 or unit == 'GB':
            return '%.1f %s' % (n, unit)
    return '0 B'


def _zh_sha256(path):
    import hashlib as _hl
    h = _hl.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _zh_download_file(fid, dest, timeout=120):
    """断点续传下载（串行，总尝试 2 次；§14 A5 校验 zip 魔数 + 大小）"""
    import urllib.request as _ur
    url = ZH_DL_URL % fid
    last = ''
    for attempt in (1, 2):
        have = os.path.getsize(dest) if os.path.isfile(dest) else 0
        try:
            hdr = {'User-Agent': _ZH_UA, 'Accept': '*/*'}
            if have > 0:
                hdr['Range'] = 'bytes=%d-' % have
            rq = _ur.Request(url, headers=hdr)
            with _ur.urlopen(rq, timeout=timeout) as r:
                code = int(getattr(r, 'status', 200) or 200)
                total = 0
                cr = str(r.headers.get('Content-Range') or '')
                if '/' in cr:
                    try:
                        total = int(cr.rsplit('/', 1)[-1])
                    except Exception:
                        total = 0
                if not total:
                    try:
                        total = int(r.headers.get('Content-Length') or 0) + (have if code == 206 else 0)
                    except Exception:
                        total = 0
                if code != 206:
                    have = 0
                _ZH_DL.update({'got': have, 'total': total})
                with open(dest, 'ab' if have else 'wb') as f:
                    while True:
                        b = r.read(1 << 20)
                        if not b:
                            break
                        f.write(b)
                        have += len(b)
                        _ZH_DL['got'] = have
                        _ZH_PREP['got'] = have
                        if total:
                            _ZH_PREP['total'] = total
                            _ZH_PREP['msg'] = (u'下载中 %s / %s（%.1f%%）'
                                               % (_zh_human(have), _zh_human(total),
                                                  100.0 * have / total))
            sz = os.path.getsize(dest) if os.path.isfile(dest) else 0
            if total and sz != total:
                last = u'大小不符 %d/%d' % (sz, total)
                if attempt < 2:
                    time.sleep(5)
                continue
            with open(dest, 'rb') as f:
                magic = f.read(4)
            if magic != b'PK\x03\x04':
                last = u'下载结果不是 zip（首 4 字节 %r）' % magic
                try:
                    os.remove(dest)
                except Exception:
                    pass
                if attempt < 2:
                    time.sleep(5)
                continue
            return {'ok': True, 'bytes': sz, 'total': total or sz, 'attempts': attempt}
        except Exception as e:
            # v6246：416 = 本地残留文件已达/超过服务端大小（Range 起点越界）
            #         -> 删掉残留，下一次 attempt 从 0 开始重下
            _c416 = (int(getattr(e, 'code', 0) or 0) == 416)
            if _c416:
                try:
                    os.remove(dest)
                except Exception:
                    pass
                last = u'HTTP 416（本地残留已达/超过服务端大小），已删除残留并重新下载'
            else:
                last = ('%s: %s' % (type(e).__name__, e))[:200]
            if attempt < 2:
                time.sleep(2 if _c416 else 5)
    return {'ok': False, 'err': last,
            'bytes': os.path.getsize(dest) if os.path.isfile(dest) else 0}


def _zh_unpack(zipp, paks_dir, ver, asset):
    """白名单取件：只解 3 个 _P 文件；HLN-A(客户端 DLL)/PDF/PNG 一律跳过（§3.5）"""
    import zipfile
    try:
        os.makedirs(paks_dir, exist_ok=True)
        out = []
        with zipfile.ZipFile(zipp) as zf:
            allnames = list(zf.namelist())
            for want in ZH_PKG_WHITELIST:
                hit = None
                for n in allnames:
                    if n == want or n.replace('\\', '/') == want:
                        hit = n
                        break
                if not hit:
                    return {'ok': False, 'err': u'包内缺少 %s' % want, 'names': allnames[:30]}
                dst = os.path.join(paks_dir, want)
                tmp = dst + '.dinozh.tmp'
                with zf.open(hit) as src, open(tmp, 'wb') as f:
                    shutil.copyfileobj(src, f, 1 << 20)
                os.replace(tmp, dst)
                out.append({'name': want, 'size': os.path.getsize(dst)})
        skipped = [n for n in allnames if n not in ZH_PKG_WHITELIST]
        man = {'ver': ver, 'variant': (asset or {}).get('variant') or '',
               'builtAt': time.strftime('%Y-%m-%d %H:%M:%S'),
               'source': {'assetId': (asset or {}).get('id') or '',
                          'name': (asset or {}).get('name') or '',
                          'bytes': os.path.getsize(zipp)},
               'paks': out, 'skipped': skipped[:30], 'skippedCount': len(skipped)}
        return {'ok': True, 'paks': out, 'manifest': man,
                'skipped': len(skipped), 'skippedNames': skipped[:10]}
    except Exception as e:
        return {'ok': False, 'err': ('%s: %s' % (type(e).__name__, e))[:220]}


def _zh_prepare_start(force=False, user=''):
    """异步：读云端清单 -> 下载 -> 白名单解压 -> 写 manifest（只写 D:\\Cache-zh）

    v6246（用户口径「本地包就是最新的，点更新本地包要提示已是最新」）：
    在启动后台任务**之前**做一次零网络快判 —— 仅当云端清单缓存仍新鲜（TTL 内）时生效，
    命中则直接返回 already，不启动下载（同版本重复下载还会触发 Google 的 416）。
    """
    try:
        if (not force) and _ZH_CACHE.get('ok') and _ZH_CACHE.get('ver') \
                and (time.time() - float(_ZH_CACHE.get('at') or 0)) < ZH_TTL:
            _lv0 = _zh_local_ver()
            if _lv0 and str(_lv0) == str(_ZH_CACHE.get('ver')):
                return {'ok': True, 'already': True, 'ver': _lv0,
                        'msg': u'当前本地包已是最新（V%s），无需更新' % _lv0,
                        'prep': dict(_ZH_PREP)}
    except Exception:
        pass
    with _ZH_PREP_LOCK:
        if _ZH_PREP.get('running'):
            return {'ok': False, 'code': 'busy',
                    'error': u'已有下载任务在执行', 'prep': dict(_ZH_PREP)}
        _ZH_PREP.update({'running': True, 'ver': '', 'phase': 'remote', 'got': 0,
                         'total': 0, 'err': '', 'at': time.time(),
                         'msg': u'读取云端清单…', 'skipped': False})

    def _job():
        # v6323（用户口径）：接入任务总线 —— 一个实例一条
        _zk = u'zhprepare|latest'

        def _zt(msg, pct, phase='run', err=''):
            try:
                _utask_put(_zk, '', 'update', user, label=u'更新本地包',
                           msg=msg, pct=pct, phase=phase,
                           steps=_steps_apply(STEP_4_ZH, pct, phase, msg, 'zh'), err=err,
                           srv_name=u'汉化包')
            except Exception:
                _sexc('zh_prepare_utask')
        _zt(u'读取云端清单…', 5)
        try:
            rem = _zh_remote(force=force)
            if not rem.get('ok'):
                raise RuntimeError(rem.get('err') or u'云端清单读取失败')
            ver = rem.get('ver') or ''
            asset = rem.get('asset') or {}
            fid = asset.get('id') or ''
            if not (ver and fid):
                raise RuntimeError(u'云端版本或文件 ID 缺失')
            # v6246：本地包已是最新 -> 不重复下载，直接完成并给出提示
            try:
                _lvz = _zh_local_ver()
            except Exception:
                _lvz = ''
            if _lvz and str(_lvz) == str(ver):
                _ZH_PREP.update({'phase': 'done', 'ver': ver, 'skipped': True,
                                 'msg': u'当前本地包已是最新（V%s），无需更新' % ver})
                _zt(u'当前本地包已是最新（V%s），无需更新' % ver, 100, 'skip')
                return
            base = os.path.join(ZH_CACHE_ROOT, ver)
            paks_dir = os.path.join(base, 'paks')
            zipp = os.path.join(base, 'pkg.zip')
            try:
                os.makedirs(base, exist_ok=True)
            except Exception as e:
                raise RuntimeError(u'创建缓存目录失败：%s' % e)
            _ZH_PREP.update({'ver': ver, 'phase': 'download',
                             'msg': u'开始下载 %s …' % (asset.get('name') or ver)})
            _zt(u'下载 %s（V%s）…' % (asset.get('name') or ver, ver), 30)
            dl = _zh_download_file(fid, zipp)
            if not dl.get('ok'):
                raise RuntimeError(u'下载失败：%s' % (dl.get('err') or ''))
            _ZH_PREP.update({'phase': 'unpack', 'msg': u'解压中（白名单取 3 个文件）…'})
            _zt(u'解压中（白名单取 3 个文件）…', 65)
            up = _zh_unpack(zipp, paks_dir, ver, asset)
            if not up.get('ok'):
                raise RuntimeError(u'解压失败：%s' % (up.get('err') or ''))
            man = up.get('manifest') or {}
            for it in (man.get('paks') or []):
                try:
                    it['sha256'] = _zh_sha256(os.path.join(paks_dir, it.get('name') or ''))
                except Exception:
                    it['sha256'] = ''
            try:
                with open(os.path.join(base, 'manifest.json'), 'w', encoding='utf-8') as f:
                    json.dump(man, f, ensure_ascii=False, indent=1)
            except Exception as e:
                raise RuntimeError(u'写 manifest 失败：%s' % e)
            _ZH_PREP.update({'phase': 'done',
                             'msg': u'已就绪：%s（3 个文件，跳过 %d 项客户端内容）'
                                    % (ver, up.get('skipped') or 0)})
            _zt(u'已就绪：V%s（3 个 pak 已解压到缓存）' % ver, 100, 'ok')
        except Exception as e:
            _ZH_PREP.update({'phase': 'fail',
                             'err': ('%s: %s' % (type(e).__name__, e))[:220],
                             'msg': u'准备失败'})
            try:
                _zt(u'准备失败：%s' % (u'%s: %s' % (type(e).__name__, e))[:160], 100, 'fail', repr(e)[:200])
            except Exception:
                pass
        finally:
            _ZH_PREP['running'] = False
            _ZH_PREP['at'] = time.time()

    try:
        threading.Thread(target=_job, daemon=True).start()
    except Exception as e:
        _ZH_PREP.update({'running': False, 'phase': 'fail', 'err': repr(e)[:160]})
        return {'ok': False, 'error': repr(e)[:160], 'prep': dict(_ZH_PREP)}
    return {'ok': True, 'started': True, 'prep': dict(_ZH_PREP)}


def _zh_status(include_remote=True, force=False):
    """B1 完整状态：cfg + servers[] + remote（远端可跳过，供首屏快速渲染 §14 B3）"""
    cfg = _zh_cfg()
    if include_remote:
        remote = _zh_remote(force=force)
    else:
        # v6240：本地模式也带上「已下载版本」，让 needUpd / pkg 仍可判断（不触发网络）
        _lv0 = _zh_local_ver()
        remote = ({'ok': True, 'ver': _lv0, 'src': 'local_cache', 'err': '',
                   'asset': {}, 'items': [], 'probe': {}} if _lv0 else {})
    servers = []
    for srv in sorted(SERVERS.keys()):
        try:
            servers.append(_zh_server_status(srv, remote))
        except Exception:
            _sexc('zh_server_status')
            servers.append({'srv': srv, 'err': 'calc_fail', 'needUpd': False})
    need = [x.get('srv') for x in servers if x.get('needUpd')]
    conf = [x.get('srv') for x in servers if x.get('conflict')]
    pkg = {'ver': '', 'downloaded': False, 'unpacked': False, 'ready': False}
    try:
        _lv = _zh_local_ver() or (remote.get('ver') or '')
        if _lv:
            zp = os.path.join(ZH_CACHE_ROOT, _lv)
            pkg['ver'] = _lv
            pkg['downloaded'] = os.path.isfile(os.path.join(zp, 'pkg.zip'))
            pkg['unpacked'] = os.path.isfile(os.path.join(zp, 'manifest.json'))
            pkg['ready'] = bool(pkg['unpacked'])
    except Exception:
        pass
    pkg['cacheRoot'] = ZH_CACHE_ROOT
    return {'ok': True, 'cfg': cfg, 'remote': remote, 'servers': servers,
            'behind': need, 'conflict': conf, 'needAny': bool(need), 'pkg': pkg,
            'prep': dict(_ZH_PREP), 'dl': dict(_ZH_DL),
            'remoteSkipped': (not include_remote),
            'ts': time.strftime('%Y-%m-%d %H:%M:%S')}


def _upd_skip_set():
    return set(x.lower() for x in UPDATE_SKIP_DIRS)


def _upd_walk(base, skip_l):
    """遍历目录（跳过存档/配置等），产出 (相对路径, 大小, mtime)"""
    b = base.rstrip('\\')
    for root, dirs, files in os.walk(b):
        dirs[:] = [x for x in dirs if x.lower() not in skip_l]
        for f in files:
            fp = os.path.join(root, f)
            try:
                st = os.stat(fp)
                yield fp[len(b) + 1:], st.st_size, int(st.st_mtime)
            except Exception:
                pass


def _upd_make_plan(srv, cache=None, limit=25):
    """生成单台分发计划（**纯只读**）：新增 / 变更 / 相同 / 目标端多余
       —— 用于与 ASAM 的实操结果逐项对照，确认一致后才允许真跑。"""
    cache = cache if isinstance(cache, dict) else _upd_cache_status()
    src = cache.get('path') or UPDATE_CACHE_PATH
    tgt = os.path.join(UPDATE_SERVERS_ROOT, srv)
    plan = {'server': srv, 'src': src, 'tgt': tgt, 'ok': False, 'msg': '',
            'add': 0, 'update': 0, 'same': 0, 'extra': 0, 'bytes': 0,
            'samples': {'add': [], 'update': [], 'extra': []},
            'acf': {}, 'skipDirs': list(UPDATE_SKIP_DIRS)}
    if not cache.get('hasContent'):
        plan['msg'] = u'缓存无实际文件（hasContent=false），无法生成计划'
        return plan
    if not os.path.isdir(tgt):
        plan['msg'] = u'目标目录不存在：%s' % tgt
        return plan
    try:
        skip_l = _upd_skip_set()
        # v6438：预演同样改为 (size, mtime) 双判据 —— 否则预演报「无需更新 N 项」
        #   而真跑却复制，用户无法通过预演判断本次到底会不会补 paks。
        srcmap = {}
        for rel, sz, mt in _upd_walk(src, skip_l):
            srcmap[rel] = (sz, mt)
        tgtmap = {}
        for rel, sz, mt in _upd_walk(tgt, skip_l):
            tgtmap[rel] = (sz, mt)
        for rel, _sv in srcmap.items():
            sz, mt = _sv
            if rel not in tgtmap:
                plan['add'] += 1
                plan['bytes'] += sz
                if len(plan['samples']['add']) < limit:
                    plan['samples']['add'].append(rel)
            else:
                _tsz, _tmt = tgtmap[rel]
                if _tsz != sz or abs(_tmt - mt) > 2:
                    plan['update'] += 1
                    plan['bytes'] += sz
                    if len(plan['samples']['update']) < limit:
                        plan['samples']['update'].append(rel)
                else:
                    plan['same'] += 1
        ex = [r for r in tgtmap.keys() if r not in srcmap]
        plan['extra'] = len(ex)
        plan['samples']['extra'] = ex[:limit]
        plan['srcFiles'] = len(srcmap)
        plan['tgtFiles'] = len(tgtmap)
        # acf 预演：把目标 acf 改成与缓存一致（ASAM 的做法：buildid + depot manifest）
        tacf = os.path.join(tgt, 'steamapps', UPDATE_ACF_NAME)
        ta = _upd_read_acf(tacf)
        plan['acf'] = {'path': tacf, 'exists': os.path.isfile(tacf),
                       'nowBuildId': ta.get('buildid') or '',
                       'nowManifest': ta.get('manifest') or '',
                       'toBuildId': cache.get('buildId') or '',
                       'toManifest': cache.get('manifest') or ''}
        plan['ok'] = True
        plan['msg'] = (u'新增 %d · 变更 %d · 相同 %d · 目标端多余 %d（不删）· 需复制 %.2f GB'
                       % (plan['add'], plan['update'], plan['same'], plan['extra'],
                          plan['bytes'] / 1073741824.0))
    except Exception as e:
        plan['msg'] = u'生成计划失败：%r' % e
    return plan


def _upd_patch_acf_text(t, buildid, manifest, sizeon, lastupd):
    """把 appmanifest 文本改成与缓存一致（**纯函数，便于先预演后写盘**）
       要改的字段（照 ASAM 的 `-app 2430930 -depot 2430931 -manifest <id>` 语义）：
         buildid / LastUpdated / SizeOnDisk / BytesToDownload / BytesDownloaded
         + depot <2430931> 的 manifest 号
       ⚠ 只改值，不动结构；找不到的字段不在文件里凭空造（保持原样）。"""
    out = t
    def _set(key, val):
        nonlocal out
        if val is None or val == '':
            return
        pat = r'("%s"\s*")[^"]*(")' % key
        if re.search(pat, out):
            out = re.sub(pat, lambda m: m.group(1) + str(val) + m.group(2), out, count=1)
    _set('buildid', buildid)
    _set('LastUpdated', lastupd)
    _set('SizeOnDisk', sizeon)
    _set('BytesToDownload', sizeon)
    _set('BytesDownloaded', sizeon)
    # depot 段里的 manifest
    if manifest:
        pat = r'("%s"\s*\{[^}]*?"manifest"\s*")[^"]*(")' % UPDATE_DEPOT_ID
        if re.search(pat, out, re.S):
            out = re.sub(pat, lambda m: m.group(1) + str(manifest) + m.group(2),
                         out, count=1, flags=re.S)
    return out


def _upd_apply_acf_from_src(tgt):
    """v6228（O3 + §12.6）：把目标 acf 改成与源缓存一致（**原子写**）
       · 取**源 acf** 的原始值逐项写入（不能用 cache_status 的 sizeGB 近似值）：
           buildid / SizeOnDisk / BytesToDownload / BytesDownloaded / depot manifest
           LastUpdated <- 当前 unix 秒
       · 写 .tmp 再 os.replace：半截 acf 会让 ASAM 判定安装损坏（比文件没复制更糟）
       · StateFlags 保持原值不动"""
    tmp = ''
    try:
        src_acf = os.path.join(UPDATE_CACHE_PATH, 'steamapps', UPDATE_ACF_NAME)
        sa = _upd_read_acf(src_acf)
        if not sa.get('ok'):
            return False, u'源 acf 不可读：%s' % src_acf
        tacf = os.path.join(tgt, 'steamapps', UPDATE_ACF_NAME)
        if not os.path.isfile(tacf):
            return False, u'目标 acf 不存在：%s' % tacf
        t = open(tacf, encoding='utf-8', errors='replace').read()
        new = _upd_patch_acf_text(t, sa.get('buildid') or '',
                                  sa.get('manifest') or '',
                                  sa.get('sizeOnDisk') or '',
                                  str(int(time.time())))
        # BytesToDownload / BytesDownloaded 用源 acf 的独立值（§12.6 与 SizeOnDisk 不同）
        _btd = sa.get('bytesToDownload') or ''
        if _btd:
            for _k in ('BytesToDownload', 'BytesDownloaded'):
                _pat = r'("%s"\s*")[^"]*(")' % _k
                if re.search(_pat, new):
                    new = re.sub(_pat, lambda m: m.group(1) + str(_btd) + m.group(2),
                                 new, count=1)
        tmp = tacf + '.tmp_' + str(int(time.time()))
        with open(tmp, 'w', encoding='utf-8', newline='') as f:
            f.write(new)
        # v6255：os.replace 覆盖前清只读（只读时 replace 会 WinError 5）
        try:
            os.chmod(tacf, _stat.S_IWRITE)
        except Exception:
            pass
        os.replace(tmp, tacf)
        return True, u'ok'
    except Exception as e:
        try:
            if tmp and os.path.isfile(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return False, repr(e)


def _upd_cache_clear():
    """v6263（用户口径）：清空版本更新缓存。
       · **前置校验**：任何服与缓存不一致 ⇒ 直接拒绝（否则清完就没法分发）
       · 只删 UPDATE_CACHE_PATH 下的内容，**保留目录本身**
       · 统计删除项数与字节数，部分失败也如实回报"""
    try:
        try:
            _st = _upd_status(include_players=False)
        except Exception:
            _st = {}
        _behind = _st.get('behind') or []
        if _behind:
            return {'ok': False, 'code': 'behind_exists',
                    'error': (u'还有 %d 台服未与缓存一致（%s），先完成分发才能清空缓存'
                              % (len(_behind), u'、'.join(_behind[:8])))}
        root = UPDATE_CACHE_PATH
        if not os.path.isdir(root):
            return {'ok': False, 'code': 'no_cache',
                    'error': u'缓存目录不存在：%s' % root}
        n = 0
        nbytes = 0
        errs = []
        for name in os.listdir(root):
            p = os.path.join(root, name)
            try:
                if os.path.isdir(p):
                    for _r, _d, _f in os.walk(p):
                        for _x in _f:
                            try:
                                nbytes += os.path.getsize(os.path.join(_r, _x))
                            except Exception:
                                pass
                    shutil.rmtree(p)
                else:
                    try:
                        nbytes += os.path.getsize(p)
                    except Exception:
                        pass
                    os.remove(p)
                n += 1
            except Exception as e:
                errs.append('%s: %s' % (name, e))
        try:
            _admin_log('UPDATE cache CLEAR n=%d bytes=%d errs=%s'
                       % (n, nbytes, ','.join(errs[:5])))
        except Exception:
            pass
        return {'ok': (not errs), 'code': ('partial' if errs else 'ok'),
                'removed': n, 'bytes': nbytes, 'errors': errs[:10],
                'msg': (u'已清空 %d 项 / %.2f GB%s'
                        % (n, nbytes / 2 ** 30, (u'（%d 项失败）' % len(errs)) if errs else u''))}
    except Exception as e:
        return {'ok': False, 'code': 'err', 'error': (repr(e))[:200]}


def _utask_busy_prefix(pref_list):
    """v6366：任务表里是否有指定前缀的进行中任务（run/queue）"""
    try:
        with _UTASK_LOCK:
            for t in _UTASK['items']:
                if str(t.get('phase') or '') not in ('run', 'queue'):
                    continue
                k = str(t.get('key') or '')
                for p in pref_list:
                    if k.startswith(p):
                        return True
    except Exception:
        pass
    return False


def _pkg_clear(kind):
    """v6366（用户口径）：清空本地包 —— 汉化包 / MOD / API 三卡右下角「清空本地包」。
       · 只删缓存目录**内容**，保留目录本身；不碰任何服务器、不碰 \\\\Tnas 自研源
       · zh  = D:\\Cache-zh 全部内容（含 backup 分发前备份 —— 用户 2026-11-09 明确要求一并清）
       · mods= _upd_cache/_modpkg 全部内容
       · api = _upd_cache/_apipkg + _apipkg_dl 全部内容
       · 相关任务在跑 ⇒ 直接拒绝（避免删到正在写的包）"""
    kind = str(kind or '').strip().lower()
    try:
        if kind == 'zh':
            roots = [ZH_CACHE_ROOT]
            label = u'汉化包本地包'
            pref = (u'zhprepare|',)
            extra_busy = bool((_ZH_PREP or {}).get('running'))
        elif kind == 'mods':
            # v6367（实测根因）：`_mods_local_pack()` 的「本地包」统计 **两处** ——
            #   ① `_modpkg/*`（CurseForge 真·本地包）
            #   ② **最新批次** `_upd_cache/mb<ts>/mods/*`
            #   原来只删 ① ⇒ count/bytes 不归零，用户点完看起来「无效」
            #   （日志实测：PKG clear kind=mods n=2 bytes=137248255 真删了，但界面仍显示 130.9 MB）
            roots = [os.path.join(_upd_cache_dir(), MODS_PKG_ROOT_NAME)]
            try:
                for _mx in os.scandir(_upd_cache_dir()):
                    if not _mx.is_dir() or not _mx.name.startswith('mb'):
                        continue
                    _mdx = os.path.join(_mx.path, 'mods')
                    if os.path.isdir(_mdx):
                        roots.append(_mdx)
            except Exception:
                _sexc('pkg_clear_mods_batches')
            label = u'MOD 本地包'
            pref = (u'modpkg|',)
            extra_busy = False
        elif kind == 'api':
            roots = [os.path.join(_upd_cache_dir(), '_apipkg'),
                     os.path.join(_upd_cache_dir(), '_apipkg_dl')]
            label = u'API 本地包'
            pref = (u'apipkg|',)
            extra_busy = False
        else:
            return {'ok': False, 'code': 'bad_kind',
                    'error': u'未知的本地包类型：%s' % kind}
    except Exception as e:
        return {'ok': False, 'code': 'err', 'error': repr(e)[:200]}
    if extra_busy or _utask_busy_prefix(pref):
        return {'ok': False, 'code': 'busy',
                'error': u'%s正在下载/解压中，等它结束再清空' % label}
    n = 0
    nbytes = 0
    errs = []
    seen = 0
    for root in roots:
        if not os.path.isdir(root):
            continue
        seen += 1
        try:
            names = os.listdir(root)
        except Exception as e:
            errs.append(u'%s 列目录失败：%s' % (root, e))
            continue
        for name in names:
            p = os.path.join(root, name)
            try:
                if os.path.isdir(p) and not os.path.islink(p):
                    try:
                        nbytes += _dir_size(p)
                    except Exception:
                        pass
                    shutil.rmtree(p)
                else:
                    try:
                        nbytes += os.path.getsize(p)
                    except Exception:
                        pass
                    os.remove(p)
                n += 1
            except Exception as e:
                errs.append(u'%s：%s' % (name, e))
    if not seen:
        return {'ok': False, 'code': 'no_pkg',
                'error': u'%s目录不存在' % label, 'roots': roots}
    # v6368（实测根因）：清完必须**失效状态缓存** ——
    #   `_MODS_CACHE` / `_API_CACHE` TTL = 30s，不清的话前端刷新拿到的还是旧值
    #   ⇒ 卡片数字不变 ⇒ 用户以为「清空无效」（日志证实已真删）
    try:
        mods_status_cache_clear()
    except Exception:
        _sexc('pkg_clear_cache')
    try:
        _admin_log('PKG clear kind=%s n=%d bytes=%d errs=%s'
                   % (kind, n, nbytes, ','.join(errs[:5])))
    except Exception:
        pass
    return {'ok': (not errs),
            'code': ('partial' if errs else 'ok'),
            'kind': kind, 'label': label, 'roots': roots,
            'removed': n, 'bytes': nbytes, 'errors': errs[:10],
            'msg': (u'已清空%s：%d 项 / %.1f MB%s'
                    % (label, n, nbytes / 1048576.0,
                       (u'（%d 项失败）' % len(errs)) if errs else u''))}


def _upd_perm_check(srv):
    """v6255b（权限加固·诊断）：在**后端进程自己的身份**下实测目标目录能力
       · write     = 新建文件（Users 的 CreateFiles）
       · overwrite = 覆写同一文件（shutil.copy2 的真实需求，WriteData）
       · replace   = os.replace 覆盖已存在文件（acf 改写 / 汉化落盘的真实需求，DELETE）
       · delete    = 删除自建文件（清理能力）
       只操作 .dino_perm_probe*，finally 必清理，**不碰任何真实游戏文件**。"""
    tgt = os.path.join(UPDATE_SERVERS_ROOT, srv)
    r = {'ok': True, 'server': srv, 'tgt': tgt, 'exists': os.path.isdir(tgt),
         'pid': os.getpid(), 'user': '', 'write': False, 'overwrite': False,
         'replace': False, 'delete': False, 'err': {}, 'verdict': '', 'msg': ''}
    if not r['exists']:
        r['ok'] = False
        r['verdict'] = 'target_missing'
        r['err']['dir'] = 'target_missing'
        r['msg'] = u'目标目录不存在：%s' % tgt
        return r
    try:
        import getpass
        r['user'] = getpass.getuser()
    except Exception:
        pass
    p1 = os.path.join(tgt, '.dino_perm_probe')
    p2 = os.path.join(tgt, '.dino_perm_probe2')
    ps = os.path.join(tgt, '.dino_perm_src')
    _PAY = b'SOURCE-PAYLOAD-v6255c'      # v6255c：长度用 len() 比对，禁止硬编码
    try:
        # ① 新建
        try:
            with open(p1, 'wb') as f:
                f.write(b'dino-perm-probe')
            r['write'] = True
        except Exception as e:
            r['err']['write'] = '%s: %s' % (type(e).__name__, e)
        # ② 覆写已存在文件（**与真实分发同一个 API**：shutil.copy2）
        if r['write']:
            try:
                with open(ps, 'wb') as f:
                    f.write(_PAY)
                try:
                    os.chmod(p1, _stat.S_IWRITE)
                except Exception:
                    pass
                shutil.copy2(ps, p1)
                r['overwrite'] = (os.path.getsize(p1) == len(_PAY))
            except Exception as e:
                r['err']['overwrite'] = '%s: %s' % (type(e).__name__, e)
        # ③ os.replace 覆盖（对应 acf 原子写 / 汉化落盘）
        try:
            with open(p2, 'wb') as f:
                f.write(b'x')
            os.replace(p2, p1)
            r['replace'] = True
        except Exception as e:
            r['err']['replace'] = '%s: %s' % (type(e).__name__, e)
        # ④ 删除
        try:
            if os.path.isfile(p1):
                os.remove(p1)
                r['delete'] = True
        except Exception as e:
            r['err']['delete'] = '%s: %s' % (type(e).__name__, e)
    finally:
        for _p in (p1, p2, ps):
            try:
                if os.path.isfile(_p):
                    os.remove(_p)
            except Exception:
                pass
    if not r['overwrite']:
        r['verdict'] = 'copy_fail'
    elif not r['replace']:
        r['verdict'] = 'replace_fail'
    else:
        r['verdict'] = 'ok'
    r['msg'] = {
        'ok': u'权限正常：可覆盖文件、可原子替换、可清理',
        'copy_fail': u'目标目录不可写：连覆盖文件都失败，一键分发会在复制阶段中止（安全）',
        'replace_fail': u'可覆盖文件，但无法原子替换（缺 DELETE 权限）：'
                        u'acf 改写与汉化落盘会失败',
        'target_missing': u'目标目录不存在',
    }.get(r['verdict'], '')
    r['ok'] = (r['verdict'] == 'ok')
    return r


def _restart_loop():
    _restart_log('orchestrator started: enable=%s dry=%s round=%ss' % (RESTART_ENABLE, RESTART_DRY, RESTART_ROUND))
    while True:
        try:
            _restart_tick()
        except Exception:
            _sexc('restart_tick')
        time.sleep(15)


# ===== v6122：统一任务总线（Task Bus）—— A 类「服务器操作进度」唯一真源 =====
#   目标：服务器控制 / 安全回档 / 启动队列 / IP 自动重启 的进度**全服共享一份**；
#         前端只读渲染（原实现存 localStorage ⇒ 每人一份，A 点了 B 看不到）。
#   权限：**不设独立权限**，跟随所在浮窗（与 /api/srvctl/* 同一 guard）。
UTASK_MAX = 200
UTASK_OK_TTL = 60.0
UTASK_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tasks_state.json')
_UTASK_ACT_LABEL = {'start': u'启动', 'kill': u'强制终止', 'savekill': u'存档后终止',
                    'saveworld': u'保存世界', 'destroy': u'清理恐龙', 'rcon': u'RCON',
                    'refresh': u'刷新状态', 'fullbackup': u'完整备份', 'update': u'更新',
                    'restart': u'重启（IP 切换）', 'rollback': u'安全回档'}
_UTASK = {'rev': 0, 'seq': 0, 'items': []}
_UTASK_LOCK = threading.Lock()


def _utask_opname(user):
    """操作人显示名：ipwatch ⇒ 自动；其余取 accounts.json 的 nick（即游戏内玩家名）。"""
    u = str(user or '')
    if not u:
        return ''
    if u == 'ipwatch':
        return u'自动'
    try:
        acc = (_accounts() or {}).get(u) or {}
        return str(acc.get('nick') or u)
    except Exception:
        return u


def _utask_save_locked():
    try:
        snap = {'rev': _UTASK['rev'], 'seq': _UTASK['seq'],
                'items': [dict((k, v) for k, v in t.items()) for t in _UTASK['items']]}
        tmp = UTASK_STATE_FILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(snap, f, ensure_ascii=False)
        os.replace(tmp, UTASK_STATE_FILE)
    except Exception:
        _sexc('utask_save')


def _utask_gc_locked(now):
    items = _UTASK['items']
    keep = []
    for t in items:
        if t.get('phase') in ('ok', 'warn') and t.get('hideAt') and now > float(t['hideAt']):
            continue
        keep.append(t)
    if len(keep) > UTASK_MAX:
        keep = keep[-UTASK_MAX:]
    _UTASK['items'] = keep


def _utask_load():
    """后端起动态：进行中/排队的任务一律置 fail('后端重启导致中断')（与旧 lbTaskLoad 语义一致）。"""
    try:
        if not os.path.isfile(UTASK_STATE_FILE):
            return
        with open(UTASK_STATE_FILE, 'r', encoding='utf-8') as f:
            d = json.load(f) or {}
        items = [t for t in (d.get('items') or []) if isinstance(t, dict)]
        _ldnow = time.time()
        for t in items:
            if t.get('phase') in ('run', 'queue'):
                t['phase'] = 'fail'
                t['err'] = u'后端重启导致中断'
                t['hideAt'] = 0
                # v6187b：补 tEnd、清 pct —— 原来 tEnd 恒为 0（前端算不出中断时刻）、
                #   pct 残留（如 cfcore=8）⇒ 失败条画成 8% 红条，看着像「卡住」而非「已失败」。
                t['tEnd'] = _ldnow
                t['pct'] = 0
        with _UTASK_LOCK:
            _UTASK['items'] = items[-UTASK_MAX:]
            _UTASK['seq'] = int(d.get('seq') or 0)
            _UTASK['rev'] = int(d.get('rev') or 0) + 1
    except Exception:
        _sexc('utask_load')


def _utask_clean_text(s):
    """v6124：任务文本清洗——剔除控制字符（RCON 包头等），保留换行/制表。"""
    s = str(s or '')
    return ''.join(ch for ch in s if ch >= ' ' or ch in '\n\t')


def _utask_master_of(server):
    """v6276（用户口径「原本启动条要显示的信息，完整整合显示在融合任务条内」）：
    该服当前是否存在「主任务」（融合条）。存在 → 启动单任务不再单独成条，信息**改投递**给它。

    优先级：编排（restart）> 安全回档（arkbk）。
    返回 'restart' / 'rollback' / 'rollback_dry' / None。
    """
    try:
        if bool(_RESTART.get('running')) and server in (_RESTART.get('servers') or {}):
            return 'restart'
    except Exception:
        pass
    try:
        for _jid, _j in (_ARKBK_JOBS or {}).items():
            if not isinstance(_j, dict):
                continue
            if _j.get('server') != server:
                continue
            if _j.get('ok') is not None:      # 已结束的 job 不接管
                continue
            return ('rollback_dry' if _j.get('dryRun') else 'rollback')
    except Exception:
        pass
    return None


def _utask_boot_mirror(server, master, msg, pct, phase, meta):
    """v6276：被主任务接管的「启动」单任务进度 → **转投**到主任务上（不新建条）。

    · master='restart'   → 写编排状态 _RESTART['servers'][srv]，进度按 **75 → 88** 映射
                           （编排 startq 段；verify 起点 90）
    · master='rollback*' → 写回档 job 的 bootPct/bootMsg，_arkbk_task_push 按 **72 → 92** 映射
    """
    _ph = str(phase or '')
    if master == 'restart':
        try:
            with _RESTART_LOCK:
                st = (_RESTART.get('servers') or {}).get(server)
                if not st:
                    return
                if str(st.get('phase') or '') != 'startq':
                    return                     # 不在起服阶段：交给正常流程
                if _ph == 'fail':
                    return                     # 失败由 _restart_tick 的 fail 分支统一处理
                _pos = 0
                try:
                    _pos = int((meta or {}).get('qpos') or 0)
                except Exception:
                    _pos = 0
                if _ph == 'queue':
                    st['pct'] = 75
                    st['msg'] = (u'排队中（第 %d 位）' % _pos) if _pos else u'排队中…'
                elif _ph == 'ok':
                    st['pct'] = 88
                    st['msg'] = str(msg or u'已对外开放加入')
                else:
                    _bp = max(0, min(100, int(pct or 0)))
                    st['pct'] = 75 + int(round(_bp * 0.13))
                    st['msg'] = str(msg or u'启动中…')
                # 节流：msg 里的耗时秒数每 2s 变一次 ⇒ 指纹去掉「（Ns）」并把 pct 量化成档位，
                #   只有**阶段或档位**变化才 push，避免每 2 秒落盘一次。
                try:
                    _core = re.sub(u'（\\d+s）', u'', str(st.get('msg') or ''))
                except Exception:
                    _core = str(st.get('msg') or '')
                _sig = '%d|%s|%s' % (int(st.get('pct') or 0) // 3, _core, _ph)
                _nowb = time.time()
                # v6277：纯指纹去重会让「（45s）」这类秒数**永远不刷新**（核心 msg 未变）。
                #   改为「指纹相同也最多每 5 秒推一次」——既保留节流，又让倒计时可见。
                if (st.get('_bmSig') == _sig
                        and (_nowb - float(st.get('_bmAt') or 0)) < 5.0):
                    return
                st['_bmSig'] = _sig
                st['_bmAt'] = _nowb
            _restart_push(server)
        except Exception:
            _sexc('utask_boot_mirror_restart')
        return
    # ---- 回档：写 job 的 boot* 字段，由 _arkbk_task_push 注入 ----
    try:
        for _jid, _j in (_ARKBK_JOBS or {}).items():
            if not isinstance(_j, dict):
                continue
            if _j.get('server') != server or _j.get('ok') is not None:
                continue
            _j['bootPct'] = (100 if _ph == 'ok' else max(0, min(100, int(pct or 0))))
            _j['bootMsg'] = str(msg or '')
            _j['bootPhase'] = _ph
            try:
                _arkbk_task_push(_j)
            except Exception:
                pass
            return
    except Exception:
        _sexc('utask_boot_mirror_arkbk')


def _utask_put(key, server, action, user, label=None, msg='', pct=0, phase='run',
               steps=None, err='', meta=None, srv_name=None):
    """登记/更新一条任务（同 key 覆盖，保留 id）。返回任务 dict（副本）。"""
    # v6259（用户口径「一个完整任务就一个条 · 同服不合并」）：编排（更新分发/回滚）在跑时，
    #   它内部驱动的启动队列**不再单独登记 start 条** —— 否则同一台服会多出「启动」条。
    try:
        # v6270（用户口径 2026-11-07「启动条还是额外生成了」）：
        #   原条件把 mode 限死为 ('update','rollback')，而**切IP 编排 mode='restart'** ⇒ 抑制失效，
        #   启动阶段照旧多出 start 条（实测任务条 n=12 → n=14）。
        #   现口径：只要**编排在跑**且该服在本次编排内，就不单独登记 start 条 —— 一种任务一条。
        # v6276（用户口径 2026-11-08「原本启动条要显示的信息，也要完整整合显示在融合任务条内」）：
        #   v6270 只做到了「不登记」，启动的实时动态（pct / 启动阶段 / 重压 / 排队位）因此**全部丢失**
        #   ⇒ 融合条在起服段长时间停在「已入启动队列（等待起服）」，整台服的启动过程看起来卡住。
        #   现把抑制点从「丢弃」改为「**改投递**」：信息转给该服的主任务
        #   （编排 restart / 安全回档 arkbk），由主任务条自己显示 —— 一条任务一条，但信息不丢。
        #   该点也是所有单任务信息的总入口 ⇒ 今后任何被接管的动作自动走同一条路。
        if str(action) == 'start' and server:
            _mst = _utask_master_of(server)
            if _mst:
                try:
                    _utask_boot_mirror(server, _mst, msg, pct, phase, meta)
                except Exception:
                    _sexc('utask_boot_mirror')
                return None
    except Exception:
        pass
    now = time.time()
    with _UTASK_LOCK:
        i = -1
        for j, t in enumerate(_UTASK['items']):
            if t.get('key') == key:
                i = j
                break
        if i >= 0:
            t = _UTASK['items'][i]
        else:
            _UTASK['seq'] += 1
            t = {'id': _UTASK['seq'], 'key': key, 't0': now, 'steps': []}
            _UTASK['items'].append(t)
        t.update({'server': server,
                  # v6178：允许显式覆盖显示名（savekill 多台汇总任务显示「9 台」）
                  'srvName': srv_name or (SERVER_THEMES.get(server) or {}).get('name') or server,
                  'action': action,
                  'label': label or _UTASK_ACT_LABEL.get(action) or action,
                  'phase': phase,
                  'pct': max(0, min(100, int(pct or 0))),
                  'msg': _utask_clean_text(msg)[:160],
                  'operator': str(user or ''),
                  'operatorName': _utask_opname(user),
                  # v6274（用户口径）：err 上限 300 → 4000 —— 错误详情要能完整看到
                  #   （前端已支持超长自动换行，不再靠截断防撑爆）。
                  'err': _utask_clean_text(err)[:4000]})
        if phase in ('run', 'queue'):
            t['tEnd'] = 0
            t['hideAt'] = 0
        else:
            t['tEnd'] = now
            t['hideAt'] = (now + UTASK_OK_TTL) if phase in ('ok', 'warn') else 0
        if steps is not None:
            t['steps'] = steps
        if meta is not None:
            t['meta'] = meta
        _UTASK['rev'] += 1
        _utask_gc_locked(now)
        _utask_save_locked()
        return dict(t)


def _utask_stage(key, server, action, user, msg='', pct=0):
    """v6140：**只推进已有任务的阶段**（前端刷新流程上报用）。
       · 不新建任务行（任务由 refresh_tamed 触发时登记）
       · 已完成/失败的任务不再被旧阶段覆盖；pct 只增不减
       · 不参与任何执行逻辑，纯展示数据"""
    now = time.time()
    with _UTASK_LOCK:
        t = None
        for x in _UTASK['items']:
            if x.get('key') == key:
                t = x
                break
        if t is None:
            return False
        if t.get('phase') not in ('run', 'queue'):
            return False
        t['msg'] = _utask_clean_text(msg)[:160]
        try:
            t['pct'] = max(int(t.get('pct') or 0), max(0, min(100, int(pct or 0))))
        except Exception:
            pass
        if user:
            t['operator'] = str(user)
            try:
                t['operatorName'] = _utask_opname(user)
            except Exception:
                pass
        _UTASK['rev'] += 1
        _utask_save_locked()
        return True


# ===== v6212（用户口径「进度条并入总线」）：缓存更新进度伪装成一条任务 =====
#   · 数据来自 SteamCMD 日志（只读推导），**不写 _UTASK / 不落盘**
#   · 因此 服务器控制 / 安全回档 / 服务器更新 三处的任务列表会自动显示同一条进度条
#     （前端 lbTaskRender 渲染同一份 /api/tasks 结果，零新增样式）
_UPD_TASK_KEY = '__cache|steamupdate'
_UPD_VIRT_SIG = ['']
_UPD_VIRT_MEM = {'at': 0.0, 'val': None}


def _utask_virtual_cache():
    _now = time.time()
    if _UPD_VIRT_MEM['val'] is not None and (_now - _UPD_VIRT_MEM['at']) < 1.2:
        return _UPD_VIRT_MEM['val']
    _v = None
    try:
        p = _upd_steam_progress()
        _ph = str(p.get('phase') or '')
        _idle_n = int(p.get('idleSec') or -1)
        # v6212b：只注入「正在进行 / 刚结束」的状态 ——
        #   实测 6.7 天前的 Success 也会被判成 phase=ok，若不加时间闸门会永久挂在任务列表里。
        _keep = ((_ph == 'run')
                 or (_ph == 'ok' and 0 <= _idle_n <= UPDATE_STEAM_OK_HOLD)
                 or (_ph == 'fail' and 0 <= _idle_n <= 300))
        if _ph in ('run', 'ok', 'fail') and _keep:
            _pct = int(p.get('pct') or 0)
            if _ph == 'run' and _pct <= 0:
                _pct = 1
            _v = {'id': -1, 'key': _UPD_TASK_KEY, 'server': '__cache',
                  'srvName': u'Steam 缓存', 'action': 'cacheupdate', 'label': u'缓存更新',
                  'phase': _ph, 'pct': max(0, min(100, _pct)),
                  'msg': str(p.get('msg') or '')[:160],
                  'err': (str(p.get('msg') or '')[:300] if _ph == 'fail' else ''),
                  'operator': '', 'operatorName': '',
                  't0': _now, 'tEnd': (0 if _ph == 'run' else _now),
                  'hideAt': (0 if _ph == 'run' else (_now + UPDATE_STEAM_OK_HOLD)),
                  'steps': p.get('steps') or []}
    except Exception:
        _sexc('utask_virtual_cache')
        _v = None
    _UPD_VIRT_MEM['at'] = _now
    _UPD_VIRT_MEM['val'] = _v
    return _v


def _utask_list(since=0):
    _virt = _utask_virtual_cache()
    with _UTASK_LOCK:
        # v6128：读取路径也做一次过期回收
        #   原实现 GC 只在写入时调用 ⇒ 带 hideAt 的「已完成」任务永远挂在列表里
        _n_before = len(_UTASK['items'])
        _utask_gc_locked(time.time())
        if len(_UTASK['items']) != _n_before:
            _UTASK['rev'] += 1
            _utask_save_locked()
        # v6212：虚拟任务状态变化时推进 rev —— 否则 since==rev 的增量轮询永远收不到进度更新
        try:
            _vsig = ('%s|%s|%s' % (_virt.get('phase'), _virt.get('pct'), _virt.get('msg'))) if _virt else ''
        except Exception:
            _vsig = ''
        if _vsig != _UPD_VIRT_SIG[0]:
            _UPD_VIRT_SIG[0] = _vsig
            _UTASK['rev'] += 1
        if since and int(since) == int(_UTASK['rev']):
            return {'rev': _UTASK['rev'], 'changed': False, 'tasks': []}
        _items = [dict((k, v) for k, v in t.items()) for t in _UTASK['items']]
        if _virt:
            _items.append(_virt)
        return {'rev': _UTASK['rev'], 'changed': True, 'tasks': _items}


def _utask_dismiss(ids=None, all_fail=False):
    removed = 0
    with _UTASK_LOCK:
        keep = []
        for t in _UTASK['items']:
            drop = False
            if all_fail and t.get('phase') == 'fail':
                drop = True
            elif ids and t.get('id') in ids:
                drop = True
            if drop:
                removed += 1
            else:
                keep.append(t)
        _UTASK['items'] = keep
        _UTASK['rev'] += 1
        _utask_save_locked()
    return removed


# ================= HTTP =================
# v988：并发上限 —— 防「线程爆炸」：ThreadingHTTPServer 每请求一线程，前端刷新轮询风暴时
#       会瞬间起上千线程 → 内存/句柄耗尽 → 进程退出 → cloudflared 报 actively refused（502）
# v996：32 → 64（实测页面一轮数据下载就要 33 个 HEAD，32 上限必然打满后静默断连）
# ⭐ 2026-09-22（方案A·根因修复）：`_CONC` 语义变更 = **「同时处理的请求数」**（不再是同时存在的连接数）；
#   另设 `_CONN` 仅做「防线程爆炸」的连接级上限（keep-alive 空闲连接吃 `_CONN`，**不吃请求令牌**）。
#   起因实测：令牌原先包在 finish_request 外层 ⇒ 生命周期 = 整条 TCP 连接（含 keep-alive 空闲期）
#   ⇒ 浏览器/cloudflared 连接池里的空闲连接持续吃令牌 ⇒ 有效并发从 64 跌到 ~22–24
#   ⇒ 页面一轮突发（30–44 个 HEAD + 多文件）必然 503 或排队 ⇒ 「下载卡/慢」、HEAD 8–10s 超时、单文件偶发 36.7s。
_CONC_LIMIT = 64
_CONC = __import__('threading').Semaphore(_CONC_LIMIT)          # 请求级（真正在处理的请求）
_CONN_LIMIT = 192
_CONN = __import__('threading').Semaphore(_CONN_LIMIT)          # 连接级（含 keep-alive 空闲连接）


class _GuardedServer(ThreadingHTTPServer):
    daemon_threads = True
    # v995 根因修复：accept backlog 默认仅 5（socketserver.TCPServer 默认值）—— 并发稍高即溢出，
    #   内核对新 SYN 回 RST → cloudflared 报 "actively refused"（09:50 / 10:07 实测，且 worker 日志无崩溃记录）
    request_queue_size = 512

    # v992 根因修正：v988 把信号量放在 process_request_thread —— 而 ThreadingHTTPServer 的顺序是
    #   process_request 先 threading.Thread().start()，线程体内才调 process_request_thread
    #   → 信号量只在「线程已创建之后」排队，线程照样爆（09:29:48 / 09:39:51 两次崩溃证实 v988 未生效）。
    #   正确做法：覆盖 process_request，在**创建线程之前**获取令牌 —— 背压落在 accept 层。
    def process_request(self, request, client_address):
        # v995：**非阻塞**限流 —— v992/v994 在 accept 循环内阻塞等待（10s 超时仍过长），
        #   会让 accept 停滞 → backlog 溢出 → actively refused。拿不到令牌立即快速失败（前端 v977 自带重试）
        # v996 根因修复：v995 的「快速失败」= 直接 shutdown_request → **不回任何 HTTP 响应**，
        #   cloudflared 侧表现为 "Unable to reach the origin service: EOF"（13:23:58 实测成批出现）。
        #   改为回 **503 + Retry-After:1**（正常 HTTP 响应，隧道不再报 EOF，前端可据此退避重试）。
        # ⭐ 2026-09-22（方案A）：此处只做**连接级**限流（防线程爆炸）；
        #   请求级令牌（_CONC）已下沉到 Handler._guarded，避免空闲连接占住请求并发。
        if not _CONN.acquire(blocking=False):
            try:
                _busy = b'{"ok":false,"busy":true,"error":"server busy, retry"}'
                request.sendall(
                    b'HTTP/1.1 503 Service Unavailable\r\n'
                    b'Content-Type: application/json; charset=utf-8\r\n'
                    b'Access-Control-Allow-Origin: ' + ALLOW_ORIGIN.encode('utf-8') + b'\r\n'
                    b'Access-Control-Allow-Credentials: true\r\n'
                    b'Retry-After: 1\r\n'
                    b'Cache-Control: no-cache\r\n'
                    b'Content-Length: ' + str(len(_busy)).encode('ascii') + b'\r\n'
                    b'Connection: close\r\n\r\n' + _busy
                )
            except Exception:
                pass
            try:
                self.shutdown_request(request)
            except Exception:
                pass
            return
        try:
            t = __import__('threading').Thread(target=self._lb_guarded_run, args=(request, client_address))
            t.daemon = True
            if self._threads is not None:
                self._threads.append(t)
            t.start()
        except Exception:
            _CONN.release()
            raise

    def _lb_guarded_run(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            try:
                self.shutdown_request(request)
            except Exception:
                pass
            _CONN.release()

    def handle_error(self, request, client_address):
        # v988：简洁错误日志（避免 traceback 刷屏淹没关键信息）
        print('[handler] error from {}'.format(client_address))



# ===================== 资讯广场 News（v5926：后端直抓 Discord） =====================
# 设计：计划/计划_资讯广场迁入搞事系统_v1_20261102.md
#   · 凭据只读 <后端目录>/dino_backend.config.json —— 不读环境变量、不下发前端、不进 Git
#   · 无定时器：客户端打开/切 Tab 才拉；全局 1 分钟冷却；after=<last_message_id> 增量
#   · 图片不转存：增量新链接自带签名；过期由前端 img onerror → POST /api/news/imgfix 单条修复
NEWS_CACHE_DIR = os.path.join(WIKI_CACHE_DIR, 'news_cache')
_NEWS_CFG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dino_backend.config.json')
NEWS_TABS = [('patch_pc', u'ASA PC版本', 'patch'),
             ('news', u'方舟新闻', 'news'),
             ('patch_channel', u'ADM版本', 'channel'),
             ('adm', u'ADM预告', 'adm'),
             ('tieba', u'汉化版本', 'tieba'),
             ('api_ver', u'API版本', 'patch'),
             ('api_cache', u'API缓存', 'patch')]
NEWS_COOL_SEC = 60          # 全局冷却：客户端打开/切 Tab 时的最小抓取间隔
NEWS_IMG_COOL_SEC = 600     # 单条消息图片修复冷却
NEWS_KEEP_MSGS = 20         # 每个 Tab 最多保留的消息条数
_news_cfg_cache = {'mtime': 0, 'cfg': None}
_news_lock = threading.Lock()
_news_img_at = {}


def _news_cfg():
    """读后端本地配置文件；缺失/异常返回 None（不读环境变量、无兜底）"""
    try:
        st = os.stat(_NEWS_CFG_PATH)
        if _news_cfg_cache['cfg'] is not None and _news_cfg_cache['mtime'] == st.st_mtime:
            return _news_cfg_cache['cfg']
        with open(_NEWS_CFG_PATH, 'r', encoding='utf-8') as f:
            doc = json.load(f)
        cfg = doc.get('discord') or {}
        _news_cfg_cache['cfg'] = cfg
        _news_cfg_cache['mtime'] = st.st_mtime
        return cfg
    except Exception:
        return None


def _news_tab(tab_id):
    for t in NEWS_TABS:
        if t[0] == tab_id:
            return t
    return None


def _news_path(tab_id):
    return os.path.join(NEWS_CACHE_DIR, tab_id + '.json')


def _news_read(tab_id):
    try:
        with open(_news_path(tab_id), 'r', encoding='utf-8') as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def _news_write(tab_id, obj):
    try:
        os.makedirs(NEWS_CACHE_DIR, exist_ok=True)
        p = _news_path(tab_id)
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False)
        os.replace(tmp, p)
        return True
    except Exception:
        return False


def _news_official_version():
    """v5981：从资讯广场 patch_pc 缓存解析「官方服务器版本」。
    口径（用户确认）：取 cards[].content 里 <h3> 标题**含 Server** 的 vX.Y 最大值
    （"for Servers and Clients" 也算服务器版本；纯 "Clients" 条目排除）。"""
    # v6230 修正（2026-11-07 实测：官服已到 97.x，系统仍报 96.9 的两条根因）
    #   ① `## v97 - Major version for Servers and Clients` —— 标题**只有 v97 没有小数**，
    #      老正则 `v?(\d+)\.(\d+)` 匹配不到 ⇒ 整个 97.0 被跳过
    #   ② `**v97.13 - Minor version for Steam**` —— **不含 server**（只有 Steam），
    #      而老规则要求含 server ⇒ 97.13 被过滤掉。但 **Steam 就是我们服务器的发行版本**
    #   ⇒ 现在：标题含 server **或 steam** 都算；版本号支持无小数（v97 = 97.0）；
    #      仍排除纯 Xbox / Playstation / Windows Clients 条目。
    try:
        d = _news_read('patch_pc') or {}
        best = None
        for c in (d.get('cards') or []):
            txt = str(c.get('content') or '')
            m = re.search(r'<h3>(.*?)</h3>', txt, re.S)
            head = m.group(1) if m else ''
            if not head:
                continue
            _low = head.lower()
            if not (re.search(r'servers?\b', _low) or re.search(r'\bsteam\b', _low)):
                continue
            vm = re.search(r'(?<![\d.])v?(\d+)(?:\.(\d+))?', head, re.I)
            if not vm:
                continue
            cur = (int(vm.group(1)), int(vm.group(2) or 0))
            if best is None or cur > best:
                best = cur
        return ('%d.%d' % best) if best else ''
    except Exception:
        return ''

# ===== v6231（用户口径 2026-11-07）：官方版本号**权威取数链** =====
# 依据（ASAM 程序实证）：ASADedicatedManager.exe v3.8.2.5 的字符串表里有
#   `https://cdn2.arkdedicated.com/asa/officialserverstatus.ini`
#   + `GetOfficialServerStatusAsync` / `ParseOfficialServerStatus` / `set_OfficialServerVersion`
# ⇒ ASAM 的 `OfficialServerVersion` 就是拉这个 ini 得来的；但它是**每台各自缓存**，
#   只有手点「验证」才刷新（2026-11-07 实测：11 台里 10 台还是陈旧 v96.9，只有点过的 Gen 是 v97.5）。
# ⇒ 我们直接读官方源，不再依赖 ASAM 缓存，也不再依赖资讯广场（Discord 抓取不稳且滞后）。
OFFI_INI_URL = 'https://cdn2.arkdedicated.com/asa/officialserverstatus.ini'
OFFI_TTL = 300                     # 5 分钟缓存（官方版本不会秒变）
_OFFI_CACHE = {'at': 0.0, 'ver': '', 'src': '', 'state': 'unknown', 'err': ''}
_OFFI_LOCK = threading.Lock()


def _offi_get(url, timeout=12):
    """极简 GET（标准库）。先做证书校验，失败再降级为不校验。"""
    import ssl as _ssl
    import urllib.request as _ur
    _hdr = {'User-Agent': 'dino-backend/offi-ver', 'Accept': '*/*'}
    _last = None
    for _ctx in (None, _ssl._create_unverified_context()):
        try:
            _rq = _ur.Request(url, headers=_hdr)
            with _ur.urlopen(_rq, timeout=timeout, context=_ctx) as _r:
                return _r.read().decode('utf-8', 'replace')
        except Exception as _e:
            _last = _e
            continue
    raise _last if _last else RuntimeError('offi_get failed')


def _offi_parse_ini(txt):
    """`ARK Official Server Network Status: <RichColor ...>Online (v97.5)</>` -> '97.5'
       · 必须含 online **或 deploying**（离线/Unknown 一律返回 ''，宁缺勿错）
       · 兼容无小数写法（v97 -> '97.0'）

    v6279（2026-11-08 实测根因）：官方状态词**不只有 Online**。
       实测 04:4x 官方 ini 内容为
         `ARK Official Server Network Status: <RichColor ...>Deploying (v97.17)</>`
       而原判据 `if 'online' not in t.lower(): return ''` ⇒ 只要官方在推新版本，
       就永远解析出空 ⇒ `/api/srvctl/status.official` 为空
       ⇒ 前端 `lbSrvCtlOfficialHtml('')` 直接 return ''
       ⇒ **「当前官服版本 vX」整行消失（版本号链接一起没了）**，
         服务器控制 / 服务器更新 两个浮窗同时中招。
       Deploying 时括号里的版本号就是**即将上线的新版本**，语义上正是用户要看的，故一并接受；
       Down / Unknown 等仍返回空（宁缺勿错）。"""
    t = _AS_TAG.sub(' ', str(txt or ''))
    _tl = t.lower()
    # v6280（用户口径 2026-11-08「这 4 种状态都要用中文标识出来」）：
    #   改为返回 **(版本号, 状态词)**，状态词供前端做中文标识：
    #     online → 在线 / deploying → 部署中 / down → 离线 / unknown → 未知
    #   落在这 4 个之外的一律按 unknown 处理（宁标未知，不猜）。
    _state = 'unknown'
    for _k in ('online', 'deploying', 'down'):
        if _k in _tl:
            _state = _k
            break
    if _state in ('down', 'unknown'):
        return '', _state          # 离线/未知：不给版本号（宁缺勿错）
    m = re.search(r'\(\s*v?(\d+)(?:\.(\d+))?\s*\)', t, re.I)
    if not m:
        return '', _state
    return ('%d.%s' % (int(m.group(1)), m.group(2) or '0')), _state


def _offi_from_ini():
    """-> (ver, state)；state ∈ online / deploying / down / unknown"""
    return _offi_parse_ini(_offi_get(OFFI_INI_URL, timeout=12))


def _official_version_ex(force=False):
    """v6232（用户口径 2026-11-07）：官方版本号统一入口 -> {'ver','src','err','at'}
       **只认官方 CDN ini 一个源，不做任何降级**
       —— v6231 曾有「官方服务器列表众数」与「Discord 资讯广场」两级兜底，
          用户明确「这两个降级都不需要，多余了」，故删除。
       取不到就返回空（前端浮窗显示「未知」，由人工确认）。"""
    now = time.time()
    with _OFFI_LOCK:
        if (not force) and _OFFI_CACHE.get('ver') and (now - float(_OFFI_CACHE.get('at') or 0) < OFFI_TTL):
            return dict(_OFFI_CACHE)
        _err = []
        ver, src, state = '', '', 'unknown'
        try:
            ver, state = _offi_from_ini()
            if ver:
                src = 'ini'
            else:
                # v6279：解析为空也要留痕 —— 原来 err 为空串，接口看上去"既没失败也没数据"，
                #   排查时无法区分「网络不通」与「状态词不认识」。
                _err.append('ini:empty:' + str(state or 'unknown'))
        except Exception as e:
            _err.append('ini:' + type(e).__name__)
            state = 'unknown'
        _OFFI_CACHE.update({'at': now, 'ver': ver, 'src': src,
                            'state': state, 'err': ';'.join(_err)})
        return dict(_OFFI_CACHE)

def _discord_api(path, cfg):
    """Discord REST GET -> (ok, data|err)"""
    import urllib.request as _u
    import urllib.error as _ue
    tok = str((cfg or {}).get('bot_token') or '').strip()
    if not tok:
        return False, 'bot_token 未配置'
    req = _u.Request('https://discord.com/api/v10' + path, headers={
        'Authorization': 'Bot ' + tok,
        'User-Agent': 'dino-backend/1.0',
    })
    try:
        with _u.urlopen(req, timeout=20) as r:
            return True, json.loads(r.read().decode('utf-8', 'ignore'))
    except _ue.HTTPError as e:
        body = ''
        try:
            body = e.read().decode('utf-8', 'ignore')[:300]
        except Exception:
            pass
        return False, 'HTTP %s %s' % (e.code, body)
    except Exception as e:
        return False, str(e)


def _news_extract(m):
    """Discord message JSON -> {text, images, youtube_links}（与 HA 侧 discord_patch_bot 同口径）"""
    parts = []
    c = (m.get('content') or '').strip()
    if c:
        parts.append(c)
    for e in (m.get('embeds') or []):
        if e.get('title'):
            parts.append(str(e['title']))
        if e.get('description'):
            parts.append(str(e['description']))
        for fd in (e.get('fields') or []):
            if fd.get('name'):
                parts.append(str(fd['name']))
            if fd.get('value'):
                parts.append(str(fd['value']))
    text = '\n'.join(parts).strip()
    imgs = []
    for a in (m.get('attachments') or []):
        u = str(a.get('url') or a.get('proxy_url') or '')
        fn = str(a.get('filename') or '').lower()
        ct = str(a.get('content_type') or '')
        if u and (ct.startswith('image/') or fn.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))):
            imgs.append(u)
    for e in (m.get('embeds') or []):
        iu = str(((e.get('image') or {}).get('url')) or ((e.get('thumbnail') or {}).get('url')) or '')
        if iu:
            imgs.append(iu)
    yt = re.findall(r'https://www\.youtube\.com/watch\?v=([A-Za-z0-9_\-]{11})', text)
    return {'text': text, 'images': imgs,
            'youtube_links': ['https://www.youtube.com/watch?v=' + v for v in yt]}


def _news_process_links(text, ctype):
    """原样搬自 asa_server_monitor_reliable.py 的 process_news/tieba/patch_links"""
    if ctype == 'news':
        pat = r'(https://survivetheark\.com/index\.php[^\s\)\]]*)'
    elif ctype == 'tieba':
        pat = r'(https?://[^\s\)\]]*)'
    else:
        pat = r'(https://[^\s\)\]]*)'
    links = re.findall(pat, text)
    return re.sub(pat, '', text).strip(), links


def _news_cards(content_list, ctype='patch'):
    """原样搬自 asa_server_monitor_reliable.py:1515 create_cards_from_content"""
    cards = []
    for item in content_list:
        if isinstance(item, dict):
            text = item.get('text', '')
            images = item.get('images', []) or []
            youtube_links = item.get('youtube_links', []) or []
        else:
            text = item
            images = []
            youtube_links = []
        lines = text.splitlines() if text and text.strip() else []
        if lines:
            body_lines = ['<h3>%s</h3>' % lines[0]]
            content_links = []
            for line in lines[1:]:
                cleaned, links = _news_process_links(line, ctype)
                if cleaned:
                    body_lines.append(cleaned)
                content_links.extend(links)
            body = '\n'.join(body_lines)
        else:
            body = ''
            content_links = []
        md = body.strip()
        if md:
            cards.append({'type': 'markdown', 'content': md})
        imgs = [i for i in images if i and str(i).strip()]
        if content_links and imgs:
            for i, link in enumerate(content_links):
                cards.append({'type': 'picture', 'image': imgs[i % len(imgs)],
                              'tap_action': {'action': 'url', 'url_path': link},
                              'aspect_ratio': '16:9'})
        elif not content_links and imgs:
            for image in [i for i in imgs if not i.startswith('https://i.ytimg.com')]:
                cards.append({'type': 'picture', 'image': image,
                              'tap_action': {'action': 'url', 'url_path': image},
                              'aspect_ratio': '16:9'})
        for y in youtube_links:
            if 'watch?v=' in y:
                vid = y.split('watch?v=')[1].split('&')[0]
                if len(vid) == 11:
                    cards.append({'type': 'iframe',
                                  'url': 'https://www.youtube.com/embed/' + vid,
                                  'aspect_ratio': '16:9'})
    return cards


# v5949（用户口径「API 已转发，为啥 60s 后还是没取到」）：
#   实测 Discord “转发”消息 = type=0 + content 空 + embeds 空 + 仅 message_reference，
#   而计数器里还会有 type=12( CHANNEL_FOLLOW_ADD，关注频道系统提示 )。
#   处理：① 过滤系统消息；② 对 message_reference 尝试读取被引用原消息（同服务器可读，跨服务器失败静默跳过）。
_NEWS_KEEP_TYPES = (0, 19, 20, 21)   # DEFAULT / REPLY / 应用命令
_NEWS_REF_BUDGET = 6                 # 单次刷新最多回溯 6 条引用，避免请求爆量


def _news_keep_msg(m):
    try:
        return int(m.get('type') or 0) in _NEWS_KEEP_TYPES
    except Exception:
        return True


def _news_fetch_ref(m, cfg, budget):
    """转发/回复消息：尝试读被引用原消息（跨服务器会失败，返回 None）"""
    try:
        ref = m.get('message_reference') or {}
        cid = str(ref.get('channel_id') or '').strip()
        mid = str(ref.get('message_id') or '').strip()
        if not cid or not mid:
            return None
        if budget.get('n', 0) >= _NEWS_REF_BUDGET:
            return None
        budget['n'] = budget.get('n', 0) + 1
        ok, data = _discord_api('/channels/%s/messages/%s' % (cid, mid), cfg)
        if ok and isinstance(data, dict):
            return data
        return None
    except Exception:
        return None


def _news_merge_ref(ex, ref):
    """把被引用原消息的文本/图片/视频合并进当前条目"""
    try:
        r = _news_extract(ref)
        rt = (r.get('text') or '').strip()
        if not rt:
            return ex
        head = (ex.get('text') or '').strip()
        ex['text'] = (head + '\n' + rt) if head else rt
        ex['images'] = list(ex.get('images') or []) + list(r.get('images') or [])
        ex['youtube_links'] = list(ex.get('youtube_links') or []) + list(r.get('youtube_links') or [])
    except Exception:
        pass
    return ex


def _news_refresh(tab_id):
    """按需刷新（全局冷却 + after 增量）-> (cache, fetched:0|1, err)"""
    tab = _news_tab(tab_id)
    if not tab:
        return None, 0, 'unknown tab'
    cur = _news_read(tab_id) or {}
    now = int(time.time())
    if int(cur.get('fetched_at') or 0) and (now - int(cur.get('fetched_at') or 0)) < NEWS_COOL_SEC:
        return cur, 0, None
    cfg = _news_cfg()
    if not cfg:
        return cur, 0, 'news 未配置（缺 dino_backend.config.json）'
    cid = str((cfg.get('channels') or {}).get(tab_id) or '').strip()
    if not cid:
        return cur, 0, 'news 未配置该 Tab 的频道 ID：' + tab_id
    with _news_lock:
        cur = _news_read(tab_id) or {}
        now = int(time.time())
        if int(cur.get('fetched_at') or 0) and (now - int(cur.get('fetched_at') or 0)) < NEWS_COOL_SEC:
            return cur, 0, None
        after = str(cur.get('last_message_id') or '').strip()
        q = '?limit=50' + (('&after=' + after) if after else '')
        ok, data = _discord_api('/channels/%s/messages%s' % (cid, q), cfg)
        if not ok:
            return cur, 0, 'Discord 拉取失败：' + str(data)
        msgs = data if isinstance(data, list) else []
        msgs = list(reversed(msgs))
        if not msgs:
            cur['fetched_at'] = now
            _news_write(tab_id, cur)
            return cur, 1, None
        by_id = {str(m.get('id')): m for m in (cur.get('messages') or [])}
        for m in msgs:
            if isinstance(m, dict):
                by_id[str(m.get('id'))] = m
        allm = sorted(by_id.values(), key=lambda x: int(x.get('id') or 0))[-NEWS_KEEP_MSGS:]
        _cards = []
        _refbudget = {'n': 0}
        for _m in allm:
            if not _news_keep_msg(_m):
                continue                          # v5949：跳过「关注频道」等系统消息
            _ex = _news_extract(_m)
            if _m.get('message_reference'):
                _refm = _news_fetch_ref(_m, cfg, _refbudget)
                if _refm:
                    _ex = _news_merge_ref(_ex, _refm)
            for _c in _news_cards([_ex], tab[2]):
                _c['mid'] = str(_m.get('id') or '')   # v5927：图片过期时按 mid 单条修复
                _cards.append(_c)
        new = {
            'ok': True, 'tab': tab_id, 'name': tab[1],
            'updated': time.strftime('%Y-%m-%d %H:%M:%S'),
            'fetched_at': now,
            'last_message_id': str(allm[-1].get('id') or '') if allm else '',
            'messages': allm,
            'cards': _cards,
        }
        _news_write(tab_id, new)
        return new, 1, None


def _news_imgfix(tab_id, mid):
    """单条消息附件链接修复（Discord CDN 签名过期时用）-> (images|None, err)"""
    tab = _news_tab(tab_id)
    if not tab:
        return None, 'unknown tab'
    k = tab_id + '|' + str(mid)
    now = int(time.time())
    if _news_img_at.get(k) and (now - _news_img_at[k]) < NEWS_IMG_COOL_SEC:
        return None, 'cooling'
    cfg = _news_cfg()
    if not cfg:
        return None, 'news 未配置'
    cid = str((cfg.get('channels') or {}).get(tab_id) or '').strip()
    if not cid:
        return None, 'news 未配置该 Tab 的频道 ID'
    ok, data = _discord_api('/channels/%s/messages/%s' % (cid, mid), cfg)
    _news_img_at[k] = now
    if not ok or not isinstance(data, dict):
        return None, str(data)
    cur = _news_read(tab_id) or {}
    msgs = cur.get('messages') or []
    for i, m in enumerate(msgs):
        if str(m.get('id')) == str(mid):
            msgs[i] = data
            break
    cur['messages'] = msgs
    _news_write(tab_id, cur)
    return (_news_extract(data).get('images') or []), None


def _news_zh_path(tab_id):
    return os.path.join(NEWS_CACHE_DIR, tab_id + '_zh.json')


def _news_zh_read(tab_id):
    try:
        with open(_news_zh_path(tab_id), 'r', encoding='utf-8') as f:
            return (json.load(f) or {}).get('map') or {}
    except Exception:
        return {}


def _news_zh_merge(tab_id, items):
    """按 id 合并，已存在不覆盖（多客户端并发安全）"""
    cur = _news_zh_read(tab_id)
    added = 0
    for it in (items or []):
        if not isinstance(it, dict):
            continue
        k = str(it.get('id') or '').strip()
        v = str(it.get('text') or it.get('zh') or '').strip()
        if k and v and not cur.get(k):
            cur[k] = v[:2000]
            added += 1
    try:
        os.makedirs(NEWS_CACHE_DIR, exist_ok=True)
        with open(_news_zh_path(tab_id), 'w', encoding='utf-8') as f:
            json.dump({'map': cur, 'ts': int(time.time())}, f, ensure_ascii=False)
    except Exception:
        pass
    return added, cur


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, fmt, *args):
        pass

    def _cors(self):
        # v6275（2026-11-08）：CORS 加固 + 诊断
        #   现象：/api/tasks、/api/ipwatch 返回 200 但无任何 CORS 头 ⇒ 浏览器 fetch 被拒。
        #   ① ALLOW_ORIGIN 为空/空白时用正式域名兜底（防环境变量被设成空串）
        #   ② 请求带 Origin 且在**白名单**内 ⇒ 回显该 Origin（兼容多前端/本地调试）
        #   ③ X-Dino-Trace 用于区分「后端没发」与「被 Cloudflare 剥离」
        _ao = str(ALLOW_ORIGIN or '').strip() or 'https://dino.whiterober.ccwu.cc'
        try:
            _org = str(self.headers.get('Origin') or '').strip()
        except Exception:
            _org = ''
        _wl = (_ao, 'https://dino.whiterober.ccwu.cc',
               'http://localhost:8080', 'http://127.0.0.1:8080')
        self.send_header('Access-Control-Allow-Origin', _org if (_org and _org in _wl) else _ao)
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, HEAD')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '86400')
        self.send_header('X-Dino-Trace', 'cors-v6275')

    # ⭐ 2026-09-22（方案A）：并发令牌改为**按请求粒度**持有 —— 只包住「一次请求的处理（含响应写入）」，
    #   连接空闲等待下一请求时不占令牌（原先包在 finish_request 外层 = 占整条连接生命周期）。
    def _busy_503(self):
        body = b'{"ok":false,"busy":true,"error":"server busy, retry"}'
        self.close_connection = True   # 关连接：防未读尽的 POST body 被当成下一个请求
        try:
            self.send_response(503)
            self._cors()
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Retry-After', '1')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Connection', 'close')
            self.end_headers()
            try:
                self.wfile.write(body)
            except Exception:
                pass
        except Exception:
            pass

    def _guarded(self, fn):
        if not _CONC.acquire(blocking=False):
            self._busy_503()
            return
        try:
            return fn()
        except Exception:
            # 2026-11-05 方案A：记录被 handle_error 吞掉的栈（行为不变，仍原样抛出）
            _sexc('route', '%s %s' % (getattr(self, 'command', ''), getattr(self, 'path', '')))
            raise
        finally:
            _CONC.release()

    def _send(self, code, obj, ctype='application/json; charset=utf-8'):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8') if ctype.startswith('application/json') else obj
        self.send_response(code)
        self._cors()
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        # 2026-08-28：HEAD 请求只发响应头不写 body（前端 lbHeadLm 用 HEAD 探测 Last-Modified，
        # 之前无 do_HEAD → 501 + 无 CORS 头 → 增量缓存失效每次全量下载 + 浏览器 CORS 报错）
        if getattr(self, '_head_only', False):
            return
        self.wfile.write(body)

    def _send_file(self, path, ctype):
        try:
            with open(path, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Last-Modified', self.date_time_string(os.path.getmtime(path)))
            self.send_header('ETag', '"%x"' % (len(data) ^ int(os.path.getmtime(path))))
            self.end_headers()
            if getattr(self, '_head_only', False):
                return
            self.wfile.write(data)
        except FileNotFoundError:
            self._send(404, {'ok': False, 'error': 'not found'})

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_HEAD(self):
        """HEAD 请求：与 GET 同逻辑但只发响应头（前端增量缓存探测 Last-Modified 依赖）。"""
        self._head_only = True
        try:
            self._guarded(self._do_GET_body)   # v2026-09-22（方案A）：请求级令牌
        finally:
            self._head_only = False

    def do_GET(self):
        """v2026-09-22（方案A）：令牌只包住「一次请求的处理」。"""
        self._guarded(self._do_GET_body)

    def _do_GET_body(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == '/healthz':
            self._send(200, {'ok': True, 'service': 'dino-backend', 'servers': sorted(SERVERS.keys())})
        elif path in ('/api/arkbackup/list', '/api/arkbackup/audit'):
            # P0 只读：回档点清单 / 审计日志（方案 §6.1 / §6.8）
            _qs_ab = parse_qs(parsed.query)
            _u_ab = _srvctl_guard(self, _qs_ab, need_token=True)
            if not _u_ab:
                return
            if _arkbk is None:
                self._send(500, {'ok': False, 'error': 'ark_backup module not loaded'})
                return
            _ab_ab = (_qs_ab.get('server') or [''])[0].strip()
            if not _ab_ab:
                self._send(400, {'ok': False, 'error': 'server required'})
                return
            try:
                if path.endswith('/list'):
                    _r_ab = _arkbk.list_points(_ab_ab)
                else:
                    try:
                        _lim_ab = int((_qs_ab.get('limit') or ['50'])[0])
                    except Exception:
                        _lim_ab = 50
                    _r_ab = _arkbk.read_audit(_ab_ab, _lim_ab)
            except Exception as _e_ab:
                self._send(500, {'ok': False, 'error': '%s: %s' % (type(_e_ab).__name__, _e_ab)})
                return
            self._send(200, _r_ab)

        elif path in ('/api/arkbackup/job', '/api/arkbackup/status'):
            _qs_g = parse_qs(parsed.query)
            _u_g = _srvctl_guard(self, _qs_g, need_token=True)
            if not _u_g:
                return
            if _arkbk is None:
                self._send(500, {'ok': False, 'error': 'ark_backup module not loaded'})
                return
            _one = lambda k: ((_qs_g.get(k) or ['']) or [''])[0].strip()

            if path == '/api/arkbackup/job':
                _jid = _one('id') or _one('jobId')
                with _ARKBK_JOB_LOCK:
                    _job = dict(_ARKBK_JOBS.get(_jid) or {})
                if not _job:
                    self._send(404, {'ok': False, 'code': 'job_not_found', 'id': _jid})
                    return
                _pc = _job.get('precheck') or {}
                _job['loss'] = len(_pc.get('loss') or [])
                _job['dup'] = len(_pc.get('dup') or [])
                _job['safe'] = len(_pc.get('safe') or [])
                _job['notice'] = _pc.get('notice')
                _job['ageSec'] = int(time.time() - _job.get('t0', time.time()))
                self._send(200, _job)
                return

            if path == '/api/arkbackup/lastjob':
                # v6057（用户口径「重新打开安全回档，进度条就消失了」）：
                # 前端 job 只存在内存里，关掉浮窗即丢 ⇒ 提供「该服最近一次 job」查询，
                # 重开面板时可把进度（含失败原因）恢复出来。
                _arkbk_job_gc()      # v6058：查询前先 GC，旧失败条不再被恢复出来
                _ls = _one('server')
                _best = None
                _now_lj = time.time()
                with _ARKBK_JOB_LOCK:
                    for _v in _ARKBK_JOBS.values():
                        if _ls and _v.get('server') != _ls:
                            continue
                        # v6058：超过保留期的不返回 —— 否则「上次失败」会永远挂在底栏
                        if _now_lj - float(_v.get('tEnd') or _v.get('t0') or 0) > _ARKBK_JOB_KEEP:
                            continue
                        if _best is None or float(_v.get('t0') or 0) > float(_best.get('t0') or 0):
                            _best = _v
                    _best = dict(_best) if _best else None
                if not _best:
                    self._send(200, {'ok': True, 'job': None})
                    return
                _pc2 = _best.get('precheck') or {}
                _best['loss'] = len(_pc2.get('loss') or [])
                _best['dup'] = len(_pc2.get('dup') or [])
                _best['safe'] = len(_pc2.get('safe') or [])
                _best['notice'] = _pc2.get('notice')
                _best['ageSec'] = int(time.time() - _best.get('t0', time.time()))
                self._send(200, {'ok': True, 'job': _best})
                return

            if path == '/api/arkbackup/dismiss':
                # v6058（按推荐补全）：手动清除已结束的 job 记录 —— 用户点「清除」把
                # 失败/完成条从底栏抹掉，不必等 30 分钟 GC。跑着的 job 不允许清。
                _ds = _one('server')
                _dj = _one('jobId')
                _rm = 0
                with _ARKBK_JOB_LOCK:
                    for _k in list(_ARKBK_JOBS.keys()):
                        _v = _ARKBK_JOBS.get(_k) or {}
                        if _dj and _v.get('id') != _dj:
                            continue
                        if _ds and _v.get('server') != _ds:
                            continue
                        if _v.get('phase') not in ('done', 'failed'):
                            continue
                        _ARKBK_JOBS.pop(_k, None)
                        _rm += 1
                self._send(200, {'ok': True, 'removed': _rm,
                                 'server': _ds, 'jobId': _dj})
                return

            # /api/arkbackup/status
            _srv_st = _one('server')
            _servers_st = [_srv_st] if _srv_st else list(_arkbk._ALL_SERVERS)
            _out_st = {}
            for _s in _servers_st:
                _r = _arkbk_rcon_alive(_s)
                try:
                    _md = _arkbk.detect_map_dir(_s)[0]
                    _act = _arkbk._active_name(_s, _md) if _md else ''
                    _p = os.path.join(_arkbk.ARK_ROOT, _s, 'ShooterGame', 'Saved',
                                      'SavedArks', _md or '', _act) if _act else ''
                    _stt = os.stat(_p) if (_p and os.path.isfile(_p)) else None
                    _r['activeFile'] = _act
                    _r['activeMB'] = round(_stt.st_size / 1048576.0, 1) if _stt else 0
                    _r['activeMtime'] = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(_stt.st_mtime)) if _stt else ''
                except Exception as _e_st:
                    _r['detectError'] = str(_e_st)
                with _ARKBK_JOB_LOCK:
                    _r['busyJob'] = _ARKBK_BUSY.get(_s)
                _out_st[_s] = _r
            self._send(200, {'ok': True, 'servers': _out_st, 'count': len(_out_st)})
            return
        elif path in ('/api/arkbackup/presence', '/api/arkbackup/profiles'):
            # v6043：玩家进出流水 / 可恢复的角色档案（只读文件名，不解压）
            _qs_p = parse_qs(parsed.query)
            _u_p = _srvctl_guard(self, _qs_p, need_token=True)
            if not _u_p:
                return
            if _arkbk is None:
                self._send(500, {'ok': False, 'error': 'ark_backup module not loaded'})
                return
            _ab_p = ((_qs_p.get('server') or ['']) or [''])[0].strip()
            if not _ab_p:
                self._send(400, {'ok': False, 'error': 'server required'})
                return
            try:
                if path.endswith('/presence'):
                    _r_p = _arkbk.read_presence(_ab_p)
                else:
                    _eos_p = ((_qs_p.get('eos') or ['']) or [''])[0].strip() or None
                    _r_p = _arkbk.list_profiles(_ab_p, _eos_p)
            except Exception as _e_p:
                self._send(500, {'ok': False, 'error': '%s: %s' % (type(_e_p).__name__, _e_p)})
                return
            self._send(200, _r_p)
            return
        elif path == '/webp_map.json':
            # WebP 缩略图映射（前端省流；后端动态维护，一键增量后自动更新）
            self._send(200, _webp_map())
        elif path == '/api/themes' or path.endswith('/api/states/sensor.asa_server_themes') or path.endswith('/api/services/script/asa_server_themes'):
            self._send(200, {'ok': True, 'server_themes': SERVER_THEMES})
        # 兼容：前端轮询 HA sensor（sensor.refresh_tamed_status / search_wild_status / player_pos_status / track_dino_status）
        elif path.endswith('/api/states/sensor.refresh_tamed_status') or path.endswith('/api/states/sensor.search_wild_status') \
                or path.endswith('/api/states/sensor.player_pos_status') or path.endswith('/api/states/sensor.track_dino_status') \
                or path.endswith('/api/states/sensor.stop_track_dino_status') or path.endswith('/api/states/sensor.get_dino_status'):
            sen = path.rsplit('/', 1)[-1]
            s = STATUS_MEM.get(sen)
            if not s:
                s = {'state': 'unknown', 'attributes': {}}
            self._send(200, s)
        elif path == '/api/harvest_flows':
            qs = parse_qs(parsed.query)
            username = (qs.get('username') or [''])[0].strip()
            nick = (qs.get('nick') or [''])[0].strip()
            ok_auth, _err = _harvest_auth(username, nick)
            if not ok_auth:
                self._send(401, {'ok': False, 'error': _err})
                return
            self._send(200, {'ok': True, 'doc': _load_harvest_flows(username)})
        elif path == '/api/user_prefs':
            qs = parse_qs(parsed.query)
            username = (qs.get('username') or [''])[0].strip()
            nick = (qs.get('nick') or [''])[0].strip()
            ok_auth, _err = _harvest_auth(username, nick)
            if not ok_auth:
                self._send(401, {'ok': False, 'error': _err})
                return
            self._send(200, {'ok': True, 'data': _load_user_prefs(username)})
        elif path == '/api/cfg_rules':
            # 2026-10-27：配置改动规则只读接口（本地读 ini + 拼 CF 基线 + mtime 缓存/ETag/304）
            _qs = parse_qs(parsed.query)
            if ((_qs.get('all') or [''])[0].strip().lower() in ('1', 'true', 'yes')):
                try:
                    _ea, _ba = _cfg_all_slim()
                except Exception as _e:
                    self._send(500, {'ok': False, 'error': 'cfg_all failed', 'detail': repr(_e)})
                    return
                _ia = (self.headers.get('If-None-Match') or '').strip()
                if _ia and _ea and _ia == _ea:
                    self.send_response(304)
                    self._cors()
                    self.send_header('ETag', _ea)
                    self.send_header('Cache-Control', 'no-cache')
                    self.end_headers()
                    return
                self.send_response(200)
                self._cors()
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(_ba)))
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('ETag', _ea or '')
                self.end_headers()
                if not getattr(self, '_head_only', False):
                    self.wfile.write(_ba)
                return
            _server = (_qs.get('server') or [''])[0].strip()
            _fk = ((_qs.get('file') or [''])[0].strip() or 'GUS').upper()
            if _server not in SERVERS:
                self._send(400, {'ok': False, 'error': 'unknown server', 'servers': sorted(SERVERS.keys())})
                return
            if _fk not in CFG_FILE_MAP:
                self._send(400, {'ok': False, 'error': 'unknown file', 'files': sorted(CFG_FILE_MAP.keys())})
                return
            try:
                _etag, _body = _cfg_rules_read(_server, _fk)
            except Exception as _e:
                self._send(500, {'ok': False, 'error': 'cfg_rules failed', 'detail': repr(_e)})
                return
            _inm = (self.headers.get('If-None-Match') or '').strip()
            if _inm and _etag and _inm == _etag:
                self.send_response(304)
                self._cors()
                self.send_header('ETag', _etag)
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                return
            try:
                self.send_response(200)
                self._cors()
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(_body)))
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('ETag', _etag or '')
                self.end_headers()
                if not getattr(self, '_head_only', False):
                    self.wfile.write(_body)
            except Exception:
                _sexc('get_static_send')
                pass
        elif path == '/api/server_config':
            # P3：公开读域名 + ASA token 掩码（**永不返回明文**）
            # v6218：追加 IP 切换三开关真值 —— 前端「切换演练」模块要用（均为非敏感 bool）。
            #   注意 enable/dry 走 _restart_*_now()（配置优先，环境变量其次），
            #   不能直接读 _srv_cfg_read()，否则环境变量锁定时显示与真实行为不一致。
            _sd = _srv_cfg_read()
            self._send(200, {'ok': True,
                             'server_domain': _sd.get('server_domain') or '',
                             'asa_base': _sd.get('asa_base') or 'https://asa.whiterober.com',
                             'asa_token_masked': _asa_mask(_sd.get('asa_token') or ''),
                             'asa_configured': bool(_sd.get('asa_token')),
                             'cf_key_masked': _asa_mask(_sd.get('cf_key') or ''),
                             'cf_key_configured': bool(_sd.get('cf_key')),
                             'mods_policy': _mods_policy(),
                             'ipwatch_restart': bool(_restart_enable_now()),
                             'ipwatch_restart_dry': bool(_restart_dry_now()),
                             'ipwatch_announce_real': bool(_restart_announce_real_now()),
                             'ipwatch_env_locked': bool(RESTART_ENABLE or os.environ.get('IPWATCH_RESTART_DRY') is not None),
                             'update_dry': bool(_upd_dry_default()),
                             'zh_patch': _zh_cfg_of(_sd)})
            return
        elif path == '/api/ipwatch':
            # v6121：公网 IP 监视状态（只读；仅域名/IP 等非敏感信息）
            with _IPWATCH_LOCK:
                _snap = dict((k, _IPWATCH[k]) for k in _IPWATCH)
                _snap['history'] = list(_IPWATCH['history'])[-20:]
            _snap['ok'] = True
            _snap['stateFile'] = os.path.basename(IPWATCH_STATE_FILE)
            # v6160：changedAt 转 epoch 秒，供前端做「服务器启动时间 < IP 变化时间」判定
            _snap['changedAtTs'] = 0
            try:
                if _snap.get('changedAt'):
                    _snap['changedAtTs'] = int(time.mktime(
                        time.strptime(str(_snap['changedAt']), '%Y-%m-%d %H:%M:%S')))
            except Exception:
                _snap['changedAtTs'] = 0
            # v6170（用户口径）：旧 IP —— 前端 tips 需显示「旧IP → 新IP」，
            #   取 history 中最近一条 event=changed 的 prev；无变更记录时为空。
            _snap['prevIp'] = ''
            try:
                for _h in reversed(_snap.get('history') or []):
                    if isinstance(_h, dict) and _h.get('event') == 'changed':
                        _snap['prevIp'] = str(_h.get('prev') or '')
                        break
            except Exception:
                _snap['prevIp'] = ''
            try:
                _snap['restart'] = _restart_snapshot()   # v6129（M3）：重启编排状态
            except Exception:
                _snap['restart'] = {'running': False}
            self._send(200, _snap)
            return
        elif path == '/api/update/cache/versions':
            # v6402（用户口径）：版本更新缓存 → **可选历史版本**（时间新→旧；只列当前主版本）
            _qs_v = parse_qs(parsed.query)
            _u_v = _srvctl_guard(self, _qs_v)
            if not _u_v:
                return
            try:
                _rv = _depot_versions()
                self._send(200, _rv)
            except Exception as e:
                self._send(500, {'ok': False, 'code': 'versions_err', 'error': repr(e)[:300]})
            return
        elif path == '/api/update/steam/cred':
            # v6402（用户口径「密码按账号级别缓存，越久越好」）：**只回账号名与是否已存密码**
            _qs_c = parse_qs(parsed.query)
            _u_c = _srvctl_guard(self, _qs_c)
            if not _u_c:
                return
            self._send(200, {'ok': True, 'accounts': _steam_cred_list(),
                             'path': STEAM_CRED_FILE})
            return
        elif path == '/api/update/permcheck':
            # v6255b（权限加固·诊断）：在**后端进程自己的身份**下实测目标目录写/覆盖/替换能力。
            #   只碰探针临时文件，不动任何真实游戏文件 —— 真跑前用它确认会不会翻车。
            _qs_pc = parse_qs(parsed.query)
            _u_pc = _srvctl_guard(self, _qs_pc)
            if not _u_pc:
                return
            _srv_pc = str((_qs_pc.get('server') or ['Isl'])[0]).strip() or 'Isl'
            if _srv_pc not in SERVERS:
                self._send(400, {'ok': False, 'code': 'bad_server',
                                 'error': u'未知服务器：%s' % _srv_pc})
                return
            try:
                _r_pc = _upd_perm_check(_srv_pc)
            except Exception:
                _sexc('upd_permcheck')
                _r_pc = {'ok': False, 'verdict': 'error', 'error': 'permcheck_fail'}
            self._send(200, _r_pc)
            return
        elif path == '/api/mods/status':
            # v6283（Round 1 只读）：MOD 卡 —— 磁盘扫描 83374/<pid>_<fid>，不写任何文件
            _qs2 = parse_qs(parsed.query)
            if not _srvctl_guard(self, _qs2):
                return
            self._send(200, mods_status())
            return
        elif path == '/api/api/status':
            # v6283（Round 1 只读）：API 卡 —— 库一致性 + 缓存就绪 + 插件矩阵
            _qs3 = parse_qs(parsed.query)
            if not _srvctl_guard(self, _qs3):
                return
            self._send(200, api_status())
            return
        elif path == '/api/update/status':
            # v6206：SteamCMD Cache 状态（只读）—— 缓存 buildid / 11 台对比 / 落后清单
            #   ?players=1 才逐台查在线人数（慢接口，前端默认不传）
            # v6206b：**必须本地 parse_qs** —— 本作用域没有 `qs`/`g()`（它们只存在于个别分支内部），
            #   原写法导致 UnboundLocalError -> 每个请求都 502。
            _qs_u = parse_qs(parsed.query)
            _u_upd = _srvctl_guard(self, _qs_u)
            if not _u_upd:
                return
            _with_p = str((_qs_u.get('players') or [''])[0]).lower() in ('1', 'true', 'yes')
            _r_up = _upd_status(include_players=_with_p)
            # v6228（P1.5）：版本档位判定 + AsaApi 缓存状态（供 §14 分发确认浮窗）
            try:
                _r_up['verKind'] = _upd_ver_info()
            except Exception:
                _sexc('upd_verkind')
                _r_up['verKind'] = {'kind': 'unknown', 'from': '', 'to': '', 'err': 'calc_fail'}
            # v6233：默认预演开关（系统管理「服务器更新预演」区块展示用）
            try:
                _r_up['defaultDry'] = bool(_upd_dry_default())
            except Exception:
                _r_up['defaultDry'] = True
            # v6296（用户口径）：下发 Steam 标识 —— 前端把 buildId 链到 SteamDB 的 depot manifest 页
            _r_up['depotId'] = UPDATE_DEPOT_ID
            _r_up['appId'] = UPDATE_APP_ID
            # v6230（用户口径「**只从版本号判断**」）：**删除 v6228 的 buildId 兜底**。
            #   原兜底会把「版本号没变但 buildId 变了」判成 forced；
            #   但那属于「同版本重打包」，按用户规则仍是非强制（只认版本号）。
            try:
                _as_st, _as_raw, _as_meta = _asaapi_state()
                _r_up['asaapi'] = {'state': _as_st, 'raw': _as_raw,
                                   # v6228：text = 剥 HTML 后的**英文原文**（前端浮窗直接展示，不翻译）
                                   'text': _AS_WS.sub(' ', _AS_TAG.sub(' ', _as_raw or '')).strip(),
                                   'hit': bool(_as_meta.get('hit')),
                                   'updated': _as_meta.get('updated') or '',
                                   'fetchedAt': int(_as_meta.get('fetchedAt') or 0),
                                   'total': int(_as_meta.get('total') or 0),
                                   'readyStr': 'Automated Cache Build: SUCCESS',
                                   'source': 'api_cache'}
            except Exception:
                _sexc('upd_asaapi')
                _r_up['asaapi'] = {'state': 'unknown', 'raw': '', 'hit': False,
                                   'total': 0, 'source': 'api_cache'}
            # v6212：附 SteamCMD 更新进度摘要（只读日志推导；**不含日志正文**，用户明确不要）
            try:
                _sp = _upd_steam_progress()
                _sp.pop('steps', None)          # steps 只给任务总线用，status 里精简
                _r_up['steam'] = _sp
            except Exception:
                _sexc('upd_status_steam')
                _r_up['steam'] = {'found': False, 'phase': 'na', 'msg': u'日志解析失败'}
            self._send(200, _r_up)
            return
        elif path == '/api/zh/status':
            # v6237（B1）：汉化补丁只读状态。?local=1 只跑本机扫描（秒回，首屏用）；
            #   不传则含远端 Google Drive 探测（首次约 2~3 秒，TTL 30 分钟）。?force=1 强刷远端。
            _qs_z = parse_qs(parsed.query)
            _u_z = _srvctl_guard(self, _qs_z)
            if not _u_z:
                return
            _loc_z = str((_qs_z.get('local') or [''])[0]).lower() in ('1', 'true', 'yes')
            _frc_z = str((_qs_z.get('force') or [''])[0]).lower() in ('1', 'true', 'yes')
            try:
                _r_z = _zh_status(include_remote=(not _loc_z), force=_frc_z)
            except Exception:
                _sexc('zh_status')
                _r_z = {'ok': False, 'error': 'status_fail'}
            self._send(200, _r_z)
            return
        elif path == '/api/srvctl/status':
            # P3：转发 ASA GET /server-status（仅读）；仅二级管理员可读
            _qs = parse_qs(parsed.query)
            _u = _srvctl_guard(self, _qs)   # v6023：token 优先，无 token 时兼容 username 直报
            if not _u:
                return
            _cfg = _srvctl_cfg()
            if not _cfg['token']:
                self._send(200, {'ok': False, 'code': 'asa_no_token',
                                 'error': 'asa_token 未配置', 'servers': []})
                return
            _t0 = time.time()
            try:
                _code, _text = _asa_http('GET', _cfg['base'] + '/server-status', _cfg['token'],
                                         None, timeout=_cfg['timeout'], verify=_cfg['verify'])
            except Exception as _e:
                self._send(504, {'ok': False, 'code': 'asa_timeout', 'error': str(_e)})
                return
            if not (200 <= _code < 300):
                _cd = 'asa_unauthorized' if _code in (401, 403) else 'asa_error'
                self._send(502, {'ok': False, 'code': _cd, 'error': 'ASA HTTP %s' % _code})
                return
            _arr = []
            try:
                _arr = (json.loads(_text) or {}).get('servers') or []
            except Exception:
                _arr = []
            _want = (_qs.get('servers') or [''])[0].strip()
            _sel = set(x.strip() for x in _want.split(',') if x.strip()) if _want else None
            _rev = {}
            for _k, _v in SERVER_THEMES.items():
                _rev[(_v or {}).get('name') or ''] = _k
            _out = []
            for _it in _arr:
                _pn = str(_it.get('ProfileName') or '')
                # P3b：ASA /server-status 返回的 ProfileName 是**英文 ID**（Isl/Sco/…），
                # 而转发 /start 等用的是**中文名**（对齐 AppDaemon）⇒ 两条路都要认
                _sid = _pn if _pn in SERVERS else _rev.get(_pn, '')
                if _sel and _sid not in _sel:
                    continue
                _out.append({'server': _sid, 'profileName': _pn,
                             'status': str(_it.get('Status') or ''),
                             'version': str(_it.get('OfficialServerVersion') or ''),
                             # v5981：该服**实际运行**版本（前端角标显示用；OfficialServerVersion 是官方网络值，语义不同）
                             'serverVersion': str(_it.get('ServerVersion') or ''),
                             # v6160：本次进程启动时刻（epoch 秒）—— IP 失效判定用；0 = 取不到
                             'bootAt': _srv_boot_at(_sid) if _sid else 0})
            # v6231：官方服务器版本改走**权威取数链**（官方 CDN ini > 官方服务器列表众数 > 资讯广场）
            #   原先是纯资讯广场 patch_pc（Discord 抓取不稳，实测滞后：官服已 v97.5 而它只到 97.13）
            try:
                _oe2 = _official_version_ex()
            except Exception:
                _oe2 = {'ver': '', 'src': '', 'err': 'chain_fail'}
            self._send(200, {'ok': True, 'servers': _out,
                             'official': _oe2.get('ver') or '',
                             # v6280：状态词（online/deploying/down/unknown），前端做中文标识
                             'officialState': _oe2.get('state') or 'unknown',
                             'officialSrc': _oe2.get('src') or '',
                             'officialErr': _oe2.get('err') or '',
                             'ms': int((time.time() - _t0) * 1000)})
            return
        elif path == '/api/health':
            # v6155：后端健康/状态（**无鉴权、极轻**）—— 前端「系统管理 → 后端服务」直读
            self._send(200, _health_payload())
            return
        elif path == '/api/tasks':
            # v6122：统一任务列表（全服共享一份；权限跟随所在浮窗 = 同一 srvctl guard）
            _qs = parse_qs(parsed.query)
            _u = _srvctl_guard(self, _qs)
            if not _u:
                return
            try:
                _since = int((_qs.get('since') or ['0'])[0] or 0)
            except Exception:
                _since = 0
            _r = _utask_list(_since)
            _r['ok'] = True
            try:
                _r['locks'] = _srv_lock_snapshot()   # v6135：锁表供前端置灰/提示
            except Exception:
                _r['locks'] = {}
            # v6278（用户口径 2026-11-08「启动队列在不同客户端显隐不一致」）：
            #   队列状态随 **/api/tasks 一起下发**（全量快照，与 changed 无关）。
            #   前端本来就在轮询 /api/tasks（1.5s），这样每个客户端拿到的队列数据
            #   完全同源、同一时刻 ⇒ 显隐一致；不再依赖各端自己额外拉 /api/srvctl/startq。
            try:
                _r['startq'] = _startq_view()
            except Exception:
                _r['startq'] = None
            self._send(200, _r)
            return
        elif path == '/api/srvctl/observe':
            # P1（v5983）：真实进度观测（只读；读服务器日志里程碑 + 主存档 mtime）
            _qs = parse_qs(parsed.query)
            _u = _srvctl_guard(self, _qs)   # v6023：token 优先，无 token 时兼容 username 直报
            if not _u:
                return
            _srv = (_qs.get('server') or [''])[0].strip()
            if _srv not in SERVERS:
                self._send(400, {'ok': False, 'error': 'bad server', 'code': 'bad_server'})
                return
            _lg = _srv_observe_log(_srv)
            _ak = _srv_observe_ark(_srv, _lg.get('map') or '')
            self._send(200, {'ok': True, 'server': _srv, 'log': _lg, 'ark': _ak,
                             'ts': int(time.time())})
            return
        elif path == '/api/srvctl/job':
            # P3：长任务轮询
            _qs = parse_qs(parsed.query)
            _u = _srvctl_guard(self, _qs)   # v6023：token 优先，无 token 时兼容 username 直报
            if not _u:
                return
            _jid = (_qs.get('id') or [''])[0].strip()
            _v = _srvctl_job_view(_jid)
            if not _v:
                self._send(404, {'ok': False, 'code': 'no_job', 'error': 'job not found'})
                return
            self._send(200, {'ok': True, 'job': _v})
            return
        elif path == '/api/srvctl/arkcheck':
            # v6007：存档完整性校验（服务器本地 SQLite quick_check，只读）
            _qs = parse_qs(parsed.query)
            _u = _srvctl_guard(self, _qs)   # v6023：token 优先，无 token 时兼容 username 直报
            if not _u:
                return
            _srv = (_qs.get('server') or [''])[0].strip()
            if _srv not in SERVERS:
                self._send(400, {'ok': False, 'error': 'bad server', 'code': 'bad_server'})
                return
            self._send(200, {'ok': True, 'check': _srv_ark_quickcheck(_srv)})
            return
        elif path == '/api/srvctl/startq':
            # v6004：多服启动队列状态（只读）
            _qs = parse_qs(parsed.query)
            _u = _srvctl_guard(self, _qs)   # v6023：token 优先，无 token 时兼容 username 直报
            if not _u:
                return
            self._send(200, {'ok': True, 'queue': _startq_view()})
            return
        elif path == '/api/cfg_rules/refresh_status':
            self._send(200, {'ok': True, 'job': _cfg_job_view()})
        elif path == '/api/wiki_probe':
            # v72e：wikily 抓取可行性探测（出网 / 耗时 / 解析 / 缓存目录）
            # v286：src=ark -> 探测 ARK Wiki（第二数据源，取 Usage/Notes 段）
            _qs = parse_qs(parsed.query)
            _slug = (_qs.get('slug') or ['ankylosaurus'])[0].strip()
            _src = (_qs.get('src') or ['wikily'])[0].strip().lower()
            self._send(200, _ark_probe(_slug) if _src == 'ark' else _wiki_probe(_slug))
        elif path == '/api/dino/tips':
            # v5740：dododex 玩家技巧（前端「技巧」TAB）。?slug=rex 或 ?cls=Rex_Character_BP_C
            #   force=1 强制刷新；返回 {ok, slug, ts, summary, rawN, items[]}
            _qs = parse_qs(parsed.query)
            _sl = (_qs.get('slug') or [''])[0].strip()
            _cl = (_qs.get('cls') or [''])[0].strip()
            _fo = ((_qs.get('force') or [''])[0].strip().lower() in ('1', 'true', 'yes'))
            self._send(200, _dodo_get(_sl or _cl, _fo))
        elif path == '/api/dino/wikitext':
            # v5745：某物种「wikily 原文经 AI 整理后」的结果（按物种共享缓存；未整理过返回 null）
            _qs = parse_qs(parsed.query)
            _sl = (_qs.get('slug') or [''])[0].strip()
            _cl = (_qs.get('cls') or [''])[0].strip()
            _sg = _dodo_slug(_sl or _cl)
            _ck = _cache_slug(_sl or _cl) or _sg   # v5871：按变体隔离的缓存键
            _d = _wt_read(_ck)
            self._send(200, {'ok': True, 'slug': _ck, 'dodoSlug': _sg, 'blocks': _d,
                             'ready': bool(_d), 'fields': list(_WT_BLOCKS)})
        elif path == '/api/dino/tips/zh':
            # v5740：已翻译缓存（{tipId: 中文}）。前端命中即直接渲染，未命中才调 AI 翻译
            _qs = parse_qs(parsed.query)
            _sl = (_qs.get('slug') or [''])[0].strip()
            _cl = (_qs.get('cls') or [''])[0].strip()
            _z, _sg = _dodo_zh_doc(_sl or _cl)
            _m = _z.get('map') or {}
            self._send(200, {'ok': True, 'slug': _sg, 'map': _m,
                             'merged': _z.get('merged') or None, 'count': len(_m)})
        elif path == '/api/item/tips':
            # v5819：物品「指南」AI 整理结果（全服共享缓存）。?cls=Stopwatch
            _qs = parse_qs(parsed.query)
            _cl = (_qs.get('cls') or [''])[0].strip()
            self._send(200, {'ok': True, 'cls': _cl, 'merged': _item_tips_read(_cl)})
        elif path.startswith('/api/wiki_item/'):
            # v212：物品 wiki 按需抓取。/api/wiki_item/index | /api/wiki_item/<Cls> | .../progress
            _irest = path[len('/api/wiki_item/'):].strip('/')
            if _irest == 'index':
                self._send(200, _wiki_item_index())
            elif _irest.endswith('/progress'):
                self._send(200, _wiki_item_get(_irest[:-len('/progress')], start=False))
            else:
                self._send(200, _wiki_item_get(_irest, start=True))
        elif path.startswith('/api/wiki/'):
            # v72f：按需抓取。/api/wiki/index | /api/wiki/<Key> | /api/wiki/<Key>/progress
            _rest = path[len('/api/wiki/'):].strip('/')
            if _rest == 'index':
                self._send(200, _wiki_index())
            elif _rest.endswith('/progress'):
                self._send(200, _wiki_tipfix(_wiki_get(_rest[:-len('/progress')], start=False)))
            else:
                self._send(200, _wiki_tipfix(_wiki_get(_rest, start=True)))
        elif path.startswith('/api/mapwiki/'):
            # v5873：地图 Wiki（ark.wiki.gg 主源）。
            #   /api/mapwiki/index | .../probe | .../text | /api/mapwiki/<Id>
            _mrest = path[len('/api/mapwiki/'):].strip('/')
            _mqs = parse_qs(parsed.query)
            _mfo = ((_mqs.get('force') or [''])[0].strip().lower() in ('1', 'true', 'yes'))
            if _mrest == 'index':
                self._send(200, _mw_index())
            elif _mrest == 'probe':
                self._send(200, _mw_probe((_mqs.get('id') or [''])[0].strip()))
            elif _mrest == 'text':
                _mid = str((_mqs.get('slug') or _mqs.get('id') or [''])[0]).strip()
                _mtd = _mw_text_read(_mid)
                self._send(200, {'ok': True, 'id': _mid, 'blocks': _mtd, 'ready': bool(_mtd),
                                 'fields': list(_MW_BLOCKS)})
            else:
                self._send(200, _mw_get(_mrest, force=_mfo))
        elif path.startswith('/api/news/'):
            # v5926：资讯广场。index | zh | <tab>（后端内部按 1 分钟冷却 + after 增量）
            _nrest = path[len('/api/news/'):].strip('/')
            _nqs = parse_qs(parsed.query)
            if _nrest == 'index':
                _tabs = []
                for _t in NEWS_TABS:
                    _tc = _news_read(_t[0]) or {}
                    _tabs.append({'id': _t[0], 'name': _t[1],
                                  'updated': _tc.get('updated') or '',
                                  'count': len(_tc.get('cards') or []),
                                  'last_fetch': _tc.get('fetched_at') or 0})
                self._send(200, {'ok': True, 'tabs': _tabs})
            elif _nrest == 'zh':
                _tid = (_nqs.get('tab') or [''])[0].strip()
                _zm = _news_zh_read(_tid) if _news_tab(_tid) else {}
                self._send(200, {'ok': True, 'tab': _tid, 'map': _zm, 'count': len(_zm)})
            else:
                _cur, _fetched, _err = _news_refresh(_nrest)
                if _err and not (_cur and _cur.get('cards')):
                    self._send(200, {'ok': False, 'tab': _nrest, 'error': _err, 'cards': []})
                else:
                    _d = dict(_cur or {})
                    _d.pop('messages', None)
                    _d['ok'] = True
                    _d['fetched'] = _fetched
                    self._send(200, _d)
            return
        elif path == '/api/bb_notes':
            # 2026-10-28：粑粑笔记（公开只读；内容由拥有者「导入 MD」覆盖）
            self._send(200, _bb_notes_read())
        elif path.startswith('/api/status/'):
            server = path[len('/api/status/'):].strip('/').strip()
            if server not in SERVERS:
                self._send(404, {'ok': False, 'error': 'unknown server'})
                return
            self._send(200, {'ok': True, 'server': server, 'port': SERVERS[server]})
        elif path.startswith('/asa-data/'):
            rel = path[len('/asa-data/'):]
            full = safe_join(ASA_DATA, rel)
            if not full or not os.path.isfile(full):
                self._send(404, {'ok': False, 'error': 'not found'})
                return
            self._send_file(full, 'application/json; charset=utf-8' if full.endswith('.json') else 'application/octet-stream')
        elif path == '/dino-data/_lm.json':
            # 2026-10-02（方案B2）：批量 Last-Modified 清单——前端一次请求替代 11 服 × 3~4 文件 ≈ 40 次 HEAD 探测。
            #   返回 {文件名: HTTP-date}；不存在的文件不在表内（前端按「无键 = 404」处理）。
            #   LM 格式与 _send_file / gz 分支的 Last-Modified 同源（date_time_string(mtime)）⇒ 前端字符串对比兼容。
            _files = {}
            try:
                for _fn in os.listdir(DINO_DATA):
                    if not (_fn.endswith('.json') or _fn.endswith('.json.gz')):
                        continue
                    try:
                        _files[_fn] = self.date_time_string(os.path.getmtime(os.path.join(DINO_DATA, _fn)))
                    except OSError:
                        continue
            except Exception:
                _files = {}
            self._send(200, {'ok': True, 'files': _files})
        elif path.startswith('/dino-data/'):
            rel = path[len('/dino-data/'):]
            full = safe_join(DINO_DATA, rel)
            # cryo 数据为 .json.gz 压缩格式：请求 xxx.json 时自动尝试 xxx.json.gz 并解压返回
            gz_full = None
            if not full or not os.path.isfile(full):
                gz_full = safe_join(DINO_DATA, rel + '.gz')
                if not gz_full or not os.path.isfile(gz_full):
                    self._send(404, {'ok': False, 'error': 'not found'})
                    return
                full = gz_full
            if full.endswith('.gz'):
                # 2026-08-28 优化：直接返回原始 .gz 字节（不 gzip.open 解压再重压——白费 CPU，且解压后 9.7MB 传输慢 13 倍）。
                # 前端 lbFetchDataJson 检测 gzip magic（1f 8b）→ DecompressionStream 自动解压；
                # 传输量 = .gz 原始大小（~745KB），CF 边缘如再压也按压缩数据走，浏览器 fetch 自动处理 Content-Encoding。
                try:
                    with open(full, 'rb') as f:
                        data = f.read()
                    self.send_response(200)
                    self._cors()
                    self.send_header('Content-Type', 'application/gzip')
                    self.send_header('Content-Length', str(len(data)))
                    self.send_header('Cache-Control', 'no-cache')
                    self.send_header('Last-Modified', self.date_time_string(os.path.getmtime(full)))
                    self.send_header('ETag', '"%x"' % (len(data) ^ int(os.path.getmtime(full))))
                    self.end_headers()
                    if getattr(self, '_head_only', False):
                        return
                    self.wfile.write(data)
                except Exception:
                    self._send(500, {'ok': False, 'error': 'gzip read failed'})
                return
            ctype = 'application/json; charset=utf-8' if full.endswith('.json') else 'application/gzip'
            self._send_file(full, ctype)
        else:
            self._send(404, {'ok': False, 'error': 'not found'})

    def do_POST(self):
        self._guarded(self._do_POST_body)   # v2026-09-22（方案A）：同上（请求级令牌）

    def _do_POST_body(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        path = parsed.path
        # 解析 body（前端 script 调用用 JSON body：{server, species, player, dino1, dino2}）
        body = {}
        try:
            ln = int(self.headers.get('Content-Length') or 0)
            if ln > 0 and ln < 524288:   # 2026-10-19：64KB → 512KB（采集流程文档）；超过 512KB 由前端预检拦截
                raw = self.rfile.read(ln)
                if raw:
                    j = json.loads(raw.decode('utf-8', 'ignore'))
                    if isinstance(j, dict):
                        body = j
        except Exception:
            body = {}
        def g(name, default=''):
            v = body.get(name)
            if v is None:
                v = (qs.get(name) or [default])[0]
            return str(v).strip()
        # 配置规则：全服刷新（仅系统拥有者；后端自己读 11 台 ini → 落快照，全玩家共享）
        # 服务器域名：写（仅系统拥有者）
        # 2026-10-28：粑粑笔记导入（仅拥有者；整份覆盖）
        if path == '/api/zh/prepare':
            # v6238（B2）：后台下载 + 白名单解压（只写 D:\\Cache-zh，不碰游戏目录）
            _u_zp = _srvctl_guard(self, qs)
            if not _u_zp:
                return
            _fr_zp = str(g('force') or '').lower() in ('1', 'true', 'yes')
            self._send(200, _zh_prepare_start(force=_fr_zp, user=_u_zp))
            return
        if path == '/api/zh/check':
            # v6237（B1）：强制刷新云端清单（只读，不下载）
            _u_zc = _srvctl_guard(self, qs)
            if not _u_zc:
                return
            try:
                _rem_zc = _zh_remote(force=True)
            except Exception as e:
                _rem_zc = {'ok': False, 'err': repr(e)[:200]}
            self._send(200, {'ok': bool(_rem_zc.get('ok')), 'remote': _rem_zc})
            return
        if path == '/api/update/cache/manifest':
            # v6409（用户口径）：填/改某 buildId 的 depot manifest（永久存储）
            _u_mf = _srvctl_guard(self, qs, need_token=True)
            if not _u_mf:
                return
            if _role_level(_u_mf) < 2:
                self._send(403, {'ok': False, 'code': 'admin_only',
                                 'error': u'仅二级管理员可用'})
                return
            _r_mf = _steamdb_set_manifest(body.get('buildId'), body.get('manifest'))
            self._send(200 if _r_mf.get('ok') else 400, _r_mf)
            return
        if path == '/api/update/cache/version/add':
            # v6402：手工补录一条 depot 版本（SteamDB 上抄到的 GID 录一次，永久复用）
            _u_va = _srvctl_guard(self, qs, need_token=True)
            if not _u_va:
                return
            if _role_level(_u_va) < 2:
                self._send(403, {'ok': False, 'code': 'admin_only', 'error': u'仅二级管理员可用'})
                return
            _man = str(body.get('manifest') or '').strip()
            _bid = str(body.get('buildId') or '').strip()
            _ver = str(body.get('ver') or '').strip().lstrip('vV')
            if not _man.isdigit() or len(_man) < 8:
                self._send(400, {'ok': False, 'code': 'bad_manifest',
                                 'error': u'manifest 需为 Steam depot 清单号（纯数字，通常 19 位）'})
                return
            _h = _depot_hist_load()
            _its = _h.get('items')
            if not isinstance(_its, dict):
                _its = {}
            _cur = _its.get(_man) or {}
            _cur['manifest'] = _man
            if _bid:
                _cur['buildId'] = _bid
            if _ver:
                _cur['ver'] = _ver
            _cur['at'] = int(time.time())
            _cur['by'] = _u_va
            _its[_man] = _cur
            _h['items'] = _its
            _ok_s = _depot_hist_save(_h)
            self._send(200 if _ok_s else 500,
                       {'ok': _ok_s, 'manifest': _man,
                        'error': ('' if _ok_s else u'写入 depot_history.json 失败')})
            return
        if path == '/api/update/steam/cred':
            # v6402：保存/更新账号密码（密码加密落盘，永不回传）
            _u_sc = _srvctl_guard(self, qs, need_token=True)
            if not _u_sc:
                return
            _r_sc = _steam_cred_set(str(body.get('user') or '').strip(),
                                    str(body.get('pwd') or ''))
            self._send(200 if _r_sc.get('ok') else 400, _r_sc)
            return
        if path == '/api/update/cache/pull':
            # v6402（危险）：按指定 manifest 拉取缓存 → 覆盖 D:\\Cache → 写 acf
            _u_cp = _srvctl_guard(self, qs, need_token=True)
            if not _u_cp:
                return
            if _role_level(_u_cp) < 2:
                self._send(403, {'ok': False, 'code': 'admin_only', 'error': u'仅二级管理员可用'})
                return
            if str(body.get('confirm') or '') != 'PULL':
                self._send(400, {'ok': False, 'code': 'need_confirm',
                                 'error': u'拉取会覆盖 D:\\Cache，需在 body 里传 confirm="PULL"'})
                return
            _man_p = str(body.get('manifest') or '').strip()
            if not _man_p.isdigit() or len(_man_p) < 8:
                self._send(400, {'ok': False, 'code': 'bad_manifest', 'error': u'manifest 无效'})
                return
            _cu = str(body.get('user') or '').strip()
            if not _cu:
                self._send(400, {'ok': False, 'code': 'need_user', 'error': u'需指定 Steam 账号'})
                return
            if not _steam_cred_get(_cu):
                self._send(400, {'ok': False, 'code': 'no_cred',
                                 'error': u'该账号没有缓存密码，请先保存一次'})
                return
            _r_cp = _cache_pull_start(_u_cp, _man_p, str(body.get('buildId') or ''), _cu)
            self._send(200, _r_cp)
            return
        if path == '/api/update/cache/clear':
            # v6263（用户口径）：清空版本更新缓存（危险操作）—— 需 token + 二级管理员 + confirm=CLEAR
            _u_cc = _srvctl_guard(self, qs, need_token=True)
            if not _u_cc:
                return
            if _role_level(_u_cc) < 2:
                self._send(403, {'ok': False, 'code': 'admin_only', 'error': u'仅二级管理员可用'})
                return
            if str(body.get('confirm') or '') != 'CLEAR':
                self._send(400, {'ok': False, 'code': 'need_confirm',
                                 'error': u'清空缓存需在 body 里传 confirm="CLEAR"'})
                return
            _r_cc = _upd_cache_clear()
            self._send(200 if _r_cc.get('ok') else 400, _r_cc)
            return
        if path == '/api/pkg/clear':
            # v6366（用户口径）：清空本地包（汉化包 / MOD / API）
            #   —— token + 二级管理员 + body confirm='CLEARPKG'，三卡右下角「清空本地包」共用
            _u_pc = _srvctl_guard(self, qs, need_token=True)
            if not _u_pc:
                return
            if _role_level(_u_pc) < 2:
                self._send(403, {'ok': False, 'code': 'admin_only', 'error': u'仅二级管理员可用'})
                return
            if str(body.get('confirm') or '') != 'CLEARPKG':
                self._send(400, {'ok': False, 'code': 'need_confirm',
                                 'error': u'清空本地包需在 body 里传 confirm="CLEARPKG"'})
                return
            _r_pc = _pkg_clear(body.get('kind'))
            self._send(200 if _r_pc.get('ok') else 400, _r_pc)
            return
        if path == '/api/mods/prefetch':
            # v6293（用户口径）：更新本地包 —— 只把基准版本复制进新批次缓存，不动任何服务器
            _u_pf = _srvctl_guard(self, qs, need_token=True)
            if not _u_pf:
                return
            if _role_level(_u_pf) < 2:
                self._send(403, {'ok': False, 'code': 'admin_only', 'error': u'仅二级管理员可用'})
                return
            _pl_pf = _mods_prefetch_plan()
            _dry_pf = bool(body.get('dry', True))
            _bid_pf = _mods_new_batch()
            if _dry_pf or str(body.get('confirm') or '') != 'PREFETCH':
                self._send(200, {'ok': True, 'dry': True, 'batchId': _bid_pf,
                                 'plans': _pl_pf,
                                 'needConfirm': u"真跑需 body {'dry': false, 'confirm': 'PREFETCH'}"})
                return
            _good_pf = [x for x in _pl_pf if x.get('ok')]
            if not _good_pf:
                self._send(400, {'ok': False, 'code': 'no_source', 'error': u'没有可用源（各服磁盘都缺目标版本）'})
                return
            _res_pf = _mods_prefetch_run(_u_pf, _bid_pf, _good_pf)
            self._send(200, {'ok': True, 'dry': False, 'batchId': _bid_pf, 'result': _res_pf,
                             'plans': _pl_pf,
                             'note': u'已更新本地包（只写缓存），可再点分发下发到各服'})
            return
        if path == '/api/mods/pkg/fetch':
            # v6354（用户口径·方案 A）：从 CurseForge **下载真·本地包** —— 只写 _upd_cache，不动任何服务器
            #   原「更新本地包」只从现有服 copytree（无源服就废）；这个是真下载，不依赖任何服
            _u_pk = _srvctl_guard(self, qs, need_token=True)
            if not _u_pk:
                return
            if _role_level(_u_pk) < 2:
                self._send(403, {'ok': False, 'code': 'admin_only', 'error': u'仅二级管理员可用'})
                return
            if not _cf_key():
                self._send(400, {'ok': False, 'code': 'no_cf_key',
                                 'error': u'未配置 CurseForge API Key（系统管理 → CurseForge API Key）'})
                return
            _dry_pk = body.get('dry')
            _dry_pk = True if _dry_pk is None else str(_dry_pk).lower() in ('1', 'true', 'yes', 'on')
            _pids_pk = body.get('mods')
            if not isinstance(_pids_pk, list):
                _pids_pk = []
            _pids_pk = [str(x).strip() for x in _pids_pk if str(x).strip()]
            if not _pids_pk:
                _po_pk = _mods_policy()
                _pids_pk = [x for x in ([_po_pk.get('bob')] + list(_po_pk.get('common') or [])) if x]
            _seen_pk, _pl_pk = set(), []
            for _p in _pids_pk:
                if _p in _seen_pk:
                    continue
                _seen_pk.add(_p)
                _f = _mods_cf_server_file(_p)
                _fid = str((_f or {}).get('id') or '')
                _have = bool(_fid and os.path.isdir(_mods_pkg_dir(_p, _fid)))
                _pl_pk.append({'pid': _p,
                               'fid': _fid,
                               'fileName': str((_f or {}).get('fileName') or ''),
                               'bytes': int((_f or {}).get('fileLength') or 0),
                               'cached': _have,
                               'ok': bool(_f)})
            if _dry_pk or str(body.get('confirm') or '') != 'PKG':
                _n_pk = sum(1 for x in _pl_pk if x['ok'] and not x['cached'])
                self._send(200, {'ok': True, 'dry': True, 'plans': _pl_pk,
                                 'needDownload': _n_pk,
                                 'needConfirm': u"真跑需 body {'dry': false, 'confirm': 'PKG'}",
                                 'note': (u'预演：未下载任何文件。%d 项需下载' % _n_pk)})
                return
            def _pk_run():
                # v6358（用户口径「点了没出现任务条」）：**必须接入任务总线** ——
                #   原实现只写 _admin_log，界面上完全看不到进度。
                _pk_key = u'modpkg|fetch'
                _todo = [x for x in _pl_pk if x['ok']]
                _tot = max(1, len(_todo))
                # v6373（用户口径「一个 MOD 一条」）：任务 meta.items 携带每个 MOD 自己的
                #   state/pct/msg，前端按行渲染「一个 MOD 一条进度条」，不再只有一个总百分比。
                _items = []
                for _x0 in _todo:
                    try:
                        _nm0 = (_mods_cf_name(_x0['pid']) or _x0['pid'])
                    except Exception:
                        _nm0 = str(_x0['pid'])
                    _items.append({'key': str(_x0['pid']), 'fid': str(_x0['fid'] or u''),
                                   'name': _nm0, 'bytes': int(_x0['bytes'] or 0),
                                   'state': 'wait', 'pct': 0, 'msg': u'等待中'})

                def _put(msg, pct, phase='run', err=u'', nm=u''):
                    try:
                        _utask_put(_pk_key, '', 'update', _u_pk,
                                   label=u'更新本地包（CurseForge）',
                                   msg=msg, pct=int(pct), phase=phase,
                                   steps=_steps_apply(STEP_4_PKG, int(pct), phase, msg, 'pkg'),
                                   err=err, meta={'items': _items},
                                   srv_name=(nm or (u'%d 个 MOD' % len(_todo))))
                    except Exception:
                        _sexc('mods_pkg_utask')

                _put(u'查询 CurseForge 文件列表…', 3)
                _i = 0
                _badn = 0
                _why = []
                _fail_name = u''
                for _x in _todo:
                    _i += 1
                    _lo = 5 + int(88.0 * (_i - 1) / _tot)
                    _span = 88.0 / _tot
                    _nmx = (_mods_cf_name(_x['pid']) or _x['pid'])
                    _mbx = (u'%.0f MB' % ((_x['bytes'] or 0) / 1048576.0))
                    _it = _items[_i - 1] if 0 <= (_i - 1) < len(_items) else {}
                    try:
                        _it.update({'state': 'query', 'pct': 0, 'msg': u'查询文件列表…'})
                    except Exception:
                        pass

                    def _pg(msg, stage, frac=None, _lo=_lo, _span=_span, _nm=_nmx, _it=_it):
                        # v6372（实测）：原来下载阶段 pct 固定为 0.45 ⇒
                        #   进度条一直卡在 44%（msg 在变、条不动），看起来像卡住。
                        #   现按**真实字节比例**推进：下载段占本项 5%~65%，解压占 80%。
                        if stage == 'dl':
                            _r = 0.05 + 0.60 * max(0.0, min(1.0, float(frac or 0.0)))
                        elif stage == 'unzip':
                            _r = 0.80
                        else:
                            _r = 0.45
                        # v6373：同步**该 MOD 自己**的 pct/state（下载段映射到 3~75%）
                        try:
                            # v6374（用户口径）：**卡片条只表示下载** ——
                            #   0~100% 就是下载 0~100%；解压/校验**不占百分比**（条停在满格变绿）
                            if stage == 'dl':
                                _it.update({'state': 'dl',
                                            'pct': int(round(100.0 * max(0.0, min(1.0, float(frac or 0.0))))) })
                            elif stage == 'unzip':
                                _it.update({'state': 'unzip', 'pct': 100})
                            _it['msg'] = msg
                        except Exception:
                            pass
                        _put(u'%s（%s）' % (msg, _mbx), _lo + _span * _r, 'run', u'', _nm)

                    try:
                        _ok2, _msg2, _fid2, _dd2 = _mods_pkg_fetch(_x['pid'], on_prog=_pg)
                        _admin_log('MODS pkg fetch pid=%s fid=%s ok=%s %s'
                                   % (_x['pid'], _fid2, _ok2, _msg2))
                        if not _ok2:
                            _badn += 1
                            _why.append(u'%s：%s' % (_nmx, str(_msg2 or u'')[:120]))
                            _fail_name = _nmx
                            try:
                                _it.update({'state': 'fail', 'pct': 100,
                                            'msg': str(_msg2 or u'')[:120]})
                            except Exception:
                                pass
                        else:
                            try:
                                _it.update({'state': 'ok', 'pct': 100, 'msg': u'已入本地包'})
                            except Exception:
                                pass
                    except Exception as _e2:
                        _sexc('mods_pkg_fetch')
                        _badn += 1
                        _why.append(u'%s：%s' % (_nmx, repr(_e2)[:120]))
                        _fail_name = _nmx
                        try:
                            _it.update({'state': 'fail', 'pct': 100,
                                        'msg': repr(_e2)[:120]})
                        except Exception:
                            pass
                try:
                    mods_status_cache_clear()
                except Exception:
                    pass
                # v6361：完成态标题也带 MOD 名（单条时）—— 否则会回落到「N 个 MOD」跳一下
                _nmfin = (u'%d 个 MOD' % len(_todo))
                if len(_todo) == 1:
                    try:
                        _nmfin = _mods_cf_name(_todo[0]['pid']) or _todo[0]['pid']
                    except Exception:
                        pass
                elif _badn == 1 and _fail_name:
                    _nmfin = _fail_name + u' 失败'      # v6363：多选时标题直接点出失败的那个
                if _badn:
                    # v6363（用户口径「为啥报错」）：fail 态前端显示的是 **err 字段**（app_core.js L9810），
                    #   原来传 'partial' ⇒ 界面只看到一个词「partial」。现在传具体原因（截断 160）。
                    _errfin = ((_why[0] if _why else u'') or u'下载失败')[:160]
                    _put(u'完成：成功 %d 个，失败 %d 个 · %s'
                         % (len(_todo) - _badn, _badn, _errfin),
                         100, 'fail', _errfin, _nmfin)
                else:
                    _put(u'完成：已进本地包（CurseForge）', 100, 'ok', u'', _nmfin)
            try:
                threading.Thread(target=_pk_run, daemon=True).start()
            except Exception as e:
                self._send(500, {'ok': False, 'error': repr(e)})
                return
            self._send(200, {'ok': True, 'dry': False, 'started': True, 'plans': _pl_pk,
                             'note': u'已开始从 CurseForge 下载本地包（后台）；完成后分发会优先用它'})
            return
        if path == '/api/mods/cleanup-extra':
            # v6309（用户口径）：MOD 多余清理 —— dry 默认；confirm='CLEANUP' 才真跑
            #   安全点：移动不是删除（-> _upd_cache/_modcleanbak/<ts>/<srv>/），可随时移回；不停服
            _u_mc = _srvctl_guard(self, qs, need_token=True)
            if not _u_mc:
                return
            if _role_level(_u_mc) < 2:
                self._send(403, {'ok': False, 'code': 'admin_only', 'error': u'仅二级管理员可用'})
                return
            _pl_mc = _mods_cleanup_plan()
            _tot_mc = sum(int(x.get('size') or 0) for x in _pl_mc)
            _dry_mc = body.get('dry')
            _dry_mc = True if _dry_mc is None else str(_dry_mc).lower() in ('1', 'true', 'yes', 'on')
            if _dry_mc or str(body.get('confirm') or '') != 'CLEANUP':
                self._send(200, {'ok': True, 'dry': True, 'plans': _pl_mc,
                                 'totalBytes': _tot_mc, 'itemCount': len(_pl_mc),
                                 'needConfirm': u"真跑需 body {'dry': false, 'confirm': 'CLEANUP'}",
                                 'note': (u'预演：未改动任何文件。共 %d 个多余 MOD 目录待移入备份，可释放 %.1f MB'
                                          % (len(_pl_mc), _tot_mc / 1048576.0))})
                return
            if not _pl_mc:
                self._send(200, {'ok': True, 'noop': True, 'code': 'nothing_to_do',
                                 'error': u'没有需要清理的多余 MOD（全部符合策略）'})
                return
            _res_mc = _mods_cleanup_run(_u_mc, _pl_mc)
            self._send(200, {'ok': True, 'dry': False, 'result': _res_mc, 'plans': _pl_mc,
                             'note': (u'已把 %d 个目录移入备份（%s），可随时移回回滚'
                                      % (_res_mc.get('ok') or 0, _res_mc.get('backupDir') or u'-')),
                             'backupSrc': 'UNC' if u'Tnas' in str(_res_mc.get('backupDir') or '') else 'local'})
            return
        if path == '/api/mods/deploy':
            # v6284（用户口径）：MOD 分发 —— dry 默认；confirm='DEPLOY' 才真跑
            _u_md = _srvctl_guard(self, qs, need_token=True)
            if not _u_md:
                return
            if _role_level(_u_md) < 2:
                self._send(403, {'ok': False, 'code': 'admin_only', 'error': u'仅二级管理员可用'})
                return
            _arr_md = body.get('servers')
            if not isinstance(_arr_md, list):
                _arr_md = [x.strip() for x in str(body.get('servers') or '').split(',') if x.strip()]
            _sv_md = []
            for _s in _arr_md:
                _s2 = str(_s or '').strip()
                if _s2 in SERVERS and _s2 not in _sv_md:
                    _sv_md.append(_s2)
            if not _sv_md:
                self._send(400, {'ok': False, 'code': 'no_servers', 'error': u'未选择服务器'})
                return
            _dry_md = body.get('dry')
            _dry_md = True if _dry_md is None else str(_dry_md).lower() in ('1', 'true', 'yes', 'on')
            _plans_md = _mods_deploy_plan(_sv_md)
            _bad_md = [x for x in _plans_md if not x.get('ok')]
            if _dry_md:
                self._send(200, {'ok': True, 'dry': True, 'plans': _plans_md,
                                 'blocked': _bad_md,
                                 'policy': _mods_policy(),
                                 'note': (u'预演：未修改任何文件。有 %d 项无可用源（需 CurseForge API Key 下载）'
                                          % len(_bad_md)) if _bad_md else
                                         u'预演：未修改任何文件。确认后传 dry=false 且 confirm=DEPLOY'})
                return
            if str(body.get('confirm') or '') != 'DEPLOY':
                self._send(400, {'ok': False, 'code': 'need_confirm',
                                 'error': u'真跑需在 body 里传 confirm="DEPLOY"', 'plans': _plans_md})
                return
            if not _plans_md:
                self._send(200, {'ok': True, 'noop': True, 'code': 'nothing_to_do',
                                 'error': u'所选服务器的 MOD 已符合策略，无需分发'})
                return
            if len(_bad_md) == len(_plans_md):
                self._send(400, {'ok': False, 'code': 'no_source',
                                 'error': (u'所有待分发项都没有可用源：请先在「系统管理 → CurseForge API Key」'
                                           u'配置 Key，或先让任意一台服拥有该版本 MOD'),
                                 'plans': _plans_md})
                return
            _bid = str(body.get('batchId') or '') or _mods_new_batch()
            _eff_md = [x for x in _plans_md if x.get('ok')]
            _admin_log('MODS deploy by %s batch=%s eff=%d bad=%d'
                       % (_u_md, _bid, len(_eff_md), len(_bad_md)))
            try:
                threading.Thread(target=_mods_deploy_run,
                                 args=(_u_md, _bid, _eff_md), daemon=True).start()
            except Exception as e:
                self._send(500, {'ok': False, 'error': repr(e)})
                return
            self._send(200, {'ok': True, 'dry': False, 'started': True, 'batchId': _bid,
                             'plans': _plans_md, 'skipped': _bad_md,
                             'note': u'已开始分发：逐台 停服→备份→复制→校验→起服（原本停服的保持停服）'})
            return
        if path == '/api/api/pkg/download':
            # v6307（用户口径）：更新本地包 = 从 GitHub 下载最新 AsaApi 官方包（库 + Permissions）
            _u_pd = _srvctl_guard(self, qs, need_token=True)
            if not _u_pd:
                return
            if _role_level(_u_pd) < 2:
                self._send(403, {'ok': False, 'code': 'admin_only', 'error': u'仅二级管理员可用'})
                return
            try:
                threading.Thread(target=_asa_pkg_download, args=(_u_pd,), daemon=True).start()
            except Exception as e:
                self._send(500, {'ok': False, 'error': repr(e)})
                return
            self._send(200, {'ok': True, 'started': True,
                             'note': u'已开始下载 AsaApi 官方包（进度见任务列表）'})
            return
        if path == '/api/api/cleanup-extras':
            # v6306（用户口径）：多余插件「安全清理」—— dry 默认；confirm='CLEANUP' 才真跑
            #   安全点：**移动不是删除** —— 移到 _upd_cache/_pluginbak/<ts>/<srv>/，同盘秒级、可随时移回回滚；
            #   只碰 extras（不在必需清单内的插件），不停服、不动游戏本体/MOD/库。
            _u_ce = _srvctl_guard(self, qs, need_token=True)
            if not _u_ce:
                return
            if _role_level(_u_ce) < 2:
                self._send(403, {'ok': False, 'code': 'admin_only', 'error': u'仅二级管理员可用'})
                return
            _pl_ce = _api_cleanup_plan()
            _n_ce = sum(1 + len(x.get('disabled') or []) for x in _pl_ce)
            _tot_ce = sum(int(x.get('bytes') or 0)
                          + sum(int(d.get('bytes') or 0) for d in (x.get('disabled') or []))
                          for x in _pl_ce)
            _dry_ce = body.get('dry')
            _dry_ce = True if _dry_ce is None else str(_dry_ce).lower() in ('1', 'true', 'yes', 'on')
            if _dry_ce or str(body.get('confirm') or '') != 'CLEANUP':
                self._send(200, {'ok': True, 'dry': True, 'plans': _pl_ce,
                                 'totalBytes': _tot_ce, 'itemCount': _n_ce,
                                 'needConfirm': u"真跑需 body {'dry': false, 'confirm': 'CLEANUP'}",
                                 'note': (u'预演：未改动任何文件。共 %d 个目录待移入备份，可释放 %.1f MB'
                                          % (_n_ce, _tot_ce / 1048576.0))})
                return
            if not _pl_ce:
                self._send(200, {'ok': True, 'noop': True, 'code': 'nothing_to_do',
                                 'error': u'没有需要清理的多余插件'})
                return
            _res_ce = _api_cleanup_run(_u_ce, _pl_ce)
            self._send(200, {'ok': True, 'dry': False, 'result': _res_ce, 'plans': _pl_ce,
                             'note': (u'已把 %d 个目录移入备份（%s），可随时移回回滚；'
                                      u'被清理的插件在该服下次重启后不再加载')
                                     % (_res_ce.get('ok') or 0, _res_ce.get('backupDir') or u'-')})
            return
        if path == '/api/api/deploy':
            # v6284：API 分发 —— **硬门控**：缓存未就绪一律拒绝（否则插件加载失败导致起不来）
            _u_ad = _srvctl_guard(self, qs, need_token=True)
            if not _u_ad:
                return
            if _role_level(_u_ad) < 2:
                self._send(403, {'ok': False, 'code': 'admin_only', 'error': u'仅二级管理员可用'})
                return
            # v6307（用户口径）：真分发 —— 只对选中服、只补「非最新」项（md5 比对）
            _arr_ad = body.get('servers')
            if not isinstance(_arr_ad, list):
                _arr_ad = [x.strip() for x in str(_arr_ad or '').split(',') if x.strip()]
            _sv_ad = []
            for _s in _arr_ad:
                _s2 = str(_s or '').strip()
                if _s2 in SERVERS and _s2 not in _sv_ad:
                    _sv_ad.append(_s2)
            if not _sv_ad:
                self._send(400, {'ok': False, 'code': 'no_servers', 'error': u'未选择服务器'})
                return
            _st_ad = api_status()
            _force_ad = str(body.get('force') or '').lower() in ('1', 'true', 'yes', 'on')
            _dry_ad = body.get('dry')
            _dry_ad = True if _dry_ad is None else str(_dry_ad).lower() in ('1', 'true', 'yes', 'on')
            _tgt_ad = _asa_targets()
            _pl_ad = _api_deploy_plan3(_sv_ad)
            _gate_ad = []
            if not _st_ad.get('deployReady'):
                _oc = str(_st_ad.get('officialCacheState') or '')
                _ocm = {'building': u'官方正在为最新游戏版本构建缓存（Discord：构建中）',
                        'detected': u'已检测到新游戏版本，官方缓存尚未开始构建',
                        'ready': u'官方缓存已就绪，但部分服本地分代缓存缺失（%d/%d）'
                                 % (int(_st_ad.get('cacheReadyCount') or 0), int(_st_ad.get('serverCount') or 11))}
                _gate_ad.append({'code': 'cache_not_ready',
                                 'text': _ocm.get(_oc, u'官方缓存状态未知')
                                         + (u'（%s）⇒ 此时替换 dll 可能因 offsets 不匹配导致服务器起不来'
                                            % (_st_ad.get('officialCacheAt') or u'时间未知'))})
            if not _tgt_ad.get('files'):
                _gate_ad.append({'code': 'no_source',
                                 'text': u'没有可用源：请先点「更新本地包」从 GitHub 下载 AsaApi 官方包'
                                         u'（或把插件 dll 放进 ' + SOK_SRC_UNC + u'）'})
            if _dry_ad:
                self._send(200, {'ok': True, 'dry': True, 'servers': _sv_ad, 'plans': _pl_ad,
                                 'targets': {'ver': _tgt_ad.get('ver'), 'vers': _tgt_ad.get('vers'),
                                             'latest': _tgt_ad.get('latest'),
                                             'files': [{'name': f['name'], 'kind': f['kind'],
                                                        'rel': f['rel'], 'size': f['size']}
                                                       for f in _tgt_ad['files']]},
                                 'gate': _gate_ad, 'deployReady': bool(_st_ad.get('deployReady')),
                                 'needForce': bool(_gate_ad),
                                 'note': (u'预演：未改动任何文件。%d 项待更新'
                                          % len(_pl_ad)) if _pl_ad else u'预演：所选服的库/插件均已是目标版本'})
                return
            if _gate_ad and not _force_ad:
                self._send(400, {'ok': False, 'code': 'gate_blocked', 'gate': _gate_ad,
                                 'error': u'存在阻断项，需勾选「强制分发」后才能提交',
                                 'plans': _pl_ad, 'deployReady': bool(_st_ad.get('deployReady'))})
                return
            if not _pl_ad:
                self._send(200, {'ok': True, 'noop': True, 'code': 'nothing_to_do',
                                 'error': u'所选服的库/插件均已是目标版本，无需分发'})
                return
            _admin_log('API deploy by %s force=%s servers=%s items=%d ver=%s'
                       % (_u_ad, _force_ad, u','.join(_sv_ad), len(_pl_ad), _tgt_ad.get('ver') or u'-'))
            try:
                threading.Thread(target=_api_deploy_run2, args=(_u_ad, _pl_ad), daemon=True).start()
            except Exception as e:
                self._send(500, {'ok': False, 'error': repr(e)})
                return
            self._send(200, {'ok': True, 'dry': False, 'started': True,
                             'servers': _sv_ad, 'plans': _pl_ad, 'forced': _force_ad,
                             'gate': _gate_ad, 'ver': _tgt_ad.get('ver'),
                             'note': u'已开始分发：逐台 停服→备份→复制→校验→起服（原本停服的保持停服）'})
            return
        if path == '/api/update/apply':
            # v6207：一键分发（**默认 dry，只出计划不写任何文件**）
            #   body: { servers: [...], dry: true(默认), confirm: 'APPLY' 才允许真跑 }
            #   真跑会：在线检查 -> 存档 -> 停服 -> 逐文件复制 -> 改 acf -> 起服（v6207b 实装）
            _u_ap = _srvctl_guard(self, qs, need_token=True)
            if not _u_ap:
                return
            if _role_level(_u_ap) < 2:
                self._send(403, {'ok': False, 'code': 'admin_only', 'error': u'仅二级管理员可用'})
                return
            _arr_a = body.get('servers')
            if not isinstance(_arr_a, list):
                _arr_a = [x.strip() for x in str(body.get('servers') or '').split(',') if x.strip()]
            _srv_a = []
            for _s in _arr_a:
                _s2 = str(_s or '').strip()
                if _s2 and (_s2 in SERVERS) and (_s2 not in _srv_a):
                    _srv_a.append(_s2)
            if not _srv_a:
                self._send(400, {'ok': False, 'code': 'no_servers', 'error': u'未选择服务器'})
                return
            # v6239（B3）：更新目标 —— server=游戏本体（Cache 分发）/ zh=汉化补丁
            _tgs_a = body.get('targets')
            if not isinstance(_tgs_a, list):
                _tgs_a = [x.strip() for x in str(body.get('targets') or '').split(',') if x.strip()]
            _tg_a = []
            for _t in _tgs_a:
                _t2 = str(_t or '').strip().lower()
                # v6340（方案 A）：四类目标全走本编排
                if _t2 in ('server', 'zh', 'mod', 'api') and (_t2 not in _tg_a):
                    _tg_a.append(_t2)
            if not _tg_a:
                _tg_a = ['server']          # 缺省向后兼容：老页面不传 targets 时行为不变
            _do_sv_a = ('server' in _tg_a)
            _do_zh_a = ('zh' in _tg_a)
            _do_mod_a = ('mod' in _tg_a)
            _do_api_a = ('api' in _tg_a)
            _dry_a = body.get('dry')
            _dry_a = True if _dry_a is None else str(_dry_a).lower() in ('1', 'true', 'yes', 'on')
            # v6233（用户口径）：系统管理「默认预演」为开时**一律强制预演**（后端强制，前端绕不过）
            _forced_a = False
            try:
                if (not _dry_a) and _upd_dry_default():
                    _dry_a = True
                    _forced_a = True
            except Exception:
                _forced_a = False
            _cache_a = _upd_cache_status()
            # v6239：只有含「服务器本体」时才要求 Cache 有内容；纯汉化分发与 Cache 无关
            if _do_sv_a and not _cache_a.get('hasContent'):
                self._send(200, {'ok': False, 'code': 'cache_empty', 'dry': _dry_a,
                                 'error': _cache_a.get('path') and
                                 (u'缓存没有实际文件，请先在 ASAM 的 Cache Manager 点'
                                  u'「Update local cache from steam」'),
                                 'cache': _cache_a})
                return
            # v6239（§14 A2）：纯汉化预演不遍历 11.3 GB 本体差异（否则要干等 40~60 秒）
            _plans = ([_upd_make_plan(_s3, _cache_a) for _s3 in _srv_a] if _do_sv_a else [])
            _zplans_a = []
            if _do_zh_a:
                try:
                    _zok_a, _zver_a, _zman_a, _zpaks_a, _zerr_a = _zh_cache_ready()
                except Exception:
                    _zok_a, _zver_a, _zman_a, _zpaks_a, _zerr_a = False, '', {}, '', 'calc_fail'
                try:
                    _zrem_a = _zh_remote()
                except Exception:
                    _zrem_a = {}
                for _s3 in _srv_a:
                    try:
                        _zs3 = _zh_server_status(_s3, _zrem_a)
                    except Exception:
                        _zs3 = {'srv': _s3}
                    _bases3 = (_zs3.get('bases') or ['ShooterGame-Windows_P'])
                    _zplans_a.append({'srv': _s3,
                                      'curVer': _zs3.get('curVer') or '',
                                      'curSrc': _zs3.get('curSrc') or '',
                                      'toVer': _zver_a or (_zrem_a.get('ver') or ''),
                                      'ready': bool(_zok_a),
                                      'needUpd': bool(_zs3.get('needUpd')),
                                      'conflict': bool(_zs3.get('conflict')),
                                      'paksBase': _bases3[0],
                                      'files': [{'name': it.get('name'), 'bytes': it.get('size')}
                                                for it in ((_zman_a or {}).get('paks') or [])],
                                      'backupTo': os.path.join(ZH_CACHE_ROOT, 'backup', _s3),
                                      'err': _zerr_a})
            # ===== v6340（方案 A）：MOD / API 计划——由本编排执行复制 ----------
            _modplans_a, _apiplans_a = [], []
            if _do_mod_a:
                try:
                    for _p8 in (_mods_deploy_plan(_srv_a) or []):
                        if not _p8.get('ok'):
                            continue
                        _modplans_a.append({'srv': _p8.get('srv'), 'pid': _p8.get('pid'),
                                            'want': _p8.get('want') or '',
                                            'src': _p8.get('srcDir') or '',
                                            'cur': _p8.get('cur') or ''})
                except Exception:
                    _sexc('apply_mod_plan')
                    _modplans_a = []
            if _do_api_a:
                try:
                    for _p9 in (_api_deploy_plan3(_srv_a) or []):
                        if not _p9.get('ok', True):
                            continue
                        _apiplans_a.append(_p9)
                except Exception:
                    _sexc('apply_api_plan')
                    _apiplans_a = []
            # v6249（用户口径「分发只分发需要更新的服」）：给每台本体计划补 needUpd，
            #   判定口径 = 该服相对缓存有「新增」或「变更」文件；相同则视为不需要。
            for _p7 in _plans:
                try:
                    _p7['needUpd'] = bool((int(_p7.get('add') or 0) + int(_p7.get('update') or 0)) > 0)
                except Exception:
                    _p7['needUpd'] = False
            if _dry_a:
                _note_a = (u'预演模式（系统管理「默认预演」为开，已强制拦截）：未修改任何文件。'
                           u'要真跑请先到「系统管理 → 服务器更新预演」把默认预演关掉。'
                           if _forced_a else
                           u'预演模式：未修改任何文件。确认计划与 ASAM 实操一致后，'
                           u'再传 dry=false 且 confirm=APPLY 才真跑')
                self._send(200, {'ok': True, 'dry': True, 'forcedDry': bool(_forced_a),
                                 'cache': _cache_a, 'plans': _plans,
                                 'zhPlans': _zplans_a, 'modPlans': _modplans_a,
                                 'apiPlans': [{'srv': x.get('srv'), 'name': x.get('name'),
                                               'rel': x.get('rel'), 'reason': x.get('reason')}
                                              for x in _apiplans_a],
                                 'targets': _tg_a, 'note': _note_a})
                return
            if str(body.get('confirm') or '') != 'APPLY':
                self._send(400, {'ok': False, 'code': 'need_confirm',
                                 'error': u'真跑需在 body 里传 confirm="APPLY"',
                                 'plans': _plans})
                return
            # ===== v6249（用户口径）：真跑**只投「需要更新」的服** =====
            #   本体：该服 plan.needUpd（有新增/变更文件）
            #   汉化：该服 zPlan.needUpd（汉化落后云端）
            #   两项同勾时，只要**任一**目标需要就保留该服（只做需要的那一部分）。
            _eff_a, _skip_a = [], []
            for _s6 in _srv_a:
                _need6 = False
                if _do_sv_a:
                    for _p6 in _plans:
                        if _p6.get('server') == _s6 and bool(_p6.get('needUpd')):
                            _need6 = True
                            break
                if (not _need6) and _do_zh_a:
                    for _z6 in _zplans_a:
                        if _z6.get('srv') == _s6 and bool(_z6.get('needUpd')):
                            _need6 = True
                            break
                if (not _need6) and _do_mod_a:
                    for _p10 in _modplans_a:
                        if _p10.get('srv') == _s6:
                            _need6 = True
                            break
                if (not _need6) and _do_api_a:
                    for _p11 in _apiplans_a:
                        if _p11.get('srv') == _s6:
                            _need6 = True
                            break
                if _need6:
                    _eff_a.append(_s6)
                else:
                    _skip_a.append(_s6)
            _admin_log('UPDATE apply eff=%s skip=%s tg=%s'
                       % (','.join(_eff_a), ','.join(_skip_a), ','.join(_tg_a)))
            if not _eff_a:
                self._send(200, {'ok': True, 'dry': False, 'noop': True,
                                 'code': 'nothing_to_do',
                                 'error': (u'所选服务器都不需要更新'
                                           u'（本体版本与缓存一致、汉化均为最新、'
                                           u'MOD/API 均已符合目标版本），本次未做任何改动'),
                                 'servers': [], 'skipped': _srv_a, 'targets': _tg_a,
                                 'cache': _cache_a, 'plans': _plans, 'zhPlans': _zplans_a})
                return
            # ===== v6228（P1）：真跑 —— 复用自动重启状态机（mode='update'）=====
            #   方案 §1.1：不做新的复制流程，走同一条 7 阶段状态机，savekill 段改为 stop -> sync
            #   §14.5：**后端不做 AsaApi 拦截** —— 用户已在前端分发确认浮窗里看过原文并确认
            #   §16：verKind 一并写入编排，任务行标注「强制/补丁」
            _vk_a = ''
            try:
                _vk_a = str((_upd_ver_info(_srv_a) or {}).get('kind') or '')
            except Exception:
                _vic = 0       # 仅供下方 except 缩进用（无实际语义）
                _vk_a = ''
            try:
                _as_st_a, _as_raw_a, _as_meta_a = _asaapi_state()
            except Exception:
                _as_st_a, _as_raw_a, _as_meta_a = 'unknown', '', {}
            # v6239：纯汉化分发前必须本地包已就绪（避免停服后才失败）
            if _do_zh_a and not _do_sv_a:
                _zok_p, _zver_p, _zman_p, _zpaks_p, _zerr_p = _zh_cache_ready()
                if not _zok_p:
                    self._send(400, {'ok': False, 'code': 'zh_not_ready',
                                     'error': _zerr_p or u'汉化包未就绪（请先下载并解压）',
                                     'zhPlans': _zplans_a})
                    return
            # v6239（§14 B1）：停服前后台预写 .dinozh.tmp（best-effort，失败不影响分发）
            if _do_zh_a:
                def _prewarm_zh():
                    for _s4 in _srv_a:
                        try:
                            _zh_prewrite(_s4)
                        except Exception:
                            _sexc('zh_prewrite')
                try:
                    threading.Thread(target=_prewarm_zh, daemon=True).start()
                except Exception:
                    _sexc('zh_prewrite_start')
            _started_a = _restart_start(
                'update-apply by %s (%d tai, skip %d) tg=%s vk=%s asaapi=%s'
                % (_u_ap, len(_eff_a), len(_skip_a), ','.join(_tg_a), _vk_a or 'na', _as_st_a or 'na'),
                dry_override=False, force=True,
                mode='update', servers=_eff_a, ver_kind=_vk_a,
                targets=_tg_a,
                deploy_plans={'mod': _modplans_a, 'api': _apiplans_a})
            if not _started_a:
                self._send(409, {'ok': False, 'code': 'orchestrator_busy',
                                 'error': u'已有编排在运行，本次分发已记为待续跑',
                                 'asaapi': {'state': _as_st_a},
                                 'verKind': _vk_a,
                                 'restart': _restart_snapshot()})
                return
            self._send(200, {'ok': True, 'dry': False, 'started': True,
                             'mode': 'update', 'servers': _eff_a, 'skipped': _skip_a,
                             'targets': _tg_a, 'verKind': _vk_a,
                             'asaapi': {'state': _as_st_a,
                                        'hit': bool((_as_meta_a or {}).get('hit'))},
                             'cache': _cache_a, 'plans': _plans,
                             'note': (u'已进入更新编排：公告→空置→静默→存档→停服→复制→起服→校验'
                                      u'（原本停服的台跳过前 5 步且分发后保持停服）')})
            return

        if path == '/api/arkbackup/verify':
            # P0 只读：单档校验（sha256 + SQLite 头）。只在用户点「验证」时调用（方案 §6.2 / O4）
            _u_av = _srvctl_guard(self, qs, need_token=True)
            if not _u_av:
                return
            if _arkbk is None:
                self._send(500, {'ok': False, 'error': 'ark_backup module not loaded'})
                return
            _ab_v = g('server')
            _pt_v = g('pointId') or g('path')
            if not _ab_v or not _pt_v:
                self._send(400, {'ok': False, 'error': 'server + pointId required'})
                return
            try:
                _r_v = _arkbk.verify_point(_ab_v, _pt_v)
            except Exception as _e_v:
                self._send(500, {'ok': False, 'error': '%s: %s' % (type(_e_v).__name__, _e_v)})
                return
            _arkbk.append_audit({'server': _ab_v, 'action': 'verify', 'pointId': _pt_v,
                                 'ok': bool(_r_v.get('ok')), 'sha256': _r_v.get('sha256', ''),
                                 'bytes': _r_v.get('bytes', 0), 'operator': _u_av})
            self._send(200, _r_v)
            return
        if path == '/api/arkbackup/create':
            # P2：备份当前档 → arkbackup\<服>\pre_restore.ark（固定名覆盖，方案 §9：每服恒 1 份）
            _u_ac = _srvctl_guard(self, qs, need_token=True)
            if not _u_ac:
                return
            if _arkbk is None:
                self._send(500, {'ok': False, 'error': 'ark_backup module not loaded'})
                return
            _ab_c = g('server')
            if not _ab_c:
                self._send(400, {'ok': False, 'error': 'server required'})
                return
            try:
                _r_c = _arkbk.create_backup(_ab_c, operator=_u_ac, job_id=g('jobId'))
            except Exception as _e_c:
                self._send(500, {'ok': False, 'error': '%s: %s' % (type(_e_c).__name__, _e_c)})
                return
            _code_map = {'disk_low': 507, 'mapdir_unknown': 400, 'no_active': 409,
                         'read_error': 500, 'write_error': 500}
            _code_c = 200 if _r_c.get('ok') else _code_map.get(_r_c.get('code'), 500)
            self._send(_code_c, _r_c)
            return

        if path == '/api/arkbackup/precheck':
            # §6.3 回档前置闸门（会写 .ark：saveworld；传 skipSaveworld:true 可严格只读）
            _u_pc = _srvctl_guard(self, qs, need_token=True)
            if not _u_pc:
                return
            if _arkbk is None:
                self._send(500, {'ok': False, 'error': 'ark_backup module not loaded'})
                return
            _ab_pc = g('server')
            _pt_pc = g('pointId') or g('path')
            if not _ab_pc or not _pt_pc:
                self._send(400, {'ok': False, 'error': 'server + pointId required'})
                return
            _sw_done = False
            _skip_sw = bool(g('skipSaveworld'))
            try:
                _st_pc = _arkbk_rcon_alive(_ab_pc)
                if _st_pc.get('running') and not _skip_sw:
                    _rsw = _srvctl_one(_ab_pc, 'saveworld', None, _srvctl_cfg())
                    _sw_done = bool(_rsw.get('ok'))
                    if _sw_done:
                        _arkbk_wait_ark_mtime(_ab_pc, budget=20)
                _r_pc = _arkbk.precheck(_ab_pc, _pt_pc)
                _r_pc['savedWorld'] = _sw_done
                _r_pc['running'] = bool(_st_pc.get('running'))
                _r_pc['operator'] = _u_pc
                _arkbk.append_audit({'server': _ab_pc, 'action': 'precheck', 'pointId': _pt_pc,
                                     'ok': bool(_r_pc.get('ok')), 'verdict': _r_pc.get('verdict', ''),
                                     'loss': len(_r_pc.get('loss') or []),
                                     'dup': len(_r_pc.get('dup') or []), 'operator': _u_pc})
            except Exception as _e_pc:
                self._send(500, {'ok': False, 'error': '%s: %s' % (type(_e_pc).__name__, _e_pc)})
                return
            self._send(200, _r_pc)
            return

        if path == '/api/arkbackup/plan':
            # §6.4 执行计划（只读，不写任何文件）
            _u_pl = _srvctl_guard(self, qs, need_token=True)
            if not _u_pl:
                return
            if _arkbk is None:
                self._send(500, {'ok': False, 'error': 'ark_backup module not loaded'})
                return
            _ab_pl = g('server')
            _pt_pl = g('pointId') or g('path')
            if not _ab_pl or not _pt_pl:
                self._send(400, {'ok': False, 'error': 'server + pointId required'})
                return
            try:
                _rp_pl = _arkbk.resolve_point(_ab_pl, _pt_pl)
                if not _rp_pl.get('ok'):
                    self._send(400, {'ok': False, 'code': _rp_pl.get('code'), 'error': _rp_pl.get('error')})
                    return
                _md_pl = _arkbk.detect_map_dir(_ab_pl)[0]
                _act_pl = _arkbk._active_name(_ab_pl, _md_pl) if _md_pl else ''
                _src_sz = os.path.getsize(_rp_pl['abs'])
                _cur_sz = 0
                _cur_abs = os.path.join(_arkbk.ARK_ROOT, _ab_pl, 'ShooterGame', 'Saved',
                                        'SavedArks', _md_pl or '', _act_pl) if _act_pl else ''
                if _cur_abs and os.path.isfile(_cur_abs):
                    _cur_sz = os.path.getsize(_cur_abs)
                _st_pl = _arkbk_rcon_alive(_ab_pl)
                _pc_pl = _arkbk.precheck(_ab_pl, _pt_pl)
                _plan = {
                    'ok': True,
                    'server': _ab_pl,
                    'serverCn': _arkbk_server_cn(_ab_pl),
                    'pointId': _pt_pl,
                    'targetPath': _rp_pl['abs'],
                    'targetMB': round(_src_sz / 1048576.0, 1),
                    'activePath': _cur_abs,
                    'activeMB': round(_cur_sz / 1048576.0, 1),
                    'running': bool(_st_pl.get('running')),
                    'rconPort': _st_pl.get('rconPort'),
                    'impactFiles': [_cur_abs, os.path.join(_arkbk.BACKUP_ROOT, _ab_pl, 'pre_restore.ark'),
                                    _cur_abs + '.pre_swap.ark'],
                    'etaSec': (30 if _st_pl.get('running') else 5) + 5 + (10 if _st_pl.get('running') else 0)
                               + 20 + 300,
                    'confirmWord': _arkbk_server_cn(_ab_pl),
                    'verdict': _pc_pl.get('verdict'),
                    'notice': _pc_pl.get('notice'),
                    'loss': len(_pc_pl.get('loss') or []),
                    'dup': len(_pc_pl.get('dup') or []),
                    'safe': len(_pc_pl.get('safe') or []),
                    'precheck': _pc_pl,
                    'steps': ['saveworld（在跑时）', 'precheck 闸门', '备份当前档 → pre_restore.ark',
                              'kill 进程', '等 RCON 端口关闭', '原子换档', 'startq 启动', '等 RCON 就绪'],
                }
            except Exception as _e_pl:
                self._send(500, {'ok': False, 'error': '%s: %s' % (type(_e_pl).__name__, _e_pl)})
                return
            self._send(200, _plan)
            return

        if path == '/api/arkbackup/execute':
            # §6.5 执行回档（异步 job）；dryRun:true ⇒ 只跑到闸门，不动文件/不停服
            _u_ex = _srvctl_guard(self, qs, need_token=True)
            if not _u_ex:
                return
            if _arkbk is None:
                self._send(500, {'ok': False, 'error': 'ark_backup module not loaded'})
                return
            _ab_ex = g('server')
            _pt_ex = g('pointId') or g('path')
            if not _ab_ex or not _pt_ex:
                self._send(400, {'ok': False, 'error': 'server + pointId required'})
                return
            with _ARKBK_JOB_LOCK:
                _busy_ex = _ARKBK_BUSY.get(_ab_ex)
            if _busy_ex:
                self._send(409, {'ok': False, 'code': 'busy',
                                 'error': '该服已有回档任务在跑', 'jobId': _busy_ex})
                return
            _dry_ex = bool(g('dryRun'))
            try:
                _pc_ex = _arkbk.precheck(_ab_ex, _pt_ex)
            except Exception as _e_ex:
                self._send(500, {'ok': False, 'error': '%s: %s' % (type(_e_ex).__name__, _e_ex)})
                return
            if not _pc_ex.get('ok'):
                self._send(400, {'ok': False, 'code': _pc_ex.get('code'),
                                 'error': _pc_ex.get('error')})
                return
            _vd = _pc_ex.get('verdict')
            _missing = []
            if _vd != 'clear':
                if not g('ackRisk'):
                    _missing.append('ackRisk')
                if (g('confirm') or '') != _arkbk_server_cn(_ab_ex):
                    _missing.append('confirm')
            if _missing:
                self._send(400, {'ok': False, 'code': 'need_ack', 'verdict': _vd,
                                 'notice': _pc_ex.get('notice'), 'missing': _missing,
                                 'confirmWord': _arkbk_server_cn(_ab_ex),
                                 'error': '存在风险角色，需确认后执行'})
                return
            _job_ex = _arkbk_new_job(_ab_ex, _pt_ex, _u_ex, _dry_ex, action='rollback')
            _argv_ex = {'server': _ab_ex, 'pointId': _pt_ex, 'dryRun': _dry_ex,
                        'ackRisk': bool(g('ackRisk')), 'confirm': g('confirm') or '',
                        'skipSaveworld': bool(g('skipSaveworld'))}
            _ARKBK_POOL.submit(_arkbk_do_rollback, _job_ex, _argv_ex, _srvctl_cfg())
            _arkbk.append_audit({'server': _ab_ex, 'action': ('dryrun' if _dry_ex else 'execute'),
                                 'pointId': _pt_ex, 'ok': True, 'jobId': _job_ex['id'],
                                 'verdict': _vd, 'loss': len(_pc_ex.get('loss') or []),
                                 'dup': len(_pc_ex.get('dup') or []), 'operator': _u_ex})
            self._send(200, {'ok': True, 'jobId': _job_ex['id'], 'dryRun': _dry_ex,
                             'verdict': _vd, 'notice': _pc_ex.get('notice'),
                             'phase': _job_ex['phase']})
            return

        if path == '/api/arkbackup/rollback':
            # §6.7 撤销回档：用 arkbackup\<服>\pre_restore.ark 还原
            _u_rb = _srvctl_guard(self, qs, need_token=True)
            if not _u_rb:
                return
            if _arkbk is None:
                self._send(500, {'ok': False, 'error': 'ark_backup module not loaded'})
                return
            _ab_rb = g('server')
            if not _ab_rb:
                self._send(400, {'ok': False, 'error': 'server required'})
                return
            _cn_rb = _arkbk_server_cn(_ab_rb)
            if (g('confirm') or '') != _cn_rb:
                self._send(400, {'ok': False, 'code': 'confirm_required',
                                 'error': '需输入服务器中文名确认', 'confirmWord': _cn_rb})
                return
            with _ARKBK_JOB_LOCK:
                _busy_rb = _ARKBK_BUSY.get(_ab_rb)
            if _busy_rb:
                self._send(409, {'ok': False, 'code': 'busy', 'error': '该服已有回档任务在跑',
                                 'jobId': _busy_rb})
                return
            _chk_rb = _arkbk.restore_pre(_ab_rb, expect_job=g('jobId'), force=bool(g('force')), dry_run=True)
            if not _chk_rb.get('ok'):
                _cm = {'no_backup': 404, 'stale': 409, 'job_mismatch': 409,
                       'sha_mismatch': 409, 'size_mismatch': 409}
                self._send(_cm.get(_chk_rb.get('code'), 400), _chk_rb)
                return
            _job_rb = _arkbk_new_job(_ab_rb, 'own:pre_restore', _u_rb, False, action='restore')
            _argv_rb = {'server': _ab_rb, 'pointId': 'own:pre_restore', 'dryRun': False,
                        'ackRisk': True, 'confirm': _cn_rb,
                        'skipSaveworld': bool(g('skipSaveworld')), 'skipBackup': True}
            _ARKBK_POOL.submit(_arkbk_do_rollback, _job_rb, _argv_rb, _srvctl_cfg())
            _arkbk.append_audit({'server': _ab_rb, 'action': 'undo', 'pointId': 'own:pre_restore',
                                 'ok': True, 'jobId': _job_rb['id'], 'operator': _u_rb})
            self._send(200, {'ok': True, 'jobId': _job_rb['id'], 'phase': _job_rb['phase'],
                             'backupMeta': _chk_rb.get('backupMeta')})
            return

        if path == '/api/arkbackup/restore_profile':
            # v6043：角色档案恢复 —— 把 PlayerProfile 里 <eosId>.arkprofile 解压回地图存档目录
            #   ⚠ 写操作：会覆盖 mapdir 下同名 .arkprofile（自动备份 .bak_<ts>）。
            #   dryRun 默认 true，前端必须先预览再执行。
            _u_rp = _srvctl_guard(self, qs, need_token=True)
            if not _u_rp:
                return
            if _arkbk is None:
                self._send(500, {'ok': False, 'error': 'ark_backup module not loaded'})
                return
            _ab_rp = g('server')
            _eos_rp = g('eosId') or g('eos')
            if not _ab_rp or not _eos_rp:
                self._send(400, {'ok': False, 'error': 'server + eosId required'})
                return
            _dry_rp = g('dryRun')
            _dry_rp = True if _dry_rp is None else bool(_dry_rp)
            # 真正写入要求显式 confirm=服务器中文名（与回档同一套防呆）
            if not _dry_rp:
                _cn_rp = _arkbk_server_cn(_ab_rp)
                if (g('confirm') or '') != _cn_rp:
                    self._send(400, {'ok': False, 'code': 'confirm_required',
                                     'error': '写入档案需输入服务器中文名确认',
                                     'confirmWord': _cn_rp})
                    return
            try:
                _r_rp = _arkbk.restore_profile(_ab_rp, _eos_rp, g('zip'), dry_run=_dry_rp)
            except Exception as _e_rp:
                self._send(500, {'ok': False, 'error': '%s: %s' % (type(_e_rp).__name__, _e_rp)})
                return
            if _r_rp.get('ok') and not _dry_rp:
                try:
                    _arkbk.append_audit({'server': _ab_rp, 'action': 'restore_profile',
                                         'eosId': _eos_rp, 'ok': True, 'operator': _u_rp})
                except Exception:
                    pass
            self._send(200 if _r_rp.get('ok') else 400, _r_rp)
            return
        if path == '/api/mapwiki/text':
            # v5873：地图 Wiki AI 整理结果回写。body {slug|id, blocks:{ovIntro,ovTips,biome,res,cave,boss,creature,mech,tips,spawn}, force}
            _mid2 = str(g('slug') or g('id') or body.get('id') or '').strip()
            if _mid2 not in _MW_SLUGS:
                self._send(400, {'ok': False, 'error': 'unknown map id'})
                return
            _mn = _mw_text_write(_mid2, body.get('blocks'), force=bool(body.get('force')))
            self._send(200, {'ok': True, 'id': _mid2, 'added': _mn,
                             'ready': bool(_mw_text_read(_mid2))})
            return
        if path == '/api/dino/wikitext':
            # v5745：前端 AI 整理完回写。body {slug|cls, blocks:{ovIntro,ovTips,tameIntro,breedDesc,abil,spawnIntro}}
            #   **只写一次**（已有则不覆盖），全服共享同一份
            _sg = _dodo_slug(g('slug') or g('cls'))
            if not _sg:
                self._send(400, {'ok': False, 'error': 'slug required'})
                return
            _ck3 = _cache_slug(g('slug') or g('cls')) or _sg   # v5871：按变体隔离写入
            _n = _wt_write(_ck3, body.get('blocks'), force=bool(body.get('force')))
            self._send(200, {'ok': True, 'slug': _ck3, 'added': _n,
                             'ready': bool(_wt_read(_ck3))})
            return
        if path == '/api/dino/tips/zh':
            # v5740：前端翻完回写中文。body {slug|cls, items:[{id, text}]}
            #   · 按 tip id 合并，已存在的中文**不覆盖**（多客户端并发安全）
            #   · 条数上限 60、单条 ≤2000 字（_dodo_zh_merge 内截断）
            _arr = body.get('items') or body.get('zh') or []
            if not isinstance(_arr, list):
                _arr = []
            if len(_arr) > 60:
                _arr = _arr[:60]
            if not _arr and not body.get('merged'):
                self._send(400, {'ok': False, 'error': 'nothing to save (items/merged both empty)'})
                return
            _mg = body.get('merged')
            _n = _dodo_zh_merge(g('slug') or g('cls'), _arr, _mg, force=bool(body.get('force')))
            _m, _sg = _dodo_zh_map(g('slug') or g('cls'))
            self._send(200, {'ok': True, 'slug': _sg, 'added': _n, 'count': len(_m)})
            return
        if path == '/api/news/imgfix':
            # v5926：单条消息附件链接修复（Discord CDN 签名过期）
            _p_tid = g('tab')
            _p_mid = g('mid')
            if not _news_tab(_p_tid) or not _p_mid:
                self._send(400, {'ok': False, 'error': 'tab/mid required'})
                return
            _p_imgs, _p_err = _news_imgfix(_p_tid, _p_mid)
            if _p_err:
                self._send(200, {'ok': False, 'error': _p_err})
            else:
                self._send(200, {'ok': True, 'images': _p_imgs or []})
            return
        if path == '/api/news/zh':
            # v5926：前端 DS 翻译完回写（按 id 合并，已存在不覆盖）
            _p_tid2 = g('tab')
            if not _news_tab(_p_tid2):
                self._send(400, {'ok': False, 'error': 'unknown tab'})
                return
            _p_items = body.get('items') or []
            _p_n, _p_map = _news_zh_merge(_p_tid2, _p_items if isinstance(_p_items, list) else [])
            self._send(200, {'ok': True, 'tab': _p_tid2, 'added': _p_n, 'count': len(_p_map)})
            return
        if path == '/api/item/tips':
            # v5819：物品指南 AI 整理回写。body {cls, merged:{points,secs,pv}, force}
            _cl = g('cls')
            _mg = body.get('merged')
            if (not _cl) or (not isinstance(_mg, dict)):
                self._send(400, {'ok': False, 'error': 'cls and merged required'})
                return
            _n2 = _item_tips_merge(_cl, _mg, force=bool(body.get('force')))
            self._send(200, {'ok': True, 'cls': _cl, 'added': _n2, 'merged': _item_tips_read(_cl)})
            return
        if path == '/api/bb_notes':
            _u = g('username')
            _n = g('nick')
            _ok, _err = _harvest_auth(_u, _n)
            if not _ok:
                self._send(401, {'ok': False, 'error': _err})
                return
            if _u not in CFG_OWNERS:
                self._send(403, {'ok': False, 'error': 'owner only'})
                return
            _notes, _nerr = _bb_notes_norm(body.get('notes'))
            if _nerr:
                self._send(400, {'ok': False, 'error': _nerr})
                return
            _doc = {'version': 1,
                    'updated': time.strftime('%Y-%m-%d'),
                    'updated_by': _u,
                    'notes': _notes}
            try:
                _bb_notes_write(_doc)
            except Exception as _e:
                self._send(500, {'ok': False, 'error': repr(_e)})
                return
            self._send(200, {'ok': True, 'count': len(_notes), 'updated': _doc['updated'], 'doc': _doc})
            return
        if path == '/api/server_config':
            _u = g('username')
            _n = g('nick')
            _ok, _err = _harvest_auth(_u, _n)
            if not _ok:
                self._send(401, {'ok': False, 'error': _err})
                return
            if _u not in CFG_OWNERS:
                self._send(403, {'ok': False, 'error': 'owner only'})
                return
            # P3：除 server_domain 外，支持写 asa_token / asa_base（仅显式提供时才改，留空=不修改）
            _has_dom = ('server_domain' in body) or ('server_domain' in qs)
            _has_tok = ('asa_token' in body) or ('asa_token' in qs)
            _has_base = ('asa_base' in body) or ('asa_base' in qs)
            _has_udry = ('update_dry' in body) or ('update_dry' in qs)
            _has_cf = ('cf_key' in body) or ('cf_key' in qs)   # v6282: CurseForge API Key
            _has_mp = ('mods_policy' in body) or ('mods_policy' in qs)   # v6284: MOD 策略
            # v6237：汉化补丁配置（folder_url / variant / auto_check）
            _bzp = body.get('zh_patch') if isinstance(body.get('zh_patch'), dict) else {}
            _has_zhp = bool(_bzp) or ('zh_folder_url' in body) or ('zh_variant' in body)
            _clr_tok = bool(body.get('asa_token_clear'))
            _clr_cf = bool(body.get('cf_key_clear'))
            try:
                _d = _srv_cfg_read()
                if _has_dom or not _d.get('server_domain'):
                    _dom = _srv_domain_norm(body.get('server_domain', g('server_domain', '')))
                    _d['server_domain'] = _dom
                else:
                    _dom = _d.get('server_domain') or ''
                if _has_tok:
                    _tk = str(body.get('asa_token', g('asa_token', '')) or '').strip()
                    if _tk:
                        _d['asa_token'] = _tk
                    elif _clr_tok:
                        _d.pop('asa_token', None)
                if _has_base:
                    _bb = str(body.get('asa_base', g('asa_base', '')) or '').strip().rstrip('/')
                    if _bb:
                        _d['asa_base'] = _bb
                if _has_udry:
                    # v6233：服务器更新「默认预演」开关（true=只出清单）
                    _udv = body.get('update_dry', g('update_dry', ''))
                    _d['update_dry'] = str(_udv).lower() in ('1', 'true', 'yes', 'on')
                if _has_mp:
                    # v6284（用户口径）：MOD 策略 —— Bob 固定 MOD + 其他服统一 MOD 列表
                    _mp = body.get('mods_policy')
                    if not isinstance(_mp, dict):
                        try:
                            _mp = json.loads(str(qs.get('mods_policy', [''])[0] or body.get('mods_policy') or '{}'))
                        except Exception:
                            _mp = {}
                    if isinstance(_mp, dict):
                        _cur = _d.get('mods_policy')
                        _cur = dict(_cur) if isinstance(_cur, dict) else {}
                        if 'bob' in _mp:
                            _b = str(_mp.get('bob') or '').strip()
                            if _b:
                                _cur['bob'] = _b
                        if 'common' in _mp:
                            _cv = _mp.get('common')
                            if isinstance(_cv, list):
                                _cur['common'] = [str(x).strip() for x in _cv if str(x).strip()]
                            else:
                                _cur['common'] = [x.strip() for x in str(_cv or '').replace(u'，', ',').split(',') if x.strip()]
                        _d['mods_policy'] = _cur
                if _has_cf:
                    # v6282：CurseForge API Key（仅存服务器本地；留空=不修改）
                    _ck = str(body.get('cf_key', g('cf_key', '')) or '').strip()
                    if _ck:
                        _d['cf_key'] = _ck
                    elif _clr_cf:
                        _d.pop('cf_key', None)
                if _has_zhp:
                    # v6237（B1）：汉化补丁配置 —— 地址必须含 /folders/<id>，变体必须在枚举内
                    _zp = _d.get('zh_patch')
                    _zp = dict(_zp) if isinstance(_zp, dict) else {}
                    _fu = str(_bzp.get('folder_url', body.get('zh_folder_url', '')) or '').strip()
                    if _fu:
                        if not _zh_folder_id(_fu):
                            self._send(400, {'ok': False, 'code': 'bad_folder_url',
                                             'error': u'下载地址必须包含 /folders/<id>'})
                            return
                        _zp['folder_url'] = _fu
                    _vr = str(_bzp.get('variant', body.get('zh_variant', '')) or '').strip().lower()
                    if _vr:
                        if _vr not in ZH_VARIANTS:
                            self._send(400, {'ok': False, 'code': 'bad_variant',
                                             'error': u'variant 只能是 %s' % ' / '.join(ZH_VARIANTS)})
                            return
                        _zp['variant'] = _vr
                    if 'auto_check' in _bzp:
                        _zp['auto_check'] = str(_bzp.get('auto_check')).lower() in ('1', 'true', 'yes', 'on')
                    _d['zh_patch'] = _zp
                _d['updated_at'] = time.strftime('%Y-%m-%dT%H:%M:%S+08:00')
                _d['updated_by'] = _u
                _srv_cfg_write(_d)
            except Exception as e:
                self._send(500, {'ok': False, 'error': repr(e)})
                return
            self._send(200, {'ok': True, 'server_domain': _dom,
                             'asa_base': _d.get('asa_base') or 'https://asa.whiterober.com',
                             'asa_token_masked': _asa_mask(_d.get('asa_token') or ''),
                             'asa_configured': bool(_d.get('asa_token')),
                             'update_dry': bool(_upd_dry_default()),
                             'cf_key_masked': _asa_mask(_d.get('cf_key') or ''),
                             'cf_key_configured': bool(_d.get('cf_key')),
                             'mods_policy': _mods_policy(),
                             'zh_patch': _zh_cfg_of(_d)})
            return
        # ===== P3：服务器控制（仅二级管理员；前端不接触 token）=====
        if path == '/api/tasks/stage':
            # v6140（含 6140b 修正：路由必须挂在 **POST 链**，先前误挂到 GET 链 ⇒ 404）
            # 刷新流程阶段上报：只推进**已存在**的 refresh 任务行 msg/pct，不新建行、不碰执行逻辑
            _u = _srvctl_guard(self, qs)   # token 优先；无 token 时兼容 username 直报（与读取任务列表一致）
            if not _u:
                return
            _srv = g('server')
            _msg = g('msg')
            try:
                _pct = int(g('pct') or 0)
            except Exception:
                _pct = 0
            _upd = False
            if _srv in SERVERS:
                try:
                    _upd = _utask_stage('refresh|%s' % _srv, _srv, 'refresh', _u, msg=_msg, pct=_pct)
                except Exception:
                    _sexc('tasks_stage')
            self._send(200, {'ok': True, 'updated': bool(_upd), 'server': _srv, 'pct': _pct})
            return
        if path == '/api/refresh/lock':
            # v6141（用户口径「加软锁」）：刷新数据同服互斥 —— action=set 抢锁 / clear 释放
            _u = _srvctl_guard(self, qs)
            if not _u:
                return
            _srv = g('server')
            _act = (g('action') or 'set').lower()
            if _srv not in SERVERS:
                self._send(400, {'ok': False, 'error': 'bad server'})
                return
            _owner = 'refresh|%s' % _srv
            if _act == 'clear':
                _srv_lock_clear(_srv, _owner)
                self._send(200, {'ok': True, 'cleared': True, 'server': _srv})
                return
            _cur = _srv_lock_get(_srv)
            if _cur:
                _k = str(_cur.get('kind') or '')
                _ku = _utask_opname(_cur.get('user') or '') or ''
                _same = (_cur.get('owner') == _owner and (_cur.get('user') or '') == _u)
                if not _same:
                    if _k in SRV_LOCK_HARD:
                        self._send(200, {'ok': True, 'acquired': False,
                                         'holder': {'kind': _k, 'label': _cur.get('label') or u'回档', 'user': _ku}})
                        return
                    if _k == 'refresh':
                        self._send(200, {'ok': True, 'acquired': False,
                                         'holder': {'kind': _k, 'label': u'刷新数据', 'user': _ku}})
                        return
                    if _k in ('restart', 'queue'):
                        self._send(200, {'ok': True, 'acquired': False,
                                         'holder': {'kind': _k, 'label': _cur.get('label') or u'重启编排', 'user': _ku}})
                        return
            try:
                _ttl = int(g('ttl') or 900)
            except Exception:
                _ttl = 900
            _srv_lock_set(_srv, 'refresh', _owner, u'刷新数据', user=_u, ttl=_ttl)
            self._send(200, {'ok': True, 'acquired': True, 'server': _srv, 'ttl': _ttl, 'user': _u})
            return
        if path == '/api/tasks/dismiss':
            # v6122：清除任务（失败条清理 / 指定 id）
            _u = _srvctl_guard(self, None, need_token=True)
            if not _u:
                return
            _ids = body.get('ids')
            _idset = set(int(x) for x in _ids) if isinstance(_ids, list) else None
            _n = _utask_dismiss(_idset, bool(body.get('allFail')))
            self._send(200, {'ok': True, 'removed': _n})
            return
        if path == '/api/srvctl/startq/abort':
            # v6437（用户实测「点了无数次中止；启动条为啥还在？」）：
            #   根因 —— 旧中止只发 kill 杀进程，**从不清 _SRVCTL_STARTQ['active']**，
            #   而 _startq_loop 每 2 秒都会给 active 里的服重推 `srv|start` run 任务条
            #   ⇒ 进程被杀、任务条每 2 秒重建，点多少次都一样。
            #   本接口把目标服从 active/queue 移除并置 fail，任务条才会真正消失。
            _u_sa = _srvctl_guard(self, qs, need_token=True)
            if not _u_sa:
                return
            if _role_level(_u_sa) < 2:
                self._send(403, {'ok': False, 'code': 'admin_only', 'error': u'仅二级管理员可用'})
                return
            _sa_list = body.get('servers')
            if not isinstance(_sa_list, list) or not _sa_list:
                _sa_one = str(body.get('server') or g('server') or '').strip()
                _sa_list = [_sa_one] if _sa_one else []
            _sa_all = bool(body.get('all'))
            # v6439：统一走 _startq_drop（内含 tries 清零 + 任务条置中止），
            #   避免与 kill 分支两处逻辑不一致。
            _sa_removed = []
            if _sa_all:
                with _SRVCTL_STARTQ_LOCK:
                    _sa_list = list(_SRVCTL_STARTQ['active'].keys()) + list(_SRVCTL_STARTQ['queue'])
                    _SRVCTL_STARTQ['queue'] = []
                    _SRVCTL_STARTQ['running'] = False
            for _sa in _sa_list:
                _sa = str(_sa or '').strip()
                if _sa not in SERVERS:
                    continue
                try:
                    if _startq_drop(_sa, _u_sa):
                        _sa_removed.append(_sa)
                except Exception:
                    _sexc('startq_abort_drop')
            self._send(200, {'ok': True, 'user': _u_sa,
                             'removed': _sa_removed, 'all': _sa_all})
            return
        if path == '/api/tasks/abort':
            # v6164（计划 §16 第 7 项 / C8）：中止自动重启编排
            #   {server:'Isl'} 中止单台（其余继续）；{all:true} 中止整批
            _u_ab = _srvctl_guard(self, qs, need_token=True)
            if not _u_ab:
                return
            if _role_level(_u_ab) < 2:
                self._send(403, {'ok': False, 'code': 'admin_only', 'error': u'仅二级管理员可用'})
                return
            _all_ab = bool(body.get('all')) or str(g('all') or '').lower() in ('1', 'true', 'yes', 'on')
            if _all_ab:
                _nab = 0
                for _s_ab in list((_RESTART.get('servers') or {}).keys()):
                    try:
                        if _restart_abort(_s_ab, _u_ab):
                            _nab += 1
                    except Exception:
                        _sexc('abort_all')
                with _RESTART_LOCK:
                    _RESTART['running'] = False
                    _RESTART['current'] = ''
                _restart_log('ABORT ALL by %s (%d 台)' % (_u_ab, _nab))
                self._send(200, {'ok': True, 'all': True, 'aborted': _nab, 'user': _u_ab})
                return
            _srv_ab = str(body.get('server') or g('server') or '').strip()
            if not _srv_ab:
                self._send(400, {'ok': False, 'code': 'bad_arg', 'error': u'缺少 server（或传 all:true）'})
                return
            _ok_ab = False
            try:
                _ok_ab = _restart_abort(_srv_ab, _u_ab)
            except Exception:
                _sexc('abort_one')
            self._send(200 if _ok_ab else 404,
                       {'ok': bool(_ok_ab), 'server': _srv_ab, 'user': _u_ab,
                        'error': '' if _ok_ab else u'该服不在编排中（或已结束）'})
            return
        if path == '/api/admin/restart':
            # v6155（用户口径「不依赖计划任务」）：仅系统拥有者；**两级 spawn 成功后**才回 200 并退出
            # v6156：guard 传 qs（否则 ?tk= 被忽略，前端不带 Authorization 头时一律 401）
            _u_rb = _srvctl_guard(self, qs, need_token=True)
            if not _u_rb:
                return
            if _role_level(_u_rb) < 3:
                self._send(403, {'ok': False, 'code': 'owner_only', 'error': u'仅系统拥有者可用'})
                return
            with _RESTART_LOCK:
                _busy_rb = bool(_RESTART.get('running'))
                _dry_rb = bool(_RESTART.get('dry'))
            _sp_ok, _sp_how, _sp_err = _admin_spawn_restart(3)
            _admin_log('RESTART request by %s -> spawn ok=%s how=%s err=%s'
                       % (_u_rb, _sp_ok, _sp_how, (_sp_err or '')[:200]))
            if not _sp_ok:
                self._send(500, {'ok': False, 'code': 'spawn_failed',
                                 'error': u'无法拉起重启进程，已放弃退出（后端保持运行）',
                                 'detail': _sp_err[:300]})
                return
            self._send(200, {'ok': True, 'msg': u'后端将在 1 秒后退出，由脚本重新拉起',
                             'how': _sp_how, 'restartRunning': _busy_rb, 'dry': _dry_rb, 'user': _u_rb})
            threading.Timer(0.2, lambda: _admin_do_restart(_u_rb, _sp_how)).start()
            return
        if path == '/api/restart/enable':
            # v6167（计划 §16 第 8 项，2026-11-06）：编排开关**热切** —— 仅系统拥有者
            #   背景：ipwatch_restart / ipwatch_restart_dry 原先只能手工编辑 server_config.json，
            #         没有文件通道时（Agent / 远程运维）无法开或关编排；本路由把它变成一次 HTTP 调用。
            _u_re = _srvctl_guard(self, qs, need_token=True)
            if not _u_re:
                return
            if _role_level(_u_re) < 3:
                self._send(403, {'ok': False, 'code': 'owner_only', 'error': u'仅系统拥有者可用'})
                return
            _has_en = ('enable' in body) or ('enable' in qs)
            _has_dry = ('dry' in body) or ('dry' in qs)
            # v6169：可选「dry 下也真发广播」开关（验收公告用，不影响停服）
            _has_ann = ('announceReal' in body) or ('announceReal' in qs)
            if not _has_en and not _has_dry and not _has_ann:
                self._send(400, {'ok': False, 'code': 'bad_arg', 'error': u'缺少 enable / dry / announceReal'})
                return

            def _bv_switch(_k):
                _v = body.get(_k)
                if _v is None:
                    _v = g(_k)
                if isinstance(_v, bool):
                    return _v
                return str(_v).strip().lower() in ('1', 'true', 'yes', 'on')

            try:
                _d_re = _srv_cfg_read()
                if _has_en:
                    _d_re['ipwatch_restart'] = _bv_switch('enable')
                if _has_dry:
                    _d_re['ipwatch_restart_dry'] = _bv_switch('dry')
                if _has_ann:
                    _d_re['ipwatch_announce_real'] = _bv_switch('announceReal')
                _d_re['updated_at'] = time.strftime('%Y-%m-%dT%H:%M:%S+08:00')
                _d_re['updated_by'] = _u_re
                _srv_cfg_write(_d_re)
            except Exception as e:
                self._send(500, {'ok': False, 'error': repr(e)})
                return
            _en_re = _restart_enable_now()
            _dr_re = _restart_dry_now()
            # v6217：热切后同步快照 —— 否则 /api/ipwatch 的 restart.dry 与任务条 meta.dry
            #   仍是上一轮的值（实测切 dry=false 后仍报 true），真跑时前端显示「演练」会误导验收。
            #   编排运行中不动（本轮模式已定，改它只会让日志与实际行为不一致）。
            try:
                with _RESTART_LOCK:
                    if not _RESTART.get('running'):
                        _RESTART['dry'] = bool(_dr_re)
            except Exception:
                pass
            _restart_log('ENABLE switch by %s -> enable=%s dry=%s' % (_u_re, _en_re, _dr_re))
            self._send(200, {'ok': True, 'enable': _en_re, 'dry': _dr_re,
                             'announceReal': _restart_announce_real_now(),
                             'envEnableLocked': bool(RESTART_ENABLE),
                             'envDryLocked': os.environ.get('IPWATCH_RESTART_DRY') is not None,
                             'user': _u_re})
            return
        if path == '/api/restart/dryrun':
            # v6132：人工触发演练（**强制 dry=true**，不会真停/真启），仅二级管理员
            _u_rd = _srvctl_guard(self, qs, need_token=True)   # v6156：兼容 ?tk=
            if not _u_rd:
                return
            with _RESTART_LOCK:
                _busy_rd = bool(_RESTART.get('running'))
            if _busy_rd:
                self._send(409, {'ok': False, 'code': 'busy', 'error': '已有重启编排在跑'})
                return
            _ok_rd = _restart_start('manual-dryrun by %s' % _u_rd, dry_override=True)
            self._send(200, {'ok': bool(_ok_rd), 'dry': True,
                             'reason': 'manual-dryrun by %s' % _u_rd})
            return
        if path == '/api/srvctl/action' or path == '/api/srvctl/rcon':
            # v6023（用户口径）：写接口**强制** token —— 挡住「知道管理员用户名即可 curl 启停/清龙」
            _u = _srvctl_guard(self, None, need_token=True)
            if not _u:
                return
            _act = 'rcon' if path.endswith('/rcon') else g('action')
            if _act not in SRVCTL_ACTIONS:
                self._send(400, {'ok': False, 'error': 'bad action', 'code': 'bad_action',
                                 'actions': list(SRVCTL_ACTIONS)})
                return
            # v6203（用户口径）：来源标记 —— 前端「任务条重试」传 retry，日志标 [重试]
            _src = str(body.get('src') or g('src') or '').strip().lower()[:16]
            _msgv = body.get('message')
            _msg = None
            if _act == 'rcon':
                _msg = str(_msgv if _msgv is not None else g('message', '') or '').strip()
                if not _msg:
                    self._send(400, {'ok': False, 'error': 'empty message', 'code': 'bad_message'})
                    return
            _arr = body.get('servers')
            if not isinstance(_arr, list):
                _arr = [x.strip() for x in (g('servers', '') or '').split(',') if x.strip()]
            _srvl = []
            for _s in _arr:
                _s2 = str(_s or '').strip()
                if _s2 and (_s2 in SERVERS) and (_s2 not in _srvl):
                    _srvl.append(_s2)
            if not _srvl:
                self._send(400, {'ok': False, 'error': 'no servers', 'code': 'no_servers',
                                 'servers': sorted(SERVERS.keys())})
                return
            # v6058（按推荐补全）：**回档期间该服禁止任何外部动作**（含 start —— start 会进
            #   启动队列，同样要在入口挡住）。原 `_srvctl_acquire(server, action)` 是按
            #   (服务器, 动作) 分锁，start 与 kill 互不排斥，挡不住「换档窗口里被拉起来」。
            _hold = [s for s in _srvl if _ARKBK_HOLD.get(s)]
            if _hold:
                self._send(409, {'ok': False, 'code': 'arkbackup_busy',
                                 'error': '该服务器正在执行回档，请等待完成后再操作',
                                 'servers': _hold, 'action': _act})
                return
            # v6135：服务器级独占锁 —— hard 拒绝；soft 需 interrupt=1，否则返回可打断提示
            try:
                _allk = _srv_lock_snapshot()
                _hard = [s for s in _srvl if (_allk.get(s) or {}).get('kind') in SRV_LOCK_HARD]
                if _hard:
                    self._send(409, {'ok': False, 'code': 'server_locked',
                                     'error': '该服务器正在执行回档，不可打断',
                                     'servers': _hard,
                                     'locks': dict((s, _allk[s]) for s in _hard)})
                    return
                _soft = [s for s in _srvl if (_allk.get(s) or {}).get('kind') in SRV_LOCK_SOFT]
                _intr = bool(g('interrupt') or body.get('interrupt'))
                if _soft and not _intr:
                    self._send(409, {'ok': False, 'code': 'will_interrupt',
                                     'error': '该服正在执行自动任务，继续将中止它',
                                     'servers': _soft,
                                     'locks': dict((s, _allk[s]) for s in _soft)})
                    return
                if _soft and _intr:
                    for _s in _soft:
                        _restart_abort(_s, _u)
                        # v6168（计划 §16 第 9 项 9b 实测暴露）：原来清锁硬编码 'restart|<服>'，
                        #   而 refresh 等其他 soft 锁的 owner 是 '<kind>|<服>' ⇒ 清错 owner，
                        #   锁会一直留到 TTL(900s) 自然过期；用户表现是「打断一次后每次操作都要再点 interrupt」。
                        #   改为按**实际 owner** 清（_restart_abort 内部已处理 restart 锁，这里补其余类型）。
                        _lk_x = (_allk.get(_s) or {})
                        _own_x = str(_lk_x.get('owner') or ('restart|%s' % _s))
                        _srv_lock_clear(_s, _own_x)
            except Exception:
                _sexc('srv_lock_gate')
            # v6014（用户口径）：**所有** start 一律走队列 —— 含单台启动与失败重试。
            #   原实现只有「多台」入队、单台直通 ⇒ 任务条上的「重试」是单台请求，
            #   可绕过重压池（同时 <= 2 台）导致并发超标；改为统一入队后重压池才真正成立。
            if _act == 'start':
                # v6276（用户口径 2026-11-08「同时只允许一个批次在运行（防止混乱）。
                #   其他人执行批次时，提示当前有批次正在进行中」）：
                #   判据 = 编排在跑，或启动队列在跑且**发起人不是自己**。
                #   同一发起人允许继续追加（前端「重试失败项」语义 = 同一批次的续加，不算新批次）。
                #   编排内部调用不走此路由（直接调 _srvctl_startq_new），天然不受限。
                try:
                    _bb, _bo, _bl, _bk = _batch_busy_probe()
                    _src_lc = str(_src or '').strip().lower()
                    _same_owner = (str(_u or '') != '' and str(_u or '') == str(_bo or ''))
                    if _bb and _src_lc != 'ipwatch' and not _same_owner:
                        _emsg = _batch_busy_error(_bb, _bo, _bl, _bk)
                        try:
                            _srvctl_log('(system)', '/'.join(_srvl), 'start', False, 0,
                                        (u'start 拒绝（批次互斥）：' + _emsg)[:250])
                        except Exception:
                            pass
                        self._send(409, {'ok': False, 'code': 'batch_busy', 'error': _emsg,
                                         'batch': {'kind': _bk, 'owner': _bo,
                                                   'remaining': int(_bl or 0)},
                                         'servers': _srvl, 'action': 'start'})
                        return
                except Exception:
                    _sexc('srvctl_start_batch_gate')
                try:
                    _q = _srvctl_startq_new(_u, _srvl, src=_src)
                except Exception as _e:
                    self._send(500, {'ok': False, 'code': 'queue_error', 'error': repr(_e)})
                    return
                self._send(200, {'ok': True, 'queued': True, 'action': 'start',
                                 'servers': _srvl, 'queue': _q})
                return
            # v6439（户实测「中止了好几次 Bob 都自动重启」）：
            #   人工终止必须先把该服从启动队列剔除并清零重试计数，否则
            #   `_startq_loop` 会把「进程退出」判成启动失败 ⇒
            #   STARTQ_AUTO_RETRY 自动重新入队再拉起 ⇒ 杀了又拉、点了也没用。
            #   排除编排来源（ipwatch 是"先杀后起"的正常流程）。
            try:
                if (_act in ('kill', 'savekill')) and (str(_src or '').lower() != 'ipwatch'):
                    for _s_dp in _srvl:
                        _startq_drop(_s_dp, _u)
            except Exception:
                _sexc('srvctl_kill_drop_startq')
            _busy = [s for s in _srvl if not _srvctl_acquire(s, _act)]
            if _busy:
                for s in _srvl:
                    if s not in _busy:
                        _srvctl_release(s, _act)
                self._send(409, {'ok': False, 'code': 'busy',
                                 'error': '该服务器此操作正在执行中',
                                 'servers': _busy})
                return
            try:
                if _act in SRVCTL_ASYNC_ACTIONS:
                    _jid = _srvctl_job_new(_u, _act, _srvl, src=_src)
                    self._send(200, {'ok': True, 'async': True, 'jobId': _jid,
                                     'action': _act, 'servers': _srvl})
                    return
                _res = _srvctl_run(_u, _srvl, _act, _msg,
                                   force=bool(body.get('force') or False), src=_src)
                self._send(200, {'ok': all(bool(r.get('ok')) for r in _res),
                                 'action': _act, 'results': _res})
            finally:
                for s in _srvl:
                    _srvctl_release(s, _act)
            return
        if path == '/api/asa_test':
            # P3：测试 ASA token 连通性（仅 owner）
            _u = g('username')
            _n = g('nick')
            _ok, _err = _harvest_auth(_u, _n)
            if not _ok:
                self._send(401, {'ok': False, 'error': _err})
                return
            if _u not in CFG_OWNERS:
                self._send(403, {'ok': False, 'error': 'owner only'})
                return
            _cfg = _srvctl_cfg()
            if not _cfg['token']:
                self._send(200, {'ok': False, 'code': 'asa_no_token', 'error': 'asa_token 未配置'})
                return
            _t0 = time.time()
            try:
                _code, _text = _asa_http('GET', _cfg['base'] + '/server-status', _cfg['token'],
                                         None, timeout=_cfg['timeout'], verify=_cfg['verify'])
                _ms = int((time.time() - _t0) * 1000)
                if 200 <= _code < 300:
                    _cnt = 0
                    try:
                        _cnt = len((json.loads(_text) or {}).get('servers') or [])
                    except Exception:
                        _cnt = 0
                    self._send(200, {'ok': True, 'count': _cnt, 'ms': _ms})
                else:
                    self._send(200, {'ok': False,
                                     'code': 'asa_unauthorized' if _code in (401, 403) else 'asa_error',
                                     'error': 'ASA HTTP %s' % _code, 'ms': _ms})
            except Exception as _e:
                self._send(200, {'ok': False, 'code': 'asa_error', 'error': str(_e),
                                 'ms': int((time.time() - _t0) * 1000)})
            return
        if path == '/api/cfg_rules/refresh':
            _u = g('username')
            _n = g('nick')
            _ok, _err = _harvest_auth(_u, _n)
            if not _ok:
                self._send(401, {'ok': False, 'error': _err})
                return
            if _u not in CFG_OWNERS:
                self._send(403, {'ok': False, 'error': 'owner only', 'owners': sorted(CFG_OWNERS)})
                return
            _started, _job = _cfg_refresh_start(_u)
            self._send(200, {'ok': True, 'started': _started, 'job': _job})
            return
        # 配置规则：上传快照（旧路径，保留兼容；建议改用 /api/cfg_rules/refresh）
        if path == '/api/cfg_rules/snapshot':
            _u = g('username')
            _n = g('nick')
            _ok, _err = _harvest_auth(_u, _n)
            if not _ok:
                self._send(401, {'ok': False, 'error': _err})
                return
            if _u not in CFG_OWNERS:
                self._send(403, {'ok': False, 'error': 'owner only', 'owners': sorted(CFG_OWNERS)})
                return
            _servers = body.get('servers')
            _one_srv = str(body.get('server') or '').strip()
            _files = body.get('files')
            if isinstance(_one_srv, str) and _one_srv and isinstance(_files, dict):
                # 逐台合并模式（避开 512KB body 上限）：{server:'Isl', files:{GUS:..,GAME:..}}
                if _one_srv not in SERVERS:
                    self._send(400, {'ok': False, 'error': 'unknown server'})
                    return
                _base = _cfg_snapshot() or {}
                _servers = dict(_base.get('servers') or {})
                _servers[_one_srv] = _files
            if not isinstance(_servers, dict) or not _servers:
                self._send(400, {'ok': False, 'error': 'missing servers/files'})
                return
            _snap = {'schema': 1,
                     'generated_at': str(body.get('generated_at') or time.strftime('%Y-%m-%dT%H:%M:%S+08:00')),
                     'updated_by': _u,
                     'servers': _servers}
            try:
                _size = _cfg_snapshot_write(_snap)
            except Exception as _e:
                self._send(500, {'ok': False, 'error': 'snapshot write failed', 'detail': repr(_e)})
                return
            self._send(200, {'ok': True, 'servers': len(_servers), 'server': (_one_srv or None),
                             'size': _size, 'generated_at': _snap['generated_at']})
            return
        # 采集流程（玩家级）：GET/POST /api/harvest_flows
        if path.endswith('/api/harvest_flows'):
            username = g('username')
            nick = g('nick')
            ok_auth, _err = _harvest_auth(username, nick)
            if not ok_auth:
                self._send(401, {'ok': False, 'error': _err})
                return
            doc = body.get('doc')
            if not isinstance(doc, dict):
                self._send(400, {'ok': False, 'error': 'missing doc'})
                return
            try:
                base_ts = int(body.get('baseUpdatedAt') or 0)
            except Exception:
                base_ts = 0
            cur = _load_harvest_flows(username)
            cur_ts = int((cur or {}).get('updatedAt') or 0) if isinstance(cur, dict) else 0
            if base_ts and cur_ts and base_ts < cur_ts:
                self._send(409, {'ok': False, 'error': 'conflict', 'doc': cur})
                return
            doc['owner'] = username
            doc['updatedAt'] = int(time.time() * 1000)
            try:
                _save_harvest_flows(username, doc)
            except Exception as e:
                self._send(500, {'ok': False, 'error': 'save failed: %s' % e})
                return
            self._send(200, {'ok': True, 'updatedAt': doc['updatedAt']})
            return
        # 玩家偏好（关注项等）：GET/POST /api/user_prefs
        if path.endswith('/api/user_prefs'):
            username = g('username')
            nick = g('nick')
            ok_auth, _err = _harvest_auth(username, nick)
            if not ok_auth:
                self._send(401, {'ok': False, 'error': _err})
                return
            data = body.get('data')
            if not isinstance(data, dict):
                self._send(400, {'ok': False, 'error': 'missing data'})
                return
            keys = data.get('keys')
            if not isinstance(keys, dict):
                self._send(400, {'ok': False, 'error': 'missing keys'})
                return
            kts = data.get('kts')
            if not isinstance(kts, dict):
                kts = {}
            doc = {'owner': username, 'updatedAt': int(time.time() * 1000), 'keys': keys, 'kts': kts}
            try:
                _save_user_prefs(username, doc)
            except Exception as e:
                self._send(500, {'ok': False, 'error': 'save failed: %s' % e})
                return
            self._send(200, {'ok': True, 'updatedAt': doc['updatedAt']})
            return
        # 独立登录：/api/login（Phase 2 认证解耦；成功返回 nick 供前端身份解析）
        if path.endswith('/api/login') or path.endswith('/login'):
            username = g('username')
            password = g('password')
            if not (username and password):
                self._send(400, {'ok': False, 'error': 'missing username/password'})
                return
            nick = check_login(username, password)
            if not nick:
                self._send(401, {'ok': False, 'error': 'invalid credentials'})
                return
            # v6023：追加 token（HMAC 无状态签名；重启后端不失效；改密码即吊销）
            self._send(200, {'ok': True, 'nick': nick, 'role': _role_level(username),
                             'token': _srvctl_make_token(username)})
        # 自助改密：/api/change_password（校验旧密码 → 写 accounts.json）
        elif path.endswith('/api/change_password') or path.endswith('change_password'):
            username = g('username')
            old_pwd = g('old_pwd')
            new_pwd = g('new_pwd')
            if not (username and old_pwd and new_pwd):
                self._send(400, {'ok': False, 'error': 'missing args'})
                return
            acc = _accounts()
            if username not in acc or str(acc[username].get('pwd', '')) != str(old_pwd):
                self._send(401, {'ok': False, 'error': 'invalid credentials'})
                return
            if len(new_pwd) < 4:
                self._send(400, {'ok': False, 'error': 'password too short'})
                return
            acc[username]['pwd'] = new_pwd
            _save_accounts(acc)
            self._send(200, {'ok': True})
        # 绑定 SteamID（玩家身份）：/api/bind_player（校验密码 → 验证玩家名存在 → 更新 nick）
        elif path.endswith('/api/bind_player') or path.endswith('bind_player'):
            username = g('username')
            pwd = g('pwd')
            player_name = g('player_name')
            if not (username and pwd and player_name):
                self._send(400, {'ok': False, 'error': 'missing args'})
                return
            acc = _accounts()
            if username not in acc or str(acc[username].get('pwd', '')) != str(pwd):
                self._send(401, {'ok': False, 'error': 'invalid credentials'})
                return
            player_name = player_name.strip()
            names = _player_names()
            if names and player_name not in names:
                self._send(404, {'ok': False, 'error': 'player not found'})
                return
            acc[username]['nick'] = player_name
            _save_accounts(acc)
            self._send(200, {'ok': True, 'nick': player_name})
        # 一键 WebP 增量检查（管理员 whiterober）：R2 只读扫描新图（不压图，压图由本地增量脚本执行）
        elif path.endswith('/api/webp_check') or path.endswith('webp_check'):
            username = g('username')
            if username != 'whiterober':
                self._send(401, {'ok': False, 'error': 'admin required'})
                return
            self._send(200, webp_check())
        # 旧路径兼容（前端双兼容新架构下 LB_API + '/api/services/script/...' 与 webhook 均落到这里）
        # refresh_tamed：/api/refresh_tamed / /api/services/script/refresh_tamed / /api/webhook/refresh_tamed
        elif path.endswith('refresh_tamed'):
            server = g('server')
            if not server:
                self._send(400, {'ok': False, 'error': 'missing server'})
                return
            _cur_rt = _srv_lock_get(server)
            if str(_cur_rt.get('kind') or '') in SRV_LOCK_HARD:
                self._send(409, {'ok': False, 'code': 'server_locked',
                                 'error': u'该服务器正在执行回档，不可刷新数据'})
                return
            # 2026-08-28 异步化：后台线程执行 RCON（旧架构 AppDaemon 异步 1s 返回；此处立即返回触发成功，前端轮询 refresh_status.json/savedAt 等结果）
            _RCON_EXECUTOR.submit(refresh_tamed, server, (g('username') or g('user') or 'system'))
            self._send(200, {'ok': True, 'server': server, 'triggered': True, 'async': True, 'ts': str(datetime.now())})
        # v17：强制保存世界（原生 RCON SaveWorld）——刷新数据选中服务器时先存档，cryo 落地后再拉数据
        elif path.endswith('save_world'):
            server = g('server')
            if not server:
                self._send(400, {'ok': False, 'error': 'missing server'})
                return
            _RCON_EXECUTOR.submit(save_world, server)
            self._send(200, {'ok': True, 'server': server, 'triggered': True, 'async': True, 'ts': str(datetime.now())})
        # v525：全图蛋信息实时刷新（TransferIdentityFix.EggProbe）——选中服务器刷新时同步触发
        elif path.endswith('refresh_eggs'):
            server = g('server')
            if not server:
                self._send(400, {'ok': False, 'error': 'missing server'})
                return
            _RCON_EXECUTOR.submit(refresh_eggs, server)
            self._send(200, {'ok': True, 'server': server, 'triggered': True, 'async': True, 'ts': str(datetime.now())})
        # v532：在线玩家列表（原生 RCON ListPlayers）——联盟位置只查在线成员，减少无效 PlayerPos 查询
        elif path.endswith('list_players'):
            server = g('server')
            if not server:
                self._send(400, {'ok': False, 'error': 'missing server'})
                return
            _RCON_EXECUTOR.submit(list_players, server)
            self._send(200, {'ok': True, 'server': server, 'triggered': True, 'async': True, 'ts': str(datetime.now())})
        elif path.endswith('search_wild_dinos') or path.endswith('search_wild'):
            server = g('server')
            species = g('species')
            if not server or not species:
                self._send(400, {'ok': False, 'error': 'missing server/species'})
                return
            # 2026-08-28 异步化：后台线程执行 RCON（旧架构 AppDaemon 异步 1s 返回；此处立即返回触发成功，前端轮询 wild_status.json 等结果）
            _RCON_EXECUTOR.submit(search_wild, server, species)
            self._send(200, {'ok': True, 'server': server, 'species': species, 'triggered': True, 'async': True, 'ts': str(datetime.now())})
        # 2026-08-28 修复：stop_track_dino 必须在 track_dino 之前匹配（'stop_track_dino'.endswith('track_dino') 为 True，
        # 原顺序 track_dino 先匹配会拦截 stop 请求，因缺 dino1/dino2 返回 400 missing args → RCON 从未执行 → 游戏标记未清理）
        elif path.endswith('stop_track_dino'):
            server = g('server')
            player = g('player')
            if not (server and player):
                self._send(400, {'ok': False, 'error': 'missing args'})
                return
            self._send(200, stop_track_dino(server, player))
        elif path.endswith('track_dino') and not path.endswith('stop_track_dino'):
            server = g('server')
            player = g('player')
            d1 = g('dino1')
            d2 = g('dino2')
            if not (server and player and d1 and d2):
                self._send(400, {'ok': False, 'error': 'missing args'})
                return
            self._send(200, track_dino(server, player, d1, d2))
        elif path.endswith('track_location'):  # v809：坐标打点（蛋/静态目标）
            server = g('server')
            player = g('player')
            x = g('x')
            y = g('y')
            z = g('z')
            if not (server and player and x is not None and y is not None):
                self._send(400, {'ok': False, 'error': 'missing args'})
                return
            self._send(200, track_location(server, player, x, y, z))
        elif path.endswith('get_dino'):
            server = g('server')
            d1 = g('dino1')
            d2 = g('dino2')
            if not (server and d1 and d2):
                self._send(400, {'ok': False, 'error': 'missing args'})
                return
            self._send(200, get_dino(server, d1, d2))
        elif path.endswith('inv_probe'):  # 2026-09-04：库存扫描（关注未成年→食物源）
            server = g('server')
            if not server:
                self._send(400, {'ok': False, 'error': 'missing server'})
                return
            self._send(200, inv_probe(server, g('filter'), g('tribe_id', '0'), g('max', '5')))
        elif path.endswith('volcano_state'):  # 2026-09-14：火山权威状态（插件 TransferIdentityFix.Volcano；带 fresh 跳过 TTL，仅调试用）
            server = g('server')
            if not server:
                self._send(400, {'ok': False, 'error': 'missing server'})
                return
            self._send(200, volcano_state(server, bool(g('fresh'))))
        elif path.endswith('volcano_log'):  # v1146（用户定稿）：火山事件台账（history[] / hooks）——与状态同源，独立缓存槽
            server = g('server')
            if not server:
                self._send(400, {'ok': False, 'error': 'missing server'})
                return
            self._send(200, volcano_log(server))
        # 2026-09-30：WorldProbe 公共设施实时查询（types / query / weather / scan；短时缓存共用 + 同键并发合并）
        elif path.endswith('worldprobe_types'):
            server = g('server')
            if not server:
                self._send(400, {'ok': False, 'error': 'missing server'})
                return
            self._send(200, worldprobe_types(server))
        elif path.endswith('worldprobe_weather'):
            server = g('server')
            if not server:
                self._send(400, {'ok': False, 'error': 'missing server'})
                return
            self._send(200, worldprobe_weather(server, g('limit', '1'), g('slim', '1') != '0'))
        elif path.endswith('worldprobe_wave'):  # v4367：Gen 巨浪
            server = g('server')
            if not server:
                self._send(400, {'ok': False, 'error': 'missing server'})
                return
            self._send(200, worldprobe_wave(server))
        elif path.endswith('worldprobe_sandstorm'):  # v4367：Rag 沙尘暴
            server = g('server')
            if not server:
                self._send(400, {'ok': False, 'error': 'missing server'})
                return
            self._send(200, worldprobe_sandstorm(server))
        elif path.endswith('worldprobe_meteor'):  # v4367：Ext 陨石雨
            server = g('server')
            if not server:
                self._send(400, {'ok': False, 'error': 'missing server'})
                return
            self._send(200, worldprobe_meteor(server))
        elif path.endswith('worldprobe_actor'):  # v4367：通用 actor（Rag 火山 / Gen 流星雨）
            server = g('server')
            if not server:
                self._send(400, {'ok': False, 'error': 'missing server'})
                return
            self._send(200, worldprobe_actor(server, g('filter'), g('propsIdx', '0'), g('probe'), g('top', '1'), g('slim', '1'), g('fields')))
        elif path.endswith('worldprobe_badwx'):  # v4367：坏天气权重
            server = g('server')
            if not server:
                self._send(400, {'ok': False, 'error': 'missing server'})
                return
            self._send(200, worldprobe_badwx(server, g('filter', 'WeatherSystem')))
        elif path.endswith('worldprobe_wprobs'):  # v4367：全服概率聚合
            server = g('server')
            if not server:
                self._send(400, {'ok': False, 'error': 'missing server'})
                return
            self._send(200, worldprobe_wprobs(server, g('propsIdx', '0')))
        elif path.endswith('wind_status'):  # v4670：风力发电机耐久（风机清单 + 逐台 5 字段；TTL 60s + 同键合并）
            server = g('server')
            if not server:
                self._send(400, {'ok': False, 'error': 'missing server'})
                return
            fresh = g('fresh').lower() in ('1', 'true', 'yes')
            self._send(200, wind_status(server, fresh))
        elif path.endswith('world_clock'):  # v5714：存档世界时钟逆推（RCON 锚点 + 存档 mtime；TTL 3 分钟）
            server = g('server')
            if not server:
                self._send(400, {'ok': False, 'error': 'missing server'})
                return
            fresh = g('fresh').lower() in ('1', 'true', 'yes')
            self._send(200, world_clock(server, fresh))
        elif path.endswith('worldprobe_zones'):  # 2026-10-03：天气区域（WorldProbe zones；TTL 60s + 同键并发合并）
            server = g('server')
            if not server:
                self._send(400, {'ok': False, 'error': 'missing server'})
                return
            fresh = g('fresh').lower() in ('1', 'true', 'yes')
            self._send(200, worldprobe_zones(server, fresh))
        elif path.endswith('worldprobe_biometemps'):  # 2026-10-04：区域温度（WorldProbe biometemps；TTL 60s + 同键并发合并）
            server = g('server')
            if not server:
                self._send(400, {'ok': False, 'error': 'missing server'})
                return
            self._send(200, worldprobe_biometemps(server, g('skip', '0'), g('count', '64'),
                                                  g('brief').lower() in ('1', 'true', 'yes'), g('filter')))
        elif path.endswith('worldprobe_query'):
            server = g('server')
            type_s = g('type')
            if not (server and type_s):
                self._send(400, {'ok': False, 'error': 'missing server/type'})
                return
            fresh = g('fresh').lower() in ('1', 'true', 'yes')
            self._send(200, worldprobe_query(server, type_s, g('limit', str(WP_LIMIT_DEFAULT)), fresh))
        elif path.endswith('worldprobe_scan'):
            type_s = g('type')
            if not type_s:
                self._send(400, {'ok': False, 'error': 'missing type'})
                return
            fresh = g('fresh').lower() in ('1', 'true', 'yes')
            self._send(200, worldprobe_scan(type_s, g('servers'), g('limit', str(WP_LIMIT_DEFAULT)), fresh))
        elif path.endswith('worldprobe_class'):
            cls_s = g('cls')
            if not cls_s:
                self._send(400, {'ok': False, 'error': 'missing cls'})
                return
            fresh = g('fresh').lower() in ('1', 'true', 'yes')
            self._send(200, worldprobe_class(cls_s, g('servers'), fresh))
        elif path.endswith('ingame_time'):  # 2026-10-03：游戏内时间（原生 RCON GetInGameTime；60s TTL + 同键合并）
            server = g('server')
            if not server:
                self._send(400, {'ok': False, 'error': 'missing server'})
                return
            fresh = g('fresh').lower() in ('1', 'true', 'yes')
            self._send(200, ingame_time(server, fresh))
        elif path.endswith('volcano_anchor'):  # v1096 旧接口（人工校准锚点）——已弃用，保留兼容；v1107 起前端不再调用
            server = g('server')
            if not server:
                self._send(400, {'ok': False, 'error': 'missing server'})
                return
            node = g('node')
            if node:
                self._send(200, volcano_anchor_set(server, node, g('by') or ''))
            else:
                self._send(200, volcano_anchor_get(server))
        elif path.endswith('crafting_cost'):  # 2026-09-13：单蓝图制作材料（蓝图卡/待制作）
            server = g('server')
            cls = g('cls')
            if not (server and cls):
                self._send(400, {'ok': False, 'error': 'missing args'})
                return
            self._send(200, crafting_cost(server, cls))
        elif path.endswith('player_pos'):
            server = g('server')
            player = g('player')
            if not (server and player):
                self._send(400, {'ok': False, 'error': 'missing args'})
                return
            # 2026-08-31 异步化：后台线程执行 RCON（原同步阻塞单线程 HTTP server，前端并行查 10 服被串行排队，
            # 联盟多成员位置查询极慢：M 成员×10 服全串行）。异步后前端并行 POST 立即返回，线程池并行 RCON，
            # 前端轮询 player_pos_status_{server}.json 拿结果（ts 变化检测，逻辑不变）。
            _RCON_EXECUTOR.submit(player_pos, server, player)
            self._send(200, {'ok': True, 'server': server, 'player': player, 'triggered': True, 'async': True, 'ts': str(datetime.now())})
        # v3：服务器管理（管理员 whiterober）：转移死亡包到最近墓碑 / 重建冷冻球
        elif path.endswith('move_death_bag'):
            username = g('username')
            if username != 'whiterober':
                self._send(401, {'ok': False, 'error': 'admin required'})
                return
            server = g('server')
            target = g('target')
            if not (server and target):
                self._send(400, {'ok': False, 'error': 'missing args'})
                return
            self._send(200, move_death_bag(server, target))
        elif path.endswith('move_all_pendings'):
            username = g('username')
            if username != 'whiterober':
                self._send(401, {'ok': False, 'error': 'admin required'})
                return
            server = g('server')
            team = g('team')
            if not (server and team):
                self._send(400, {'ok': False, 'error': 'missing args'})
                return
            self._send(200, move_all_pendings(server, team))
        # 生物改名（登录用户，前端仅自己的生物卡显示）：/api/rename_dino
        elif path.endswith('rename_dino'):
            username = g('username')
            if not username:
                self._send(401, {'ok': False, 'error': 'login required'})
                return
            server = g('server')
            dino_id1 = g('dino_id1')
            dino_id2 = g('dino_id2')
            name = g('name')
            if not (server and dino_id1 and dino_id2 and name):
                self._send(400, {'ok': False, 'error': 'missing args'})
                return
            self._send(200, rename_dino(server, dino_id1, dino_id2, name))
        # 容器箱改名（登录用户，前端仅自己部落的容器箱显示「改名」按钮）：/api/rename_container
        elif path.endswith('rename_container'):
            username = g('username')
            if not username:
                self._send(401, {'ok': False, 'error': 'login required'})
                return
            server = g('server')
            obj = g('obj') or g('objName') or g('objname')
            name = g('name')
            if not (server and obj and name):
                self._send(400, {'ok': False, 'error': 'missing args'})
                return
            self._send(200, rename_container(server, obj, name))
        # 牌子/墓碑写文字（2026-09-19 插件 0.4.0）：/api/set_sign_text（登录用户）
        elif path.endswith('set_sign_text'):
            username = g('username')
            if not username:
                self._send(401, {'ok': False, 'error': 'login required'})
                return
            server = g('server')
            obj = g('obj') or g('objName') or g('objname')
            text = g('text') if g('text') else g('name')
            if not (server and obj and text):
                self._send(400, {'ok': False, 'error': 'missing args'})
                return
            self._send(200, set_sign_text(server, obj, text))
        # 床/棺材/睡眠舱改名（2026-09-19 插件 0.4.0）：/api/set_bed_name（登录用户）
        elif path.endswith('set_bed_name'):
            username = g('username')
            if not username:
                self._send(401, {'ok': False, 'error': 'login required'})
                return
            server = g('server')
            obj = g('obj') or g('objName') or g('objname')
            name = g('name')
            if not (server and obj and name):
                self._send(400, {'ok': False, 'error': 'missing args'})
                return
            self._send(200, set_bed_name(server, obj, name))
        else:
            self._send(404, {'ok': False, 'error': 'not found'})


def main():
    _sinfo('dino_backend starting: port=%s DINO_DATA=%s' % (PORT, DINO_DATA))
    # v6122：恢复任务总线（进行中 → fail(后端重启导致中断)）
    try:
        _utask_load()
    except Exception:
        _sexc('utask_load_main')
    # v6121：公网 IP 监视线程（只观察 + 通知，不自动动作）
    try:
        threading.Thread(target=_ipwatch_loop, daemon=True, name='ipwatch').start()
        # v6129（M3）：重启编排器守护线程（仅 IPWATCH_RESTART=1 时才真正启动编排）
        threading.Thread(target=_restart_loop, daemon=True, name='restart-orch').start()
        _sinfo('ipwatch thread started: domain=%s interval=%ss' % (_ipwatch_domain(), IPWATCH_INTERVAL))
    except Exception:
        _sexc('ipwatch_start')
    # v6415：SteamDB/Steam 官方 latest buildId↔manifest 自动配对（每 30 分钟）
    try:
        threading.Thread(target=_steamdb_pair_loop, daemon=True, name='steamdb-pair').start()
        _sinfo('steamdb-pair thread started: interval=%ss' % STEAMDB_PAIR_INTERVAL)
    except Exception:
        _sexc('steamdb_pair_start')
    print('dino_backend listening on :{}'.format(PORT))
    print('  RCON_HOST={}  DINO_DATA={}'.format(RCON_HOST, DINO_DATA))
    print('  ASA_DATA={}  ALLOW_ORIGIN={}'.format(ASA_DATA, ALLOW_ORIGIN))
    srv = _GuardedServer(('0.0.0.0', PORT), Handler)
    try:
        srv.serve_forever()
    except Exception as e:  # v988：异常兑底（留日志后交由 watchdog 重启）
        print('[main] serve_forever exited: {}'.format(e))
        _sexc('main', 'serve_forever exited')
        raise


# ================= 自动重启守护（watchdog） =================
# v2（2026-08-30）：worker 子进程异常退出后自动拉起，避免 cloudflared 报
# "dial tcp 127.0.0.1:8080 ... actively refused"（2026-08-28~29 多时段后端 down，dino-data/track 全失败）。
# 运行方式不变：python dino_backend.py（默认启动 watchdog）；仅跑服务体：python dino_backend.py --worker
# 特性：worker 崩溃 3s 自动重启；60s 内连续崩 5 次改 30s 退避；watchdog 永不退出（Ctrl+C 不退出，仅重启 worker，用户 2026-08-30）。
def _worker():
    main()

# v992：崩溃日志落盘 —— 用户 2026-09-11 反馈「卡了自动重启，看不到任何报错」。
#   worker 的 stdout/stderr 全部重定向到本文件，含完整 traceback + 退出码 + 时间戳。
_CRASH_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dino_backend.log')


def _wlog(msg):
    line = '[{}] {}'.format(time.strftime('%Y-%m-%d %H:%M:%S'), msg)
    try:
        print(line, flush=True)
    except Exception:
        pass
    try:
        with open(_CRASH_LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def _watchdog():
    import subprocess, sys
    # v994：忽略 Ctrl+C —— 用户 2026-09-11 实测「Ctrl+C 关隧道」会连同 watchdog/worker 一起杀掉
    #       （后端日志只剩一行 "watchdog started"、无 worker exited 记录，即此因）。
    #       worker 子进程仍会被 Ctrl+C 终止 → 由本 watchdog 自动拉起，符合设计预期。
    try:
        import signal
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    except Exception:
        pass
    _wlog('[watchdog] dino_backend watchdog started (never exits, worker auto-restart)  log={}'.format(_CRASH_LOG))
    crashes = 0
    last = time.time()
    while True:
        try:
            _lf = open(_CRASH_LOG, 'a', encoding='utf-8')
            p = subprocess.Popen([sys.executable, os.path.abspath(__file__), '--worker'],
                                 stdout=_lf, stderr=subprocess.STDOUT)
        except Exception as e:
            _wlog('[watchdog] spawn worker failed: {}'.format(e))
            time.sleep(5)
            continue
        try:
            rc = p.wait()
        except KeyboardInterrupt:
            # 用户 2026-08-30：一直重试不退出——Ctrl+C 仅记录并重启 worker，watchdog 保持运行
            _wlog('[watchdog] Ctrl+C received, keeping watchdog alive (worker restart)')
            try:
                p.kill()
            except Exception:
                pass
            time.sleep(1)
            continue
        now = time.time()
        if now - last > 60:
            crashes = 0
        last = now
        crashes += 1
        delay = 30 if crashes >= 5 else 3
        _wlog('[watchdog] worker exited rc={} (crashes={}), restart in {}s'.format(rc, crashes, delay))
        time.sleep(delay)


if __name__ == '__main__':
    import sys
    if '--worker' in sys.argv:
        _worker()
    else:
        _watchdog()
