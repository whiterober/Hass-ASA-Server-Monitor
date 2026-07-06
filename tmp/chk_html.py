import paramiko
h='192.168.197.253';p=22;u='root';pw='1219Wu1219@'
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(h,port=p,username=u,password=pw,look_for_keys=False,allow_agent=False)

# Check what the generated HTML looks like for base table
sin,sout,serr=c.exec_command("grep -A2 'device-icon-wrapper' /config/www/preview_tab.html | head -20",timeout=10)
print("device-icon-wrapper context:", sout.read().decode())

# Check if the HTML uses the new image_url reading
sin,sout,serr=c.exec_command("grep 'images' /config/www/preview_tab.html | head -5",timeout=10)
print("\nimages references:", sout.read().decode() or "(none)")

# Check the base table section
sin,sout,serr=c.exec_command("grep -c 'Cryofridge\|Cloth_Boots' /config/www/preview_tab.html",timeout=10)
print("\nImage URLs in HTML:", sout.read().decode())

c.close()
