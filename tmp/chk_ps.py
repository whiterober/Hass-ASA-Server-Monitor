import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Check how preview_server.py works - look for main/entry point
sin,sout,serr=c.exec_command('grep -n "if __name__\|def main\|def regenerate\|def render\|tab\|argparse\|sys.argv" /config/preview_server.py | head -20',timeout=10)
print(sout.read().decode())
c.close()
