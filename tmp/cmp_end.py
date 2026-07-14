import paramiko,os
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)

# Read current server file
sftp=ssh.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:cur=f.read().decode()
sftp.close()

# Read v1337c baseline
v1337c=r'c:\Users\white\.copilot\bak\asa_v1337c_20260714\build_lovelace.py'
with open(v1337c,'r',encoding='utf-8') as f:v1337c_bl=f.read()

print('v1337c: {} chars, {} lines'.format(len(v1337c_bl),len(v1337c_bl.split('\n'))))
print('Current: {} chars, {} lines'.format(len(cur),len(cur.split('\n'))))
print('Diff: {} chars'.format(len(v1337c_bl)-len(cur)))

# Check what v1337c has that current doesn't
cur_n=cur.replace('\r\n','\n')
v1337c_n=v1337c_bl.replace('\r\n','\n')

# Check key patterns
for pat in ['def build\\(','if __name__','_log_step','SAVED_OK','asa_built_views']:
    vc=v1337c_n.count(pat)
    cc=cur_n.count(pat)
    print('{}: v1337c={}, cur={}'.format(pat,vc,cc))

# Show last 5 lines of v1337c
print('\n=== v1337c last 5 lines ===')
for l in v1337c_n.split('\n')[-5:]:
    print('  '+l[:120])

print('\n=== Current last 5 lines ===')
for l in cur_n.split('\n')[-5:]:
    print('  '+l[:120])

ssh.close()
