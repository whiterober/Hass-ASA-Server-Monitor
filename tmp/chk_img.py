import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Check if img tags exist inside device-icon-wrapper
sin,sout,serr=c.exec_command("grep -c 'device-icon-wrapper.*img' /config/www/preview_tab.html; echo '---'; grep -o 'device-icon-wrapper[^<]*<img[^>]*>' /config/www/preview_tab.html | head -5",timeout=10)
print(sout.read().decode())
c.close()
