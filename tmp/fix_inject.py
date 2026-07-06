import paramiko, re
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

sftp = c.open_sftp()
sftp.get('/config/preview_server.py', r'b:\项目\Hass ASA Server Monitor\tmp\ps_restore.py')
sftp.close()

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps_restore.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find body rendering area
# Strategy: After reading body, inject images from structured data into empty device-icon-wrapper divs
old = "if b.get('body'):\n                        body_parts.append(b['body'])"

new = """if b.get('body'):
                        body_html = b['body']
                        # Inject images from structured data into body HTML
                        if bt == 'base_storage' and b.get('rows'):
                            rows = b['rows']
                            import re as _re2
                            wrappers = list(_re2.finditer(r'<div class=\"device-icon-wrapper[^\"]*\"></div>', body_html))
                            for ri, row in enumerate(rows):
                                img_url = (row.get('images',[{}])[0].get('image_url','') if row.get('images') else '')
                                if img_url and ri < len(wrappers):
                                    w = wrappers[ri]
                                    img_tag = '<img src=\"'+img_url+'\" style=\"width:30px;height:30px;object-fit:contain\" />'
                                    body_html = body_html[:w.start()] + w.group().replace('></div>','>'+img_tag+'</div>') + body_html[w.end():]
                        body_parts.append(body_html)"""

content = content.replace(old, new)

# Also ensure condition is correct
content = content.replace("if bt != 'base_storage' and b.get('body'):", "if b.get('body'):")

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps_restore.py', 'w', encoding='utf-8') as f:
    f.write(content)

sftp = c.open_sftp()
sftp.put(r'b:\项目\Hass ASA Server Monitor\tmp\ps_restore.py', '/config/preview_server.py')
sftp.close()

# Quickly test syntax
sin,sout,serr=c.exec_command('cd /config && python3 -c "compile(open(chr(39)+chr(112)+chr(114)+chr(101)+chr(118)+chr(105)+chr(101)+chr(119)+chr(95)+chr(115)+chr(101)+chr(114)+chr(118)+chr(101)+chr(114)+chr(46)+chr(112)+chr(121)+chr(39)).read(),chr(39)+chr(112)+chr(114)+chr(101)+chr(118)+chr(105)+chr(101)+chr(119)+chr(95)+chr(115)+chr(101)+chr(114)+chr(118)+chr(101)+chr(114)+chr(46)+chr(112)+chr(121)+chr(39),chr(39)+chr(101)+chr(120)+chr(101)+chr(99)+chr(39))" 2>&1 || python3 -c "compile(open('/config/preview_server.py').read(),'preview_server.py','exec');print('OK')" 2>&1',timeout=10)
print(sout.read().decode(), serr.read().decode())

c.close()
