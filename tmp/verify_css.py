import paramiko, io
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

script = b'''import re
c=open("/config/lovelace").read()
m=re.findall(r'ic-block-img-before[^}]*ic-qty', c)
print(f"Found {len(m)} matches")
for x in m: print(x[:200])
'''

sftp = c.open_sftp()
sftp.putfo(io.BytesIO(script), '/tmp/check_css.py')
sftp.close()

si,so,se=c.exec_command("python3 /tmp/check_css.py",timeout=10)
print(so.read().decode())
c.close()
