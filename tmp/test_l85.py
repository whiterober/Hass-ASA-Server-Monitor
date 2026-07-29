sid = "Isl"
r, g, b = 76, 175, 80
# Test line 85 pattern EXACTLY
s = 'ha-card .ic-text.ic-block-{0} .ic-qty{{position:absolute!important;right:0!important;bottom:0!important;color:var(--primary-background-color)!important;font-size:0.8em!important;padding:1px 5px!important;border-radius:4px 0 0 0!important;-webkit-text-stroke:2px rgb('+str(r)+','+str(g)+','+str(b)+')!important;paint-order:stroke fill!important}}'.format(sid)
print("Has {0}:", '{0}' in s)
print("Output:", s[:200])
