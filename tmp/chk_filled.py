import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Show first few filled wrappers
sin,sout,serr=c.exec_command("python3 -c \"c=open('/config/www/preview_tab.html').read();import re;ms=re.findall(r\"device-icon-wrapper[^>]*>(<img[^>]*>)<\",c);print('\\\\n'.join(ms[:5]))\"",timeout=10)
print("Filled wrappers:", sout.read().decode())

# Check a specific empty wrapper to see what data it should have  
sin,sout,serr=c.exec_command("python3 -c \"c=open('/config/www/preview_tab.html').read();idx=c.find('device-icon-wrapper-vertical'></div>');print(c[max(0,idx-500):idx+100])\"",timeout=10)
print("\nContext around first empty:", sout.read().decode()[:500])

c.close()
