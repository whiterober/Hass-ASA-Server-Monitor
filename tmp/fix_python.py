import paramiko

h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Pull and fix build_lovelace.py
sftp = c.open_sftp()
sftp.get('/config/build_lovelace.py', r'b:\项目\Hass ASA Server Monitor\tmp\build_lovelace.py')
sftp.get('/config/preview_server.py', r'b:\项目\Hass ASA Server Monitor\tmp\preview_server.py')
sftp.close()

# Read and fix
for fpath in [r'b:\项目\Hass ASA Server Monitor\tmp\build_lovelace.py', r'b:\项目\Hass ASA Server Monitor\tmp\preview_server.py']:
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    fname = fpath.split('\\')[-1]
    
    # Find ALL device_icon_url references
    cnt = content.count('device_icon_url')
    print(f"{fname}: {cnt} references to device_icon_url")
    
    if cnt > 0:
        # Show each occurrence
        import re
        for m in re.finditer(r'.{0,80}device_icon_url.{0,80}', content):
            print(f"  -> {m.group().strip()}")
        
        # Replace: row.get('device_icon_url','') -> (row.get('images',[{}])[0].get('image_url','') if row.get('images') else '')
        # But need to be more careful with different patterns
        # Pattern 1: row.get('device_icon_url','') inside f-string or concat
        content = content.replace(
            "row.get('device_icon_url','')",
            "(row.get('images',[{}])[0].get('image_url','') if row.get('images') else '')"
        )
        # Pattern 2: row.get('device_icon_url')
        content = content.replace(
            "row.get('device_icon_url')",
            "(row.get('images',[{}])[0].get('image_url','') if row.get('images') else '')"
        )
        # Also handle item-level (for base items)  
        content = content.replace(
            "item.get('device_icon_url','')",
            "(item.get('images',[{}])[0].get('image_url','') if item.get('images') else '')"
        )
        
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  FIXED. Remaining: {content.count('device_icon_url')}")

# Upload fixed files
for fpath, remote in [
    (r'b:\项目\Hass ASA Server Monitor\tmp\build_lovelace.py', '/config/build_lovelace.py'),
    (r'b:\项目\Hass ASA Server Monitor\tmp\preview_server.py', '/config/preview_server.py'),
]:
    sftp = c.open_sftp()
    sftp.put(fpath, remote)
    sftp.close()
    print(f"Uploaded: {remote}")

# Also check bin files
sin,sout,serr=c.exec_command("grep -rl 'device_icon_url' /config/ 2>/dev/null | head -10",timeout=10)
print("\n=== Other files with device_icon_url on server ===")
print(sout.read().decode() or "(none)")

c.close()
print("\nDONE")
