import paramiko, json
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sin,sout,serr=c.exec_command("python3 -c \"import json;d=json.load(open('/config/www/asa-data/asa_base_quick_ref.json'));srvs=d.get('servers',{});print('Servers:',list(srvs.keys()));s=srvs.get('Isl',{});tabs=s.get('tabs',[]);print('Tabs:',len(tabs));[print(f'Tab {i}: {len(t.get(\\'sections\\',[]))} sections') for i,t in enumerate(tabs)]\"",timeout=10)
print(sout.read().decode())
c.close()
