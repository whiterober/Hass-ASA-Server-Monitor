import paramiko, json, io
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
t=paramiko.Transport((h,p));t.connect(username=u,password=pw)
s=paramiko.SFTPClient.from_transport(t)

urls = [
    'https://img.whiterober.ccwu.cc/ASA/consumables/FileArchelon Algae.png',
    'https://img.whiterober.ccwu.cc/ASA/misc/FileCompanion On.png',
    'https://img.whiterober.ccwu.cc/ASA/misc/FileEmote Bark.png',
    'https://img.whiterober.ccwu.cc/ASA/misc/FileEmote Beg.png',
    'https://img.whiterober.ccwu.cc/ASA/misc/FileEmote Bow.png',
    'https://img.whiterober.ccwu.cc/ASA/misc/FileEmote Pet.png',
    'https://img.whiterober.ccwu.cc/ASA/misc/FileEmote Rollover.png',
    'https://img.whiterober.ccwu.cc/ASA/misc/FileFetch.png',
    'https://img.whiterober.ccwu.cc/ASA/misc/FileFree Me.png',
    'https://img.whiterober.ccwu.cc/ASA/misc/FileHere Pup.png',
    'https://img.whiterober.ccwu.cc/ASA/misc/FilePlay Dead.png',
    'https://img.whiterober.ccwu.cc/ASA/misc/FileSit.png',
    'https://img.whiterober.ccwu.cc/ASA/misc/FileWho Is There.png',
    'https://img.whiterober.ccwu.cc/ASA/tools/FileArmadoggo Whistle.png',
]

d = {'categories': {'biology': {'original': 'dark'}}, 'files': {}}
for u in urls:
    d['files'][u] = {'original': 'light'}

buf = io.BytesIO(json.dumps(d, indent=2, ensure_ascii=False).encode())
s.putfo(buf, '/config/www/asa-data/icon_anti_color.json')
s.close();t.close()
print(f'DONE: biology=dark, {len(urls)} files=light')
