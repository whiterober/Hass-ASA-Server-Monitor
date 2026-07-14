import paramiko, os

h='192.168.197.253'
local_json = r'B:\项目\Hass ASA Server Monitor\tmp\asa_base_quick_ref_new.json'
remote_json = '/config/www/asa-data/asa_base_quick_ref.json'

# Backup server JSON
c=paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
c.exec_command(f'cp {remote_json} {remote_json}.pre_phase2')
print('Server backup: OK')

# Upload new JSON
t=paramiko.Transport((h,22))
t.connect(username='root',password='1219Wu1219@')
s=paramiko.SFTPClient.from_transport(t)
s.put(local_json, remote_json)
s.close();t.close()
print(f'Upload: OK ({os.path.getsize(local_json)}B)')

# Update preview_server.py base_quick_ref handling
# Read preview_server.py
_,out,_ = c.exec_command('cat /config/preview_server.py', timeout=10)
ps = out.read().decode('utf-8')

# Change: make base_quick_ref tabs also use render_tab_html for mixed_content
# The current code at the base_quick_ref section needs to handle mixed_content type
old_ps = """    # Handle base_quick_ref format (servers) vs standard format (tabs)
    if source == 'base_quick_ref':
        # tab_name format: "server_id:tab_index" e.g. "Isl:0"
        parts = tab_name.split(':', 1)
        server_id = parts[0] if len(parts) > 0 else 'Isl'
        tab_idx = int(parts[1]) if len(parts) > 1 else 0
        servers = data.get('servers', {})
        server = servers.get(server_id, {})
        server_tabs = server.get('tabs', [])
        tab = server_tabs[tab_idx] if tab_idx < len(server_tabs) else None
        if not tab:
            print(f"ERROR: server '{server_id}' tab {tab_idx} not found")
            sys.exit(1)"""

new_ps = """    # Handle base_quick_ref format: now uses tabs array like tribe_ops/server_rules
    if source == 'base_quick_ref':
        tabs = data.get('tabs', [])
        if not tabs:
            print("ERROR: no tabs in base_quick_ref")
            sys.exit(1)
        # tab_name can be name or index
        tab = None
        try:
            idx = int(tab_name) if tab_name else 0
            tab = tabs[idx] if idx < len(tabs) else None
        except:
            for t in tabs:
                if t.get('name') == tab_name:
                    tab = t; break
        if not tab:
            tab = tabs[0]
        server_id = 'Isl'  # default"""

assert old_ps in ps, 'OLD preview base_quick_ref code not found!'
ps = ps.replace(old_ps, new_ps)

# Write back
_,out,_ = c.exec_command('cat > /config/preview_server.py', timeout=10)
out.read()
_.write(ps)
_.close()

print('preview_server.py: updated')
c.close()
print('Done')
