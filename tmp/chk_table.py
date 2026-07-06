import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Extract the base-table content
sin,sout,serr=c.exec_command("python3 -c \"c=open('/config/www/preview_tab.html').read();import re;m=re.search(r'<table id=.base-table.*?</table>',c,re.DOTALL);print(m.group()[:2000] if m else 'NOT FOUND')\"",timeout=10)
print(sout.read().decode()[:2000])
c.close()
