with open('/config/configuration.yaml') as f:
    t = f.read()
old = 'python3 /config/build_lovelace.py; echo $? > /config/www/asa-data/_bl_result.txt'
new = 'python3 /config/build_lovelace.py && echo 0 > /config/www/asa-data/_bl_result.txt || echo 1 > /config/www/asa-data/_bl_result.txt'
t = t.replace(old, new)
with open('/config/configuration.yaml', 'w') as f:
    f.write(t)
print('ok')
