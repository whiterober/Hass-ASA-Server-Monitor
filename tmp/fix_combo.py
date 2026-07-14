import paramiko

h='192.168.197.253'
c=paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)

script = r"""
with open('/config/www/asa-data/asa-admin-v1316.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = "images.forEach(function(img,i){if(img){var p=positions[i];ctx.drawImage(img,p.x,p.y,p.w,p.h);URL.revokeObjectURL(img.src)}});"
new = "images.forEach(function(img,i){if(img){var p=positions[i];var nw=img.naturalWidth||img.width;var nh=img.naturalHeight||img.height;var scale=Math.min(p.w/nw,p.h/nh);var dw=nw*scale;var dh=nh*scale;var dx=p.x+(p.w-dw)/2;var dy=p.y+(p.h-dh)/2;ctx.drawImage(img,0,0,nw,nh,dx,dy,dw,dh);URL.revokeObjectURL(img.src)}});"

if old not in content:
    print('ERROR')
else:
    content = content.replace(old, new)
    with open('/config/www/asa-data/asa-admin-v1316.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK')
"""

_,out,_ = c.exec_command("cat > /tmp/_fix_combo.py", timeout=10)
out.read()
_.write(script)
_.close()

_,out,err = c.exec_command("python3 /tmp/_fix_combo.py", timeout=30)
print(out.read().decode().strip())
e = err.read().decode().strip()
if e: print(f'ERR: {e}')

c.exec_command("rm /tmp/_fix_combo.py")
c.close()
