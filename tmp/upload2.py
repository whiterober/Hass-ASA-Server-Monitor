import paramiko, hashlib
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
local=r'b:\项目\Hass ASA Server Monitor\tmp\_remote_preview_server.py'
remote='/config/preview_server.py'
t=paramiko.Transport((h,p));t.connect(username=u,password=pw)
sftp=paramiko.SFTPClient.from_transport(t);sftp.put(local,remote);sftp.close();t.close()
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
si,so,se=c.exec_command('md5sum /config/preview_server.py;wc -l /config/preview_server.py',timeout=10)
out=so.read().decode().strip()
c.close()
lm=hashlib.md5(open(local,'rb').read()).hexdigest()
ll=len(open(local,encoding='utf-8').read().split('\n'))
rm=out.split()[0];rl=out.split('\n')[1].split()[0] if '\n' in out else out.split()[-2]
print(f'Local: {ll} lines, MD5={lm}')
print(f'Remote: {rl} lines, MD5={rm}')
print('OK' if lm==rm else 'FAIL')
