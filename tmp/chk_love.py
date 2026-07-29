c=open("/config/lovelace").read()
idx=c.find("ic-block-{0}")
print(f"{{0}} in lovelace: {idx >= 0}")
if idx>=0:
    print("Context:", c[max(0,idx-50):idx+150])
# Also check brace balance in a view card_mod
print(f"Total {{0}}: {c.count('{0}')}")
