import json, base64, sys
data = json.loads(base64.b64decode(sys.argv[1]))
json.dump(data, open('/config/www/asa-data/r2_config.json', 'w'), indent=2, ensure_ascii=False)
