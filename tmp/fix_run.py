import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Delete the offending file and re-run
sin,sout,serr=c.exec_command('rm -f /tmp/types.py /tmp/types.pyc /tmp/__pycache__/types* 2>/dev/null; python3 /tmp/_chk_bt.py 2>&1',timeout=10)
print(sout.read().decode())
print(serr.read().decode())
c.close()
