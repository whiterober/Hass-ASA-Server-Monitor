c=open("/config/www/preview_tab.html").read()
css=c[c.find("<style>")+7:c.find("</style>")]
print("braces:", css.count("{"), css.count("}"))
print("{0} in css:", css.count("{0}"))
print("30px:", css.count("30px"))
