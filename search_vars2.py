import paramiko,time
h="whiterober.mycloudnas.com";p=25322;u="root";pw="1219Wu1219@"
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Fast grep on key paths
for target in ['ha-font-size-m','paper-font-body1']:
    print(f"\n=== {target} ===")
    sin,sout,serr=c.exec_command(f"grep -rn '{target}' /config/themes/ /config/configuration.yaml /config/.storage/ 2>/dev/null | head -10")
    time.sleep(1)
    out=sout.read().decode(errors='replace')
    if out.strip(): print(out[:1000])
    else: print("  not found in /config/")

# Check build_lovelace
print("\n=== build_lovelace paper/ha-font ===")
sin2,sout2,serr2=c.exec_command("grep -n 'paper-font\|ha-font' /config/build_lovelace.py 2>/dev/null | head -5")
out2=sout2.read().decode(errors='replace')
print(out2[:500] if out2.strip() else "  not found")

# Check HA frontend Python module for defaults
print("\n=== HA frontend component ===")
sin3,sout3,serr3=c.exec_command("grep -rn 'font.size\|FONT_SIZE\|font_size' /usr/src/homeassistant/homeassistant/components/frontend/ 2>/dev/null | head -10")
out3=sout3.read().decode(errors='replace')
print(out3[:500] if out3.strip() else "  not found")

# Check if there's a frontend_latest with defaults
print("\n=== frontend dirs ===")
sin4,sout4,serr4=c.exec_command("ls -d /config/*front* /config/.storage/*front* 2>/dev/null")
out4=sout4.read().decode(errors='replace')
print(out4[:300] if out4.strip() else "  none")

c.close()
