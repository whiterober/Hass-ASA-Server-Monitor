import paramiko
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
sftp=ssh.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:bl=f.read().decode()
sftp.close()
import re
# Find all make_ic_css occurrences
for m in re.finditer(r'make_ic_css',bl):
    start=max(0,m.start()-20)
    end=min(len(bl),m.end()+40)
    print('{}: ...{}...'.format(m.start(),bl[start:end].replace('\n',' ')))
print('\nTotal: {}'.format(len(re.findall(r'make_ic_css',bl))))
ssh.close()
