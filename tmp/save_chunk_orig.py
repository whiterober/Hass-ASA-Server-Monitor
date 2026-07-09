import sys,base64,os
f=sys.argv[1];d=sys.argv[2]
p=os.path.join("/config/www/asa-data",f)
if not d:
  if os.path.exists(p): os.remove(p)
  sys.exit(0)
data=base64.b64decode(d)
open(p,"ab" if os.path.exists(p) else "wb").write(data)
