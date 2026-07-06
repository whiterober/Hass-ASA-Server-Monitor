import json
d=json.load(open('/config/www/asa-data/asa_base_quick_ref.json'))
secs=d['servers']['Isl']['tabs'][0]['sections']
print('Sections:',len(secs))
for si,s in enumerate(secs):
    blks=s.get('content_blocks',[])
    print(f'  sec{si}: {len(blks)} blocks')
    for bi,b in enumerate(blks):
        rows=b.get('rows',[])
        for ri,r in enumerate(rows):
            imgs=r.get('images',[])
            if imgs and imgs[0].get('image_url',''):
                print(f'    block{bi} row{ri}: {imgs[0]["image_url"][:60]}')
