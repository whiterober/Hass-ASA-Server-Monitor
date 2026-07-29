c=open("/config/www/preview_tab.html").read()
s=c.find("<style>")+7
css=c[s:c.find("</style>")]
print(f"Braces: {{ {css.count('{')} }} {css.count('}')} diff={css.count('{')-css.count('}')}")
print(f"{{0}}: {css.count('{0}')}")
print(f"ic-block-img: {css.count('ic-block-img')}")
print(f"30px: {css.count('30px')}")
