import sys
sys.path.insert(0, '/config')
src = open('/config/preview_server.py').read()
lines = src.split('\n')
for i in range(340, 410):
    print(f'{i+1}: {lines[i][:150]}')
