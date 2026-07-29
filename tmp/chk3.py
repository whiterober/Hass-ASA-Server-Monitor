c=open("/config/lovelace").read()
idx = c.find("ig-title-badge")
print(f"First at offset {idx}")
if idx >= 0:
    # Show a big chunk around it
    chunk = c[max(0,idx-50):idx+300]
    print(repr(chunk[:500]))
else:
    # Search for partial match
    for pat in ["ig-title-badge", "ig-title", "ic-block-img-before"]:
        idx = c.find(pat)
        print(f"{pat}: offset={idx}")
        if idx >= 0:
            print(f"  Context: {c[max(0,idx-20):idx+200]}")
