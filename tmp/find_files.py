import paramiko, json
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Search icons2.json for files starting with "File"
si,so,se = c.exec_command("python3 -c \"import json;d=json.load(open('/config/www/asa-data/icons2.json'));files=[i for i in d if i.get('name','').startswith('File')];print('Count:',len(files));[print(f['url']) for f in files[:20]]\"",timeout=10)
out = so.read().decode().strip()
err = se.read().decode().strip()
print(out)
if err: print('ERR:', err[:200])
c.close()
