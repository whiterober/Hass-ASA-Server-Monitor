src = open("/config/build_lovelace.py").read()
lines = src.split('\n')
# Show fixed_styles_map ig-title rules
for i in range(100, 108):
    print(f'{i+1}: {lines[i]}')
