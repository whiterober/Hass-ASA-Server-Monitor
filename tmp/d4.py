import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

cmd = "python3 -c \"import re;c=open('/config/www/preview_tab.html').read();styles=re.findall(r'<style[^>]*>(.*?)</style>',c,re.S);print('Style blocks:',len(styles),[len(s) for s in styles]);print('Total chars:',len(c));h=c.find('</head>');b=c.find('</body>');print('Head len:',h,'Body len:',b-h);icons=re.findall(r'mdi:[\w-]+',c);print('MDI unique:',len(set(icons)),'total:',len(icons));print('Icons:',sorted(set(icons))[:30])\""
si,so,se = c.exec_command(cmd, timeout=10)
print(so.read().decode())
e=se.read().decode()
if e:print('ERR:',e[:200])
c.close()
