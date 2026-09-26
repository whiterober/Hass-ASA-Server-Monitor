import paramiko,time
h="whiterober.mycloudnas.com";p=25322;u="root";pw="1219Wu1219@"
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Search entire filesystem but exclude large dirs
for target in ['ha-font-size-m','paper-font-body1_-_font-size','ha-font-size']:
    print(f"\n=== {target} ===")
    # Exclude /proc /sys /dev /run /var/lib/docker
    sin,sout,serr=c.exec_command(
        f"grep -rn '{target}' "
        f"/config/ /usr/src/homeassistant/ /usr/local/ 2>/dev/null "
        f"--exclude-dir=__pycache__ --exclude-dir=node_modules "
        f"--exclude='*.db' --exclude='*.log' --exclude='*.pyc' "
        f"| head -20"
    )
    time.sleep(3)
    out=sout.read().decode(errors='replace')
    if out.strip():
        for line in out.strip().split('\n')[:15]:
            print(line[:200])
    else:
        print("  not found")

# Also try searching inside HA container
print("\n=== docker exec into HA ===")
sin2,sout2,serr2=c.exec_command(
    "docker exec homeassistant grep -rn 'ha-font-size-m\\|paper-font-body1' "
    "/usr/src/homeassistant/homeassistant/ 2>/dev/null | head -10 || "
    "echo 'docker not accessible'"
)
time.sleep(3)
out2=sout2.read().decode(errors='replace')
print(out2[:1000] if out2.strip() else "  docker not reachable")

c.close()
