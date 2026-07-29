c=open("/config/www/preview_tab.html").read()
s=c.find("<style>")+7
css=c[s:c.find("</style>")]

# Find where depth first exceeds 1 and where it's last 0
depth = 0
last_zero = 0
rules_started = []
for i, ch in enumerate(css):
    if ch == '{':
        if depth == 0:
            rules_started.append(i)
        depth += 1
    elif ch == '}':
        depth -= 1
        if depth == 0:
            last_zero = i

# Show the rules around where depth stops returning to 0
print(f"Last offset where depth=0: {last_zero}")
print(f"Total rules started after last_zero:")
for rs in rules_started:
    if rs > last_zero:
        print(f"  Rule at {rs}: {css[rs:rs+80]}...")

# Show the unclosed rules
depth = 0
for i, ch in enumerate(css):
    if ch == '{':
        if depth == 0:
            rule_start = i
        depth += 1
    elif ch == '}':
        depth -= 1
    if i > last_zero and ch == '{' and depth == 1:
        # This is a new unclosed rule
        print(f"\nUnclosed rule at {i}:")
        print(css[i-50:i+200])
