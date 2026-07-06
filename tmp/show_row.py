import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Show the exact row line
sin,sout,serr=c.exec_command("sed -n '212p' /config/preview_server.py",timeout=10)
line = sout.read().decode()
print("RAW:", repr(line[:200]))

# Check if there's category data
sin,sout,serr=c.exec_command("python3 -c \"import json;d=json.load(open('/config/www/asa-data/asa_base_quick_ref.json'));r=d['servers']['Isl']['tabs'][0]['sections'][0]['content_blocks'][1]['rows'][0];print('cats:',len(r.get('categories',[])));print('dev_name:',r.get('device_name',''))\"",timeout=10)
print(sout.read().decode())
c.close()
