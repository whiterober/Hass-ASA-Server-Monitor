import sys, json, io, traceback
sys.path.insert(0, '/config')

try:
    from preview_server import render_tab_html, SERVER_MAP, FIXED_STYLES_MAP, CARD_CORE_CSS, BASE_RAW_CSS, SHARED_CSS
    import build_lovelace

    d = json.load(open('/config/www/asa-data/tribe_ops.json'))
    tab = d['tabs'][0]

    html_body = render_tab_html(tab)

    block_types = set()
    for b in tab.get('content_blocks', []):
        bt = b.get('block_type', 'text')
        block_types.add(bt)
        if bt == 'info_card':
            for d in b.get('descriptions', []):
                block_types.add(d.get('type', 'desc_row'))

    css = CARD_CORE_CSS + BASE_RAW_CSS
    if 'info_card' in block_types:
        IC_CSS = build_lovelace.make_ic_css(SERVER_MAP, FIXED_STYLES_MAP)
        css += IC_CSS
        print("CSS added:", len(IC_CSS))
    else:
        print("INFO_CARD not in block_types:", block_types)

    print("CSS len:", len(css))
    print("ic-block-img:", "ic-block-img" in css)
    print("30px:", "30px" in css)
except Exception as e:
    print("ERROR:", e)
    traceback.print_exc()
