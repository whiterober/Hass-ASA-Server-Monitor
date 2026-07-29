c=open("/config/www/preview_tab.html").read()
s=c.find("<style>")+7
css=c[s:c.find("</style>")]
# The base rule was at html offset 97241, css offset = 97241-s
css_off = 97241 - s
print("CSS around base .ic-block-img:")
print(css[max(0,css_off-200):css_off+200])
# Check for CSS syntax: count braces
opens = css.count('{')
closes = css.count('}')
print(f"\nBraces: {{ {opens} }} {closes} difference: {opens-closes}")
