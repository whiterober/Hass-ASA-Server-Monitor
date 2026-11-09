# -*- coding: utf-8 -*-
"""
_deply_cf.py — dino-import 前端固定部署脚本（CF Workers Assets）
============================================================
流程：1) 打包 tmp/dino-flat（调 _sync_repack2.py） 2) wrangler deploy 3) 线上验证
用法：python tmp/_deploy_cf.py
前置：wrangler 已登录（wrangler.cmd whoami 确认 whiter.rober@gmail.com）
"""
import io, os, re, subprocess, sys, json, urllib.request

BASE = r'b:\项目\Hass ASA Server Monitor'
OUT = r'C:\Users\white\AppData\Roaming\Code\User\workspaceStorage\_deploy_cf_out.txt'
lines = []

def log(s):
    lines.append(s)
    print(s)

def run(cmd, cwd=None, timeout=180):
    """运行命令并返回 (rc, stdout)"""
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    r = subprocess.run(cmd, capture_output=True, cwd=cwd or BASE, env=env, timeout=timeout)
    out = (r.stdout or b'').decode('utf-8', 'replace')
    err = (r.stderr or b'').decode('utf-8', 'replace')
    return r.returncode, out, err

# ---- 0. 同步 pwa/sw.js 的 VER 到当前 LB_VERSION（P0-2 防复发）----
# 2026-11-05：复核报告的 P0-2 就是「sw.js VER 未随前端同步」，修好后又回退了 8 个版本。
#   SW 的 SHELL 缓存名 = 'dino-import-shell-' + VER ⇒ VER 落后则壳永不换新。
#   此步骤在打包**之前**执行，保证 _sync_repack2.py 复制进 dino-flat 的那份已同步。
log('== 0/3 同步 sw.js VER ==')
def _sync_sw_ver():
    _hp = os.path.join(BASE, 'dino-import.html')
    _sp = os.path.join(BASE, 'pwa', 'sw.js')
    try:
        _h = io.open(_hp, encoding='utf-8').read()
        _s = io.open(_sp, encoding='utf-8').read()
    except Exception as e:
        return 'WARN: 读取失败，跳过 VER 同步（%s）' % e
    _mh = re.search(r"var LB_VERSION = '(v[0-9]+-[0-9]+)'", _h)
    _ms = re.search(r"var VER = '(v[0-9]+-[0-9]+)'", _s)
    if not _mh:
        return 'WARN: dino-import.html 未找到 LB_VERSION，跳过'
    if not _ms:
        return 'WARN: sw.js 未找到 var VER，跳过'
    _ver, _old = _mh.group(1), _ms.group(1)
    if _old == _ver:
        return 'VER 已同步 = %s（无需改动）' % _ver
    _s2 = _s.replace("var VER = '%s'" % _old, "var VER = '%s'" % _ver, 1)
    io.open(_sp, 'w', encoding='utf-8', newline='').write(_s2)
    _v = io.open(_sp, encoding='utf-8').read()
    _ok = ("var VER = '%s'" % _ver) in _v
    return 'VER %s -> %s（读回校验 %s）' % (_old, _ver, 'OK' if _ok else 'FAIL')
log('  ' + _sync_sw_ver())

# ---- 0.5 版本递增卡口（v6113）----
# 背景：_headers 给 app.css / app_data.js / app_core.min.js / app_ui.min.js 设了 immutable（一年），
#   换文件只能靠 URL 里的 ?v=LB_VERSION 变。若忘记递增版本号 ⇒ 新旧 URL 相同 ⇒ 用户永远拿旧文件，
#   部署日志却照样"成功"，修复永远到不了老用户。此步骤在打包**之前**拦截。
log('== 0.5 卡口 版本递增 ==')
def _local_version():
    try:
        _h = io.open(os.path.join(BASE, 'dino-import.html'), encoding='utf-8').read()
        _m = re.search(r"var LB_VERSION = '([^']+)'", _h)
        return _m.group(1) if _m else None
    except Exception:
        return None

def _online_version():
    try:
        _req = urllib.request.Request(
            'https://dino.whiterober.ccwu.cc/?cb=' + str(int(__import__('time').time() * 1000)),
            headers={'User-Agent': 'Mozilla/5.0'})
        _html = urllib.request.urlopen(_req, timeout=20).read().decode('utf-8', 'replace')
        _m = re.search(r"var LB_VERSION = '([^']+)'", _html)
        return _m.group(1) if _m else None
    except Exception:
        return None

_local_ver = _local_version()
_online_ver = _online_version()
if os.environ.get('DINO_ALLOW_SAME_VER') == '1':
    log('  WARN: DINO_ALLOW_SAME_VER=1，跳过版本递增检查（线上 %s / 本地 %s）' % (_online_ver, _local_ver))
elif _online_ver is None:
    log('  WARN: 取不到线上版本，跳过递增检查（不中止）；本地 %s' % _local_ver)
elif _local_ver and _online_ver == _local_ver:
    log('  FAIL: 本地版本 == 线上版本（%s）—— 忘记递增会让 immutable 年缓存把旧文件钉住' % _local_ver)
    log('  已中止。确需同版本重发：设 DINO_ALLOW_SAME_VER=1 后重跑')
    io.open(OUT, 'w', encoding='utf-8').write('\n'.join(lines))
    sys.exit(1)
else:
    log('  线上 %s -> 本地 %s OK' % (_online_ver, _local_ver))

# ---- 1. 打包 ----
log('== 1/3 打包 ==')
rc, out, err = run([sys.executable, os.path.join(BASE, 'tmp', '_sync_repack2.py')])
log('repack rc=%d' % rc)
for ln in (out + err).splitlines():
    if ln.strip():
        log('  ' + ln.strip())
if rc != 0:
    log('打包失败，中止')
    io.open(OUT, 'w', encoding='utf-8').write('\n'.join(lines))
    sys.exit(1)

# ---- 1.5 sw.js 语法卡口 ----
# 2026-11-05：sw.js 曾因编码损坏吞掉代码行，带语法错误静默上线两周
#   （浏览器不报错、旧 SW 继续跑，表现为「版本冻结」）。此处做最低门槛拦截。
log('== 1.5 卡口 sw.js 语法 ==')
import shutil as _shutil
_flat_sw = os.path.join(BASE, 'tmp', 'dino-flat', 'sw.js')
_node = _shutil.which('node')
if not _node:
    log('  WARN: 未找到 node，跳过 sw.js 语法校验（不中止）')
elif not os.path.isfile(_flat_sw):
    log('  FAIL: 缺少 tmp/dino-flat/sw.js，中止部署')
    io.open(OUT, 'w', encoding='utf-8').write('\n'.join(lines))
    sys.exit(1)
else:
    _nrc, _nout, _nerr = run([_node, '--check', _flat_sw], timeout=60)
    if _nrc != 0:
        log('  node --check rc=%d' % _nrc)
        for _ln in (_nout + _nerr).splitlines()[:12]:
            if _ln.strip():
                log('    ' + _ln.strip())
        log('  sw.js 语法错误，中止部署')
        io.open(OUT, 'w', encoding='utf-8').write('\n'.join(lines))
        sys.exit(1)
    log('  node --check rc=0 OK')

# ---- 2. wrangler 部署 ----
log('== 2/3 wrangler deploy ==')
rc, out, err = run(['wrangler.cmd', 'deploy', '--config', 'tmp/wrangler.dino.toml'], timeout=300)
for ln in (out + err).splitlines():
    if ln.strip():
        log('  ' + ln.strip())
if rc != 0:
    log('部署失败 rc=%d' % rc)
    io.open(OUT, 'w', encoding='utf-8').write('\n'.join(lines))
    sys.exit(1)

# ---- 2.5 CF 边缘缓存精准清理（v6468，用户实报「为啥页面没弹更新浮窗」）----
# 根因：Cloudflare 静态资源边缘缓存**忽略 query string**，
#   `dino-import.version?t=<时间戳>` 与 fetch 的 cache:'no-store' 都拦不住边缘副本；
#   边缘副本会滞留旧版本号 ⇒ lbCheckVersion() 的 v !== LB_VERSION 永不成立 ⇒ 更新浮窗永不出现。
#   同时首页 index.html（600s）也会滞留旧壳，让"版本一致"验证误报 False。
# 做法：部署成功后用 CF API 精准 purge 这三个 URL（不整站 purge）。
# 凭据：tmp/_cf_purge.json（token 只有 Cache Purge: Purge 权限，仅限本 zone）。
# 失败**不中止**部署，只 WARN —— 避免 token 过期卡死发版。
log('== 2.5/3 CF 缓存清理 ==')
_cfp = os.path.join(BASE, 'tmp', '_cf_purge.py')
if not os.path.isfile(_cfp):
    log('  WARN: 缺少 tmp/_cf_purge.py，跳过（更新浮窗可能不弹）')
else:
    _prc, _pout, _perr = run([sys.executable, _cfp], timeout=120)
    for _ln in (_pout + _perr).splitlines():
        if _ln.strip():
            log('  ' + _ln.strip())
    if _prc != 0:
        log('  WARN: purge 失败 rc=%d（不中止部署，但版本自检可能滞留旧值）' % _prc)

# ---- 3. 线上验证 ----
log('== 3/3 线上验证 ==')
try:
    req = urllib.request.Request('https://dino.whiterober.ccwu.cc/?cb=' + str(int(__import__('time').time()*1000)),
                                 headers={'User-Agent': 'Mozilla/5.0'})
    r = urllib.request.urlopen(req, timeout=30)
    html = r.read().decode('utf-8', 'replace')
    log('线上 HTTP %d, 大小 %dB' % (r.status, len(html)))
    ver = None
    import re
    m = re.search(r"var LB_VERSION = '([^']+)'", html)
    if m:
        ver = m.group(1)
        log('线上 LB_VERSION = %s' % ver)
    # 对比本地版本
    local_html = io.open(os.path.join(BASE, 'dino-import.html'), encoding='utf-8').read()
    m2 = re.search(r"var LB_VERSION = '([^']+)'", local_html)
    log('本地 LB_VERSION = %s' % (m2.group(1) if m2 else '?'))
    log('版本一致: %s' % (ver == (m2.group(1) if m2 else None)))
    # v6113：外链资源 ?v= 必须全部等于本地版本
    #   这三条资源带 immutable 年缓存，URL 没带上新版本 = 用户永远读旧文件
    _lv = m2.group(1) if m2 else None
    _bad_q = []
    if _lv:
        for _a in ('/app.css', '/app_data.js', '/app_core.min.js'):
            if (_a + '?v=' + _lv) not in html:
                _bad_q.append(_a)
    log('外链 ?v= 校对: %s%s' % ('全部匹配' if not _bad_q else '不匹配 -> ' + ','.join(_bad_q),
                                 '' if not _bad_q else '（会影响缓存失效，请检查打包步骤）'))
    if _bad_q:
        log('WARN: 外链 ?v= 未全部对齐（不中止，但请立即核查）')
    # 版本自检文件
    try:
        r2 = urllib.request.urlopen('https://dino.whiterober.ccwu.cc/dino-import.version', timeout=20)
        log('dino-import.version = %s' % r2.read().decode('utf-8','replace').strip())
    except Exception as e:
        log('version 文件读取失败: %r' % e)
except Exception as e:
    log('验证失败: %r' % e)

io.open(OUT, 'w', encoding='utf-8').write('\n'.join(lines))
log('DONE')
