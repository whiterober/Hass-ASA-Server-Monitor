import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sin,sout,serr=c.exec_command('grep -c "image_url" /config/www/asa-data/asa_base_quick_ref.json; grep -c "device_icon_url" /config/www/asa-data/asa_base_quick_ref.json; echo ---; python3 -c "import json;d=json.load(open(\"/config/www/asa-data/asa_base_quick_ref.json\"));r=d[\"servers\"][\"Isl\"][\"tabs\"][0][\"sections\"][0][\"content_blocks\"];print(\"blocks:\",len(r));[print(b.get(\"block_type\"),b.get(\"rows\",[])[:1]) for b in r[:1]]"',timeout=10)
print(sout.read().decode())
c.close()
