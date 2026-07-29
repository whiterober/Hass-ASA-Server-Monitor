src = open("/config/build_lovelace.py", "rb").read()
lines = src.split(b'\n')
# Show line 103 raw
line = lines[102]
print("Line 103 raw bytes:")
print(line)
print("\nDecoded:", line.decode('utf-8', errors='replace'))
