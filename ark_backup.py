# -*- coding: utf-8 -*-
"""方舟安全回档 · P0 只读能力
================================================================
用途：给搞事系统「🗄 安全回档」面板提供**只读**数据，不触碰任何存档文件。

接口（由 dino_backend.py 的 Handler 调用）：
    list_points(abbr)                 回档点清单（不算 sha256，毫秒级）
    verify_point(abbr, rel_or_abs)    校验单个档（sha256 + SQLite 头）
    read_audit(abbr, limit)           审计日志

依赖：只读文件系统；不需要 RCON、不需要游戏在跑。
================================================================
"""
import io
import os
import re
import json
import time
import glob
import calendar
import hashlib
import shutil
import threading
from datetime import datetime

# ---------------- 路径（SERVER 本机；本地测试可用环境变量覆盖） ----------------
ARK_ROOT = os.environ.get('ARK_ROOT', r'D:\ARK Server\Servers')
DINO_DATA = os.environ.get('DINO_DATA', r'D:\ARK Server\DinoData')
BACKUP_ROOT = os.environ.get('ARKBACKUP_DIR', r'D:\dino_backend\arkbackup')
AUDIT_FILE = os.path.join(BACKUP_ROOT, 'audit.log')
# v6055：在线玩家快照目录 —— dino_backend.list_players 用 RCON ListPlayers 写 <abbr>_online.json
# 到这里（默认同 DINO_DATA 下 asa-data，与 dino_backend 的 ASA_DATA 一致）
ONLINE_DIR = os.environ.get('ONLINE_DIR', os.path.join(DINO_DATA, 'asa-data'))
ONLINE_TTL_DEFAULT = 300        # 5 分钟内的快照视为「当前在线」

# 支持的回档点扩展名（.arkrbf 同为 SQLite，见方案 §15 C5 / D4 待复议）
POINT_EXTS = ('.ark',)
MIN_VALID_BYTES = 10 * 1024 * 1024      # 小于 10 MB 视为无效占位档（实测多数地图是 0 B）

# 文件名时间戳：<地图>_WP_DD.MM.YYYY_HH.MM.SS.ark
_RE_TS = re.compile(r'_(\d{2})\.(\d{2})\.(\d{4})_(\d{2})\.(\d{2})\.(\d{2})$')
# 现有 4 个 bat 留下的中间态（§2.5）：<地图>_WP_now.ark / _new.ark —— 单列，不混进回档点
_RE_LEGACY = re.compile(r'_(now|new)\.ark$', re.I)

# ---------------- 内存缓存 ----------------
_MAPDIR_CACHE = {}          # abbr -> {'ts':float,'dir':str,'how':str}
_MAPDIR_TTL = 120           # 地图目录判定缓存 2 分钟（Profile 变了也能较快跟上）
_GUARD = threading.Lock()


def _log(msg):
    try:
        with io.open(os.path.join(BACKUP_ROOT, 'arkbackup.log'), 'a', encoding='utf-8') as f:
            f.write('[%s] %s\n' % (datetime.now().strftime('%m-%d %H:%M:%S'), msg))
    except Exception:
        pass


# ---------------- ① 地图目录三级判定 ----------------
def _profile_mapdir(abbr):
    """① 读 ASA Manager 当前运行配置 Servers\\<abbr>\\Profile\\serverProfil.json 的 MapFolder。

    实测（2026-11-04）：
      · serverProfil.json = **当前运行配置**，MapFolder 正确（Sco → ScorchedEarth_WP）
      · <abbr>.json       = **保存的旧配置**，可能是默认值（Sco.json 里仍是 TheIsland_WP）⇒ 不可用
      · 该方案同样能正确处理 BobsMissions 这类不带 _WP 的目录
    """
    p = os.path.join(ARK_ROOT, abbr, 'Profile', 'serverProfil.json')
    if not os.path.isfile(p):
        return ''
    try:
        j = json.load(io.open(p, encoding='utf-8', errors='ignore'))
        d = str(j.get('MapFolder') or '').strip()
        if d:
            return d
    except Exception:
        pass
    return ''


def _scandir_mapdir(abbr):
    """② 退化：SavedArks 下**含有效 <地图>.ark（>10MB）** 且 mtime 最新的目录。"""
    base = os.path.join(ARK_ROOT, abbr, 'ShooterGame', 'Saved', 'SavedArks')
    if not os.path.isdir(base):
        return ''
    best, best_ts = '', -1.0
    try:
        for n in os.listdir(base):
            d = os.path.join(base, n)
            if not os.path.isdir(d):
                continue
            # 该目录下最大的 .ark（排除 0 B 占位）
            mx, mts = 0, 0.0
            for f in glob.glob(os.path.join(d, '*.ark')):
                try:
                    st = os.stat(f)
                except Exception:
                    continue
                if st.st_size > mx:
                    mx = st.st_size
                if st.st_mtime > mts:
                    mts = st.st_mtime
            if mx < MIN_VALID_BYTES:
                continue
            if mts > best_ts:
                best, best_ts = n, mts
    except Exception:
        return ''
    return best


def detect_map_dir(abbr, force=False):
    """返回 (mapdir, how)。how ∈ {'profile','scandir',''}；空串表示判定失败（调用方应报错让用户手选）。"""
    now = time.time()
    with _GUARD:
        hit = _MAPDIR_CACHE.get(abbr)
        if hit and not force and now - hit['ts'] < _MAPDIR_TTL:
            return hit['dir'], hit['how']
    d, how = _profile_mapdir(abbr), 'profile'
    if not d:
        d, how = _scandir_mapdir(abbr), 'scandir'
    if not d:
        how = ''
    with _GUARD:
        _MAPDIR_CACHE[abbr] = {'ts': now, 'dir': d, 'how': how}
    if not d:
        _log('detect_map_dir FAIL %s' % abbr)
    return d, how


def map_dir_info(abbr):
    d, how = detect_map_dir(abbr)
    base = os.path.join(ARK_ROOT, abbr, 'ShooterGame', 'Saved', 'SavedArks')
    return {
        'server': abbr,
        'mapDir': d,
        'detectedBy': how,                      # profile / scandir / '' (失败)
        'savedArksDir': base,
        'candidates': _list_mapdir_candidates(base) if not d else [],
    }


def _list_mapdir_candidates(savedarks):
    out = []
    try:
        for n in sorted(os.listdir(savedarks)):
            d = os.path.join(savedarks, n)
            if not os.path.isdir(d):
                continue
            arks = glob.glob(os.path.join(d, '*.ark'))
            valid = [f for f in arks if os.path.getsize(f) >= MIN_VALID_BYTES] if arks else []
            out.append({'dir': n, 'arkCount': len(arks), 'validCount': len(valid),
                        'maxMB': round(max([os.path.getsize(f) for f in arks] or [0]) / 1048576.0, 1)})
    except Exception:
        pass
    return out


# ---------------- ② 回档点扫描（不算 hash） ----------------
def _parse_rbf_point(path):
    """解析 `.arkrbf` 滚动备份（v6038 用户口径：列入可选回档点并置顶）。

    实测依据（2026-11-04，Cen/Isl）：
      · 文件头 `SQLite format 3` ⇒ 与 `.ark` 同为完整存档，exe 可直接解析（players=17 实测通过）
      · 每服**恒 4 个**，循环覆盖；时间点 = 服务器每次存盘时刻
        （比约 3 小时一个的定时快照密得多：Cen 实测 15:42 / 16:40 / 17:03）
    风险：可能被服务器新存盘覆盖 ⇒ 调用方应先用 `verify_point` 校验，换档前 `precheck` 会真正解析一次。
    """
    name = os.path.basename(path)
    try:
        st = os.stat(path)
    except Exception:
        return None
    if st.st_size < MIN_VALID_BYTES:
        return None
    stem = name[:-7] if name.lower().endswith('.arkrbf') else name
    m = _RE_TS.search(stem)
    if not m:
        return None
    dd, mm, yy, HH, MM, SS = m.groups()
    try:
        # 文件名时间同样是 **UTC**（与 .ark 快照一致，见 _parse_point 注释）
        ts = calendar.timegm(datetime(int(yy), int(mm), int(dd),
                                      int(HH), int(MM), int(SS)).timetuple())
    except Exception:
        ts = st.st_mtime
    return {
        'id': 'rbf:%s%s%s%s%s%s' % (yy, mm, dd, HH, MM, SS),
        'kind': 'rollback_backup',
        'name': name,
        'ts': datetime.fromtimestamp(ts).strftime('%Y-%m-%dT%H:%M:%S'),
        'tsEpoch': int(ts),
        'bytes': st.st_size,
        'mb': round(st.st_size / 1048576.0, 1),
        'mtime': datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%dT%H:%M:%S'),
        'rel': name,
        'label': '服务器滚动备份',
    }


def _parse_point(path, active_name):
    name = os.path.basename(path)
    try:
        st = os.stat(path)
    except Exception:
        return None
    if st.st_size < MIN_VALID_BYTES:
        return None
    ts, kind, pid = 0.0, 'auto_snapshot', ''
    if name == active_name:
        ts, kind, pid = st.st_mtime, 'active', 'active'
    else:
        ml = _RE_LEGACY.search(name)
        if ml:
            # 现有 bat 的中间态：_now = 上次回档前备份，_new = 停服前备份（单文件覆盖，不可靠）
            return {
                'id': 'legacy:' + name, 'kind': 'legacy_' + ml.group(1).lower(),
                'name': name, 'ts': datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%dT%H:%M:%S'),
                'tsEpoch': int(st.st_mtime), 'bytes': st.st_size,
                'mb': round(st.st_size / 1048576.0, 1),
                'mtime': datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%dT%H:%M:%S'),
                'rel': name,
                'note': '旧 bat 流程残留（单文件覆盖、无校验），建议清理；如要使用请先 verify',
            }
        stem = name[:-4] if name.lower().endswith('.ark') else name
        m = _RE_TS.search(stem)
        if m:
            dd, mm, yy, HH, MM, SS = m.groups()
            try:
                # ⚠ 存档文件名里的时间是 **UTC**（实测 2026-11-04：文件名 05.24.02 ↔ 文件 mtime 13:24:02，差 +8h）
                # 必须用 calendar.timegm 按 UTC 解析；用 time.mktime 会被当成本地时间 ⇒ 显示早 8 小时
                ts = calendar.timegm(datetime(int(yy), int(mm), int(dd),
                                              int(HH), int(MM), int(SS)).timetuple())
            except Exception:
                ts = st.st_mtime
            pid = 'auto:%s%s%s%s%s%s' % (yy, mm, dd, HH, MM, SS)
        else:
            ts, kind, pid = st.st_mtime, 'unknown', 'file:' + name
    return {
        'id': pid,
        'kind': kind,
        'name': name,
        'ts': datetime.fromtimestamp(ts).strftime('%Y-%m-%dT%H:%M:%S'),
        'tsEpoch': int(ts),
        'bytes': st.st_size,
        'mb': round(st.st_size / 1048576.0, 1),
        'mtime': datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%dT%H:%M:%S'),
        'rel': name,
    }


def list_points(abbr):
    """回档点清单（按时间倒序）。**不算 sha256**（方案 O4：23 档 × 165 MB 要 20~30 秒）。"""
    d, how = detect_map_dir(abbr)
    if not d:
        return {'ok': False, 'code': 'mapdir_unknown',
                'error': '无法判定地图目录，请先在 ASA Manager 里确认该服的 MapFolder',
                'info': map_dir_info(abbr)}
    folder = os.path.join(ARK_ROOT, abbr, 'ShooterGame', 'Saved', 'SavedArks', d)
    if not os.path.isdir(folder):
        return {'ok': False, 'code': 'dir_missing', 'error': '存档目录不存在: ' + folder,
                'info': map_dir_info(abbr)}
    mapname = d[:-3] if d.lower().endswith('_wp') else d
    active_name = '%s.ark' % d if os.path.isfile(os.path.join(folder, d + '.ark')) else None
    # 当前活跃档名 = <MapFolder>.ark（如 TheIsland_WP.ark）
    if active_name is None:
        cand = glob.glob(os.path.join(folder, '*.ark'))
        base_names = [os.path.basename(x) for x in cand]
        if (d + '.ark') in base_names:
            active_name = d + '.ark'
        elif (mapname + '.ark') in base_names:
            active_name = mapname + '.ark'
    points, legacy, active = [], [], None
    t0 = time.time()
    for f in glob.glob(os.path.join(folder, '*.ark')):
        p = _parse_point(f, active_name)
        if not p:
            continue
        if p['kind'] == 'active':
            active = p
        elif p['kind'].startswith('legacy_'):
            legacy.append(p)
        else:
            points.append(p)
    points.sort(key=lambda x: x['tsEpoch'], reverse=True)
    legacy.sort(key=lambda x: x['tsEpoch'], reverse=True)

    # v6038（用户口径）：滚动备份 .arkrbf —— 单独成组，前端**置顶**显示
    rbf_points = []
    for f in glob.glob(os.path.join(folder, '*.arkrbf')):
        rp = _parse_rbf_point(f)
        if rp:
            rbf_points.append(rp)
    rbf_points.sort(key=lambda x: x['tsEpoch'], reverse=True)

    # 自建备份（每服固定 1 份，方案 §9）
    own_path = os.path.join(BACKUP_ROOT, abbr, 'pre_restore.ark')
    own = None
    if os.path.isfile(own_path):
        meta = read_backup_meta(abbr)
        try:
            st = os.stat(own_path)
        except Exception:
            st = None
        if st:
            ts = (meta or {}).get('tsEpoch') or int(st.st_mtime)
            own = {
                'id': 'own:pre_restore', 'kind': 'own_backup',
                'name': os.path.basename(own_path), 'absPath': own_path,
                'ts': datetime.fromtimestamp(ts).strftime('%Y-%m-%dT%H:%M:%S'),
                'tsEpoch': int(ts), 'bytes': st.st_size,
                'mb': round(st.st_size / 1048576.0, 1),
                'label': '回档前自动备份',
                'sourceArk': (meta or {}).get('sourceArk', ''),
                'jobId': (meta or {}).get('jobId', ''),
                'operator': (meta or {}).get('operator', ''),
                'undoCount': int((meta or {}).get('undoCount') or 0),
                'lastUndoStr': (meta or {}).get('lastUndoStr', ''),
            }

    return {
        'ok': True,
        'server': abbr,
        'mapDir': d,
        'detectedBy': how,
        'activeFile': active,
        'ownBackup': own,
        'points': points,
        'rbf': rbf_points,
        'legacy': legacy,
        'count': len(points) + (1 if own else 0),
        'rbfCount': len(rbf_points),
        'legacyCount': len(legacy),
        'elapsedMs': int((time.time() - t0) * 1000),
    }


# ---------------- ③ 单档校验（算 sha256） ----------------
def _sha256_file(path, chunk=4 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def verify_point(abbr, rel_or_abs):
    """校验单个回档点：可读性 + SQLite 头 + sha256。**只在用户点「验证」时调用**。"""
    d, _how = detect_map_dir(abbr)
    if not d:
        return {'ok': False, 'code': 'mapdir_unknown', 'error': '无法判定地图目录'}
    if os.path.isabs(rel_or_abs):
        path = rel_or_abs
    else:
        path = os.path.join(ARK_ROOT, abbr, 'ShooterGame', 'Saved', 'SavedArks', d, rel_or_abs)
    if not os.path.isfile(path):
        return {'ok': False, 'code': 'not_found', 'error': '文件不存在: ' + path}
    t0 = time.time()
    try:
        st = os.stat(path)
        if st.st_size < MIN_VALID_BYTES:
            return {'ok': False, 'code': 'too_small',
                    'error': '文件过小（%d B），疑似占位/损坏' % st.st_size}
        with open(path, 'rb') as f:
            head = f.read(16)
        is_sqlite = head.startswith(b'SQLite format 3')
        digest = _sha256_file(path)
        return {
            'ok': True,
            'path': path,
            'name': os.path.basename(path),
            'bytes': st.st_size,
            'mb': round(st.st_size / 1048576.0, 1),
            'sqlite': is_sqlite,
            'head': head[:16].hex(),
            'sha256': digest,
            'elapsedMs': int((time.time() - t0) * 1000),
        }
    except Exception as e:
        return {'ok': False, 'code': 'read_error', 'error': '%s: %s' % (type(e).__name__, e)}


# ---------------- ④ 自建备份元数据 ----------------
def read_backup_meta(abbr):
    p = os.path.join(BACKUP_ROOT, abbr, 'pre_restore.json')
    if not os.path.isfile(p):
        return None
    try:
        return json.load(io.open(p, encoding='utf-8', errors='ignore'))
    except Exception:
        return None


def bump_undo(abbr):
    """v6059（用户口径「要记录已执行撤销的次数，当前备份档，非所有的撤销次数」）：
    给**当前这一份** `pre_restore.ark` 的撤销次数 +1。

    口径说明：
      · 只统计「当前这份备份档」被撤销过几次，**不是历史所有撤销的累计**
      · `create_backup` 覆盖写入新备份时 undoCount 重置为 0（备份源换了，旧次数失去意义）
    """
    p = os.path.join(BACKUP_ROOT, abbr, 'pre_restore.json')
    meta = read_backup_meta(abbr)
    if not meta:
        return {'ok': False, 'error': 'no_backup_meta'}
    try:
        meta['undoCount'] = int(meta.get('undoCount') or 0) + 1
        meta['lastUndoEpoch'] = int(time.time())
        meta['lastUndoStr'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        io.open(p, 'w', encoding='utf-8').write(
            json.dumps(meta, ensure_ascii=False, indent=1))
        return {'ok': True, 'undoCount': meta['undoCount']}
    except Exception as e:
        return {'ok': False, 'error': '%s: %s' % (type(e).__name__, e)}


# ---------------- ④.5 创建备份（方案 §9：每服固定 1 份，循环覆盖） ----------------
def create_backup(abbr, operator='', job_id=''):
    """把**当前档**复制为 `arkbackup\\<服>\\pre_restore.ark`（固定名，**覆盖上一份**）。

    方案 §9 口径：每服恒 1 份 ⇒ 10 台合计 ≈ 1.7 GB，永不增长，无需轮转任务。
    原子写入：先复制到 `.tmp` 再 `os.replace`，避免读到半截文件。

    返回 {ok, ts, sourceArk, bytes, mb, sha256, overwrote, elapsedMs}
    失败码：mapdir_unknown / no_active / disk_low / write_error
    """
    d, _how = detect_map_dir(abbr)
    if not d:
        return {'ok': False, 'code': 'mapdir_unknown', 'error': '无法判定地图目录'}
    folder = os.path.join(ARK_ROOT, abbr, 'ShooterGame', 'Saved', 'SavedArks', d)

    # ① 找当前活跃档：优先 <MapFolder>.ark；退化取最大的有效 .ark
    src = os.path.join(folder, d + '.ark')
    if not os.path.isfile(src):
        cands = []
        for f in glob.glob(os.path.join(folder, '*.ark')):
            try:
                sz = os.path.getsize(f)
            except Exception:
                continue
            if sz >= MIN_VALID_BYTES and not _RE_LEGACY.search(os.path.basename(f)):
                cands.append((sz, f))
        if not cands:
            return {'ok': False, 'code': 'no_active',
                    'error': '找不到当前活跃档：' + src}
        cands.sort(reverse=True)
        src = cands[0][1]
    try:
        st = os.stat(src)
    except Exception as e:
        return {'ok': False, 'code': 'read_error', 'error': str(e)}
    if st.st_size < MIN_VALID_BYTES:
        return {'ok': False, 'code': 'no_active', 'error': '当前档过小（%d B）' % st.st_size}

    dst_dir = os.path.join(BACKUP_ROOT, abbr)
    dst = os.path.join(dst_dir, 'pre_restore.ark')
    tmp = dst + '.tmp'

    # ② 磁盘检查（剩余 ≥ 1.2 × 源档；覆盖时新旧短暂共存，留 20% 余量）
    try:
        os.makedirs(dst_dir, exist_ok=True)
        du = shutil.disk_usage(dst_dir)
        need = int(st.st_size * 1.2)
        if du.free < need:
            return {'ok': False, 'code': 'disk_low',
                    'error': '磁盘剩余 %.2f GB < 需求 %.2f GB'
                             % (du.free / 1073741824.0, need / 1073741824.0),
                    'freeBytes': du.free, 'needBytes': need}
    except Exception as e:
        return {'ok': False, 'code': 'write_error', 'error': 'mkdir/disk: %s' % e}

    # ③ 记下将被覆盖的旧备份（供前端提示）
    old_meta = read_backup_meta(abbr) or {}
    overwrote = None
    if os.path.isfile(dst):
        overwrote = {'ts': old_meta.get('ts', ''), 'sourceArk': old_meta.get('sourceArk', '')}

    # ④ 复制（.tmp → 原子替换）
    t0 = time.time()
    try:
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)
    except Exception as e:
        try:
            if os.path.isfile(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return {'ok': False, 'code': 'write_error', 'error': '%s: %s' % (type(e).__name__, e)}

    try:
        digest = _sha256_file(dst)
    except Exception:
        digest = ''

    # ⑤ 写元数据 + 审计
    now = datetime.now()
    meta = {
        'ts': now.strftime('%Y-%m-%dT%H:%M:%S'),
        'tsEpoch': int(now.timestamp()),
        'server': abbr,
        'sourceArk': os.path.basename(src),
        'sourcePath': src,
        'sourceMtime': int(st.st_mtime),
        'sizeBytes': st.st_size,
        'sha256': digest,
        'jobId': job_id or '',
        'operator': operator or '',
        # v6059：新备份 = 新计数起点（备份源换了，上一份的撤销次数不再适用）
        'undoCount': 0,
    }
    try:
        io.open(os.path.join(dst_dir, 'pre_restore.json'), 'w', encoding='utf-8').write(
            json.dumps(meta, ensure_ascii=False, indent=1))
    except Exception as e:
        _log('write meta FAIL %s' % e)

    append_audit({'server': abbr, 'action': 'create', 'ok': True,
                  'sourceArk': meta['sourceArk'], 'bytes': meta['sizeBytes'],
                  'sha256': digest, 'jobId': meta['jobId'], 'operator': operator,
                  'overwrote': (overwrote or {}).get('ts', '')})

    return {'ok': True, 'ts': meta['ts'], 'sourceArk': meta['sourceArk'],
            'bytes': meta['sizeBytes'], 'mb': round(meta['sizeBytes'] / 1048576.0, 1),
            'sha256': digest, 'overwrote': overwrote,
            'elapsedMs': int((time.time() - t0) * 1000)}


# ---------------- ⑧ 玩家进出流水 + 角色档案（Full_Serveur_Backup\PlayerProfile，v6043） ----------------
# 用户 2026-11-04 指出：「你为啥没考虑 Full_Serveur_Backup\PlayerProfile 里面的玩家进出情况？」
# 实测（Cen 69 / Isl 125 个 zip，2024-09 ~ 2026-11 仍在增长）：
#   connect-YYYYMMDDHHMMSS-<玩家名>-<eosId32>.zip       玩家**进入**
#   disconnect-YYYYMMDDHHMMSS-<玩家名>-<eosId32>.zip    玩家**离开**
#   每个 zip 内 = <eosId>.arkprofile（角色档案，12 KB ~ 300 KB）
# ⚠ 文件名时间是**本地时间**（connect-…171716 ↔ mtime 17:17:16）；
#   而 `.ark` 快照文件名是 **UTC** —— 两套时间基准，绝不能混用解析函数。
_RE_PP = re.compile(r'^(connect|disconnect)-(\d{14})-(.+)-([0-9a-fA-F]{32})\.zip$')


def pp_dir(abbr):
    r"""`Saved\SavedArks\Full_Serveur_Backup\PlayerProfile`"""
    return os.path.join(ARK_ROOT, abbr, 'ShooterGame', 'Saved', 'SavedArks',
                        'Full_Serveur_Backup', 'PlayerProfile')


def _pp_time(digits):
    """`YYYYMMDDHHMMSS`（**本地时间**）→ epoch 秒"""
    try:
        return int(time.mktime(datetime(int(digits[0:4]), int(digits[4:6]), int(digits[6:8]),
                                        int(digits[8:10]), int(digits[10:12]),
                                        int(digits[12:14])).timetuple()))
    except Exception:
        return 0


def read_presence(abbr):
    """扫描 PlayerProfile 的连接流水（**只读文件名，不解压**，几百个文件毫秒级）。

    返回 {ok, dir, count, players:{eosId:{eosId,name,lastConnect,lastDisconnect,
          connects,disconnects,online,lastConnectStr,lastDisconnectStr}}, elapsedMs}
    `online` = 最后一次是 connect（据此可判断「该玩家现在应该在本服」）。
    """
    t0 = time.time()
    d = pp_dir(abbr)
    if not os.path.isdir(d):
        return {'ok': False, 'code': 'pp_missing',
                'error': '没有 Full_Serveur_Backup/PlayerProfile 目录：%s' % d}
    players = {}
    n = 0
    try:
        names = os.listdir(d)
    except Exception as e:
        return {'ok': False, 'code': 'pp_list', 'error': '%s: %s' % (type(e).__name__, e)}
    for fn in names:
        m = _RE_PP.match(fn)
        if not m:
            continue
        n += 1
        kind = m.group(1).lower()
        t = _pp_time(m.group(2))
        pname = m.group(3)
        eos = m.group(4).lower()
        p = players.get(eos)
        if p is None:
            p = players[eos] = {'eosId': eos, 'name': pname, 'lastConnect': 0,
                                'firstConnect': 0, 'lastDisconnect': 0, 'firstDisconnect': 0,
                                'connects': 0, 'disconnects': 0, 'events': []}
        if pname:
            p['name'] = pname
        # v6045：保留**逐条**进出事件 —— precheck 要按「目标档时刻 T」切窗口列出名单，
        #   只有 last*/first* 无法回答「T 之后这个人到底进出了几次、什么时候」
        p['events'].append({'kind': kind, 'ts': int(t)})
        if kind == 'connect':
            p['connects'] += 1
            if t > p['lastConnect']:
                p['lastConnect'] = t
            if not p['firstConnect'] or t < p['firstConnect']:
                p['firstConnect'] = t
        else:
            p['disconnects'] += 1
            if t > p['lastDisconnect']:
                p['lastDisconnect'] = t
            if not p['firstDisconnect'] or t < p['firstDisconnect']:
                p['firstDisconnect'] = t
    for p in players.values():
        p['events'].sort(key=lambda e: e['ts'])
        if len(p['events']) > 40:          # 上限 40 条，防老服流水膨胀
            p['events'] = p['events'][-40:]
        # ⚠ 语义修正（v6043b）：`lastAction` 只说明**最后一次记录的类型**（进入/离开），
        #   **不代表该玩家现在在线** —— 实测 Cen 的 JaronV5 最后一次是 connect（23:47），
        #   但那是 12 天前的记录，人早下线了。前端只显示时间，不要拿它当实时在线开关。
        p['lastAction'] = ('connect' if (p['lastConnect'] or 0) >= (p['lastDisconnect'] or 0)
                            else 'disconnect')
        p['online'] = bool(p['lastConnect'] and p['lastConnect'] > p['lastDisconnect'])  # 兼容旧字段
        p['lastConnectStr'] = (datetime.fromtimestamp(p['lastConnect']).strftime('%Y-%m-%dT%H:%M:%S')
                               if p['lastConnect'] else '')
        p['lastDisconnectStr'] = (datetime.fromtimestamp(p['lastDisconnect']).strftime('%Y-%m-%dT%H:%M:%S')
                                  if p['lastDisconnect'] else '')
    return {'ok': True, 'dir': d, 'count': n, 'players': players,
            'playerCount': len(players), 'elapsedMs': int((time.time() - t0) * 1000)}


def read_online(abbr, max_age=ONLINE_TTL_DEFAULT):
    """读 <ONLINE_DIR>/<abbr>_online.json（dino_backend.list_players 的 RCON ListPlayers 产物）。

    文件结构：{'state': 'ok'|'error', 'attributes': {ok, server, players:[{eosId,name}], count, ts}}

    返回 {ok, fresh, ageSec, count, players, tsStr, reason}
      ok=False ⇒ 没有可用快照（从未探测 / 上次 RCON 失败 / 服务器离线）＝「在线状态未知」
      ok=True  ⇒ count = 快照时刻的在线人数；fresh=False 表示快照已超过 max_age

    v6055（用户口径「同时风险要考虑在线用户」）：回档会把当前在线玩家**直接踢下线**，
    且他们的进度退回目标档时刻 ⇒ 在线人数必须计入 verdict。只在前端提示不够：
    直接调 /api/arkbackup/execute 会绕过前端，只有 precheck 里算进 verdict 才拦得住。
    """
    p = os.path.join(ONLINE_DIR, '%s_online.json' % abbr)
    if not os.path.isfile(p):
        return {'ok': False, 'reason': 'no_snapshot', 'count': 0, 'players': []}
    try:
        st = os.stat(p)
        age = int(time.time() - st.st_mtime)
        with io.open(p, encoding='utf-8') as f:
            doc = json.load(f)
    except Exception as e:
        return {'ok': False, 'reason': '%s: %s' % (type(e).__name__, e), 'count': 0, 'players': []}
    at = doc.get('attributes') if isinstance(doc, dict) else None
    if not isinstance(at, dict):
        at = doc if isinstance(doc, dict) else {}
    if not at.get('ok'):
        # 上次探测 RCON 失败 ⇒ 服务器可能离线 / 未就绪，不能据此断言「无人在线」
        return {'ok': False, 'reason': (at.get('error') or 'rcon_failed'),
                'state': (doc.get('state') if isinstance(doc, dict) else ''),
                'ageSec': age, 'count': 0, 'players': []}
    out = []
    for x in (at.get('players') or []):
        if not isinstance(x, dict):
            continue
        out.append({'eosId': (x.get('eosId') or '').lower(), 'name': x.get('name') or ''})
    return {'ok': True, 'fresh': (age <= max_age), 'ageSec': age,
            'count': len(out), 'players': out, 'tsStr': at.get('ts') or ''}


def list_profiles(abbr, eos=None):
    """列出可恢复的角色档案（按玩家聚合，取**最新**那份 zip）。

    返回 {ok, count, items:[{eosId,name,ts,tsEpoch,zip,zipPath,bytes,connect,disconnect}]}
    """
    d = pp_dir(abbr)
    if not os.path.isdir(d):
        return {'ok': False, 'code': 'pp_missing', 'error': '没有 PlayerProfile 目录'}
    latest = {}
    try:
        names = os.listdir(d)
    except Exception as e:
        return {'ok': False, 'code': 'pp_list', 'error': '%s: %s' % (type(e).__name__, e)}
    for fn in names:
        m = _RE_PP.match(fn)
        if not m:
            continue
        eos_id = m.group(4).lower()
        if eos and eos_id != str(eos).lower():
            continue
        t = _pp_time(m.group(2))
        fp = os.path.join(d, fn)
        cur = latest.get(eos_id)
        if cur is None or t > cur['tsEpoch']:
            try:
                sz = os.path.getsize(fp)
            except Exception:
                sz = 0
            latest[eos_id] = {
                'eosId': eos_id, 'name': m.group(3), 'ts': m.group(2),
                'tsEpoch': t,
                'tsStr': (datetime.fromtimestamp(t).strftime('%Y-%m-%dT%H:%M:%S') if t else ''),
                'kind': m.group(1).lower(), 'zip': fn, 'zipPath': fp, 'bytes': sz,
            }
    items = sorted(latest.values(), key=lambda x: x['tsEpoch'], reverse=True)
    return {'ok': True, 'count': len(items), 'items': items,
            'elapsedMs': int((time.time() - t0) * 1000) if False else 0}


def restore_profile(abbr, eos, zip_name=None, dry_run=True):
    """把 PlayerProfile 里 `<eosId>.arkprofile` 解压到地图存档目录（游戏据此恢复角色）。

    ⚠ 写操作：会**覆盖** mapdir 下同名 `.arkprofile`。
    约定：服务器**运行时**写入可能被游戏缓存覆盖 ⇒ 建议**先停服**再恢复，或恢复后重启。
    返回 {ok, dryRun, target, from_zip, bytes, backup, elapsedMs}
    """
    import zipfile
    d = pp_dir(abbr)
    if not os.path.isdir(d):
        return {'ok': False, 'code': 'pp_missing', 'error': '没有 PlayerProfile 目录'}
    eos_l = str(eos or '').lower()
    if not re.match(r'^[0-9a-f]{32}$', eos_l):
        return {'ok': False, 'code': 'bad_eos', 'error': 'eosId 格式不对（需 32 位 hex）'}

    zp = os.path.join(d, zip_name) if zip_name else ''
    if not zp or not os.path.isfile(zp):
        zs = []
        for fn in os.listdir(d):
            m = _RE_PP.match(fn)
            if m and m.group(4).lower() == eos_l:
                t = _pp_time(m.group(2))
                zs.append((t, fn))
        if not zs:
            return {'ok': False, 'code': 'no_zip', 'error': '该玩家没有连接记录'}
        zs.sort(reverse=True)
        zp = os.path.join(d, zs[0][1])

    md, _how = detect_map_dir(abbr)
    if not md:
        return {'ok': False, 'code': 'mapdir_unknown', 'error': '无法判定地图目录'}
    folder = os.path.join(ARK_ROOT, abbr, 'ShooterGame', 'Saved', 'SavedArks', md)
    if not os.path.isdir(folder):
        return {'ok': False, 'code': 'mapdir_missing', 'error': '地图目录不存在'}
    target = os.path.join(folder, eos_l + '.arkprofile')

    try:
        with zipfile.ZipFile(zp) as z:
            inner = None
            for nm in z.namelist():
                if nm.lower().endswith('.arkprofile'):
                    inner = nm
                    break
            if not inner:
                return {'ok': False, 'code': 'no_profile_in_zip',
                        'error': '压缩包里没有 .arkprofile：%s' % os.path.basename(zp)}
            raw_data = z.read(inner)
    except Exception as e:
        return {'ok': False, 'code': 'unzip_error', 'error': '%s: %s' % (type(e).__name__, e)}

    info = {'ok': True, 'dryRun': bool(dry_run), 'target': target,
            'fromZip': zp, 'innerName': inner, 'bytes': len(raw_data),
            'targetExisted': os.path.isfile(target),
            'targetBytesBefore': (os.path.getsize(target) if os.path.isfile(target) else 0)}
    if dry_run:
        info['elapsedMs'] = 0
        return info

    bak = ''
    try:
        if os.path.isfile(target):
            bak = target + '.bak_%s' % datetime.now().strftime('%Y%m%d_%H%M%S')
            shutil.copy2(target, bak)
        tmp = target + '.tmp'
        with io.open(tmp, 'wb') as f:
            f.write(raw_data)
        os.replace(tmp, target)
        info['backup'] = bak
    except Exception as e:
        return {'ok': False, 'code': 'write_error', 'error': '%s: %s' % (type(e).__name__, e)}
    append_audit({'server': abbr, 'action': 'restore_profile', 'ok': True,
                  'eosId': eos_l, 'zip': os.path.basename(zp), 'bytes': len(raw_data),
                  'backup': os.path.basename(bak) if bak else ''})
    return info


# ---------------- ⑤ 审计 ----------------
def read_audit(abbr, limit=50):
    rows = []
    if not os.path.isfile(AUDIT_FILE):
        return {'ok': True, 'server': abbr, 'rows': [], 'total': 0}
    try:
        with io.open(AUDIT_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    j = json.loads(line)
                except Exception:
                    continue
                if abbr and j.get('server') != abbr:
                    continue
                rows.append(j)
    except Exception as e:
        return {'ok': False, 'error': '%s: %s' % (type(e).__name__, e)}
    rows.reverse()
    return {'ok': True, 'server': abbr, 'rows': rows[:max(1, int(limit))], 'total': len(rows)}


def append_audit(rec):
    """追加一条审计记录（JSON Lines）。写入失败不影响主流程。"""
    try:
        os.makedirs(BACKUP_ROOT, exist_ok=True)
        rec = dict(rec)
        rec.setdefault('ts', datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
        with io.open(AUDIT_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
        return True
    except Exception as e:
        _log('append_audit FAIL %s' % e)
        return False


# ---------------- ⑥ P3：解析与角色集合（方案 §5.5.3 / §5.5.5） ----------------
EXE_PATH = os.path.join(DINO_DATA, 'ark_save_reader.exe')
OFFLINE_DIR = os.path.join(DINO_DATA, '_offline')
CRYO_TTL_DEFAULT = 1800          # _cryo 超过 30 分钟视为过期（§15 C1）
_ALL_SERVERS = ('Isl', 'Sco', 'Cen', 'Abe', 'Ext', 'Ast', 'Rag', 'Val', 'Los', 'Gen')

_EXE_CACHE = {}                  # cacheKey -> {'ts':float, 'parsed':dict}
_EXE_CACHE_TTL = 600             # 同一目标档解析结果缓存 10 分钟（§15 O1）
_EXE_LOCK = threading.Lock()
_CRYO_CACHE = {}                 # abbr -> {'key':str, 'ts':float, 'parsed':dict}


def _read_gz_json(path):
    """读 .json.gz → dict"""
    import gzip
    with gzip.open(path, 'rb') as f:
        return json.loads(f.read().decode('utf-8', 'replace'))


def _split_players(doc):
    """产物 doc → (players{pid:info}, tribes, pid2tribe{pid:tribeName}, pid2tid{pid:tribeId})"""
    players = {}
    for p in (doc.get('players') or []):
        if not isinstance(p, dict):
            continue
        try:
            pid = int(p.get('pid') or 0)
        except Exception:
            pid = 0
        if not pid:
            continue
        players[pid] = {
            'pid': pid,
            'eosId': p.get('eosId') or '',
            'characterName': p.get('characterName') or '',
            'name': p.get('name') or '',
        }
    tribes = doc.get('tribes') or {}
    pid2tribe, pid2tid = {}, {}
    if isinstance(tribes, dict):
        for tid, t in tribes.items():
            if not isinstance(t, dict):
                continue
            tname = t.get('name') or ''
            for m in (t.get('members') or []):
                if not isinstance(m, dict):
                    continue
                try:
                    mp = int(m.get('pid') or 0)
                except Exception:
                    mp = 0
                if mp:
                    pid2tribe[mp] = tname
                    try:
                        pid2tid[mp] = int(tid)
                    except Exception:
                        pass
    return players, tribes, pid2tribe, pid2tid


def _cleanup_exe_side(out_base):
    """清理 exe 的中间产物（.db / .snap / _db），只保留 .json.gz"""
    for ext in ('.db', '.snap', '.json.db', '.json.snap'):
        p = out_base + ext
        try:
            if os.path.isfile(p):
                os.remove(p)
        except Exception:
            pass


def run_exe(ark_abs, abbr, timeout=150, out_base=None):
    """直调插件端解析器（方案 §5.5.5①）。

    返回 {ok, okParse, players{pid:info}, tribes, pid2tribe, pid2tid,
          gzPath, outBytes, rc, elapsedMs, stderr, cacheHit}
    产物：`<out_base>.gz`（自动清理 .db/.snap）。
    """
    import subprocess
    if not os.path.isfile(EXE_PATH):
        return {'ok': False, 'code': 'exe_missing', 'error': '解析器不存在: ' + EXE_PATH}
    if not ark_abs or not os.path.isfile(ark_abs):
        return {'ok': False, 'code': 'ark_missing', 'error': '存档不存在: %s' % ark_abs}

    try:
        st = os.stat(ark_abs)
        ckey = '%s|%d|%d' % (os.path.normcase(ark_abs), st.st_size, int(st.st_mtime))
    except Exception:
        ckey = os.path.normcase(ark_abs)
    now = time.time()
    with _EXE_LOCK:
        c = _EXE_CACHE.get(ckey)
        if c and (now - c['ts']) < _EXE_CACHE_TTL:
            r = dict(c['parsed'])
            r['cacheHit'] = True
            return r

    if not out_base:
        base = re.sub(r'[^A-Za-z0-9_.-]', '_', os.path.basename(ark_abs))[:60]
        out_base = os.path.join(OFFLINE_DIR, '%s__%s__%d' % (abbr, base, int(now * 1000) % 10 ** 9))
    if not out_base.lower().endswith('.json'):
        out_base += '.json'
    try:
        if not os.path.isdir(OFFLINE_DIR):
            os.makedirs(OFFLINE_DIR)
    except Exception:
        pass

    t0 = time.time()
    try:
        pr = subprocess.run([EXE_PATH, ark_abs, out_base, abbr, 'light'],
                            capture_output=True, timeout=timeout,
                            creationflags=0x08000000)
        rc = pr.returncode
        err = (pr.stderr or b'').decode('utf-8', 'replace')[:400]
    except subprocess.TimeoutExpired:
        _cleanup_exe_side(out_base)
        return {'ok': False, 'code': 'exe_timeout', 'error': '解析超时 %ds' % timeout}
    except Exception as e:
        _cleanup_exe_side(out_base)
        return {'ok': False, 'code': 'exe_error', 'error': '%s: %s' % (type(e).__name__, e)}

    gz = out_base + '.gz'
    elapsed = (time.time() - t0) * 1000
    if rc != 0 or not os.path.isfile(gz):
        _cleanup_exe_side(out_base)
        return {'ok': False, 'code': 'exe_failed', 'rc': rc, 'stderr': err,
                'error': '解析失败 rc=%s %s' % (rc, err[:160])}
    try:
        doc = _read_gz_json(gz)
    except Exception as e:
        _cleanup_exe_side(out_base)
        return {'ok': False, 'code': 'exe_badjson', 'error': '%s: %s' % (type(e).__name__, e)}
    _cleanup_exe_side(out_base)

    players, tribes, pid2tribe, pid2tid = _split_players(doc)
    res = {
        'ok': True,
        'players': players, 'tribes': tribes, 'pid2tribe': pid2tribe, 'pid2tid': pid2tid,
        'gzPath': gz, 'outBytes': os.path.getsize(gz),
        'rc': rc, 'elapsedMs': int(elapsed), 'cacheHit': False,
        'arkPath': doc.get('arkPath') or ark_abs,
        'serverId': doc.get('serverId') or abbr,
        'playerCount': len(players), 'tribeCount': len(tribes),
    }
    with _EXE_LOCK:
        _EXE_CACHE[ckey] = {'ts': now, 'parsed': dict(res)}
    return res


def cryo_doc(abbr, max_age=CRYO_TTL_DEFAULT):
    """读 DinoData\\<abbr>_cryo.json.gz（插件定时全量导出）。

    返回 {ok, players, tribes, pid2tribe, pid2tid, cryopod, structures, facilities,
          ageSec, mtime, gzPath, fresh}
    """
    gz = os.path.join(DINO_DATA, '%s_cryo.json.gz' % abbr)
    if not os.path.isfile(gz):
        return {'ok': False, 'code': 'cryo_missing', 'error': '未找到 %s' % gz}
    try:
        st = os.stat(gz)
    except Exception as e:
        return {'ok': False, 'code': 'cryo_stat', 'error': '%s: %s' % (type(e).__name__, e)}
    ckey = '%d|%d' % (st.st_size, int(st.st_mtime))
    now = time.time()
    with _EXE_LOCK:
        c = _CRYO_CACHE.get(abbr)
        if c and c['key'] == ckey:
            parsed = c['parsed']
            out = dict(parsed)
            out['ageSec'] = int(now - st.st_mtime)
            out['fresh'] = out['ageSec'] <= max_age
            return out
    try:
        doc = _read_gz_json(gz)
    except Exception as e:
        return {'ok': False, 'code': 'cryo_badjson', 'error': '%s: %s' % (type(e).__name__, e)}
    players, tribes, pid2tribe, pid2tid = _split_players(doc)
    parsed = {
        'ok': True,
        'players': players, 'tribes': tribes, 'pid2tribe': pid2tribe, 'pid2tid': pid2tid,
        'cryopod': doc.get('cryopod') or [],
        'structures': doc.get('structures') or [],
        'facilities': doc.get('facilities') or [],
        'arkPath': doc.get('arkPath') or '',
        'mtime': int(st.st_mtime),
        'gzPath': gz,
        'playerCount': len(players),
    }
    with _EXE_LOCK:
        _CRYO_CACHE[abbr] = {'key': ckey, 'ts': now, 'parsed': parsed}
    out = dict(parsed)
    out['ageSec'] = int(now - st.st_mtime)
    out['fresh'] = out['ageSec'] <= max_age
    return out


def current_players(abbr, max_age=CRYO_TTL_DEFAULT, allow_reparse=True):
    """当前档角色集合（§5.5.3 ③）。

    先用 `_cryo.json.gz`；过期时若 allow_reparse 则 exe 重解析**当前档**。
    返回 {ok, source:'cryo'|'exe'|'cryo_stale', players, pid2tribe, pid2tid,
          cryo, reparsed, ageSec, elapsedMs}
    """
    t0 = time.time()
    cr = cryo_doc(abbr, max_age=max_age)
    if cr.get('ok') and cr.get('fresh'):
        return {'ok': True, 'source': 'cryo', 'players': cr['players'],
                'pid2tribe': cr['pid2tribe'], 'pid2tid': cr['pid2tid'],
                'cryo': cr, 'reparsed': False, 'ageSec': cr.get('ageSec'),
                'elapsedMs': int((time.time() - t0) * 1000)}

    if not allow_reparse:
        if cr.get('ok'):
            return {'ok': True, 'source': 'cryo_stale', 'players': cr['players'],
                    'pid2tribe': cr['pid2tribe'], 'pid2tid': cr['pid2tid'],
                    'cryo': cr, 'reparsed': False, 'ageSec': cr.get('ageSec'),
                    'elapsedMs': int((time.time() - t0) * 1000)}
        return {'ok': False, 'code': cr.get('code') or 'cryo_missing',
                'error': cr.get('error') or '当前档角色获取失败'}

    # _cryo 过期/缺失 → exe 重解析当前档
    md, _how_md = detect_map_dir(abbr)
    ark = os.path.join(ARK_ROOT, abbr, 'ShooterGame', 'Saved', 'SavedArks', md,
                       _active_name(abbr, md)) if md else ''
    pr = run_exe(ark, abbr)
    if not pr.get('ok'):
        if cr.get('ok'):
            return {'ok': True, 'source': 'cryo_stale', 'players': cr['players'],
                    'pid2tribe': cr['pid2tribe'], 'pid2tid': cr['pid2tid'],
                    'cryo': cr, 'reparsed': False, 'ageSec': cr.get('ageSec'),
                    'warn': '重解析失败：' + (pr.get('error') or ''),
                    'elapsedMs': int((time.time() - t0) * 1000)}
        return {'ok': False, 'code': pr.get('code'), 'error': pr.get('error')}
    return {'ok': True, 'source': 'exe', 'players': pr['players'],
            'pid2tribe': pr['pid2tribe'], 'pid2tid': pr['pid2tid'],
            'cryo': cr, 'reparsed': True, 'ageSec': cr.get('ageSec'),
            'elapsedMs': int((time.time() - t0) * 1000)}


def _active_name(abbr, mapdir):
    """当前档文件名（优先 <MapFolder>.ark，退化取最新有效 .ark）"""
    d = os.path.join(ARK_ROOT, abbr, 'ShooterGame', 'Saved', 'SavedArks', mapdir)
    exact = mapdir + '.ark'
    if os.path.isfile(os.path.join(d, exact)):
        return exact
    best, best_m = '', -1
    try:
        for fn in os.listdir(d):
            if not fn.lower().endswith('.ark') or _RE_LEGACY.search(fn) or _RE_TS.search(fn):
                continue
            p = os.path.join(d, fn)
            try:
                sz = os.path.getsize(p)
                mt = os.path.getmtime(p)
            except Exception:
                continue
            if sz < MIN_VALID_BYTES:
                continue
            if mt > best_m:
                best, best_m = fn, mt
    except Exception:
        pass
    return best


def pid_index(servers=None, max_age=CRYO_TTL_DEFAULT):
    """把 N 台服的 players 汇成 {pid: [服缩写...]}（§5.5.3 ⑤，O(1) 查表）"""
    idx, ages = {}, {}
    for s in (servers or _ALL_SERVERS):
        cr = cryo_doc(s, max_age=max_age)
        if not cr.get('ok'):
            ages[s] = None
            continue
        ages[s] = cr.get('ageSec')
        for pid in cr['players'].keys():
            idx.setdefault(pid, []).append(s)
    return {'index': idx, 'ages': ages, 'servers': len(ages)}


def resolve_point(abbr, point):
    """把前端给的 pointId（或文件名 / 绝对路径）解析成目标档绝对路径。

    支持：
      own:pre_restore                  → BACKUP_ROOT\\<服>\\pre_restore.ark
      auto:YYYYMMDDHHMMSS              → mapDir 内匹配 _DD.MM.YYYY_HH.MM.SS.ark
      active                           → 当前活跃档
      <文件名>.ark                     → mapDir\\<文件名>
      <绝对路径>                       → 原样（存在即用）
    返回 {ok, abs, kind, name, error?}
    """
    if not point:
        return {'ok': False, 'code': 'point_required', 'error': '缺少 pointId'}
    p = str(point).strip()

    if os.path.isabs(p):
        if os.path.isfile(p):
            return {'ok': True, 'abs': p, 'kind': 'abs', 'name': os.path.basename(p)}
        return {'ok': False, 'code': 'point_missing', 'error': '路径不存在: %s' % p}

    if p == 'own:pre_restore':
        ap = os.path.join(BACKUP_ROOT, abbr, 'pre_restore.ark')
        if os.path.isfile(ap):
            return {'ok': True, 'abs': ap, 'kind': 'own_backup', 'name': 'pre_restore.ark'}
        return {'ok': False, 'code': 'no_backup', 'error': '该服还没有回档前备份'}

    md, _how = detect_map_dir(abbr)
    if not md:
        return {'ok': False, 'code': 'mapdir_unknown', 'error': '无法判定地图目录'}
    folder = os.path.join(ARK_ROOT, abbr, 'ShooterGame', 'Saved', 'SavedArks', md)

    if p == 'active':
        nm = _active_name(abbr, md)
        if not nm:
            return {'ok': False, 'code': 'no_active', 'error': '未找到当前档'}
        return {'ok': True, 'abs': os.path.join(folder, nm), 'kind': 'active', 'name': nm}

    if p.startswith('rbf:'):
        # v6038：滚动备份 .arkrbf
        digits = p[4:]
        if len(digits) == 14 and digits.isdigit():
            fn = '%s_%s.%s.%s_%s.%s.%s.arkrbf' % (
                md, digits[6:8], digits[4:6], digits[0:4],
                digits[8:10], digits[10:12], digits[12:14])
            ap = os.path.join(folder, fn)
            if os.path.isfile(ap):
                return {'ok': True, 'abs': ap, 'kind': 'rollback_backup', 'name': fn}
        return {'ok': False, 'code': 'point_missing', 'error': '找不到该滚动备份: %s' % p}

    if p.startswith('auto:'):
        digits = p[5:]
        if len(digits) == 14 and digits.isdigit():
            fn = '%s_%s.%s.%s_%s.%s.%s.ark' % (
                md, digits[6:8], digits[4:6], digits[0:4], digits[8:10], digits[10:12], digits[12:14])
            ap = os.path.join(folder, fn)
            if os.path.isfile(ap):
                return {'ok': True, 'abs': ap, 'kind': 'auto_snapshot', 'name': fn}
        return {'ok': False, 'code': 'point_missing', 'error': '找不到该回档点: %s' % p}

    if p.startswith('legacy:') or p.startswith('file:'):
        p = p.split(':', 1)[1]
    ap = os.path.join(folder, os.path.basename(p))
    if os.path.isfile(ap):
        return {'ok': True, 'abs': ap, 'kind': 'file', 'name': os.path.basename(ap)}
    return {'ok': False, 'code': 'point_missing', 'error': '找不到回档点: %s' % p}


def precheck(abbr, target, current=None, index=None, server_names=None):
    """回档前置闸门（方案 §5.5.2 / §5.5.3）。

    target：相对 mapDir 的文件名，或绝对路径（own:pre_restore / 历史档）。
    current：可选，调用方在 saveworld 后自行取（否则内部取）。
    index：可选，调用方预先构建的 pid 反向索引。
    返回对齐 §6.3 契约。
    """
    t0 = time.time()
    md, _how_md = detect_map_dir(abbr)
    if not md:
        return {'ok': False, 'code': 'mapdir_unknown', 'error': '无法判定地图目录'}
    rp = resolve_point(abbr, target)
    if not rp.get('ok'):
        return {'ok': False, 'code': rp.get('code') or 'target_missing',
                'error': rp.get('error') or '目标档无效'}
    target_abs = rp['abs']
    if not os.path.isfile(target_abs):
        return {'ok': False, 'code': 'target_missing', 'error': '目标档不存在: %s' % target_abs}

    cur = current or current_players(abbr)
    if not cur.get('ok'):
        return {'ok': False, 'code': cur.get('code') or 'current_failed',
                'error': cur.get('error') or '当前档角色获取失败'}

    tp = run_exe(target_abs, abbr)
    if not tp.get('ok'):
        return {'ok': False, 'code': tp.get('code') or 'target_parse_failed',
                'error': tp.get('error') or '目标档解析失败'}

    C = cur['players']
    T = tp['players']
    cur_tribe = cur.get('pid2tribe') or {}
    tgt_tribe = tp.get('pid2tribe') or {}

    safe_ids = sorted(set(C.keys()) & set(T.keys()))
    loss_ids = sorted(set(C.keys()) - set(T.keys()))
    dup_ids = sorted(set(T.keys()) - set(C.keys()))

    # 仅当存在 🔴 时才去建全服索引（省时间）
    idx = None
    if dup_ids and index is None:
        idx = pid_index()
    elif index is not None:
        idx = index

    # v6045（用户口径）：玩家进出流水**无条件**读取。
    #   v6043 时被包在 `if loss_ids or dup_ids` 里 ⇒ 全绿档（loss/dup 皆 0）根本不读，
    #   用户实测 Val clear 档「角色进出风险」完全不显示。原理由不成立：进出是独立维度，
    #   与 pid 层面的 loss/dup 无因果。
    _pres = {}
    _pres_risk = {'ok': False}
    try:
        _pr = read_presence(abbr)
        if _pr.get('ok'):
            _pres = _pr['players']
            _pres_risk['ok'] = True
            _pres_risk['ppCount'] = _pr.get('count') or 0
            _pres_risk['ppPlayers'] = _pr.get('playerCount') or 0
    except Exception:
        _pres = {}

    # v6045：以**目标档时刻 T** 为界切窗口，列出「当前档 ↔ 目标档」之间进出过的角色。
    #   T 取自目标档文件名时间（UTC，calendar.timegm），与 PlayerProfile 的本地时间
    #   各自解析成 epoch 后比较 —— epoch 无时区，可直接比。
    try:
        if target_abs.lower().endswith('.arkrbf'):
            _tmeta = _parse_rbf_point(target_abs) or {}
        else:
            _tmeta = _parse_point(target_abs, None) or {}
        _t_tgt = int(_tmeta.get('tsEpoch') or 0)
    except Exception:
        _t_tgt = 0
    if _pres and _t_tgt:
        _tgt_eos = set()
        for _pi in T.values():
            _e = (_pi.get('eosId') or '').lower()
            if _e:
                _tgt_eos.add(_e)
        _moved, _newrole = [], []
        for _eos, _pp in _pres.items():
            _ev = [e for e in (_pp.get('events') or []) if int(e.get('ts') or 0) > _t_tgt]
            if not _ev:
                continue          # 该玩家在 T 之后没有任何进出记录 ⇒ 不受回档影响
            _has = _eos in _tgt_eos
            _first = int(_pp.get('firstConnect') or 0)
            # 判「新角色」必须**两个条件同时成立**：
            #   ① 首次进服晚于 T   ② 目标档里确实没有他的角色
            # 只看 ① 会在 PlayerProfile 被清理过时误判；加上 ② 后语义收敛为
            # 「回档后这个账号在本服没有角色」= 角色真的消失。
            _isnew = bool(_first and _first > _t_tgt and not _has)
            _row = {
                'eosId': _eos,
                'name': _pp.get('name') or '',
                'firstConnect': _first,
                'lastConnect': int(_pp.get('lastConnect') or 0),
                'lastDisconnect': int(_pp.get('lastDisconnect') or 0),
                'hasRoleInTarget': _has,
                'newRole': _isnew,
                'winConnect': len([e for e in _ev if e.get('kind') == 'connect']),
                'winDisconnect': len([e for e in _ev if e.get('kind') == 'disconnect']),
                'events': [{'kind': e.get('kind'), 'ts': int(e.get('ts') or 0)} for e in _ev[-8:]],
            }
            _moved.append(_row)
            if _isnew:
                _newrole.append(_row)
        _moved.sort(key=lambda x: -x['lastConnect'])
        _pres_risk.update({
            'tTarget': _t_tgt,
            'tTargetStr': datetime.fromtimestamp(_t_tgt).strftime('%Y-%m-%d %H:%M:%S'),
            'windowToStr': datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'),
            'moved': _moved,
            'newRole': _newrole,
            'count': len(_moved),
            'newRoleCount': len(_newrole),
        })

    cr = cur.get('cryo') or {}
    pods = cr.get('cryopod') or []
    structs = cr.get('structures') or []
    pid2tid = cur.get('pid2tid') or {}

    def _pod_count(pid):
        n = 0
        for p in pods:
            if not isinstance(p, dict):
                continue
            try:
                if int(p.get('containerOwnerPid') or 0) != pid:
                    continue
            except Exception:
                continue
            if (p.get('name') or '') == '空球' or not (p.get('dinoClass') or ''):
                continue
            n += 1
        return n

    def _struct_count(pid):
        tid = pid2tid.get(pid)
        if not tid:
            return 0
        n = 0
        for s in structs:
            if isinstance(s, dict) and s.get('tribeId') == tid:
                n += 1
        return n

    def _who(pid, src):
        i = src.get(pid) or {}
        return {'pid': pid,
                'eosId': i.get('eosId') or '',
                'characterName': i.get('characterName') or '',
                'accountName': i.get('name') or ''}

    safe, loss, dup = [], [], []
    for pid in safe_ids:
        d = _who(pid, C)
        d['tribeName'] = cur_tribe.get(pid, '')
        safe.append(d)
    for pid in loss_ids:
        d = _who(pid, C)
        d['tribeName'] = cur_tribe.get(pid, '')
        d['cryoDinoCount'] = _pod_count(pid)
        d['structuresByTribe'] = _struct_count(pid)
        d['presence'] = _pres.get((d.get('eosId') or '').lower())
        loss.append(d)
    for pid in dup_ids:
        d = _who(pid, T)
        d['tribeName'] = tgt_tribe.get(pid, '')
        now_at = (idx or {}).get('index', {}).get(pid) or []
        d['nowAt'] = [s for s in now_at if s != abbr]
        d['presence'] = _pres.get((d.get('eosId') or '').lower())
        dup.append(d)

    # v6045（用户口径 A）：回档点之后才创建的角色会**整个消失**（不是掉物品，是人物没了）
    #   ⇒ 与物品丢失同级，判 block。
    _nr = int(_pres_risk.get('newRoleCount') or 0)
    _mv = int(_pres_risk.get('count') or 0)

    # v6055（用户口径「同时风险要考虑在线用户」）：此刻在线的玩家会被回档直接踢下线，
    #   进度也退回目标档时刻 ⇒ 与物品丢失同级，计入 block。
    #   快照读不到（no_snapshot / rcon_failed）时**不升级** verdict —— 否则服务器离线时
    #   永远无法回档；前端据 onlineRisk.ok=False 自行显示「未知」。
    try:
        _on = read_online(abbr)
    except Exception:
        _on = {'ok': False, 'reason': 'read_failed', 'count': 0, 'players': []}
    _on_n = int(_on.get('count') or 0)

    verdict = 'clear' if (not loss and not dup and not _nr and not _on_n) else 'block'
    bits = []
    if _on_n:
        bits.append('%d 名玩家当前在线（回档会将其踢下线，进度退回目标档时刻）' % _on_n)
    if loss:
        bits.append('%d 名角色物品将丢失（背包/装备清空）' % len(loss))
    if dup:
        bits.append('%d 名角色将出现重复（回档后请勿立即跨服）' % len(dup))
    if _nr:
        bits.append('%d 名角色在回档点后才创建（回档后将消失）' % _nr)
    if not bits:
        if _mv:
            bits.append('%d 名角色在回档点后进出过（进度将回退到目标档时刻）' % _mv)
        else:
            bits.append('全部 %d 名角色安全' % len(safe))

    return {
        'ok': True,
        'server': abbr,
        'mapDir': md,
        'target': os.path.basename(target_abs),
        'targetPath': target_abs,
        'verdict': verdict,
        'currentSource': cur.get('source'),
        'reparsed': bool(cur.get('reparsed')),
        'cryoAgeSec': cur.get('ageSec'),
        'targetPlayerCount': len(T),
        'currentPlayerCount': len(C),
        'safe': safe, 'loss': loss, 'dup': dup,
        'presenceRisk': _pres_risk,
        'onlineRisk': _on,
        'notice': '；'.join(bits),
        'elapsedMs': int((time.time() - t0) * 1000),
    }


def swap_ark(abbr, source_abs, mapdir=None, dry_run=False):
    """把 source_abs 换成本服当前档（方案 §5 的 F5）。

    顺序：先 `os.replace` 备份现有当前档为 `<当前档>_pre_swap.ark`，再把 source 复制到当前档名。
    dry_run=True ⇒ 只校验与演算，**不动任何文件**。
    返回 {ok, dryRun, active, source, steps[], elapsedMs}
    """
    t0 = time.time()
    md = mapdir or detect_map_dir(abbr)[0]
    if not md:
        return {'ok': False, 'code': 'mapdir_unknown', 'error': '无法判定地图目录'}
    d = os.path.join(ARK_ROOT, abbr, 'ShooterGame', 'Saved', 'SavedArks', md)
    if not os.path.isdir(d):
        return {'ok': False, 'code': 'mapdir_missing', 'error': '地图目录不存在: %s' % d}
    active = _active_name(abbr, md)
    if not active:
        return {'ok': False, 'code': 'no_active', 'error': '未找到当前档'}
    active_abs = os.path.join(d, active)
    if not os.path.isfile(source_abs):
        return {'ok': False, 'code': 'source_missing', 'error': '源档不存在: %s' % source_abs}
    if os.path.normcase(os.path.abspath(source_abs)) == os.path.normcase(os.path.abspath(active_abs)):
        return {'ok': False, 'code': 'same_file', 'error': '源档与当前档是同一个文件'}

    src_sz = os.path.getsize(source_abs)
    steps = []
    try:
        du = shutil.disk_usage(d)
        if du.free < src_sz * 1.2:
            return {'ok': False, 'code': 'disk_low',
                    'error': '磁盘不足：需 %.0f MB，剩余 %.0f MB' % (src_sz * 1.2 / 1048576, du.free / 1048576)}
    except Exception:
        pass

    if dry_run:
        return {'ok': True, 'dryRun': True,
                'active': active_abs, 'source': source_abs, 'mapDir': md,
                'sourceMB': round(src_sz / 1048576.0, 2),
                'steps': ['[dry-run] 停服 → 备份当前档 → 复制源档 → 校验 → 启动'],
                'elapsedMs': int((time.time() - t0) * 1000)}

    tmp = active_abs + '.restoring.tmp'
    try:
        shutil.copyfile(source_abs, tmp)
        steps.append('copy->tmp')
        if os.path.getsize(tmp) != src_sz:
            raise IOError('副本大小不一致')
        prev = active_abs + '.pre_swap.ark'
        try:
            if os.path.isfile(prev):
                os.remove(prev)
        except Exception:
            pass
        os.replace(active_abs, prev)
        steps.append('active->pre_swap')
        os.replace(tmp, active_abs)
        steps.append('tmp->active')
    except Exception as e:
        for p in (tmp,):
            try:
                if os.path.isfile(p):
                    os.remove(p)
            except Exception:
                pass
        return {'ok': False, 'code': 'swap_error', 'error': '%s: %s' % (type(e).__name__, e),
                'steps': steps}
    return {'ok': True, 'dryRun': False, 'active': active_abs, 'source': source_abs,
            'mapDir': md, 'sourceMB': round(src_sz / 1048576.0, 2),
            'prevBackup': active_abs + '.pre_swap.ark',
            'steps': steps, 'elapsedMs': int((time.time() - t0) * 1000)}


def restore_pre(abbr, expect_job=None, force=False, dry_run=False, max_age_hours=48):
    """从 `arkbackup\\<服>\\pre_restore.ark` 还原（方案 §6.7）。

    校验：① 元数据存在 ② jobId 匹配（除非 force）③ sha256/大小一致 ④ ts < 48h（除非 force）
    """
    meta = read_backup_meta(abbr)
    if not meta:
        return {'ok': False, 'code': 'no_backup', 'error': '没有可还原的备份'}
    src = meta.get('file')
    if not src:
        src = os.path.join(BACKUP_ROOT, abbr, 'pre_restore.ark')
    if not os.path.isfile(src):
        return {'ok': False, 'code': 'backup_missing', 'error': '备份文件不存在: %s' % src}

    if expect_job and meta.get('jobId') and expect_job != meta.get('jobId') and not force:
        return {'ok': False, 'code': 'job_mismatch',
                'error': '备份已被更新的回档覆盖（当前 jobId=%s，期望 %s）' % (meta.get('jobId'), expect_job)}

    age_h = (time.time() - float(meta.get('tsEpoch') or 0)) / 3600.0
    if age_h > max_age_hours and not force:
        return {'ok': False, 'code': 'stale',
                'error': '备份已 %.1f 小时（超过 %d 小时），需 force:true' % (age_h, max_age_hours)}

    sz = os.path.getsize(src)
    if meta.get('sizeBytes') and sz != meta['sizeBytes']:
        return {'ok': False, 'code': 'size_mismatch',
                'error': '备份大小 %d 与记录 %d 不一致' % (sz, meta['sizeBytes'])}

    if meta.get('sha256') and not dry_run:
        h = _sha256_file(src)
        if h != meta['sha256']:
            return {'ok': False, 'code': 'sha_mismatch',
                    'error': '备份 sha256 与记录不一致（可能被截断）'}

    r = swap_ark(abbr, src, dry_run=dry_run)
    if r.get('ok'):
        r['restoredFrom'] = src
        r['backupMeta'] = meta
        r['ageHours'] = round(age_h, 2)
    return r


# ---------------- 本地自测 ----------------
if __name__ == '__main__':
    import sys
    os.makedirs(BACKUP_ROOT, exist_ok=True)
    for ab in ['Isl', 'Sco', 'Cen', 'Bob', 'Gen']:
        info = map_dir_info(ab)
        print('%-4s mapDir=%-20s by=%-8s' % (info['server'], info['mapDir'] or '(失败)', info['detectedBy']))
    for ab in ['Cen', 'Isl']:
        r = list_points(ab)
        print('\n=== %s  list ===' % ab)
        print('ok=%s mapDir=%s by=%s count=%d elapsedMs=%s' %
              (r.get('ok'), r.get('mapDir'), r.get('detectedBy'), r.get('count', 0), r.get('elapsedMs')))
        act = r.get('activeFile') or {}
        print('  当前档: %s  %s MB  %s' % (act.get('name'), act.get('mb'), act.get('ts')))
        for p in (r.get('points') or [])[:5]:
            print('   - %-40s %6.1f MB  %s  %s' % (p['name'], p['mb'], p['ts'], p['kind']))
