import sys
sys.path.insert(0, '/config')
src = open('/config/preview_server.py').read()
lines = src.split('\n')

# Show lines 315-340 to see the <style> tag template
for i in range(314, 340):
    print(f'{i+1}: {lines[i][:150]}')
