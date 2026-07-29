c=open("/config/www/preview_tab.html").read()
idx=c.find(".ic-block-img{")
if idx>=0:
    print("Base .ic-block-img at", idx)
    print(c[idx:idx+180])
else:
    print("BASE RULE NOT IN FILE")
    # Search for width:30px
    idx30=c.find("width:30px")
    print("width:30px at:", idx30 if idx30>=0 else "NOT FOUND")
