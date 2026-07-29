c=open("/config/www/preview_tab.html").read()
s=c.find("<style>")
e=c.find("</style>")
css=c[s+7:e]
# Check for unclosed braces
import re
# Find all view-specific CSS blocks (content sections, not style tags)
# The CSS is one long compressed string. Check around position 97000
print("CSS around offset 97000-97500:")
print(css[97000:97500])
