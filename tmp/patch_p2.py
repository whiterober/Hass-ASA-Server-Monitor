import requests

bl = requests.get('https://raw.githubusercontent.com/whiterober/Hass-ASA-Server-Monitor/master/build_lovelace.py', timeout=10).text

# Progress log function
log_fn = "\nimport time\ndef _log(s):\n open('/config/www/asa-data/_bl_progress.txt','a').write(time.strftime('%H:%M:%S.%f')[:-3]+' '+s+'\\n')\n"

# Add _log at key milestones
markers = [
    ("def esc(s):", "_log('A_esc_def')"),
    ("DATA_DIR = _SERVER_DATA", "_log('B_DATA_DIR_set')"),  
    ("SERVER_MAP = {", "_log('C_SERVER_MAP_start')"),
    ("def _render_mdi_inline", "_log('D_mdi_func')"),
    ("def _server_rules_sections", "_log('E_sr_sections_func')"),
    ("def _render_tab", "_log('F_render_tab_func')"),
    ("def _render_base", "_log('G_render_base_func')"),
    ("def html_page", "_log('H_html_page_func')"),
    ("def main():", "_log('I_main_enter')"),
    ("server_data = json.load(f)", "_log('J_server_loaded')"),
    ("tribe_data = json.load(f)", "_log('K_tribe_loaded')"),
    ("base_data = json.load(f)", "_log('L_base_loaded')"),
    ("print('Server rules: REBUILT", "_log('M_sr_done')"),
    ("print('info_whiterober: REBUILT", "_log('N_info_done')"),
    ("print('Base views: REBUILT", "_log('O_base_done')"),
    ("print(f'\\nSaved: {len(raw)} bytes", "_log('Z_SAVED')"),
]

# Inject _log function (before first function def)
bl = bl.replace("def esc(s):", log_fn + "def esc(s):", 1)
bl = bl.replace("def esc(s):", "_log('A0_esc_def')\ndef esc(s):", 1)

for pattern, marker in markers:
    old = pattern
    new = marker + "\n" + pattern
    bl = bl.replace(old, new, 1)

open(r'B:\项目\Hass ASA Server Monitor\tmp\bl_progress2.py','w',encoding='utf-8').write(bl)
print('done:', len(bl))
