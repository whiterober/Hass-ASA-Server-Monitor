import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
si,so,se=c.exec_command("grep -n 'ic-block-img-before.*ic-qty' /config/build_lovelace.py",timeout=10)
print("Server:", so.read().decode() or "NOT FOUND")

# Also check lovelace
si,so,se=c.exec_command("grep -c 'has(.ic-block-img-before).ic-qty' /config/lovelace",timeout=10)
print("Lovelace count:", so.read().decode().strip())
c.close()
