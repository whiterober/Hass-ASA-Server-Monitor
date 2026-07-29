c=open("/config/lovelace").read()
# Find ig-title-badge qty rules
import re
matches = re.findall(r'ig-title-badge:has\(\.ic-block-img[^)]*\) \.ic-qty[^}]+}', c)
print(f"ig-title-badge rules: {len(matches)}")
if matches:
    print("First:", matches[0][:200])
    print("Last:", matches[-1][:200])
# Check ig-item qty is intact
matches2 = re.findall(r'ig-item \.ic-qty\{position:absolute.*?right:-2px', c)
print(f"ig-item right:-2px: {len(matches2)}")
# Check ic-qty badge style
matches3 = re.findall(r'\.ic-qty\{display:inline-flex.*?line-height:1\.5', c)
print(f"ic-qty badge: {len(matches3)}")
if matches3:
    print("First:", matches3[0][:150])
