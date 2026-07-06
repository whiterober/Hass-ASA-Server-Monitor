import paramiko, json
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Check the base_quick_ref.json for images with image_url
sin,sout,serr=c.exec_command("python3 -c \"import json;d=json.load(open('/config/www/asa-data/asa_base_quick_ref.json'));srvs=d.get('servers',{});from pprint import pprint;[print(f'{sid}/{ti}/{si}:',json.dumps(r.get('images',[]))[:100]) for sid,s in srvs.items() for ti,t in enumerate(s.get('tabs',[])) for si,sec in enumerate(t.get('sections',[])) for b in sec.get('content_blocks',[]) for r in b.get('rows',[]) if r.get('images') and r['images'][0].get('image_url','')]\"",timeout=15)
print(sout.read().decode())
c.close()
