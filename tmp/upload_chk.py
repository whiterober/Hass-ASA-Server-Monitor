import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Upload fixed file
local = r'b:\项目\Hass ASA Server Monitor\tmp\preview_server.py'
sftp = c.open_sftp()
sftp.put(local, '/config/preview_server.py')
sftp.close()
print("Uploaded preview_server.py")

# Search ALL config files for device_icon
sin,sout,serr=c.exec_command("grep -rn 'device_icon' /config/ 2>/dev/null | grep -v '.bak' | grep -v '.pyc'",timeout=10)
out = sout.read().decode()
print("\n=== Remaining device_icon references ===")
print(out if out.strip() else "(NONE - clean!)")

# Also check for device_icon in common locations
sin,sout,serr=c.exec_command("grep -rn 'device_icon' /homeassistant/ 2>/dev/null | head -5",timeout=10)
out2 = sout.read().decode()
print("\n=== /homeassistant/ ===")
print(out2 if out2.strip() else "(none)")

c.close()
