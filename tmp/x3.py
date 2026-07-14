import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
with sftp.open('/config/preview_server.py','r') as f:srv=f.read().decode()
sftp.close()
loc=open(r'b:\项目\Hass ASA Server Monitor\bak\asa_v1336_20260714\preview_server.py',encoding='utf-8').read()
print('Server:',len(srv),'chars')
print('Local v1336:',len(loc),'chars')
print('Diff:',len(srv)-len(loc),'chars')
print()
for kw in ['raw_html','render_tab_html','make_ic_css','supply_card','expandable_detail','farming_table','server_grid','card_grid']:
    sn=srv.count(kw);ln=loc.count(kw)
    flag=' <<< DIFF' if sn!=ln else ''
    print(f'{kw}: srv={sn}, local={ln}{flag}')
c.close()
