import paramiko,json
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Search all backup places
cmds = [
    "find /config -name '*asa_base*' -type f 2>/dev/null",
    "find /backup -name '*asa_base*' -type f 2>/dev/null",
    "find /tmp -name '*asa_base*' -type f 2>/dev/null",
    "ls -la /config/backup/ 2>/dev/null",
    "ls -la /config/www/asa-data/ 2>/dev/null",
]
for cmd in cmds:
    sin,sout,serr=c.exec_command(cmd,timeout=10)
    out=sout.read().decode().strip()
    if out:
        print(f"=== {cmd} ===")
        print(out)

c.close()
