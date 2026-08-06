#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASA 最新生物 - 刷新代理服务
用途：前端调用触发多服 tamed 刷新（RCON ArkTamedDinos）+ 轮询确认 tamed.json 已更新。
部署：NAS Docker（QNAP Container Station），由 QNAP 反向代理把 /api 转发到本服务。

接口：
  GET  /healthz                      健康检查
  POST /api/refresh-tamed?server=Sco 触发刷新 + 轮询确认（串行，一次一台）

环境变量：
  RCON_HOST      ARK 服务器地址（默认 work.whiterober.cn）
  RCON_PASSWORD  RCON 密码（仅容器内）
  DINO_DATA      数据目录（容器内 /data，卷挂载 NAS DinoData）
  PORT           监听端口（默认 8080）
  RCON_TIMEOUT   RCON 超时秒（默认 10）
  POLL_TIMEOUT   轮询确认超时秒（默认 30）

仅依赖 Python 标准库，无需 pip install。
"""
import json
import os
import socket
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

RCON_HOST = os.environ.get('RCON_HOST', 'work.whiterober.cn')
RCON_PASSWORD = os.environ.get('RCON_PASSWORD', '')
DINO_DATA = os.environ.get('DINO_DATA', '/data')
PORT = int(os.environ.get('PORT', '8080'))
RCON_TIMEOUT = int(os.environ.get('RCON_TIMEOUT', '10'))
POLL_TIMEOUT = int(os.environ.get('POLL_TIMEOUT', '30'))

# 服务器 RCON 端口表（与接口文档 §1.1 对齐）
SERVERS = {
    'Isl': 32320, 'Sco': 32321, 'Cen': 32322, 'Abe': 32323, 'Ext': 32324,
    'Ast': 32325, 'Rag': 32326, 'Val': 32327, 'Los': 32328, 'Gen': 32329,
}

CMD_ARK_TAMED = 'TransferIdentityFix.ArkTamedDinos'


def rcon_command(host, port, password, command, timeout=RCON_TIMEOUT):
    """标准 Source RCON：认证(Type=3) + 命令(Type=2) + 收响应。返回原始字节。"""
    s = socket.create_connection((host, port), timeout=timeout)
    try:
        # 1. 认证
        payload = struct.pack('<ii', 1, 3) + password.encode('utf-8') + b'\x00\x00'
        s.sendall(payload)
        s.recv(4096)
        # 2. 发命令
        payload2 = struct.pack('<ii', 2, 2) + command.encode('utf-8') + b'\x00\x00'
        s.sendall(payload2)
        s.settimeout(timeout)
        data = b''
        while True:
            try:
                chunk = s.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            data += chunk
            if len(data) > 1 << 20:  # 1MB 上限，防异常
                break
        return data
    finally:
        s.close()


def extract_json(data):
    """从 RCON 原始响应中提取最后一个 JSON 对象。"""
    if not data:
        return None
    text = data.decode('utf-8', errors='ignore')
    idx = text.rfind('{')
    if idx < 0:
        return None
    try:
        return json.loads(text[idx:])
    except Exception:
        return None


def read_saved_marker(server):
    """读取 tamed.json 的更新标记：优先 savedAt 字段，否则文件 mtime。"""
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


def poll_until_updated(server, old_marker, timeout=POLL_TIMEOUT):
    """轮询 tamed.json，直到更新标记变化或超时。返回 (updated:bool, new_marker)。"""
    kind, old_val = old_marker
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(1.0)
        new_marker = read_saved_marker(server)
        if new_marker != old_marker:
            return True, new_marker
    return False, old_marker


def refresh_tamed(server):
    """触发一台服务器 tamed 刷新并确认更新。返回结果 dict。"""
    port = SERVERS.get(server)
    if not port:
        return {'ok': False, 'error': 'unknown server: ' + server}

    old_marker = read_saved_marker(server)

    # RCON 触发
    try:
        raw = rcon_command(RCON_HOST, port, RCON_PASSWORD, CMD_ARK_TAMED)
    except Exception as e:
        return {'ok': False, 'server': server, 'error': 'rcon: ' + str(e)}

    resp = extract_json(raw) or {}
    ok = bool(resp.get('ok'))

    # 冷却处理：等待冷却后重试一次
    if ok and resp.get('cooldown'):
        time.sleep(20.0)
        try:
            raw2 = rcon_command(RCON_HOST, port, RCON_PASSWORD, CMD_ARK_TAMED)
            resp2 = extract_json(raw2) or {}
            if resp2.get('ok') and not resp2.get('cooldown'):
                ok = True
                resp = resp2
            elif resp2.get('cooldown'):
                return {'ok': False, 'server': server, 'cooldown': True, 'error': 'still cooldown after retry'}
        except Exception as e:
            return {'ok': False, 'server': server, 'error': 'rcon retry: ' + str(e)}

    if not ok:
        return {'ok': False, 'server': server, 'error': resp.get('error') or 'trigger failed'}

    # 轮询确认 tamed.json 已更新
    updated, new_marker = poll_until_updated(server, old_marker)
    result = {'ok': updated, 'server': server, 'triggered': True, 'updated': updated,
              'savedAt': new_marker[1] if new_marker[0] == 'savedAt' else None}
    if not updated:
        result['error'] = 'tamed.json not updated within {}s'.format(POLL_TIMEOUT)
    return result


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # 静默日志

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/healthz':
            self._send(200, {'ok': True, 'service': 'asa-refresh-proxy', 'servers': sorted(SERVERS.keys())})
        else:
            self._send(404, {'ok': False, 'error': 'not found'})

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != '/api/refresh-tamed':
            self._send(404, {'ok': False, 'error': 'not found'})
            return
        qs = parse_qs(parsed.query)
        server = (qs.get('server') or [''])[0].strip()
        if not server:
            self._send(400, {'ok': False, 'error': 'missing server'})
            return
        result = refresh_tamed(server)
        self._send(200, result)


def main():
    # 非容器环境（本地测试）无密码时给出提示
    if not RCON_PASSWORD:
        print('[warn] RCON_PASSWORD 未设置（仅容器/生产需要）')
    if not os.path.isdir(DINO_DATA):
        print('[warn] DINO_DATA 目录不存在: ' + DINO_DATA)
    srv = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    print('asa-refresh-proxy listening on :{}  (dino_data={})'.format(PORT, DINO_DATA))
    srv.serve_forever()


if __name__ == '__main__':
    main()
