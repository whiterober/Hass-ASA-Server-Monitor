import subprocess, sys
sys.path.insert(0, '/config')
r = subprocess.run(['grep', '-o', 'tb-div-double[^>]*', '/config/www/preview_tab.html'], capture_output=True, text=True)
print('HR double:', r.stdout.strip()[:300])
r2 = subprocess.run(['grep', '-c', '--div-color:var(--primary-text-color)', '/config/www/preview_tab.html'], capture_output=True, text=True)
print('inline var count:', r2.stdout.strip())
