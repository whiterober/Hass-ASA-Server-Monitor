import json
content = open('/config/lovelace').read()
# Find ic-block-img-before near Cryofridge
idx = content.find('Cryofridge')
if idx >= 0:
    snippet = content[max(0,idx-50):idx+200]
    print("Around Cryofridge:", snippet)
    hasQty = 'ic-qty' in snippet
    print(f"Has ic-qty: {hasQty}")
else:
    print("Cryofridge not found in lovelace")
# Also search for ×77
if '×77' in content:
    idx2 = content.index('×77')
    print(f"×77 found at pos {idx2}: {content[max(0,idx2-80):idx2+80]}")
else:
    print("×77 not found in lovelace")
