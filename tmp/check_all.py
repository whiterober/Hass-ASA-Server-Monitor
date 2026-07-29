import json
d=json.load(open("/config/www/asa-data/tribe_ops.json"))
found=0
for t in d["tabs"]:
    for bi,b in enumerate(t.get("content_blocks",[])):
        for di,desc in enumerate(b.get("descriptions",[])):
            img=(desc.get("images",[{}])[0] or {})
            qty=img.get("quantity",0) or desc.get("quantity",0)
            if qty>0:
                found+=1
                print(f"{t.get('label','?')} b{bi} d{di} | qty={qty} | pos={img.get('image_position','after')} | url={'Y' if img.get('image_url','') else 'N'}")
print(f"\nTotal: {found} desc rows with qty>0")
