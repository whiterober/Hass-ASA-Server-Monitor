import paramiko
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)

# Test build_lovelace.py directly
print('=== Testing build_lovelace.py ===')
sin,sout,serr=ssh.exec_command('cd /config && python3 build_lovelace.py 2>&1; echo "EXIT:$?"',timeout=30)
out=sout.read().decode()
err=serr.read().decode()

# Show last lines
lines=out.split('\n')
print('Output (last 10 lines):')
for l in lines[-10:]:
    print('  '+l[:150])
if err.strip():
    print('Stderr:',err[:500])

# Check _bl_step.txt 
print('\n=== _bl_step.txt ===')
sin,sout,serr=ssh.exec_command('cat /config/www/asa-data/_bl_step.txt',timeout=10)
print(sout.read().decode())

# Check if output was written
sin,sout,serr=ssh.exec_command('stat -c "%n %Y %s" /config/lovelace',timeout=10)
print(sout.read().decode())

ssh.close()
