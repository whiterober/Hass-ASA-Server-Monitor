import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Upload clean script to server and execute there
script='''
import sys
f=open("/config/build_lovelace.py","r")
lines=f.readlines()
f.close()
orig=len(lines)

# Delete in REVERSE order (bottom to top)
dels=[
    (3276,3281,"main dispatch"),
    (3148,3153,"ic_css tab_type"),
    (3089,3092,"ic_css block_types"),
    (3081,3086,"ic_css bbt"),
]
for s,e,desc in sorted(dels,reverse=True):
    del lines[s-1:e]
    print(f"Deleted L{s}-L{e}: {desc}")

# Fix supply_card condition
for i,l in enumerate(lines):
    if "'supply_card' in block_types or 'map_filter' in block_types" in l:
        lines[i]=l.replace("'supply_card' in block_types or ","")
        print(f"Fixed L{i+1}: supply_card condition")
        break

f=open("/tmp/_bl_new.py","w")
f.writelines(lines)
f.close()
print(f"Lines: {orig} -> {len(lines)}")
'''

sftp=c.open_sftp()
with sftp.open('/tmp/_do_clean.py','w') as f:f.write(script)
sftp.close()

sin,sout,serr=c.exec_command('python3 /tmp/_do_clean.py',timeout=10)
print(sout.read().decode())

# Verify syntax of new file
sin,sout,serr=c.exec_command('python3 -c "compile(open(chr(47)+chr(116)+chr(109)+chr(112)+chr(47)+chr(95)+chr(98)+chr(108)+chr(95)+chr(110)+chr(101)+chr(119)+chr(46)+chr(112)+chr(121)).read(),chr(47)+chr(116)+chr(109)+chr(112)+chr(47)+chr(95)+chr(98)+chr(108)+chr(95)+chr(110)+chr(101)+chr(119)+chr(46)+chr(112)+chr(121),chr(101)+chr(120)+chr(101)+chr(99))";print("SYNTAX_OK")',timeout=10)
print('Syntax:', sout.read().decode().strip())

c.close()
