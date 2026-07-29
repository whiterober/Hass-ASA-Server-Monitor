c=open("/config/lovelace").read()
idx=c.find("ic-block-img-before")
if idx>=0:
    # Find the surrounding CSS context
    snippet=c[max(0,idx-5):idx+200]
    print(snippet)
else:
    print("ic-block-img-before NOT in lovelace")
print("---")
idx2=c.find("left:0")
if idx2>=0:
    print("left:0 found at", idx2, c[max(0,idx2-50):idx2+100])
