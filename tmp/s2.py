import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:bl=f.read().decode()
sftp.close()

# Read specific regions
ranges = [
    (2160,2180,'supply_card + expandable_detail bbt handlers'),
    (2520,2600,'bt handlers for supply_card/server_grid/card_grid/expandable_detail'),
    (2700,2770,'farming_table ttype + render_server_grid'),
    (2790,2900,'render_expandable_detail + render_farming_table'),
    (3075,3100,'IC_CSS bbt checks'),
    (3140,3160,'IC_CSS tab_type checks'),
    (3270,3290,'Main dispatch'),
]
lines=bl.split('\n')
for start,end,label in ranges:
    print(f'\n=== {label} (L{start}-L{end}) ===')
    for i in range(start-1, min(end, len(lines))):
        print(f'{i+1}: {lines[i]}')
c.close()
