src=open(r'b:\项目\Hass ASA Server Monitor\bak\baseline_20260729_155105\build_lovelace.py',encoding='utf-8').read()
total=src.count('{0}')
print(f'Total {{0}}: {total}')
idx=0
for i in range(min(total,10)):
    idx=src.find('{0}',idx)
    if idx<0:break
    ln=src[:idx].count('\n')+1
    print(f'  L{ln}: ...{src[max(0,idx-30):idx+30]}...')
    idx+=1
