import paramiko,re
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
with sftp.open('/config/www/preview_tab.html','r') as f:
    html=f.read().decode()
# Check section IDs
ids=re.findall(r'id="[^"]*-body"',html)
print(f'Section body IDs ({len(ids)}):')
for i in ids[:15]:
    print(f'  {i}')
# Check table IDs
tids=re.findall(r'id="base-table"',html)
print(f'\nbase-table IDs: {len(tids)}')
# Count unique section- ids
sec_ids=set()
for m in re.finditer(r"id=\"(section-\d+-body)\"",html):
    sec_ids.add(m.group(1))
print(f'Unique section bodies: {sorted(sec_ids)}')
sftp.close()
c.close()
