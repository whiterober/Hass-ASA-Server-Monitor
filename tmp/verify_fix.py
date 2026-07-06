import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Verify the fix is in place on server
sin,sout,serr=c.exec_command("sed -n '207,211p' /config/preview_server.py",timeout=10)
print("Server preview_server.py lines 207-211:")
print(sout.read().decode())

# Check if the fix is correct by testing locally
sin,sout,serr=c.exec_command("python3 -c \"d={'images':[{'image_url':'test.png'}]};icon_url=d.get('images',[{}])[0].get('image_url','') if d.get('images') else '';print('icon_url:',repr(icon_url))\"",timeout=10)
print("\nTest:", sout.read().decode())

c.close()
