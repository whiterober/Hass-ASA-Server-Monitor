import requests

bl = requests.get('https://raw.githubusercontent.com/whiterober/Hass-ASA-Server-Monitor/master/build_lovelace.py', timeout=10).text

# Find the last print statement in main() and add result write after it
# The last line of main() is: print(f'\nSaved: {len(raw)} bytes, {len(views)} views')
old_end = "print(f'\\nSaved: {len(raw)} bytes, {len(views)} views')"
new_end = "print(f'\\nSaved: {len(raw)} bytes, {len(views)} views')\n    with open('/config/www/asa-data/_bl_result.txt','w') as f: f.write('0')"
bl = bl.replace(old_end, new_end)

open(r'B:\项目\Hass ASA Server Monitor\tmp\bl_fixed2.py','w',encoding='utf-8').write(bl)
print('modified:', len(bl), 'bytes')
print('check:', 'f.write' in bl[-200:])
