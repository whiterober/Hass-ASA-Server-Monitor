with open('preview_server.py','r',encoding='utf-8') as f:
    content=f.read()

# Remove old filter-bar button + filter-card CSS lines
old_lines = [
    "css += 'ha-card .filter-bar button{padding:4px 12px!important;border-radius:16px!important;border:1px solid var(--divider-color)!important;background:var(--primary-background-color)!important;color:var(--secondary-text-color)!important;font-size:.85em!important;cursor:pointer!important}'",
    "css += 'ha-card .filter-bar button.active{background:var(--accent-color,#4fc3f7)!important;color:#000!important;border-color:var(--accent-color,#4fc3f7)!important}'",
    "css += 'ha-card .filter-card{display:none!important}ha-card .filter-card.show{display:flex!important}'",
]
for old in old_lines:
    if old in content:
        content = content.replace(old + '\n', '')
        print('Removed:', old[:60])

# Add new radio CSS after the filter-bar display CSS
insert_after = "css += 'ha-card .filter-bar{display:flex!important;flex-wrap:wrap!important;gap:6px!important;margin-bottom:12px!important}'"
new_css = """css += 'ha-card .filter-radio{position:absolute!important;opacity:0!important;pointer-events:none!important}'
css += 'ha-card .filter-label{padding:4px 12px!important;border-radius:16px!important;border:1px solid var(--divider-color)!important;background:var(--primary-background-color)!important;color:var(--secondary-text-color)!important;font-size:.85em!important;cursor:pointer!important}'
css += 'ha-card .filter-radio:checked+.filter-label{background:var(--accent-color,#4fc3f7)!important;color:#000!important;border-color:var(--accent-color,#4fc3f7)!important}'
css += 'ha-card .filter-radio[value=\"\"]:checked~.filterable{display:flex!important}'
css += 'ha-card .filter-radio#mf-isl:checked~.filterable{display:none!important}'
css += 'ha-card .filter-radio#mf-isl:checked~.filterable[data-filter-maps*=Isl]{display:flex!important}'
css += 'ha-card .filter-radio#mf-sco:checked~.filterable{display:none!important}'
css += 'ha-card .filter-radio#mf-sco:checked~.filterable[data-filter-maps*=Sco]{display:flex!important}'
css += 'ha-card .filter-radio#mf-cen:checked~.filterable{display:none!important}'
css += 'ha-card .filter-radio#mf-cen:checked~.filterable[data-filter-maps*=Cen]{display:flex!important}'
css += 'ha-card .filter-radio#mf-abe:checked~.filterable{display:none!important}'
css += 'ha-card .filter-radio#mf-abe:checked~.filterable[data-filter-maps*=Abe]{display:flex!important}'
css += 'ha-card .filter-radio#mf-ext:checked~.filterable{display:none!important}'
css += 'ha-card .filter-radio#mf-ext:checked~.filterable[data-filter-maps*=Ext]{display:flex!important}'"""
if insert_after in content:
    content = content.replace(insert_after, insert_after + '\n' + new_css)
    print('Added radio CSS')

with open('preview_server.py','w',encoding='utf-8') as f:
    f.write(content)

import py_compile
py_compile.compile('preview_server.py', doraise=True)
print('COMPILES OK')
