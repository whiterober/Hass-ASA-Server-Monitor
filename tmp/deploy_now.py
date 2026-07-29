import paramiko, io

h = '192.168.197.253'; p = 22; u = 'root'; pw = '1219Wu1219@'
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h, port=p, username=u, password=pw, look_for_keys=False, allow_agent=False)

c.exec_command('rm -rf /config/__pycache__', timeout=5)

with open(r'b:\项目\Hass ASA Server Monitor\tmp\bl_work_v2.py', 'rb') as f:
    sftp = c.open_sftp()
    sftp.putfo(io.BytesIO(f.read()), '/config/build_lovelace.py')
    sftp.close()

si, so, se = c.exec_command('python3 /config/build_lovelace.py 2>&1 | tail -1; python3 /config/preview_server.py 0 tribe_ops 2>&1 | tail -1', timeout=30)
print(so.read().decode())

c.close()
