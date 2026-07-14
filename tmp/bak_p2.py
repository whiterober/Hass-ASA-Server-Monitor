import paramiko, os, datetime

h = '192.168.197.253'
p = 22
u = 'root'
pw = '1219Wu1219@'
ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
bak = r'B:\项目\Hass ASA Server Monitor\bak'
bak_dir = os.path.join(bak, f'asa_{ts}')
os.makedirs(bak_dir, exist_ok=True)

files = [
    '/config/build_lovelace.py',
    '/config/preview_server.py',
    '/config/lovelace',
    '/homeassistant/.storage/lovelace.lovelace',
    '/config/www/asa-data/server_rules.json',
    '/config/www/asa-data/tribe_ops.json',
    '/config/www/asa-data/asa_base_quick_ref.json',
]

t = paramiko.Transport((h, p))
t.connect(username=u, password=pw)
sftp = paramiko.SFTPClient.from_transport(t)
ok = 0
for rf in files:
    fname = os.path.basename(rf)
    lf = os.path.join(bak_dir, fname)
    try:
        sftp.get(rf, lf)
        sz = os.path.getsize(lf)
        print(f'OK: {fname} ({sz}B)')
        ok += 1
    except Exception as e:
        print(f'FAIL: {rf} - {e}')
sftp.close()
t.close()
print(f'\n{ok}/{len(files)} files -> {bak_dir}')
