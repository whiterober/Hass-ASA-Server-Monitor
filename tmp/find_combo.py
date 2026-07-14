import paramiko
h='192.168.197.253'
c=paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)

# Find the drawImage line
_,out,_ = c.exec_command("grep -n 'drawImage' /config/www/asa-data/asa-admin-v1316.html",timeout=10)
for line in out.read().decode().split('\n'):
    if 'drawImage' in line:
        print(line[:200])

# Read the surrounding context
_,out,_ = c.exec_command("sed -n '7945,7965p' /config/www/asa-data/asa-admin-v1316.html",timeout=10)
print('\n=== Context ===')
print(out.read().decode())

c.close()
