import paramiko, time
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Time preview_server.py execution
t0=time.time()
si,so,se=c.exec_command('cd /config && python3 -c "import time;t0=time.time();from build_lovelace import make_ic_css,SERVER_MAP,FIXED_STYLES_MAP;css=make_ic_css(SERVER_MAP,FIXED_STYLES_MAP);print(f\"make_ic_css: {len(css)} chars, {time.time()-t0:.3f}s\")"',timeout=15)
print(so.read().decode().strip())
e=se.read().decode()
if e:print('ERR:',e[:200])
print(f'Total: {time.time()-t0:.3f}s')

# Time full preview generation
t0=time.time()
si,so,se=c.exec_command('cd /config && time python3 preview_server.py 0 tribe_ops 2>&1',timeout=15)
out=so.read().decode().strip()
print(out[:500])
print(f'Total: {time.time()-t0:.3f}s')

# Check preview_tab.html size and generation time
si,so,se=c.exec_command('stat -c "%n %s %Y" /config/www/preview_tab.html',timeout=5)
print(so.read().decode().strip())

c.close()
