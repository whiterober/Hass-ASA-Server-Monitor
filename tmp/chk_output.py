import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
# Count base-table rows and check storage content
sin,sout,serr=c.exec_command("python3 -c \"\nimport re\nhtml=open('/config/www/preview_tab.html').read()\n# Count img tags in base-table\nbase_tables=re.findall(r'<table id=\\\\"base-table\\\\".*?</table>',html,re.DOTALL)\nprint(f'base-table count: {len(base_tables)}')\nfor i,t in enumerate(base_tables):\n    imgs=len(re.findall(r'<img ',t))\n    trs=len(re.findall(r'<tr>',t))\n    empty_tds=len(re.findall(r'<td[^>]*></td>',t))\n    has_storage=len(re.findall(r'blockquote',t))\n    print(f'  table{i}: {trs} rows, {imgs} imgs, {has_storage} blockquotes, {empty_tds} empty-tds')\n\" 2>&1",timeout=15)
print(sout.read().decode())
c.close()
