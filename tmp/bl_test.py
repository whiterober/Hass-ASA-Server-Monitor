import subprocess, sys, time
with open('/config/www/asa-data/_bl_progress.txt','w') as f: f.write('TEST_START\n')
subprocess.run([sys.executable, '/config/build_lovelace.py.bak'])
with open('/config/www/asa-data/_bl_progress.txt','a') as f: f.write('TEST_DONE\n')
