import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Test preview_server.py with different tab names
tests = [
    'python3 /config/preview_server.py "0" base_quick_ref 2>&1 | head -3',
    'python3 /config/preview_server.py "Isl:0" base_quick_ref 2>&1 | head -3',
    'python3 /config/preview_server.py "孤岛-英灵殿" base_quick_ref 2>&1 | head -3',
]
for t in tests:
    sin,sout,serr=c.exec_command(t,timeout=10)
    out=sout.read().decode().strip()
    err=serr.read().decode().strip()
    print(f'--- {t[35:70]} ---')
    if out: print(out[:200])
    if err: print('ERR:',err[:200])
c.close()
