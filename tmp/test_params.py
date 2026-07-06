import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
# Try different param combos
for args in [
    "python3 /config/preview_server.py 'base_quick_ref' 'Isl' 2>&1 | tail -3",
    "python3 /config/preview_server.py 'Isl' 'base_quick_ref' 2>&1 | tail -3",
    "python3 /config/preview_server.py '0' 'base_quick_ref' 2>&1 | tail -3",
]:
    sin,sout,serr=c.exec_command('cd /config && '+args,timeout=30)
    out=sout.read().decode().strip()
    err=serr.read().decode().strip()
    print(f"CMD: {args}")
    print(f"  out: {out}")
    if err: print(f"  err: {err}")
c.close()
