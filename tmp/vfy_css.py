c=open("/config/lovelace").read()
print("ig-title-badge:has(.ic-block-img) .ic-qty:", c.count("ig-title-badge:has(.ic-block-img) .ic-qty"))
print("ig-title-badge:has(.ic-block-img-before) .ic-qty:", c.count("ig-title-badge:has(.ic-block-img-before) .ic-qty"))
print("ic-qty{display:inline-flex:", c.count("ic-qty{display:inline-flex"))
