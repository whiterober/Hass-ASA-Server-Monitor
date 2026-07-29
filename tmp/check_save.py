import json
d=json.load(open("/config/www/asa-data/tribe_ops.json"))
for t in d["tabs"]:
    if "经验获取" in t.get("label",""):
        for bi,b in enumerate(t.get("content_blocks",[])):
            if bi!=3: continue
            for di,desc in enumerate(b.get("descriptions",[])):
                if di!=1: continue
                img=(desc.get("images",[{}])[0] or {})
                print(f"label={t['label']} b{bi} d{di}")
                print(f"  image_url={img.get('image_url','')[:60]}")
                print(f"  quantity={img.get('quantity','?')}")
                print(f"  image_position={img.get('image_position','?')}")
                print(f"  desc.quantity={desc.get('quantity','?')}")
