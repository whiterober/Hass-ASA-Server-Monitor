#!/bin/bash
CONFIG="/config/www/asa-data/r2_config.json"
ACCESS_KEY=$(python3 -c "import json;print(json.load(open('$CONFIG'))['access_key'])")
SECRET_KEY=$(python3 -c "import json;print(json.load(open('$CONFIG'))['secret_key'])")
BUCKET=$(python3 -c "import json;print(json.load(open('$CONFIG'))['bucket'])")
ENDPOINT=$(python3 -c "import json;print(json.load(open('$CONFIG'))['endpoint'])")
PREFIX=$(python3 -c "import json;print(json.load(open('$CONFIG'))['prefix'])")
BASE=$(python3 -c "import json;print(json.load(open('$CONFIG'))['public_base'])")

aws s3api list-objects-v2 \
  --bucket "$BUCKET" \
  --endpoint-url "$ENDPOINT" \
  --prefix "$PREFIX" \
  --aws-access-key-id "$ACCESS_KEY" \
  --aws-secret-access-key "$SECRET_KEY" \
  --query "Contents[?contains(Key,'.png')||contains(Key,'.webp')||contains(Key,'.svg')||contains(Key,'.jpg')].[Key]" \
  --output json 2>/dev/null | \
python3 -c "
import json,sys
data = json.load(sys.stdin)
result = []
for item in data:
    key = item[0] if isinstance(item,list) else item
    name = key.rsplit('/',1)[-1].rsplit('.',1)[0]
    result.append({'name':name,'url':'$BASE/'+key})
print(json.dumps(result,ensure_ascii=False))
"
