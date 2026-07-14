import paramiko,re,os

print('=== 1. asa-admin.html audit ===')
html=open(r'b:\项目\Hass ASA Server Monitor\www\asa-admin.html',encoding='utf-8').read()
print('Size: {:,} bytes'.format(len(html)))

# Search for potential dead code patterns
patterns={
    'old_base_funcs':['saveBaseTab','copyBRFrom','addBRTab','deleteBRTab','renderBaseRef_old','loadBaseRef_old'],
    'dead_wrappers':['loadServerRules','loadTribeOps','saveTOTab','saveTabToMemory'],
    'combo_desc_old':['saveComboDesc_old','renderCombo_old'],
    'TODO/FIXME':[r'TODO',r'FIXME',r'HACK'],
    'console.log':['console.log'],
    'debugger':['debugger'],
}
for cat,pats in patterns.items():
    found=[]
    for pat in pats:
        n=len(re.findall(pat,html))
        if n>0:found.append('{}:{}'.format(pat,n))
    if found:print('  {}: {}'.format(cat,', '.join(found)))

# Search for unused functions (declared but not called - rough check)
print()

print('=== 2. build_lovelace.py audit ===')
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
sftp=ssh.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:bl=f.read().decode()
sftp.close()
print('Size: {:,} bytes ({:,} chars)'.format(len(bl.encode()),len(bl)))
bl_n=bl.replace('\r\n','\n')

# Check for unused CSS constants
css_consts=['SERVER_GRID_CSS','EXPANDABLE_DETAIL_CSS','FARMING_TABLE_CSS','SHARED_CSS',
            'BASE_RAW_CSS','TABLE_CORE_CSS','CARD_CORE_CSS']
for cc in css_consts:
    n=bl_n.count(cc)
    if n>0:print('  {}: {} refs'.format(cc,n))

# Check for dead functions
funcs=['render_server_grid','render_expandable_detail','render_farming_table',
       '_lookup_style','strip_and_append_empty_rows','make_ic_css','render_tab_html']
for fn in funcs:
    defs=len(re.findall(r'def '+fn+r'\b',bl_n))
    calls=len(re.findall(fn+r'\b',bl_n))-defs
    if defs>0:print('  def {}: {} defs, {} calls'.format(fn,defs,calls))

# Check imports
imp=re.search(r'^import .*|^from .*import',bl_n,re.MULTILINE)
print('  Imports at top:')
for m in re.finditer(r'^(import .*|from .*import)',bl_n,re.MULTILINE):
    print('    '+m.group().strip()[:80])

print('\n=== 3. preview_server.py audit ===')
with sftp.open('/config/preview_server.py','r') as f:pr=f.read().decode()
ssh.close()
print('Size: {:,} bytes ({:,} chars)'.format(len(pr.encode()),len(pr)))
pr_n=pr.replace('\r\n','\n')

# Check imports from build_lovelace
imp_block=re.search(r'from build_lovelace import \((.*?)\)',pr_n,re.DOTALL)
if imp_block:
    imported=[x.strip() for x in imp_block.group(1).split(',') if x.strip()]
    print('  Imports from build_lovelace:')
    for name in imported:
        used=pr_n.count(name)
        # Count usage (minus 1 for import line)
        usage=max(0,used-1)
        print('    {}: used {} times'.format(name,usage))
