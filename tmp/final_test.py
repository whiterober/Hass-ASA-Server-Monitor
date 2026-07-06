import paramiko,re
from collections import Counter
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
# Upload
sftp=c.open_sftp()
sftp.put(r'b:\项目\Hass ASA Server Monitor\tmp\preview_server_remote.py','/config/preview_server.py')
sftp.close()
# Compile
sin,sout,serr=c.exec_command('python3 -m py_compile /config/preview_server.py 2>&1 && echo OK',timeout=10)
print('Compile:',sout.read().decode().strip())
# Regenerate
sin,sout,serr=c.exec_command('cd /config && python3 preview_server.py Isl base_quick_ref 2>&1 | tail -3',timeout=30)
print('Generate:',sout.read().decode().strip())
# Check
sftp=c.open_sftp()
with sftp.open('/config/www/preview_tab.html','r') as f:
    html=f.read().decode()
ids=re.findall(r'id="(section-\d+-body)"',html)
cnt=Counter(ids)
print(f'Section bodies: {len(ids)} total, unique: {dict(cnt)}')
tables=len(re.findall(r'<table id="base-table"',html))
print(f'base-tables: {tables}')
sftp.close()
c.close()
