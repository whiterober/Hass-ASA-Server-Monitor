lines = open("/config/build_lovelace.py").read().split('\n')
for i, l in enumerate(lines):
    if '{0}' in l and 'IC_CSS' in l:
        # Show last 80 chars
        end = l.rstrip()[-80:]
        print(f"L{i+1}: ...{end}")
