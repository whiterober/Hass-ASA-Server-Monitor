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
import re
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
VOLCANO_FILE = os.path.join(os.path.dirname(ACCOUNTS_FILE), 'volcano_anchor.json')  # v1096：火山喷发锚点（已弃用，保留兼容；v1107 改用插件权威查询）
VOLCANO_ERUPT_FILE = os.path.join(os.path.dirname(ACCOUNTS_FILE), 'volcano_erupt_anchor.json')  # v1138：共享「真喷发锚点」——任何客户端捕获 phase→eruption 后上报，落盘持久化（跨客户端/换设备/后端重启均不丢）
VOLCANO_SERVERS = {'Gen'}  # 阶段一：仅创世有火山计时
VOLC_STATE_TTL_MS = 3000   # 2026-09-14：火山状态内存缓存 TTL——后端单点轮询 ⇒ N 个客户端也只 3s 一次 RCON（插件文档 §4 强约束）
VOLC_LOG_TTL_MS = 2000     # v1146（用户定稿）：火山**事件台账**独立缓存槽——仅当 hooks.events 变化 / 30s 兜底时才被前端请求
_VOLC_STATE_CACHE = {}     # server -> {'ts': epoch_ms, 'data': {...}}
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
        raw = rcon_command(RCON_HOST, port, RCON_PASSWORD, CMD_SAVE_WORLD, timeout=30)
    except Exception as e:
        r = {'ok': False, 'server': server, 'error': 'rcon: ' + str(e), 'ts': now}
        write_status_file('save_world_status.json', 'error', r)
        write_status_file('save_world_status_%s.json' % server, 'error', r)
        mem_status('sensor.save_world_status', 'error', r)
        return r
    text = (raw or b'').decode('utf-8', errors='ignore').strip(' \x00\r\n\t')
    ok = bool(raw)
    r = {'ok': ok, 'server': server, 'saved': ok, 'reply': text[:80], 'ts': now}
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
    print('dino_backend listening on :{}'.format(PORT))
    print('  RCON_HOST={}  DINO_DATA={}'.format(RCON_HOST, DINO_DATA))
    print('  ASA_DATA={}  ALLOW_ORIGIN={}'.format(ASA_DATA, ALLOW_ORIGIN))
    srv = _GuardedServer(('0.0.0.0', PORT), Handler)
    try:
        srv.serve_forever()
    except Exception as e:  # v988：异常兑底（留日志后交由 watchdog 重启）
        print('[main] serve_forever exited: {}'.format(e))
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
