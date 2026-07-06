import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Find the 1 img tag in base table
sin,sout,serr=c.exec_command("python3 -c \"c=open('/config/www/preview_tab.html').read();import re;m=re.search(r'<table id=.base-table.*?</table>',c,re.DOTALL);t=m.group() if m else '';imgs=re.findall(r'<img[^>]*>',t);print(f'IMG count: {len(imgs)}');[print(i) for i in imgs[:5]]\"",timeout=10)
print(sout.read().decode())
c.close()
