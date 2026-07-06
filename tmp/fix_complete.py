import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Strategy: Make base_storage rendering in preview_server.py complete.
# Don't use body field for base_storage. Render everything from structured data.

sftp = c.open_sftp()
sftp.get('/config/preview_server.py', r'b:\项目\Hass ASA Server Monitor\tmp\ps_complete.py')
sftp.close()

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps_complete.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Change condition: base_storage NEVER uses body, always uses structured rendering
old_cond = "if b.get('body'):\n                        body_parts.append(b['body'])"
new_cond = "if bt != 'base_storage' and b.get('body'):\n                        body_parts.append(b['body'])"
content = content.replace(old_cond, new_cond)

# 2. Remove the broken inject code if present
content = content.replace(
    "                        # Inject images from structured data into body HTML\n                        if bt == 'base_storage' and b.get('rows'):\n                            rows = b['rows']\n                            import re as _re2\n                            wrappers = list(_re2.finditer(r'<div class=\"device-icon-wrapper[^\"]*\"></div>', body_html))\n                            for ri, row in enumerate(rows):\n                                img_url = (row.get('images',[{}])[0].get('image_url','') if row.get('images') else '')\n                                if img_url and ri < len(wrappers):\n                                    w = wrappers[ri]\n                                    img_tag = '<img src=\"'+img_url+'\" style=\"width:30px;height:30px;object-fit:contain\" />'\n                                    body_html = body_html[:w.start()] + w.group().replace('></div>','>'+img_tag+'</div>') + body_html[w.end():]",
    ""
)

# 3. Replace the base_storage row rendering to include all columns
# Find the exact row append line
old_row = "rows_html.append('<tr><td class=\"border border-gray-300 p-2 text-left align-top\"><div class=\"device-container\"><div class=\"materials-box\"><span class=\"bio-capacity-tag-bottom\">'+cap+'</span><div class=\"materials-box-inner\"><div class=\"device-icon-wrapper\">'+icon+'</div></div></div></div></td><td class=\"border border-gray-300 p-2 text-left align-top\" colspan=\"2\"></td></tr>')"

new_row = """rows_html.append('<tr><td class="border border-gray-300 p-2 text-left align-top"><div class="device-container"><div class="materials-box"><span class="bio-capacity-tag-bottom">'+cap+'</span><div class="materials-box-inner"><div class="device-icon-wrapper">'+icon+'</div></div></div></div></td><td class="border border-gray-300 p-2 text-left align-top" colspan="2">'+(''.join(['<blockquote class="quote" style="border-left-color:'+(c.get('marker_color','#ccc') if c.get('marker_color','#ccc')!='#ccc' else '#ff9800')+'!important"><div>'+('<span class="text-bold">'+c.get('label','')+'</span><br>' if c.get('label') else '')+'<br>'.join([i.get('name','') for i in c.get('items',[])])+'</div></blockquote>' for c in row.get('categories',[])]))+'</td></tr>')"""

count = content.count(old_row)
print(f"Found row line: {count}x")
if count > 0:
    content = content.replace(old_row, new_row)

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps_complete.py', 'w', encoding='utf-8') as f:
    f.write(content)

sftp = c.open_sftp()
sftp.put(r'b:\项目\Hass ASA Server Monitor\tmp\ps_complete.py', '/config/preview_server.py')
sftp.close()

# Test syntax
sin,sout,serr=c.exec_command('cd /config && python3 -m py_compile preview_server.py 2>&1 && echo "SYNTAX OK"',timeout=10)
print(sout.read().decode(), serr.read().decode())

# Regenerate
sin,sout,serr=c.exec_command('cd /config && python3 preview_server.py "Isl:0" base_quick_ref 2>&1',timeout=30)
out = sout.read().decode()
err = serr.read().decode()
print("REGEN:", out[:200])
if err: print("ERR:", err[:300])

# Quick check
sin,sout,serr=c.exec_command('grep -c "text-bold\|Cloth_Boots" /config/www/preview_tab.html; ls -la /config/www/preview_tab.html',timeout=10)
print("RESULT:", sout.read().decode())

c.close()
