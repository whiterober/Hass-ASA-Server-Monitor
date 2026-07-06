import json
d=json.load(open('/config/www/asa-data/asa_base_quick_ref.json'))
secs=d['servers']['Isl']['tabs'][0]['sections']
for si,sec in enumerate(secs):
    for bi,b in enumerate(sec.get('content_blocks',[])):
        bt=b.get('block_type','text')
        rows=len(b.get('rows',[]))
        print(f'sec{si} blk{bi}: type={bt} rows={rows}')
