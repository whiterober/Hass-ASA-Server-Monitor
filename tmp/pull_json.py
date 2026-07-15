import paramiko, json
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
t=paramiko.Transport((h,p));t.connect(username=u,password=pw)
s=paramiko.SFTPClient.from_transport(t)
s.get('/config/www/asa-data/icon_anti_color.json', r'b:\项目\Hass ASA Server Monitor\icon_anti_color.json')
s.close();t.close()
print('PULLED')

# Also print contents
with open(r'b:\项目\Hass ASA Server Monitor\icon_anti_color.json', encoding='utf-8') as f:
    d = json.load(f)
print(f"categories: {list(d['categories'].keys())}")
print(f"files: {len(d['files'])} entries")
for url in sorted(d['files']):
    print(f"  {url.split('/')[-1]}")
