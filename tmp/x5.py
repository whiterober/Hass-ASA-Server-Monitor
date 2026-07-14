import paramiko,re
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
with sftp.open('/config/www/preview_tab.html','r') as f:data=f.read().decode()
sftp.close()
# Find <body> tag position
m=re.search(r'<body[^>]*>',data)
if m:
    start=m.start()
    print('Body starts at byte:',start)
    print('---BODY (first 2000 chars after body)---')
    print(data[start:start+2000])
c.close()
