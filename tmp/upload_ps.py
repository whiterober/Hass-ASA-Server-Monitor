import paramiko, hashlib, os

host = '192.168.197.253'
port = 22
user = 'root'
password = '1219Wu1219@'
local = r'b:\项目\Hass ASA Server Monitor\tmp\_remote_preview_server.py'
remote = '/config/preview_server.py'

# Backup server copy first
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, port=port, username=user, password=password, look_for_keys=False, allow_agent=False)
sin, sout, serr = c.exec_command('cp /config/preview_server.py /config/preview_server.py.bak_p0p1', timeout=10)
print('Backup: OK')
c.close()

# Upload
t = paramiko.Transport((host, port))
t.connect(username=user, password=password)
sftp = paramiko.SFTPClient.from_transport(t)
sftp.put(local, remote)
sftp.close()
t.close()
print('Upload: OK')

# Verify
with open(local, 'rb') as f:
    local_md5 = hashlib.md5(f.read()).hexdigest()

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, port=port, username=user, password=password, look_for_keys=False, allow_agent=False)
sin, sout, serr = c.exec_command('md5sum /config/preview_server.py', timeout=10)
remote_md5 = sout.read().decode().strip().split()[0]
# Count lines
sin, sout, serr = c.exec_command('wc -l /config/preview_server.py', timeout=10)
remote_lines = sout.read().decode().strip().split()[0]
c.close()

local_lines = len(open(local, encoding='utf-8').read().split('\n'))

print(f'Local:  {local_lines} lines, MD5={local_md5}')
print(f'Remote: {remote_lines} lines, MD5={remote_md5}')
print('VERIFIED' if local_md5 == remote_md5 else 'MISMATCH - RETRY')
