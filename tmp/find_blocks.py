import paramiko,re
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)
sftp=c.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:content=f.read().decode()
sftp.close()
content=content.replace('\r\n','\n')

# Find each dead block by looking for the elif/def line then matching to the next elif/def/return at same indent
def find_block(content, pattern, end_patterns):
    """Find block starting with pattern, ending before end_patterns"""
    m=re.search(pattern, content)
    if not m: return None,None
    start=m.start()
    rest=content[m.end():]
    # Find the earliest end pattern
    end_pos=len(rest)
    for ep in end_patterns:
        em=re.search(ep, rest)
        if em and em.start()<end_pos:
            end_pos=em.start()
    block=content[start:m.end()+end_pos]
    # Verify unique
    count=content.count(block)
    return block,count

# bt supply_card
block,c=find_block(content,
    r'\n            elif bt==.supply_card.:',
    [r'\n            elif bt==.', r'\n            else:', r'\n        elif ttype', r'\n    parts\.append'])
if c==1: print('supply_card bt: {} chars, unique'.format(len(block)))
elif c==0: print('supply_card bt: NOT FOUND')
else: print('supply_card bt: {} occurrences, NOT unique'.format(c))

# bt server_grid
block,c=find_block(content,
    r'\n            elif bt==.server_grid.:',
    [r'\n            elif bt==.', r'\n            else:', r'\n        elif ttype', r'\n    parts\.append'])
if c==1: print('server_grid bt: {} chars, unique'.format(len(block)))
elif c==0: print('server_grid bt: NOT FOUND')
else: print('server_grid bt: {} occurrences, NOT unique'.format(c))

# bt card_grid
block,c=find_block(content,
    r'\n            elif bt==.card_grid.:',
    [r'\n            elif bt==.', r'\n            else:', r'\n        elif ttype', r'\n    parts\.append'])
if c==1: print('card_grid bt: {} chars, unique'.format(len(block)))
elif c==0: print('card_grid bt: NOT FOUND')
else: print('card_grid bt: {} occurrences, NOT unique'.format(c))

# bt expandable_detail
block,c=find_block(content,
    r'\n            elif bt==.expandable_detail.:',
    [r'\n            elif bt==.', r'\n            else:', r'\n        elif ttype', r'\n    parts\.append'])
if c==1: print('expandable_detail bt: {} chars, unique'.format(len(block)))
elif c==0: print('expandable_detail bt: NOT FOUND')
else: print('expandable_detail bt: {} occurrences, NOT unique'.format(c))

# ttype farming_table
block,c=find_block(content,
    r'\n    elif ttype == .farming_table.:',
    [r'\n    elif ttype == ', r'\n    parts\.append\(\'</div>\'\)', r'\ndef render_'])
if c==1: print('farming_table ttype: {} chars, unique'.format(len(block)))
elif c==0: print('farming_table ttype: NOT FOUND')
else: print('farming_table ttype: {} occurrences, NOT unique'.format(c))

# render_farming_table - from def to next def at same indent (0 spaces)
m=re.search(r'\ndef render_farming_table\(tab\):', content)
if m:
    start=m.start()+1  # skip the leading \n
    rest=content[start:]
    # Find next top-level def
    em=re.search(r'\ndef [a-z_]', rest)
    if em:
        block=content[start:start+em.start()]
        c=content.count(block)
        print('render_farming_table fn: {} chars, {} occurrences'.format(len(block),c))
    else:
        print('render_farming_table fn: no end found')
else:
    print('render_farming_table fn: NOT FOUND')

c.close()
