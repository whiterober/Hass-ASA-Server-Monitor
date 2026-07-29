import sys, json
sys.path.insert(0, '/config')

d = json.load(open('/config/www/asa-data/tribe_ops.json'))
tab = d['tabs'][0]  # 经验获取速查
print("Tab:", tab.get('label'))
print("Type:", tab.get('type'))

block_types = {b.get('block_type','') for b in tab.get('content_blocks',[])}
print("block_types:", block_types)
print("'info_card' in block_types:", 'info_card' in block_types)

# Show each block
for bi, b in enumerate(tab.get('content_blocks',[])):
    print(f"  b{bi}: {b.get('block_type','?')} has {len(b.get('descriptions',[]))} descs")
