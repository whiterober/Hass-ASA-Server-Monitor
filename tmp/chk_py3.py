import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
# Search for base rendering across all config files
for fname in ['build_lovelace.py', 'preview_server.py', 'preview_tab.html']:
    cmd = f'grep -c "device_icon" /config/{fname} 2>/dev/null; grep -c "images\[0\]" /config/{fname} 2>/dev/null; grep -c "base_storage\|base-table\|device-icon-wrapper" /config/{fname} 2>/dev/null; echo "---{fname}"'
    sin,sout,serr=c.exec_command(cmd,timeout=10)
    print(sout.read().decode())
c.close()
