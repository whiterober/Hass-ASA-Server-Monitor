import sys
sys.path.insert(0,"/config")
from preview_server import parse_theme_yaml

v = parse_theme_yaml("/config/themes/material_you/material_you.yaml")

# Check the raw chain for secondary-background-color
print("=== secondary-background-color chain ===")
print("secondary-background-color:", repr(v.get("secondary-background-color", "?")))
print("md-sys-color-secondary-container:", repr(v.get("md-sys-color-secondary-container", "?")))
print("md-sys-color-secondary-container-dark:", repr(v.get("md-sys-color-secondary-container-dark", "?")))

print("\n=== other key vars ===")
for k in ["primary-text-color","secondary-text-color","primary-color","accent-color","divider-color","primary-background-color","app-theme-color","card-background-color"]:
    print(f"{k}: {repr(v.get(k, '?'))}")

# Check if vars with commas are being parsed correctly
print("\n=== raw entries with var() comma ===")
import re
for k,val in v.items():
    if "," in str(val) and "var(" in str(val):
        print(f"  {k}: {val}")
        break
