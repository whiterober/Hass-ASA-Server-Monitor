import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Check which server/tab has images data
sin,sout,serr=c.exec_command("python3 -c \"import json;d=json.load(open('/config/www/asa-data/asa_base_quick_ref.json'));[print(f'{sid}:{ti}={t[chr(39)+chr(110)+chr(97)+chr(109)+chr(101)+chr(39)]}') for sid,s in d.get('servers',{}).items() for ti,t in enumerate(s.get('tabs',[]))]\"",timeout=15)
print(sout.read().decode())
c.close()
