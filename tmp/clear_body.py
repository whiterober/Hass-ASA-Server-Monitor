import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Strategy: Clear body field for base_storage blocks in JSON,
# then regenerate preview with structured rendering (which has storage data).

# Step 1: Clear body field
sin,sout,serr=c.exec_command("python3 -c \"import json;d=json.load(open('/config/www/asa-data/asa_base_quick_ref.json'));[b.pop('body',None) for s in d['servers']['Isl']['tabs'][0]['sections'] for b in s.get('content_blocks',[]) if b.get('block_type')=='base_storage'];json.dump(d,open('/config/www/asa-data/asa_base_quick_ref.json','w'),ensure_ascii=False,indent=2)\"",timeout=15)
print("Clear body:", sout.read().decode(), serr.read().decode())

# Step 2: Regenerate
sin,sout,serr=c.exec_command('cd /config && python3 preview_server.py "Isl:0" base_quick_ref 2>&1',timeout=30)
print("Regen:", sout.read().decode())
print("Err:", serr.read().decode()[:200])

# Step 3: Check
sin,sout,serr=c.exec_command('grep -c Cloth_Boots /config/www/preview_tab.html; echo "---"; grep -c "Cryofridge\|孤岛\|废生物\|text-bold" /config/www/preview_tab.html',timeout=10)
print("Verify:", sout.read().decode())

c.close()
