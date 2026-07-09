import requests
bl = requests.get('https://raw.githubusercontent.com/whiterober/Hass-ASA-Server-Monitor/master/build_lovelace.py', timeout=10).text
bl += '\nwith open("/config/www/asa-data/_bl_result.txt","w") as f: f.write("0")\n'
open(r'B:\项目\Hass ASA Server Monitor\tmp\bl_fixed.py','w',encoding='utf-8').write(bl)
print('modified:', len(bl))
