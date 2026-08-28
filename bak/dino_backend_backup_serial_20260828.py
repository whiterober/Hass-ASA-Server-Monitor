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
import socket
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# ================= 配置 =================
DINO_DATA = os.environ.get('DINO_DATA', r'D:\ARK Server\DinoData')
ASA_DATA = os.environ.get('ASA_DATA', os.path.join(DINO_DATA, 'asa-data'))
# 2026-08-28 修复：硬编码 RCON 目标为物理服务器内网 IP（游戏服 MultiHomeIp 绑定地址，实测返回真实 JSON）。
# 不用 os.environ 读取——服务器残留系统环境变量 RCON_HOST=127.0.0.1 会覆盖默认值导致连到错误服务（返回 Keep Alive）。
RCON_HOST = '192.168.199.3'
RCON_PASSWORD = os.environ.get('RCON_PASSWORD', '1219wu1219')
PORT = int(os.environ.get('PORT', '8080'))
RCON_TIMEOUT = int(os.environ.get('RCON_TIMEOUT', '15'))
ALLOW_ORIGIN = os.environ.get('ALLOW_ORIGIN', 'https://dino.whiterober.ccwu.cc')
ACCOUNTS_FILE = os.environ.get('ACCOUNTS_FILE', r'D:\dino_backend\accounts.json')
# R2 / WebP 全自动更新配置（cf_config.json：api_token/account_id/r2_bucket/r2_endpoint/r2_s3_access_key/r2_s3_secret_key）
CF_CONFIG_FILE = os.environ.get('CF_CONFIG_FILE', os.path.join(os.path.dirname(ACCOUNTS_FILE), 'cf_config.json'))
WEBP_MAP_FILE = os.path.join(os.path.dirname(ACCOUNTS_FILE), 'webp_map.json')
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
    'Ast': {'name': '繁星', 'icon': 'mdi:star-four-points', 'emoji': '✨', 'primary_color': '#3F51B5',
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
    'Gen': {'name': '创世模拟', 'icon': 'mdi:dna', 'emoji': '🧬', 'primary_color': '#009688',
            'light_color': '#80CBC4', 'dark_color': '#00796B',
            'bg_image': "url('https://img.whiterober.ccwu.cc/ASA/misc/Gen_compressed.jpg')",
            'overlay_color': 'rgba(0, 150, 136, 0.7)'},
}

# RCON 命令
CMD_TAMED = 'TransferIdentityFix.ArkTamedDinos'
CMD_WILD = 'TransferIdentityFix.WildDinos'
CMD_TRACK = 'TransferIdentityFix.TrackDino'
CMD_STOP_TRACK = 'TransferIdentityFix.StopTrackDino'
CMD_PLAYER_POS = 'TransferIdentityFix.PlayerPos'
CMD_GET_DINO = 'TransferIdentityFix.ArkGetDino'

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


# 写 accounts.json（线程锁 + .bak 备份 + 原子替换；写后刷新内存缓存）
_ACCOUNTS_LOCK = threading.Lock()


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
    """对齐旧架构 receive_packets：阻塞 recv(4096) 循环直到收到不足 buffer_size 的块
    （服务器暂时无更多数据）或 socket 超时。返回原始字节流（可能包含多个 RCON 包/保活包）。"""
    s.settimeout(timeout)
    data = b""
    buf = 4096
    while True:
        try:
            part = s.recv(buf)
        except socket.timeout:
            break
        if not part:
            break
        data += part
        if len(part) < buf:
            break
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
_RCON_EXECUTOR = __import__('concurrent.futures', fromlist=['ThreadPoolExecutor']).ThreadPoolExecutor(max_workers=6)

def refresh_tamed(server):
    """触发一台服务器 tamed 刷新（RCON ArkTamedDinos）+ 轮询确认更新。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'error': 'unknown server: ' + server}
    try:
        raw = rcon_command(RCON_HOST, port, RCON_PASSWORD, CMD_TAMED)
    except Exception as e:
        return {'ok': False, 'server': server, 'error': 'rcon: ' + str(e)}
    resp = extract_json(raw) or {}
    ok = bool(resp.get('ok'))
    if ok and resp.get('cooldown'):
        time.sleep(20.0)
        try:
            raw2 = rcon_command(RCON_HOST, port, RCON_PASSWORD, CMD_TAMED)
            resp2 = extract_json(raw2) or {}
            if resp2.get('ok') and not resp2.get('cooldown'):
                ok = True
                resp = resp2
            elif resp2.get('cooldown'):
                r = {'ok': False, 'server': server, 'cooldown': True, 'error': 'still cooldown after retry', 'ts': str(datetime.now())}
                write_status_file('refresh_status.json', 'cooldown', r)
                return r
        except Exception as e:
            return {'ok': False, 'server': server, 'error': 'rcon retry: ' + str(e)}
    if not ok:
        r = {'ok': False, 'server': server, 'error': resp.get('error') or 'trigger failed', 'ts': str(datetime.now())}
        write_status_file('refresh_status.json', 'error', r)
        return r
    # 2026-08-28 提速：去掉 poll_until_updated 最长 30s 轮询（这是新架构 tamed 刷新比旧架构慢的主因）——
    # 对齐旧架构 AppDaemon：RCON 触发成功即立即写 status 返回，tamed.json 文件生成由前端 lbWaitTamed 轮询 savedAt 确认。
    # 2026-08-28 修复：必须写静态 refresh_status.json（前端 lbWaitStatusFile 轮询该文件，缺此文件会一直 404 等到 15s 超时 = 刷新显得慢）
    result = {'ok': True, 'server': server, 'triggered': True, 'updated': None,
              'ts': str(datetime.now())}
    write_status_file('refresh_status.json', 'ok', result)
    mem_status('sensor.refresh_tamed_status', 'ok', result)
    return result


def search_wild(server, species):
    """搜野生：RCON WildDinos <species> → 写 wild_status.json。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
    try:
        success, result = _rcon_str(port, CMD_WILD + ' ' + species)
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
    write_status_file('wild_status.json', 'ok' if ok else ('cooldown' if cooldown else 'error'), attrs)
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


def get_dino(server, dino1, dino2):
    """单龙实时查询：RCON ArkGetDino。返回 {found, tribeId}；tribeId>0 = 已驯服。"""
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
    if success and result:
        try:
            j = json.loads(result)
            ok = bool(j.get('ok'))
            found = j.get('found')
            tribe_id = j.get('tribeId') if 'tribeId' in j else j.get('tribe_id')
            err = j.get('error')
        except Exception:
            ok = True
    r = {'ok': ok, 'server': server, 'dino': '%s_%s' % (dino1, dino2),
         'found': found, 'tribeId': tribe_id, 'error': err,
         'result': str(result)[:200], 'ts': str(datetime.now())}
    mem_status('sensor.get_dino_status', 'ok' if ok else 'error', r)
    return r


def player_pos(server, player):
    """玩家位置：RCON PlayerPos。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'server': server, 'error': 'unknown server'}
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
    mem_status('sensor.player_pos_status', 'ok' if ok else 'error', r)
    return r


def _rcon_str(port, command):
    raw = rcon_command(RCON_HOST, port, RCON_PASSWORD, command)
    if not raw:
        return False, None
    text = raw.decode('utf-8', errors='ignore')
    idx = text.rfind('{')
    if idx >= 0:
        # 2026-08-28 修复：剥掉 RCON 包末尾 \x00\x00 控制字符，避免 json.loads 失败
        return True, text[idx:].rstrip('\x00\r\n\t ')
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

    def _send(self, code, obj, ctype='application/json; charset=utf-8'):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8') if ctype.startswith('application/json') else obj
        self.send_response(code)
        self._cors()
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
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
            self.wfile.write(data)
        except FileNotFoundError:
            self._send(404, {'ok': False, 'error': 'not found'})

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == '/healthz':
            self._send(200, {'ok': True, 'service': 'dino-backend', 'servers': sorted(SERVERS.keys())})
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
                import gzip
                try:
                    with gzip.open(full, 'rb') as f:
                        data = f.read()
                    self.send_response(200)
                    self._cors()
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Content-Length', str(len(data)))
                    self.send_header('Cache-Control', 'no-cache')
                    self.send_header('Last-Modified', self.date_time_string(os.path.getmtime(full)))
                    self.send_header('ETag', '"%x"' % (len(data) ^ int(os.path.getmtime(full))))
                    self.end_headers()
                    self.wfile.write(data)
                except Exception:
                    self._send(500, {'ok': False, 'error': 'gzip read failed'})
                return
            ctype = 'application/json; charset=utf-8' if full.endswith('.json') else 'application/gzip'
            self._send_file(full, ctype)
        else:
            self._send(404, {'ok': False, 'error': 'not found'})

    def do_POST(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        path = parsed.path
        # 解析 body（前端 script 调用用 JSON body：{server, species, player, dino1, dino2}）
        body = {}
        try:
            ln = int(self.headers.get('Content-Length') or 0)
            if ln > 0 and ln < 65536:
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
            self._send(200, {'ok': True, 'nick': nick})
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
        elif path.endswith('search_wild_dinos') or path.endswith('search_wild'):
            server = g('server')
            species = g('species')
            if not server or not species:
                self._send(400, {'ok': False, 'error': 'missing server/species'})
                return
            # 2026-08-28 异步化：后台线程执行 RCON（旧架构 AppDaemon 异步 1s 返回；此处立即返回触发成功，前端轮询 wild_status.json 等结果）
            _RCON_EXECUTOR.submit(search_wild, server, species)
            self._send(200, {'ok': True, 'server': server, 'species': species, 'triggered': True, 'async': True, 'ts': str(datetime.now())})
        elif path.endswith('track_dino'):
            server = g('server')
            player = g('player')
            d1 = g('dino1')
            d2 = g('dino2')
            if not (server and player and d1 and d2):
                self._send(400, {'ok': False, 'error': 'missing args'})
                return
            self._send(200, track_dino(server, player, d1, d2))
        elif path.endswith('stop_track_dino'):
            server = g('server')
            player = g('player')
            if not (server and player):
                self._send(400, {'ok': False, 'error': 'missing args'})
                return
            self._send(200, stop_track_dino(server, player))
        elif path.endswith('get_dino'):
            server = g('server')
            d1 = g('dino1')
            d2 = g('dino2')
            if not (server and d1 and d2):
                self._send(400, {'ok': False, 'error': 'missing args'})
                return
            self._send(200, get_dino(server, d1, d2))
        elif path.endswith('player_pos'):
            server = g('server')
            player = g('player')
            if not (server and player):
                self._send(400, {'ok': False, 'error': 'missing args'})
                return
            self._send(200, player_pos(server, player))
        else:
            self._send(404, {'ok': False, 'error': 'not found'})


def main():
    print('dino_backend listening on :{}'.format(PORT))
    print('  RCON_HOST={}  DINO_DATA={}'.format(RCON_HOST, DINO_DATA))
    print('  ASA_DATA={}  ALLOW_ORIGIN={}'.format(ASA_DATA, ALLOW_ORIGIN))
    srv = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    srv.serve_forever()


if __name__ == '__main__':
    main()
