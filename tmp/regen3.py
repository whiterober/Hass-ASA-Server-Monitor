import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Regenerate preview_tab.html for base data
sin,sout,serr=c.exec_command('cd /config && python3 preview_server.py "Isl:0" base_quick_ref 2>&1',timeout=30)
print(sout.read().decode())
print(serr.read().decode())

# Check if img tags appeared
sin,sout,serr=c.exec_command("python3 -c \"c=open('/config/www/preview_tab.html').read();import re;ms=re.findall(r'device-icon-wrapper[^>]*>([^<]*)<',c);print('Empty wrappers:',sum(1 for m in ms if not m.strip()));print('Filled wrappers:',sum(1 for m in ms if m.strip()))\"",timeout=10)
print("\n", sout.read().decode())

c.close()
