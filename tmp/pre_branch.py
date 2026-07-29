import sys
sys.path.insert(0, '/config')
src = open('/config/preview_server.py').read()
lines = src.split('\n')
# Show lines 220-280
for i in range(219, 280):
    print(f'{i+1}: {lines[i][:150]}')
