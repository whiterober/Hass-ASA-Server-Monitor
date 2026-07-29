import sys
sys.path.insert(0, '/config')
src = open('/config/preview_server.py').read()
lines = src.split('\n')

# Find the full_html % formatting
for i, line in enumerate(lines):
    if 'full_html' in line and '%' in line:
        print(f'{i+1}: {line.strip()[:200]}')
