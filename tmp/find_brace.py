c=open("/config/www/preview_tab.html").read()
s=c.find("<style>")+7
css=c[s:c.find("</style>")]

# Find positions of unclosed braces
depth = 0
for i, ch in enumerate(css):
    if ch == '{':
        depth += 1
    elif ch == '}':
        depth -= 1
    if depth > 10:  # unusually deep nesting
        # Show context
        start = max(0, i-100)
        print(f"Depth {depth} at offset {i}:")
        print(css[start:i+100])
        print("---")
        if depth > 15:
            break

# Show last few rules before the first depth mismatch
print(f"\nFinal depth: {depth}")
# Find where depth stays positive and increases
