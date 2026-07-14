"""Safe dead code cleanup for build_lovelace.py - uses exact string replacement, no line numbers."""
import paramiko, os

h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

sftp=c.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:content=f.read().decode()
sftp.close()

original=content
replacements=[]

# ===== 1. Main dispatch: remove server_grid/expandable_detail/farming_table =====
# These are 3 dead elifs at the end of the dispatch chain
old = """            if ttype == 'server_grid':
                t_html = render_server_grid(t)
            elif ttype == 'expandable_detail':
                t_html = render_expandable_detail(t)
            elif ttype == 'farming_table':
                t_html = render_farming_table(t)
            else:"""
new = """            else:"""
replacements.append(('main_dispatch', old, new))

# ===== 2. IC_CSS tab_type checks =====
old = """            elif tab_type == 'server_grid':
                css = SERVER_GRID_CSS
            elif tab_type == 'expandable_detail':
                css += EXPANDABLE_DETAIL_CSS.replace(SHARED_CSS, '')
            elif tab_type == 'farming_table':
                css += TABLE_CORE_CSS"""
new = ""
replacements.append(('ic_css_tab_type', old, new))

# ===== 3. IC_CSS block_types conditions =====
old = """            if 'server_grid' in block_types:
                css = SERVER_GRID_CSS  # includes SHARED_CSS
            if 'expandable_detail' in block_types:
                css += EXPANDABLE_DETAIL_CSS.replace(SHARED_CSS, '')
            if 'supply_card' in block_types or 'map_filter' in block_types:"""
new = """            if 'map_filter' in block_types:"""
replacements.append(('ic_css_block_types', old, new))

# ===== 4. IC_CSS bbt handlers (supply_card + expandable_detail) =====
old = """                    elif bbt == 'supply_card':
                        fm = blk.get('filter_maps','')
                        if fm: active_maps.update(fm.split(','))
                    elif bbt == 'expandable_detail':
                        fm = blk.get('filter_maps','')
                        if fm: active_maps.update(fm.split(','))"""
new = ""
replacements.append(('ic_css_bbt', old, new))

# ===== 5. bt handlers (block-level rendering) =====
old = """            elif bt=='supply_card':
                parts.append('<div class="supply-card">')
                parts.append('<img class="sc-icon" src="'+esc(b.get('icon_url',''))+'" alt="'+esc(b.get('title',''))+'" />')
                parts.append('<div class="sc-body">')
                parts.append('<div class="sc-title">'+esc(b.get('title',''))+'</div>')
                parts.append('<div class="sc-servers">')
                for srv in b.get('servers',[]):
                    sm=SERVER_MAP.get(srv,{})
                    parts.append('<span class="sc-srv" data-map="'+srv+'"><img src="'+esc(sm.get('icon',''))+'" />'+esc(sm.get('name',srv))+'</span>')
                parts.append('</div></div></div>')"""
new = ""
replacements.append(('bt_supply_card', old, new))

old = """            elif bt=='server_grid':
                # Render a server_grid block
                parts.append(render_server_grid_block(b))"""
new = ""
replacements.append(('bt_server_grid', old, new))

old = """            elif bt=='card_grid':
                # Render cards in a grid
                cards=b.get('cards',[])
                parts.append('<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px">')
                for card in cards:
                    parts.append('<div class="supply-card">')
                    parts.append('<img class="sc-icon" src="'+esc(card.get('icon_url',''))+'" />')
                    parts.append('<div class="sc-body"><div class="sc-title">'+esc(card.get('title',''))+'</div>')
                    parts.append('<div class="sc-servers">')
                    for srv in card.get('servers',[]):
                        sm=SERVER_MAP.get(srv,{})
                        parts.append('<span class="sc-srv" data-map="'+srv+'"><img src="'+esc(sm.get('icon',''))+'" />'+esc(sm.get('name',srv))+'</span>')
                    parts.append('</div></div></div>')
                parts.append('</div>')"""
new = ""
replacements.append(('bt_card_grid', old, new))

old = """            elif bt=='expandable_detail':
                # Render expandable detail blocks
                blks=b.get('blocks',[])
                for blk in blks:
                    parts.append('<details class="exp-detail"')
                    if blk.get('open'): parts.append(' open')
                    parts.append('>')
                    title=blk.get('title','')
                    parts.append('<summary><span class="exp-title">'+esc(title)+'</span></summary>')
                    parts.append('<div class="exp-body">')
                    for item in blk.get('items',[]):
                        if item.get('type')=='text':
                            parts.append('<p>'+esc(item.get('text',''))+'</p>')
                        elif item.get('type')=='ol':
                            parts.append('<ol>')
                            for step in item.get('steps',[]):
                                parts.append('<li>'+esc(str(step))+'</li>')
                            parts.append('</ol>')
                    parts.append('</div></details>')"""
new = ""
replacements.append(('bt_expandable_detail', old, new))

# ===== 6. bbt handlers (in render_tab_html or wherever) =====
old = """            elif bbt=='supply_card':
                # Supply card block
                icon=b.get('icon_url','')
                title=b.get('title','')
                servers=b.get('servers',[])
                parts.append('<div class="supply-card filterable"')
                if b.get('filter_maps'): parts.append(' data-filter-maps="'+b['filter_maps']+'"')
                parts.append('>')
                if icon: parts.append('<img class="sc-icon" src="'+esc(icon)+'" />')
                parts.append('<div class="sc-body"><div class="sc-title">'+esc(title)+'</div>')
                parts.append('<div class="sc-servers">')
                for srv in servers:
                    sm=SERVER_MAP.get(srv,{})
                    parts.append('<span class="sc-srv" data-map="'+srv+'"><img src="'+esc(sm.get('icon',''))+'" />'+esc(sm.get('name',srv))+'</span>')
                parts.append('</div></div></div>')"""
new = ""
replacements.append(('bbt_supply_card', old, new))

old = """            elif bbt=='expandable_detail':
                # Expandable detail block
                title=b.get('title','')
                blks=b.get('blocks',[])
                parts.append('<details class="exp-detail filterable"')
                if b.get('filter_maps'): parts.append(' data-filter-maps="'+b['filter_maps']+'"')
                if b.get('open'): parts.append(' open')
                parts.append('><summary><span class="exp-title">'+esc(title)+'</span></summary>')
                parts.append('<div class="exp-body">')
                for blk in blks:
                    bt_t=blk.get('type','')
                    if bt_t=='text':
                        parts.append('<p style="margin:4px 0">'+esc(blk.get('text',''))+'</p>')
                    elif bt_t=='ol':
                        parts.append('<ol>')
                        for step in blk.get('steps',[]):
                            if isinstance(step,dict) and 'html' in step:
                                parts.append('<li>'+step['html']+'</li>')
                            else:
                                parts.append('<li>'+esc(str(step))+'</li>')
                        parts.append('</ol>')
                    elif bt_t=='md_hl':
                        parts.append('<span class="'+blk.get('class','')+'">'+blk.get('text','')+'</span>')
                    elif bt_t=='strong':
                        parts.append('<strong>'+blk.get('text','')+'</strong>')
                parts.append('</div></details>')"""
new = ""
replacements.append(('bbt_expandable_detail', old, new))

# ===== 7. Render functions =====
# Need to read exact function bodies from server
# Let's do these last since they're large

# Apply all replacements
ok=0;fail=0
for name,old_str,new_str in replacements:
    count=content.count(old_str)
    if count==0:
        print(f'SKIP {name}: not found (may already be cleaned)')
        continue
    if count>1:
        print(f'SKIP {name}: found {count} times (not unique)')
        continue
    content=content.replace(old_str,new_str)
    ok+=1
    print(f'OK {name}')

print(f'\nApplied: {ok}, Skipped: {fail}')
print(f'Chars: {len(original)} -> {len(content)} (diff: {len(content)-len(original)})')

# Verify syntax
sftp=c.open_sftp()
with sftp.open('/tmp/_clean_bl.py','w') as f:f.write(content)
sftp.close()

sin,sout,serr=c.exec_command('python3 -m py_compile /tmp/_clean_bl.py 2>&1 && echo SYNTAX_OK || echo SYNTAX_FAIL',timeout=10)
result=sout.read().decode().strip()
print('\nSyntax check:', result)

if 'SYNTAX_OK' in result:
    # Backup original
    sftp=c.open_sftp()
    with sftp.open('/config/build_lovelace.py.bak3','w') as f:f.write(original)
    # Upload new
    with sftp.open('/config/build_lovelace.py','w') as f:f.write(content)
    sftp.close()
    print('Uploaded! Backup saved as .bak3')
    
    # Test preview
    sin,sout,serr=c.exec_command('python3 /config/preview_server.py "0" base_quick_ref 2>/dev/null',timeout=10)
    out=sout.read().decode().strip()
    if 'written' in out.lower():
        print('Preview OK:', out[:100])
    else:
        print('Preview:', out[:200])
else:
    err=serr.read().decode().strip()
    print('SYNTAX ERROR:', err[:300] if err else result)

c.close()
