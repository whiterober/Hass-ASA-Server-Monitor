import json
d=json.load(open("/config/www/asa-data/tribe_ops.json"))
desc=d["tabs"][0]["content_blocks"][3]["descriptions"][3]
print("title_icon_quantity:", desc.get("title_icon_quantity","?"))
print("title_icon_image_position:", desc.get("title_icon_image_position","?"))
