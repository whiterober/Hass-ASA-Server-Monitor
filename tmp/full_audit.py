import paramiko,os,re

v1337c_dir=r'c:\Users\white\.copilot\bak\asa_v1337c_20260714'

# Read v1337c baselines
with open(os.path.join(v1337c_dir,'build_lovelace.py'),'rb') as f:v1337c_bl=f.read()
with open(os.path.join(v1337c_dir,'preview_server.py'),'rb') as f:v1337c_pr=f.read()
with open(os.path.join(v1337c_dir,'asa-admin.html'),'rb') as f:v1337c_html=f.read()

# Current server files
ssh=paramiko.SSHClient();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.197.253',port=22,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
sftp=ssh.open_sftp()
with sftp.open('/config/build_lovelace.py','r') as f:cur_bl=f.read()
with sftp.open('/config/preview_server.py','r') as f:cur_pr=f.read()
sftp.close()

# Current local HTML
with open(r'b:\项目\Hass ASA Server Monitor\www\asa-admin.html','rb') as f:cur_html=f.read()

# Helper
def audit(name,old,cur):
    old_s=old.decode(errors='replace').replace('\r\n','\n')
    cur_s=cur.decode(errors='replace').replace('\r\n','\n')
    print('\n=== {} ==='.format(name))
    print('  v1337c: {:,} chars, {:,} lines'.format(len(old_s),len(old_s.split('\n'))))
    print('  NOW:    {:,} chars, {:,} lines'.format(len(cur_s),len(cur_s.split('\n'))))
    diff=len(cur_s)-len(old_s)
    print('  Delta:  {:,} chars'.format(diff))
    
    # Critical patterns to check
    patterns={
        'build_lovelace.py':[
            'def build\\(','if __name__','_log_step','SAVED_OK',
            'asa_built_views','make_content_card','render_tab_html',
            'make_ic_css','SERVER_MAP','FIXED_STYLES_MAP',
            'CARD_CORE_CSS','TABLE_CORE_CSS','SHARED_CSS','BASE_RAW_CSS',
        ],
        'preview_server.py':[
            'from build_lovelace','make_ic_css','render_tab_html',
            'def main\\(','preview_tab','DATA_DIR',
        ],
        'asa-admin.html':[
            'EDITOR_CONFIGS','renderMixedEditor','saveEditor',
            'loadEditorData','showPreview','saveJSON',
            'applyAllChanges','incPending','WS.callService',
        ],
    }
    patterns=patterns.get(name,patterns.get(name.split('/')[-1],[]))
    if patterns:
        for pat in patterns:
            oc=len(re.findall(pat,old_s))
            cc=len(re.findall(pat,cur_s))
            mark='' if oc==cc else ' *** DIFF ***'
            if oc>0 or cc>0:
                print('  {}: v1337c={}, cur={}{}'.format(pat,oc,cc,mark))

# Audit all three
audit('build_lovelace.py',v1337c_bl,cur_bl)
audit('preview_server.py',v1337c_pr,cur_pr)
audit('asa-admin.html',v1337c_html,cur_html)

# Also verify build_lovelace can still build
print('\n=== BUILD TEST ===')
sin,sout,serr=ssh.exec_command('cd /config && python3 build_lovelace.py 2>&1 | tail -3; echo E:$?',timeout=30)
out=sout.read().decode()
print(out[-300:])

ssh.close()
