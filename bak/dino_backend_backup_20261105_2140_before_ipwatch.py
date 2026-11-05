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
import socket
import struct
import subprocess
import threading
import time
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
    """抽检存档族文件完整性（gzip 尾 CRC / JSON 开头）-> 损坏列表。"""
    bad = []
    try:
        import gzip
    except Exception:
        gzip = None
    for sfx in ('_cryo.json.gz', '_players.json.gz', '_item.json.gz', '_eggs.json.gz'):
        p = os.path.join(DINO_DATA, server + sfx)
        if not os.path.isfile(p):
            continue
        try:
            sz = os.path.getsize(p)
            if sz <= 0:
                bad.append(server + sfx + ' size=0')
                continue
            if gzip is None:
                continue
            with gzip.open(p, 'rb') as f:
                if sz <= 30 * 1024 * 1024:
                    f.read()      # 全量解压：尾部 CRC 校验（能拓到半截文件）
                else:
                    f.read(2)     # 超大文件只验头部，避免阻塞
        except Exception as e:
            bad.append('%s %s' % (server + sfx, type(e).__name__))
    for sfx in ('_cryo.json', '_tamed.json', '_item.json'):
        p = os.path.join(DINO_DATA, server + sfx)
        if not os.path.isfile(p):
            continue
        try:
            with open(p, 'rb') as f:
                head = f.read(64).lstrip()
            if not head or head[:1] not in (b'{', b'['):
                bad.append(server + sfx + ' 非 JSON 开头')
        except Exception as e:
            bad.append('%s %s' % (server + sfx, type(e).__name__))
    return bad


def _dinodata_wait_stable(server, since_ts=None, budget=90, quiet=3.0, poll=0.5, require_update=True):
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
    while True:
        cur = _dinodata_files(server)
        now = time.time()
        fam = {k: v for k, v in cur.items() if any(k.endswith(s) for s in _DD_SAVE_FAMILIES)}
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


def _cfg_proc_start(server):
    """该服 ArkAscendedServer.exe 的启动时间（epoch 秒）；取不到返回 None。60s 缓存。"""
    now = time.time()
    if _CFG_PROC['map'] is None or (now - _CFG_PROC['ts']) > 60:
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
SRVCTL_ACTIONS = ('start', 'stop', 'kill', 'update', 'saveworld', 'fullbackup', 'destroy', 'rcon')
SRVCTL_T_TIMEOUT = 60            # 普通动作超时（秒）
SRVCTL_T_DESTROY = 600           # destroy 超时（对齐 HA）
SRVCTL_T_FULLBACKUP = 600        # fullbackup 超时（保守同档）
SRVCTL_ASYNC_ACTIONS = ('destroy', 'fullbackup')   # 走异步 job
_SRVCTL_POOL = __import__('concurrent.futures', fromlist=['ThreadPoolExecutor']).ThreadPoolExecutor(max_workers=4)
_SRVCTL_JOB_POOL = __import__('concurrent.futures', fromlist=['ThreadPoolExecutor']).ThreadPoolExecutor(max_workers=1)
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
        text = (data or b'').decode('utf-8', errors='ignore').replace('\x00', '').strip()
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


def _srvctl_log(user, server, action, ok, ms, msg=''):
    """审计：每服一行（时间/用户/服务器/动作/结果/耗时）。"""
    try:
        line = '%s\t%s\t%s\t%s\t%s\t%dms\t%s\n' % (
            time.strftime('%Y-%m-%d %H:%M:%S'), user, server, action,
            'OK' if ok else 'FAIL', int(ms), str(msg or '').replace('\n', ' ')[:200])
        with open(SRVCTL_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line)
    except Exception:
        pass


def _srvctl_one(server, action, message, cfg):
    """单服单动作：返回 {server, profileName, ok, message, ms, retried}。"""
    prof = (SERVER_THEMES.get(server) or {}).get('name') or server
    t0 = time.time()
    retried = False
    last_msg = ''
    # v54b：to 必须在下面的 rcon 直连分支之前定义（v54 把它留在 for 循环前，
    # 导致 _rcon_exec(timeout=min(to, 20)) 抛 UnboundLocalError）
    to = cfg['timeout_destroy'] if action in ('destroy', 'fullbackup') else cfg['timeout']
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
        _t_save = time.time()
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
            _dw = _dinodata_wait_stable(server, since_ts=_t_save, budget=_budget)
            _out['data'] = _dw
            _out['message'] = (_out['message'] + ' · DinoData ' + (
                '稳定 %.0fs（%d 文件）' % (float(_dw.get('waited') or 0), int(_dw.get('files') or 0))
                if _dw.get('ok') else '未确认稳定（%s）' % (_dw.get('reason') or 'unknown')))[:300]
        return _out
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


def _srvctl_run(user, servers, action, message):
    """并发执行（max_workers=4）；results[] 顺序与 servers 一致。失败自动重试 1 轮。"""
    cfg = _srvctl_cfg()
    results = [None] * len(servers)

    def _job(idx, srv):
        try:
            results[idx] = _srvctl_one(srv, action, message, cfg)
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
            _srvctl_log(user, r.get('server'), action, r.get('ok'), r.get('ms', 0), r.get('message', ''))
    return [r for r in results if r]


def _srvctl_job_new(user, action, servers):
    """长任务（destroy / fullbackup）异步 job。"""
    jid = 'j%d_%d' % (int(time.time() * 1000), len(_SRVCTL_JOBS))
    with _SRVCTL_JOBS_LOCK:
        now = time.time()
        for k in [k for k, v in _SRVCTL_JOBS.items() if now - v.get('ts', 0) > _SRVCTL_JOB_TTL]:
            _SRVCTL_JOBS.pop(k, None)
        _SRVCTL_JOBS[jid] = {'ts': now, 'done': False, 'action': action,
                             'servers': list(servers), 'user': user, 'results': []}

    def _run():
        try:
            res = _srvctl_run(user, servers, action, None)
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
SRVCTL_STARTQ_FIRST_TIMEOUT = 180    # v6011：等「日志首行出现/变化」上限（原硬编码 90s；实测 Bob 67s 才出首行）
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
    with _SRVCTL_STARTQ_LOCK:
        q = _SRVCTL_STARTQ
        act = []
        now = time.time()
        for srv, v in q['active'].items():
            act.append({'server': srv, 'pct': v.get('pct', 0), 'label': v.get('label', ''),
                        'el': int(now - float(v.get('t0') or now)),
                        'heavy': bool(v.get('heavy')), 'msg': v.get('msg', '')})
        return {'running': bool(q['running']), 'user': q['user'], 'ts': int(q['ts'] or 0),
                'total': q.get('total', 0), 'doneCount': len(q['done']),
                'done': list(q['done']), 'active': act,
                'activeCount': len(act), 'heavyCount': _startq_heavy_count(),
                'queued': list(q['queue']), 'queuedCount': len(q['queue']),
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
        # ---- 采样各服实际阶段（读日志，放锁外）----
        try:
            _psnap = _srvctl_proc_snapshot() or {}
        except Exception:
            _psnap = {}
        for srv in srv_list:
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
                    if el > SRVCTL_STARTQ_FIRST_TIMEOUT:
                        v.update({'ok': False, 'phase': 'fail', 'heavy': False,
                                  'err': u'未见新进程启动（%ds 内日志首行未变）%s'
                                         % (SRVCTL_STARTQ_FIRST_TIMEOUT,
                                            _startq_logtail(srv))})
                    continue
                v['pct'] = pct
                v['label'] = label
                v['msg'] = u'%s…（%ds）' % (label, int(el))
                # v6011（用户口径 2026-11-03）：**advertising 才算启动完成**。
                #   原 `started or advertising` 在 started（实测 Isl 119s）就判完成并
                #   交还重压槽位，而 advertising 在 149s ⇒ 中间 30s 可再下发一台，
                #   出现「3 台同时启动」的窗口，违反重压上限 2。
                done_boot = bool(marks.get('advertising'))
                # v6006：槽位从「下发」即占用，直到 advertising（或超时）才释放。
                if done_boot:
                    v.update({'ok': True, 'phase': 'ok', 'pct': 100, 'heavy': False,
                              'msg': u'已对外开放加入 · 全程 %ds' % int(el)})
                elif (now - float(v.get('t0') or now)) > SRVCTL_STARTQ_HEAVY_TIMEOUT:
                    v.update({'ok': False, 'phase': 'fail', 'heavy': False,
                              'err': u'启动超时（%ds），已释放槽位' % SRVCTL_STARTQ_HEAVY_TIMEOUT})
                elif el > SRVCTL_STARTQ_ITEM_TIMEOUT:
                    v.update({'ok': False, 'phase': 'fail', 'heavy': False,
                              'err': u'启动超时（%ds）' % SRVCTL_STARTQ_ITEM_TIMEOUT})
                else:
                    v['heavy'] = True
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
            heavy = _startq_heavy_count()
            if (heavy < SRVCTL_STARTQ_HEAVY_MAX and _SRVCTL_STARTQ['queue']
                    and (now - float(_SRVCTL_STARTQ.get('lastSent') or 0)) >= SRVCTL_STARTQ_MIN_GAP):
                srv_next = _SRVCTL_STARTQ['queue'].pop(0)
                _SRVCTL_STARTQ['lastSent'] = now
            if not srv_next and not _SRVCTL_STARTQ['queue'] and not _SRVCTL_STARTQ['active']:
                _SRVCTL_STARTQ['running'] = False
                return
        if not srv_next:
            continue
        # ---- 下发（锁外，ASAM 调用可能耗时数秒）----
        if not _srvctl_acquire(srv_next, 'start'):
            with _SRVCTL_STARTQ_LOCK:
                _SRVCTL_STARTQ['queue'].insert(0, srv_next)   # 撞车 -> 放回队首稍后再试
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
            u0 = _SRVCTL_STARTQ.get('user') or ''
            if r.get('ok'):
                _SRVCTL_STARTQ['active'][srv_next] = {
                    't0': now, 'baseFirst': base_first,
                    # v6006：**下发即占槽位** —— 原实现等 world_load 日志出现才算重压，
                    #   而该日志约 113s 才打印 ⇒ 前 113s 槽位恒空，8s 间隔把 11 台全推下去压垮机器
                    'heavy': True, 't_heavy': now, 'seenProc': False,
                    'pct': 2, 'label': u'启动游戏进程', 'phase': 'run',
                    'msg': u'已下发，等待进程…', 'err': ''}
            else:
                _SRVCTL_STARTQ['done'].append({
                    'server': srv_next, 'ok': False, 'pct': 0, 'msg': '',
                    'err': str(r.get('message') or 'start failed'), 't_end': int(now)})
        _srvctl_release(srv_next, 'start')
        try:
            _srvctl_log(u0, srv_next, 'start', bool(r.get('ok')), r.get('ms', 0),
                        ('queued-sent' if r.get('ok') else str(r.get('message') or '')))
        except Exception:
            pass


def _srvctl_startq_new(user, servers):
    """建启动队列并起 worker；队列已在跑时把新服追加到队尾（自动去重）。"""
    global _SRVCTL_STARTQ_THREAD
    with _SRVCTL_STARTQ_LOCK:
        q = _SRVCTL_STARTQ
        if not q['running']:
            q.update({'running': True, 'user': user, 'ts': time.time(), 'total': 0,
                      'queue': [], 'active': {}, 'done': [], 'lastSent': 0.0})
        # v6014：done 里只有「成功」的服算占用（防重复启动）；
        #   「失败」的服不再占用 —— 否则任务条上的「重试」会被去重掉，根本不会重新下发。
        busy = set(q['queue']) | set(q['active'].keys())
        busy |= set(x.get('server') for x in q['done'] if x.get('ok'))
        add = [s for s in servers if s not in busy]
        if add:
            q['done'] = [x for x in q['done'] if x.get('server') not in add]
        q['queue'].extend(add)
        q['total'] = len(q['queue']) + len(q['active']) + len(q['done'])
        need_thread = (_SRVCTL_STARTQ_THREAD is None) or (not _SRVCTL_STARTQ_THREAD.is_alive())
    if need_thread:
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

def refresh_tamed(server):
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
    if ok:
        try:
            _dw = _dinodata_wait_stable(server, since_ts=_t_save, budget=90)
        except Exception:
            _dw = {}
    r = {'ok': ok, 'server': server, 'saved': ok, 'reply': text[:80], 'data': _dw, 'ts': now}
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
            raw = rcon_command(RCON_HOST, port, RCON_PASSWORD, 'GetInGameTime')
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
    try:
        d = _news_read('patch_pc') or {}
        best = None
        for c in (d.get('cards') or []):
            txt = str(c.get('content') or '')
            m = re.search(r'<h3>(.*?)</h3>', txt, re.S)
            head = m.group(1) if m else ''
            if not re.search(r'servers?\b', head, re.I):
                continue
            vm = re.search(r'(?<![\d.])v?(\d+)\.(\d+)', head, re.I)
            if not vm:
                continue
            cur = (int(vm.group(1)), int(vm.group(2)))
            if best is None or cur > best:
                best = cur
        return ('%d.%d' % best) if best else ''
    except Exception:
        return ''

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
        self.send_header('Access-Control-Allow-Origin', ALLOW_ORIGIN)
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, HEAD')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '86400')

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
            _sd = _srv_cfg_read()
            self._send(200, {'ok': True,
                             'server_domain': _sd.get('server_domain') or '',
                             'asa_base': _sd.get('asa_base') or 'https://asa.whiterober.com',
                             'asa_token_masked': _asa_mask(_sd.get('asa_token') or ''),
                             'asa_configured': bool(_sd.get('asa_token'))})
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
                             'serverVersion': str(_it.get('ServerVersion') or '')})
            # v5981：官方服务器版本 = 资讯广场 patch_pc 里 Server 补丁的最大版本号（96.9 这类）
            self._send(200, {'ok': True, 'servers': _out, 'official': _news_official_version(),
                             'ms': int((time.time() - _t0) * 1000)})
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
            _clr_tok = bool(body.get('asa_token_clear'))
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
                _d['updated_at'] = time.strftime('%Y-%m-%dT%H:%M:%S+08:00')
                _d['updated_by'] = _u
                _srv_cfg_write(_d)
            except Exception as e:
                self._send(500, {'ok': False, 'error': repr(e)})
                return
            self._send(200, {'ok': True, 'server_domain': _dom,
                             'asa_base': _d.get('asa_base') or 'https://asa.whiterober.com',
                             'asa_token_masked': _asa_mask(_d.get('asa_token') or ''),
                             'asa_configured': bool(_d.get('asa_token'))})
            return
        # ===== P3：服务器控制（仅二级管理员；前端不接触 token）=====
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
            # v6014（用户口径）：**所有** start 一律走队列 —— 含单台启动与失败重试。
            #   原实现只有「多台」入队、单台直通 ⇒ 任务条上的「重试」是单台请求，
            #   可绕过重压池（同时 <= 2 台）导致并发超标；改为统一入队后重压池才真正成立。
            if _act == 'start':
                try:
                    _q = _srvctl_startq_new(_u, _srvl)
                except Exception as _e:
                    self._send(500, {'ok': False, 'code': 'queue_error', 'error': repr(_e)})
                    return
                self._send(200, {'ok': True, 'queued': True, 'action': 'start',
                                 'servers': _srvl, 'queue': _q})
                return
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
                    _jid = _srvctl_job_new(_u, _act, _srvl)
                    self._send(200, {'ok': True, 'async': True, 'jobId': _jid,
                                     'action': _act, 'servers': _srvl})
                    return
                _res = _srvctl_run(_u, _srvl, _act, _msg)
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
            # 2026-08-28 异步化：后台线程执行 RCON（旧架构 AppDaemon 异步 1s 返回；此处立即返回触发成功，前端轮询 refresh_status.json/savedAt 等结果）
            _RCON_EXECUTOR.submit(refresh_tamed, server)
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
