import subprocess, sys
with open('/config/www/asa-data/_bl_progress.txt','w') as f: f.write('START\n')
subprocess.Popen([sys.executable, '/config/build_lovelace.py.bak'])
with open('/config/www/asa-data/_bl_progress.txt','a') as f: f.write('LAUNCHED\n')
