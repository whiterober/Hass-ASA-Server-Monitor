lines = open("/config/build_lovelace.py").read().split('\n')
# Show the ig-title lines
for i in [86, 87, 88, 102, 103, 104]:
    print(f'{i+1}: {lines[i][:150]}')
