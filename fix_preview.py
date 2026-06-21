import re
with open(r'B:\项目\Hass ASA Server Monitor\preview_server_fixed.py','r',encoding='utf-8') as f:
    content=f.read()

# Fix border style
old='border:1px solid var(--divider-color)!important;margin-bottom:8px!important;padding:12px!important;display:flex!important;gap:12px!important;background:var(--primary-background-color)!important}'
new='border-left:4px solid var(--divider-color)!important;margin-bottom:8px!important;padding:12px!important;display:flex!important;gap:12px!important;background:var(--primary-background-color)!important}'
content=content.replace(old,new)

# Remove .off rule
content=content.replace("ha-card .supply-card .sc-body .sc-srv.off{opacity:.35!important}",'')

# Add per-server map colors after the img rule
img_rule="ha-card .supply-card .sc-body .sc-srv img{width:20px!important;height:20px!important;object-fit:contain!important;border-radius:2px!important}'"
map_colors="""
            css += 'ha-card .supply-card .sc-srv[data-map=Isl]{color:#4CAF50!important}'
            css += 'ha-card .supply-card .sc-srv[data-map=Sco]{color:#FF5722!important}'
            css += 'ha-card .supply-card .sc-srv[data-map=Cen]{color:#009688!important}'
            css += 'ha-card .supply-card .sc-srv[data-map=Abe]{color:#9C27B0!important}'
            css += 'ha-card .supply-card .sc-srv[data-map=Ext]{color:#00BCD4!important}'"""
content=content.replace(img_rule, img_rule+map_colors)

with open(r'B:\项目\Hass ASA Server Monitor\preview_server_fixed.py','w',encoding='utf-8') as f:
    f.write(content)

import py_compile
py_compile.compile(r'B:\项目\Hass ASA Server Monitor\preview_server_fixed.py', doraise=True)
print('OK')
