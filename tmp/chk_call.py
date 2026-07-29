c=open("/config/build_lovelace.py").read()
print("make_ic_css calls:", c.count("make_ic_css("))
# Find where IC_CSS is used
for line in c.split("\n"):
    if "make_ic_css" in line and "def" not in line:
        print("CALL:", line.strip()[:200])
