c=open("/config/www/preview_tab.html").read()
# Show 300 chars before .ic-block-img to check for CSS errors
idx=c.find(".ic-block-img{")
print(c[max(0,idx-400):idx])
print("---BEFORE RULE END---")
# Also check what's right before
start=max(0,idx-50)
print("CONTEXT:", repr(c[start:start+100]))
