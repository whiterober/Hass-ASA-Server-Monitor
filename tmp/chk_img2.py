import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Count img tags in base table
sin,sout,serr=c.exec_command("python3 -c \"c=open('/config/www/preview_tab.html').read();import re;base_start=c.find('id=\\\"base-table\\\"');base_end=c.find('</table>',base_start);base=c[base_start:base_end];imgs=re.findall(r'<img[^>]*>',base);print('IMG count in base-table:',len(imgs));[print(i.get('src','')) for i in [dict(re.findall(r'(\\\\w+)=\\\"([^\\\"]+)\\\"',img)) for img in imgs[:3]]]\"",timeout=10)
print(sout.read().decode())
c.close()
