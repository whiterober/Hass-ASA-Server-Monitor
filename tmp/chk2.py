with open(r"b:\项目\Hass ASA Server Monitor\www\asa-admin.html", "rb") as f:
    data = f.read()
# Find the mode: pattern around L2904
idx = data.find(b"openIconPicker({mode:")
if idx >= 0:
    chunk = data[idx:idx+60]
    print("Bytes:", chunk)
    print("Has backslash:", b"\\'" in chunk)
    print("Decoded:", chunk.decode("utf-8"))
