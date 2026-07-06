import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Regenerate
sin,sout,serr=c.exec_command('cd /config && python3 preview_server.py "Isl:0" base_quick_ref 2>&1',timeout=30)
print(sout.read().decode())

# Check immediately
sin,sout,serr=c.exec_command("stat -c '%Y' /config/www/preview_tab.html; grep -c 'Cloth_Boots' /config/www/preview_tab.html; echo '---'; python3 -c \"import json;d=json.load(open('/config/www/asa-data/asa_base_quick_ref.json'));secs=d['servers']['Isl']['tabs'][0]['sections'];print('Sections:',len(secs));[print(f'  sec{si}: {len(s.get(chr(34)+chr(99)+chr(111)+chr(110)+chr(116)+chr(101)+chr(110)+chr(116)+chr(95)+chr(98)+chr(108)+chr(111)+chr(99)+chr(107)+chr(115),[]))} blocks') for si,s in enumerate(secs)]\"",timeout=15)
print(sout.read().decode())

c.close()
