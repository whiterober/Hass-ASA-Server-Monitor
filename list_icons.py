#!/usr/bin/env python3
import json, boto3

with open('/config/www/asa-data/r2_config.json') as f:
    cfg = json.load(f)

client = boto3.client('s3',
    aws_access_key_id=cfg['access_key'],
    aws_secret_access_key=cfg['secret_key'],
    endpoint_url=cfg['endpoint'],
    region_name='auto'
)

result = []
paginator = client.get_paginator('list_objects_v2')
for page in paginator.paginate(Bucket=cfg['bucket'], Prefix=cfg['prefix']):
    for obj in page.get('Contents', []):
        key = obj['Key']
        if key.lower().endswith(('.png','.webp','.svg','.jpg')):
            name = key.rsplit('/',1)[-1].rsplit('.',1)[0]
            result.append({'name': name, 'url': cfg['public_base'] + '/' + key})

print(json.dumps(result, ensure_ascii=False))
