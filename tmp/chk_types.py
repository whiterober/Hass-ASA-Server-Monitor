import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Check block types in the data
sin,sout,serr=c.exec_command("python3 -c \"import json;d=json.load(open('/config/www/asa-data/asa_base_quick_ref.json'));secs=d['servers']['Isl']['tabs'][0]['sections'];[(print(f'sec{si} blk{bi}: type={b.get(chr(34)+chr(98)+chr(108)+chr(111)+chr(99)+chr(107)+chr(95)+chr(116)+chr(121)+chr(112)+chr(101)+chr(34),chr(34)+chr(116)+chr(101)+chr(120)+chr(116)+chr(34))} rows={len(b.get(chr(34)+chr(114)+chr(111)+chr(119)+chr(115)+chr(34),[]))}')) for si,sec in enumerate(secs) for bi,b in enumerate(sec.get('content_blocks',[]))]\"",timeout=10)
print(sout.read().decode())
c.close()
