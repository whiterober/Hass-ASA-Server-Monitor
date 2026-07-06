import paramiko,re
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
with sftp.open('/config/www/preview_tab.html','r') as f:
    html=f.read().decode()
# Extract first 2 base-tables
tables=re.findall(r'(<table id="base-table".*?</table>)',html,re.DOTALL)
print(f'Total base-tables: {len(tables)}')
for i,t in enumerate(tables[:3]):
    trs=re.findall(r'<tr[^>]*>(.*?)</tr>',t,re.DOTALL)
    print(f'\nTable {i}: {len(trs)} rows')
    for j,tr in enumerate(trs[:4]):
        imgs=re.findall(r'<img ',tr)
        bq=re.findall(r'blockquote',tr)
        td_empty=re.findall(r'<td[^>]*></td>',tr)
        print(f'  Row {j}: {len(imgs)} imgs, {len(bq)} bq, {len(td_empty)} empty-td')
        if imgs:
            src=re.findall(r'src="([^"]*)"',tr)
            print(f'    src: {src[0][:60]}')
        if bq:
            labels=re.findall(r'text-bold">([^<]*)<',tr)
            items=re.findall(r'<br>([^<]*)<',tr)
            print(f'    labels: {labels[:3]}, items: {items[:5]}')
sftp.close()
c.close()
