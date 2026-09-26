import paramiko,time
h="whiterober.mycloudnas.com";p=25322;u="root";pw="1219Wu1219@"
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Search /config/ for ha-font-size-m or paper-font-body1
targets = ['ha-font-size-m','paper-font-body1_-_font-size','ha-font-size','paper-font-body']
for target in targets:
    print(f"\n=== Searching: {target} ===")
    sin,sout,serr=c.exec_command(f"grep -rn '{target}' /config/ 2>/dev/null | grep -v '.db' | grep -v 'home-assistant.log' | grep -v '__pycache__' | head -20")
    time.sleep(2)
    out=sout.read().decode(errors='replace')
    err=serr.read().decode(errors='replace')
    if out.strip(): print(out[:2000])
    else: print("  (not found in /config/)")

# Search HA container for these
print("\n=== Searching HA source ===")
sin2,sout2,serr2=c.exec_command("find /usr/src/homeassistant -name '*.py' -exec grep -l 'ha-font-size-m\|paper-font-body1' {} \\; 2>/dev/null | head -10")
time.sleep(3)
out2=sout2.read().decode(errors='replace')
if out2.strip(): print(out2[:2000])
else: print("  (not found in HA source)")

# Search HA frontend JS files
print("\n=== Searching HA frontend JS ===")
sin3,sout3,serr3=c.exec_command("find /usr/src/homeassistant -name '*.js' -exec grep -l 'ha-font-size-m\|paper-font' {} \\; 2>/dev/null | head -10")
time.sleep(3)
out3=sout3.read().decode(errors='replace')
if out3.strip(): print(out3[:2000])
else: print("  (not found)")

# Check in frontend_latest directory
print("\n=== Checking frontend_latest ===")
sin4,sout4,serr4=c.exec_command("ls /config/frontend_latest/ 2>/dev/null || ls /config/.storage/frontend* 2>/dev/null")
time.sleep(1)
out4=sout4.read().decode(errors='replace')
print(out4[:500] if out4.strip() else "  (no frontend dir)")

c.close()
