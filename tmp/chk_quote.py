with open(r"b:\项目\Hass ASA Server Monitor\www\asa-admin.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
# Line 2904 (0-indexed: 2903)
line = lines[2903]
# Check for backslash before single quotes around icon_group
print("L2904 length:", len(line))
# Find the mode part
idx = line.find("mode:")
if idx >= 0:
    snippet = line[idx:idx+50]
    print("Snippet:", repr(snippet))
    # Check for backslash
    if "\\'" in snippet:
        print("ESCAPED single quotes found")
    else:
        print("UNESCAPED single quotes!")
