import sys, re

sys.path.insert(0, "/config")
from preview_server import parse_theme_yaml

# Get raw values before resolution by calling parse directly
# Let's re-read the file and check
with open("/config/themes/material_you/material_you.yaml") as f:
    content = f.read()

# Check if 'md-sys-color-secondary-container' is in the file
if 'md-sys-color-secondary-container' in content:
    print("KEY FOUND in file")

# Check the actual raw parsing
raw_test = {}
for line in content.split('\n'):
    if 'md-sys-color-secondary-container' in line:
        print("LINE:", repr(line.strip()))
    if 'secondary-background-color' in line:
        print("SECBG LINE:", repr(line.strip()))

# Now test resolve manually
raw_test['secondary-background-color'] = 'var(--md-sys-color-secondary-container)'
raw_test['md-sys-color-secondary-container'] = 'var(--md-sys-color-secondary-container-dark, #414659)'

def resolve_value(value, raw, visited=None):
    if visited is None:
        visited = set()
    m = re.search(r'var\(--([^,)]+)(?:,\s*([^)]*))?\)', value)
    if not m:
        return value
    ref = m.group(1)
    fallback = m.group(2)
    full_match = m.group(0)
    print(f"  resolve: value={value} ref={ref} fallback={fallback} ref_in_raw={ref in raw}")

    if ref in visited:
        return value.replace(full_match, fallback if fallback else '')

    if ref in raw:
        replacement = resolve_value(raw[ref], raw, visited | {ref})
        result = value.replace(full_match, replacement)
        print(f"  -> resolved to: {result}")
        return result

    if fallback is not None:
        result = value.replace(full_match, fallback)
        print(f"  -> fallback to: {result}")
        return result

    return value

print("\n=== manual resolve test ===")
result = resolve_value(raw_test['secondary-background-color'], raw_test)
print(f"FINAL: {result}")
