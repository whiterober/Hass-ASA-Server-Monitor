with open('/config/configuration.yaml') as f:
    t = f.read()
old = 'build_lovelace: "python3 /config/build_lovelace.py"'
new = 'build_lovelace: "python3 -u /config/build_lovelace.py"'
t = t.replace(old, new)
with open('/config/configuration.yaml', 'w') as f:
    f.write(t)
print('done')
