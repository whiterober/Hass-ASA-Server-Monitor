import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
sftp.put(r'b:\项目\Hass ASA Server Monitor\tmp\preview_server_remote.py', '/config/preview_server.py')
sftp.close()
# Compile check
sin,sout,serr=c.exec_command('python3 -m py_compile /config/preview_server.py 2>&1 && echo "OK"',timeout=10)
print(sout.read().decode())
# Regenerate preview
sin,sout,serr=c.exec_command('cd /config && python3 preview_server.py Isl base_quick_ref 2>&1 | tail -3',timeout=30)
print(sout.read().decode())
# Check dupes
sftp=c.open_sftp()
with sftp.open('/config/www/preview_tab.html','r') as f:
    html=f.read().decode()
import re
tables=re.findall(r'<table id="base-table".*?</table>',html,re.DOTALL)
section_divs=len(re.findall(r"id='section-\d+-body'",html))
print(f'base-tables: {len(tables)}, section-bodies: {section_divs}')
# Show first 2 tables
for i,t in enumerate(tables[:2]):
    imgs=len(re.findall(r'<img ',t))
    trs=len(re.findall(r'<tr>',t))
    bq=len(re.findall(r'blockquote',t))
    print(f'  table{i}: {trs} rows, {imgs} imgs, {bq} blockquotes')
sftp.close()
c.close()
