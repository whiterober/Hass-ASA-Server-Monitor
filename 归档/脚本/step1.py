
with open(r"B:\项目\Hass ASA Server Monitor\wwwsa-admin.html", "rb") as f:
    c = f.read()

Q = bytes([34])
N = bytes([13, 10])
changes = 0

# 1. CSS
pos = c.find(b".cat-col-bq .cat-bq-seg.active")
css = N.join([
    b".cat-color-dot { width:8px;height:8px;border-radius:50%;flex-shrink:0;cursor:pointer;margin-right:1px; }",
    b".cat-color-popup { display:none;position:fixed;background:var(--card);border:1px solid var(--border);border-radius:6px;padding:4px 6px;z-index:99999;box-shadow:0 4px 16px rgba(0,0,0,0.45);gap:4px;align-items:center; }",
    b".cat-color-popup.show { display:flex; }",
    b".cat-color-opt { width:16px;height:16px;border-radius:50%;cursor:pointer;flex-shrink:0;border:2px solid transparent;transition:border-color .15s; }",
    b".cat-color-opt:hover { border-color:var(--text); }",
    b".cat-color-opt.active { border-color:var(--accent);box-shadow:0 0 0 1px var(--accent); }",
    b""
]) + N
c = c[:pos] + css + c[pos:]
print("1. CSS")
changes += 1

# Save
with open(r"B:\项目\Hass ASA Server Monitor\wwwsa-admin.html", "wb") as f:
    f.write(c)
print("Saved step 1")
