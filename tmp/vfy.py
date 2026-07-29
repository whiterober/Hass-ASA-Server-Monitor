import re
c=open("/config/lovelace").read()
m=re.findall(r"ic-block-img-before.*?ic-qty[^}]+",c)
if m:
    for x in m[:2]:
        print(x[:200])
else:
    print("NOT FOUND")
