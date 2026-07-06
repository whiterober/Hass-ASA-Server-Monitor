import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

sftp = c.open_sftp()
sftp.get('/config/preview_server.py', r'b:\项目\Hass ASA Server Monitor\tmp\ps_fix4.py')
sftp.close()

with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps_fix4.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the exact row rendering line
old = "rows_html.append('<tr><td class=\"border border-gray-300 p-2 text-left align-top\"><div class=\"device-container\"><div class=\"materials-box\"><span class=\"bio-capacity-tag-bottom\">'+cap+'</span><div class=\"materials-box-inner\"><div class=\"device-icon-wrapper\">'+icon+'</div></div></div></div></td><td class=\"border border-gray-300 p-2 text-left align-top\" colspan=\"2\"></td></tr>')"

new = """                        # Render categories for storage columns
                        cat_parts = []
                        for c in row.get('categories', []):
                            items_html = '<br>'.join([(i.get('name','') or '') for i in c.get('items', [])])
                            if items_html:
                                label = c.get('label','')
                                cat_parts.append(('<span class=\"text-bold\">'+label+'</span><br>'+items_html) if label else items_html)
                        col2 = '<br>'.join(cat_parts) if cat_parts else ''
                        rows_html.append('<tr><td class=\"border border-gray-300 p-2 text-left align-top\"><div class=\"device-container\"><div class=\"materials-box\"><span class=\"bio-capacity-tag-bottom\">'+cap+'</span><div class=\"materials-box-inner\"><div class=\"device-icon-wrapper\">'+icon+'</div></div></div></div></td><td class=\"border border-gray-300 p-2 text-left align-top\" colspan=\"2\">'+col2+'</td></tr>')"""

cnt = content.count(old)
print(f"Found old row: {cnt}x")

if cnt > 0:
    content = content.replace(old, new)
    with open(r'b:\项目\Hass ASA Server Monitor\tmp\ps_fix4.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    sftp = c.open_sftp()
    sftp.put(r'b:\项目\Hass ASA Server Monitor\tmp\ps_fix4.py', '/config/preview_server.py')
    sftp.close()
    
    # Regenerate
    sin,sout,serr=c.exec_command('cd /config && python3 preview_server.py "Isl:0" base_quick_ref 2>&1',timeout=30)
    print("OUT:", sout.read().decode())
    err = serr.read().decode()
    if err:
        print("ERR:", err[:300])
else:
    print("ROW NOT FOUND")

c.close()
