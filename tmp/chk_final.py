import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Check only key files
for f in ['/config/preview_server.py', '/config/build_lovelace.py']:
    sin,sout,serr=c.exec_command(f"grep -c 'device_icon' {f}; grep -c \"images\[0\]\" {f}",timeout=10)
    out = sout.read().decode().strip()
    print(f"{f.split('/')[-1]}: device_icon={out.split(chr(10))[0] if out else '?'} images[0]={out.split(chr(10))[1] if out and chr(10) in out else '?'}")

c.close()
