import requests, re

bl = requests.get('https://raw.githubusercontent.com/whiterober/Hass-ASA-Server-Monitor/master/build_lovelace.py', timeout=10).text

# Progress log function to inject
progress_log = "\nimport time\ndef _log(s):\n open('/config/www/asa-data/_bl_progress.txt','a').write(time.strftime('%H:%M:%S')+' '+s+'\\n')\n_log('START')\n"

# Inject after imports (after the first blank line following imports)
bl = bl.replace("def esc(s):", progress_log + "def esc(s):", 1)

# Add markers at key points
bl = bl.replace("print('Server rules: REBUILT", "_log('server_rules_rebuilt')\n    print('Server rules: REBUILT")
bl = bl.replace("print('info_whiterober: REBUILT", "_log('info_whiterober_rebuilt')\n    print('info_whiterober: REBUILT")
bl = bl.replace("print('Base views: REBUILT", "_log('base_views_rebuilt')\n    print('Base views: REBUILT")
bl = bl.replace("print(f'\\nSaved: {len(raw)} bytes", "_log('SAVED')\n    print(f'\\nSaved: {len(raw)} bytes")

open(r'B:\项目\Hass ASA Server Monitor\tmp\bl_progress.py','w',encoding='utf-8').write(bl)
print('done:', len(bl), 'bytes')
