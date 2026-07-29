c=open("/config/www/preview_tab.html").read()
css=c[c.find("<style>")+7:c.find("</style>")]
print("braces:", css.count("{"), css.count("}"))
print("{0}:", css.count("{0}"))
print("ic-block-img:", "ic-block-img" in css)
print("30px:", "30px" in css)
