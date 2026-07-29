import re
c=open("/config/build_lovelace.py").read()
print("ig-title-badge:has:", c.count("ig-title-badge:has(.ic-block-img) .ic-qty"))
print("ic-text:not:", c.count("ic-text:not([class*=\"ic-block-\"]) .ic-qty"))
# Also show the ig-title line
idx = c.find("ig-title-badge:has(.ic-block-img)")
if idx > 0:
    print("FOUND at", c[:idx].count("\n")+1)
    print(c[idx:idx+200])
else:
    print("NOT FOUND")
