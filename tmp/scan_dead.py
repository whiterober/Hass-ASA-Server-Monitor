import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

sftp=c.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f: bl=f.read().decode()
with sftp.open('/config/preview_server.py','r') as f: pr=f.read().decode()
sftp.close()

print('BL:', len(bl), 'chars,', len(bl.split('\n')), 'lines')
print('PR:', len(pr), 'chars,', len(pr.split('\n')), 'lines')
print()

for kw in ['supply_card','expandable_detail','farming_table','server_grid','card_grid']:
    bn=bl.count(kw);pn=pr.count(kw)
    if bn+pn>0:
        print(f'{kw}: bl={bn}, pr={pr.count(kw)}')

# Show ALL lines with these keywords in build_lovelace
print('\n=== build_lovelace.py references ===')
bl_lines=bl.split('\n')
for kw in ['supply_card','expandable_detail','farming_table','server_grid','card_grid']:
    for i,l in enumerate(bl_lines,1):
        if kw in l:
            print(f'  L{i}: {l.strip()[:120]}')

c.close()
