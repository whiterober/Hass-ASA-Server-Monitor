import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Read server file via SSH
sftp=c.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:content=f.read().decode()
sftp.close()
content_n=content.replace('\r\n','\n')

# Find render_server_grid exact content
import re
# Find the function from "def render_server_grid" to next "def " at same indent
m=re.search(r'(def render_server_grid\(tab\):.*?)(?=\n\ndef |\n\n# ===|\n\ndef build|\Z)', content_n, re.DOTALL)
if m:
    func=m.group(1)
    print('render_server_grid: {} chars'.format(len(func)))
    # Verify unique
    if content_n.count(func)==1:
        # Delete it
        new_content=content_n.replace('\n'+func, '')
        print('  Will delete, new content: {} chars'.format(len(new_content)))
    else:
        print('  NOT unique: {} occurrences'.format(content_n.count(func)))

m=re.search(r'(def render_expandable_detail\(tab\):.*?)(?=\n\ndef |\n\n# ===|\n\ndef build|\Z)', content_n, re.DOTALL)
if m:
    func=m.group(1)
    print('render_expandable_detail: {} chars'.format(len(func)))
    if content_n.count(func)==1:
        print('  Unique, can delete')
    else:
        print('  NOT unique: {} occurrences'.format(content_n.count(func)))

m=re.search(r'(def render_farming_table\(tab\):.*?)(?=\n\ndef |\n\n# ===|\n\ndef build|\Z)', content_n, re.DOTALL)
if m:
    func=m.group(1)
    print('render_farming_table: {} chars'.format(len(func)))
    if content_n.count(func)==1:
        print('  Unique, can delete')
    else:
        print('  NOT unique: {} occurrences'.format(content_n.count(func)))
c.close()
