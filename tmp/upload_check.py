import paramiko

h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

with open(r'b:\项目\Hass ASA Server Monitor\tmp\check_save.py', 'rb') as f:
    script = f.read()

sftp = c.open_sftp()
sftp.putfo(__import__('io').BytesIO(script), '/tmp/check_save.py')
sftp.close()

si, so, se = c.exec_command("python3 /tmp/check_save.py", timeout=10)
print(so.read().decode())
c.close()
