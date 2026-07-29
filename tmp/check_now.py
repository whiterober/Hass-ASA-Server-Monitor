import paramiko

h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

script = b'''import json
d=json.load(open("/config/www/asa-data/tribe_ops.json"))
for t in d["tabs"]:
    for bi,b in enumerate(t.get("content_blocks",[])):
        if bi!=3: continue
        for di,desc in enumerate(b.get("descriptions",[])):
            if di!=1: continue
            img=(desc.get("images",[{}])[0] or {})
            print(f"qty={img.get('quantity','?')} pos={img.get('image_position','?')}")
'''

sftp = c.open_sftp()
import io
sftp.putfo(io.BytesIO(script), '/tmp/check_now.py')
sftp.close()

si, so, se = c.exec_command("python3 /tmp/check_now.py", timeout=10)
print(so.read().decode())
c.close()
