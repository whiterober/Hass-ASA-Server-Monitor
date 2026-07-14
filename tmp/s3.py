import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:bl=f.read().decode()
sftp.close()

lines=bl.split('\n')

# Print specific regions for manual review
def show(label, start, end):
    print(f'\n=== {label} (L{start}-L{end}) ===')
    for i in range(start-1, min(end, len(lines))):
        print(f'{i+1}: {lines[i]}')

show('bbt supply+expandable', 2158, 2175)
show('bt chain', 2520, 2655)
show('farming_table ttype', 2705, 2725)
show('render_server_grid', 2722, 2750)
show('render_expandable_detail', 2794, 2825)
show('render_farming_table', 2870, 2900)
show('IC_CSS bbt+block_types', 3078, 3098)
show('IC_CSS tab_type', 3143, 3158)
show('Main dispatch', 3273, 3285)
c.close()
