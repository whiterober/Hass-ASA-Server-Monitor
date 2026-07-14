import paramiko

h='192.168.197.253'
c=paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)

for ver in ['v1316', 'v1317']:
    _,out,_ = c.exec_command(f"grep -c 'drawImage' /config/www/asa-data/asa-admin-{ver}.html 2>/dev/null || echo 0", timeout=10)
    cnt = out.read().decode().strip()
    _,out,_ = c.exec_command(f"grep -c 'naturalWidth' /config/www/asa-data/asa-admin-{ver}.html 2>/dev/null || echo 0", timeout=10)
    nw = out.read().decode().strip()
    print(f'{ver}: drawImage={cnt}, naturalWidth={nw}')

c.close()
