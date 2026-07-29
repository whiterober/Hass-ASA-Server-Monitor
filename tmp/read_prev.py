c=open("/config/www/preview_tab.html").read()
idx=c.find("ic-block-img")
print("ic-block-img at", idx)
if idx>=0:
    print(c[max(0,idx-100):idx+300])
else:
    print("NOT IN FILE")
# Also check total size and style tag
print("Total len:", len(c))
s=c.find("<style>")
e=c.find("</style>")
print(f"Style tag: {s} to {e}, len={e-s if e>s else 0}")
