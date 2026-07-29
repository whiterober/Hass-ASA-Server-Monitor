src = open("/config/build_lovelace.py").read()
lines = src.split('\n')
# Show lines 85-92
for i in range(84, 92):
    print(f'{i+1}: {lines[i]}')
