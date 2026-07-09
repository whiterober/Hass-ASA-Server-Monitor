with open('/config/configuration.yaml') as f:
    t = f.read()
t = t.replace('build_lovelace: "python3 /config/_run_bl.py"', 'build_lovelace: "python3 /config/build_lovelace.py"')
with open('/config/configuration.yaml', 'w') as f:
    f.write(t)
print('fixed')
