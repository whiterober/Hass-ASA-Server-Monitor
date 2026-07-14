# Fix images:[] -> images:[{}]
c = open(r'b:\项目\Hass ASA Server Monitor\tmp\migrate_base.py', encoding='utf-8').read()
c = c.replace('"images": [],', '"images": [{}],')
open(r'b:\项目\Hass ASA Server Monitor\tmp\migrate_base.py', 'w', encoding='utf-8').write(c)
print('Fixed')

# Re-run migration
exec(compile(open(r'b:\项目\Hass ASA Server Monitor\tmp\migrate_base.py', encoding='utf-8').read(), 'migrate_base.py', 'exec'))
