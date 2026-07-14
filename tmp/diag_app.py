import paramiko,time
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)

# Check all lovelace file timestamps
print('=== LOVELACE FILES ===')
sin,sout,serr=ssh.exec_command('stat -c "%n  size=%s  mtime=%Y  $(date -d @%Y +%H:%M:%S 2>/dev/null || echo)" /config/lovelace /config/lovelace.lovelace /config/.storage/lovelace /homeassistant/.storage/lovelace.lovelace 2>&1',timeout=10)
print(sout.read().decode())

# Check build log
print('=== BUILD LOG ===')
sin,sout,serr=ssh.exec_command('cat /config/www/asa-data/_bl_step.txt 2>&1',timeout=10)
print(sout.read().decode())

# Check preview_tab.html
print('=== PREVIEW ===')
sin,sout,serr=ssh.exec_command('stat -c "%n  size=%s  mtime=%Y" /config/www/preview_tab.html 2>&1',timeout=10)
print(sout.read().decode())

# Check build_lovelace.py timestamp
print('=== BUILD_LOVELACE.PY ===')
sin,sout,serr=ssh.exec_command('stat -c "%n  size=%s  mtime=%Y" /config/build_lovelace.py 2>&1',timeout=10)
print(sout.read().decode())

# Check shell_command in configuration.yaml
print('=== SHELL_COMMAND build_lovelace ===')
sin,sout,serr=ssh.exec_command('grep -A1 "build_lovelace:" /config/configuration.yaml 2>&1',timeout=10)
out=sout.read().decode()
print(out if out.strip() else 'NOT FOUND')

ssh.close()
