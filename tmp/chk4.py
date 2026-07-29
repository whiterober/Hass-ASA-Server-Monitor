c=open("/config/lovelace").read()
for sid in ["Isl","Sco","Cen","Abe","Ext","_hint","_default"]:
    pat = f"ic-linear-{sid} .ig-title-badge:has(.ic-block-img) .ic-qty"
    n = c.count(pat)
    print(f"{sid}: {n}")
# Also check the base rule
for pat in ["ig-title-badge:has(.ic-block-img) .ic-qty{position:absolute", "ig-title-badge:has(.ic-block-img) .ic-qty,ha-card .ig-title-row"]:
    n = c.count(pat)
    print(f"base ({pat[:40]}): {n}")
