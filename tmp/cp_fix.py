import paramiko

h='192.168.197.253'
c=paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)

# Copy v1316 (has fix) to v1317
_,out,_ = c.exec_command("cp /config/www/asa-data/asa-admin-v1316.html /config/www/asa-data/asa-admin-v1317.html", timeout=10)
out.read()

# Verify
_,out,_ = c.exec_command("grep -c 'naturalWidth' /config/www/asa-data/asa-admin-v1317.html", timeout=10)
cnt = out.read().decode().strip()
print(f'v1317 naturalWidth count: {cnt}')
print('OK' if cnt == '1' else 'FAILED')

c.close()
