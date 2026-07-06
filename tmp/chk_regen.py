import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Check how preview is regenerated
sin,sout,serr=c.exec_command('grep -n "preview_server\|preview_tab" /config/shell_commands.yaml 2>/dev/null || grep -n "preview_server\|preview_tab" /config/configuration.yaml 2>/dev/null | head -10',timeout=10)
print("Shell commands:", sout.read().decode() or "(none)")

# Check preview_tab.html date vs preview_server.py date
sin,sout,serr=c.exec_command('stat -c "%n %Y" /config/www/preview_tab.html /config/preview_server.py',timeout=10)
print("\nFile times:", sout.read().decode())

c.close()
