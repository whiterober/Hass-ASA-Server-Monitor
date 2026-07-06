import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Upload check script
sftp = c.open_sftp()
sftp.put(r'b:\项目\Hass ASA Server Monitor\tmp\check_data.py', '/tmp/check_data.py')
sftp.close()

# Run it
sin,sout,serr=c.exec_command('python3 /tmp/check_data.py',timeout=10)
print("=== Data check ===")
print(sout.read().decode())

# Regenerate
sin,sout,serr=c.exec_command('cd /config && python3 preview_server.py "Isl:0" base_quick_ref 2>&1',timeout=30)
print("=== Regenerate ===")
print(sout.read().decode())

# Verify
sin,sout,serr=c.exec_command('grep -c Cloth_Boots /config/www/preview_tab.html; stat -c "%Y" /config/www/preview_tab.html',timeout=10)
print("=== Verify ===")
print(sout.read().decode())

c.close()
