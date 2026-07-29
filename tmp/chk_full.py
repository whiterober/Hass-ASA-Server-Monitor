import sys
sys.path.insert(0, '/config')
src = open('/config/preview_server.py').read()
lines = src.split('\n')

# Find all lines with full_html
for i, line in enumerate(lines):
    if 'full_html' in line:
        print(f'{i+1}: {line.strip()[:200]}')
