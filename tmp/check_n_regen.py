import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Check current JSON state
sin,sout,serr=c.exec_command("python3 -c \"import json;d=json.load(open('/config/www/asa-data/asa_base_quick_ref.json'));s=d['servers']['Isl']['tabs'][0]['sections'];print('sections:',len(s));[print(f'  sec{si}: {len(sec.get(chr(34)+chr(99)+chr(111)+chr(110)+chr(116)+chr(101)+chr(110)+chr(116)+chr(95)+chr(98)+chr(108)+chr(111)+chr(99)+chr(107)+chr(115),[]))} blocks, {sum(len(b.get(chr(34)+chr(114)+chr(111)+chr(119)+chr(115)+chr(34),[])) for b in sec.get(chr(34)+chr(99)+chr(111)+chr(110)+chr(116)+chr(101)+chr(110)+chr(116)+chr(95)+chr(98)+chr(108)+chr(111)+chr(99)+chr(107)+chr(115),[]))} rows') for si,sec in enumerate(s)]\"",timeout=10)
out = sout.read().decode()
print("JSON state:", out[:300])

# Check if preview_server.py condition is correct
sin,sout,serr=c.exec_command("grep -n 'b.get.*body\|bt.*base_storage' /config/preview_server.py | head -5",timeout=10)
print("\nConditions:", sout.read().decode())

# Regenerate for Isl tab 0  
sin,sout,serr=c.exec_command('cd /config && python3 preview_server.py "Isl:0" base_quick_ref 2>&1',timeout=30)
print("\nRegen:", sout.read().decode())

# Quick verify
sin,sout,serr=c.exec_command("grep -c 'text-bold\|device-icon-wrapper.*img' /config/www/preview_tab.html; wc -c /config/www/preview_tab.html",timeout=10)
print("Verify:", sout.read().decode())

c.close()
