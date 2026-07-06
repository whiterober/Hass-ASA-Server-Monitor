import paramiko, json
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Check Cloth_Boots in JSON
sin,sout,serr=c.exec_command("python3 -c \"import json;d=json.load(open('/config/www/asa-data/asa_base_quick_ref.json'));srvs=d.get('servers',{});found=False\nfor sid,s in srvs.items():\n for ti,t in enumerate(s.get('tabs',[])):\n  for si,sec in enumerate(t.get('sections',[])):\n   for bi,b in enumerate(sec.get('content_blocks',[])):\n    for ri,r in enumerate(b.get('rows',[])):\n     imgs=r.get('images',[])\n     if imgs and 'Cloth_Boots' in imgs[0].get('image_url',''):\n      print(f'FOUND: {sid} tab{ti} sec{si} blk{bi} row{ri} url={imgs[0][chr(34)+chr(105)+chr(109)+chr(97)+chr(103)+chr(101)+chr(95)+chr(117)+chr(114)+chr(108)+chr(34)]}')\n      found=True\nprint('Not found' if not found else '')\"",timeout=15)
print(sout.read().decode())
c.close()
