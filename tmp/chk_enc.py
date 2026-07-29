c=open("/config/lovelace").read()
# HTML-encoded : is &#58;
print("ig-title-badge (raw):", c.count("ig-title-badge"))
print("ig-title-badge&#58;has:", c.count("ig-title-badge&#58;has"))
print("ic-text&#58;not:", c.count("ic-text&#58;not"))
# Also check for common patterns
import re
print("ic-qty total:", len(re.findall(r'ic-qty', c)))
# Check block-img-before
print("block-img-before:", c.count("block-img-before"))
