import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Update function signature
c = c.replace(
    'function openIconPicker(si, bi, ri) {',
    'function openIconPicker(si, bi, ri, ci, ii) {'
)
print('Sig fixed')

# 2. Update: selectDeviceIconFromEl(this,si,bi,ri) → selectDeviceIconFromEl(this,si,bi,ri,(ci||0),(ii||0))
c = c.replace(
    "selectDeviceIconFromEl(this,'+si+','+bi+','+ri+')",
    "selectDeviceIconFromEl(this,'+si+','+bi+','+ri+','+(ci||0)+','+(ii||0)+')"
)
print('Call fixed:', c.count('+(ci||0)'))

with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'w', encoding='utf-8') as f:
    f.write(c)
print('Done')
