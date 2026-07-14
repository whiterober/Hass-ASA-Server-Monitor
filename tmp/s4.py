import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:content=f.read().decode()
sftp.close()

lines=content.split('\n')

# Show key lines with exact content (repr for whitespace visibility)
targets={
    'main_dispatch':(3276,3282),
    'ic_css_tab_type':(3148,3153),
    'ic_css_block_types':(3089,3094),
    'ic_css_bbt':(3081,3087),
}

for name,(s,e) in targets.items():
    print(f'\n=== {name} ===')
    for i in range(s-1, min(e,len(lines))):
        print(repr(lines[i]))

c.close()
