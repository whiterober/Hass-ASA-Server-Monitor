"""Build lovelace with embedded HTML from JSON data using tailwindcss-template-card."""
import json, os, re
from datetime import datetime

# Server: /config/www/asa-data (absolute, avoids symlink issues). Local: ./data
_SERVER_DATA = '/config/www/asa-data'
DATA_DIR = _SERVER_DATA if os.path.isdir(_SERVER_DATA) else os.path.join(os.path.dirname(__file__), 'data')

def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

def _render_mdi_inline(text, extra_class=''):
    """将文本中所有 mdi:xxx 替换为 <ha-icon>，其余文本 escape"""
    result = []
    last = 0
    for m in re.finditer(r'mdi:([\w-]+)', text, re.ASCII):
        if m.start() > last:
            result.append(esc(text[last:m.start()]))
        cls = ' class=\"{}\"'.format(extra_class) if extra_class else ''
        result.append('<ha-icon icon=\"mdi:{}\"{}></ha-icon>'.format(m.group(1), cls))
        last = m.end()
    if last < len(text):
        result.append(esc(text[last:]))
    return ''.join(result)

# Server colors — single source, shared with asa-admin.html
import json, os
_COLORS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server_colors.json')
if os.path.exists(_COLORS_JSON):
    with open(_COLORS_JSON, 'r', encoding='utf-8') as _f:
        _colors = json.load(_f)
    SERVER_MAP = _colors['servers']
    FIXED_STYLES_MAP = _colors['presets']
else:
    # Fallback (should never happen in production)
    SERVER_MAP = {}
    FIXED_STYLES_MAP = {}
def _lookup_style(key):
    return SERVER_MAP.get(key) or FIXED_STYLES_MAP.get(key) or {}

def _render_badges(text, is_block_mode=False):
    """Parse [xxx] in text as badge spans. In block mode, badges get hollow style."""
    import re
    badge_cls = 'ic-badge ic-badge-hollow' if is_block_mode else 'ic-badge'
    return re.sub(r'\[([^\]]+)\]', r'<span class="'+badge_cls+r'">\1</span>', text)

def make_ic_css(server_map, fixed_styles_map):
    """Generate info_card CSS block. Shared by build_lovelace and preview_server."""
    IC_CSS = 'ha-card .info-card-block{border-radius:12px!important;border-left:4px solid!important;margin-bottom:8px!important;padding:12px!important;display:flex!important;align-items:flex-start!important;gap:12px!important}'
    for sid, sm in server_map.items():
        IC_CSS += 'ha-card .info-card-block[data-map='+sid+']{border-color:'+sm['color']+'!important;background:transparent!important}'
    IC_CSS += 'ha-card .info-card-block .ic-icon{width:48px!important;height:48px!important;flex-shrink:0!important;object-fit:contain!important;border-radius:8px!important;background:transparent!important}'
    IC_CSS += 'ha-card .ic-icon-wrap .ic-qty{position:absolute!important;right:0!important;bottom:0!important;color:var(--primary-text-color)!important;font-size:0.8em!important;padding:1px 5px!important;border-radius:4px 0 0 0!important;-webkit-text-stroke:2px var(--primary-background-color)!important;paint-order:stroke fill!important}'
    IC_CSS += 'ha-card [data-old-webkit] .ic-icon-wrap .ic-qty{font-weight:950!important;font-family:HarmonyOS Sans SC,system-ui,Impact,sans-serif!important;-webkit-text-stroke:0.5px var(--primary-background-color)!important}'
    IC_CSS += 'ha-card .info-card-block .ic-body{flex:1!important;min-width:0!important}'
    # ic-title: flex container matching ic-text alignment
    IC_CSS += 'ha-card .info-card-block .ic-body .ic-title{font-weight:600!important;font-size:1.05em!important;margin-bottom:4px!important;display:flex!important;align-items:center!important;gap:4px!important}'
    IC_CSS += 'ha-card .info-card-block .ic-body .ic-title ha-icon{flex-shrink:0}'
    IC_CSS += 'ha-card .ic-title > span{display:inline-flex!important;align-items:center!important;gap:2px!important}'
    IC_CSS += 'ha-card .info-card-block .ic-body .ic-text{font-size:.9em!important;line-height:1.5!important;word-break:break-all!important;display:flex!important;align-items:center!important;gap:2px!important;flex-wrap:wrap!important}'
    IC_CSS += 'ha-card .info-card-block .ic-body .ic-text ha-icon,ha-card .info-card-block .ic-body .ic-text i.mdi{flex-shrink:0!important;align-self:center!important}'
    IC_CSS += 'ha-card .info-card-block .ic-sum-end{display:none}'
    IC_CSS += 'ha-card .info-card-block details[open] .ic-sum-top{display:none!important}'
    IC_CSS += 'ha-card .info-card-block details[open] .ic-sum-end{display:block!important}'
    IC_CSS += 'ha-card .info-card-block img.ic-auto-dark{filter:none}'
    IC_CSS += 'ha-card .info-card-block img.ic-auto-light{filter:none}'
    IC_CSS += '[data-theme="dark"] .info-card-block img.ic-auto-dark{filter:invert(1)}'
    IC_CSS += '[data-theme="light"] .info-card-block img.ic-auto-light{filter:invert(1)}'
    IC_CSS += 'ha-card .ic-desc-img{width:24px!important;height:24px!important;object-fit:contain!important;vertical-align:middle!important;margin:0 1px 0 1px!important;flex-shrink:0!important}'
    IC_CSS += 'ha-card .ic-qty{font-size:0.75em!important;font-weight:600!important;margin-left:0!important;flex-shrink:0!important;line-height:1!important}'
    for sid, sm in server_map.items():
        r = int(sm['color'][1:3], 16); g = int(sm['color'][3:5], 16); b = int(sm['color'][5:7], 16)
        IC_CSS += 'ha-card .ic-text.ic-block-{} .ic-qty{{background:rgba({},{},{},0)!important;-webkit-text-stroke:2px rgb({},{},{})!important;paint-order:stroke fill!important}}'.format(sid, r, g, b, r, g, b)
        IC_CSS += 'ha-card .ic-text.ic-block-'+sid+'{position:relative!important;overflow:hidden!important}'
        IC_CSS += 'ha-card .ic-text.ic-block-'+sid+' .ic-qty{position:absolute!important;right:0!important;bottom:0!important;color:var(--primary-background-color)!important;font-size:0.8em!important;padding:1px 5px!important;border-radius:4px 0 0 0!important}'
        IC_CSS += 'ha-card .ic-text.ic-block-'+sid+' .ig-item .ic-qty{padding-right:0!important}'
        IC_CSS += 'ha-card [data-old-webkit] .ic-text.ic-block-{} .ic-qty{{font-weight:950!important;font-family:HarmonyOS Sans SC,system-ui,Impact,sans-serif!important;-webkit-text-stroke:0.5px rgb({},{},{})!important}}'.format(sid, r, g, b)
    for fk, fv in fixed_styles_map.items():
        fc = fv.get('color', '#666')
        if not fc or fc == 'auto': fc = '#666666'
        r = int(fc[1:3], 16); g = int(fc[3:5], 16); b = int(fc[5:7], 16)
        IC_CSS += 'ha-card .ic-text.ic-block-{} .ic-qty{{background:rgba({},{},{},0)!important;-webkit-text-stroke:2px rgb({},{},{})!important;paint-order:stroke fill!important}}'.format(fk, r, g, b, r, g, b)
        IC_CSS += 'ha-card .ic-text.ic-block-'+fk+'{position:relative!important;overflow:hidden!important}'
        IC_CSS += 'ha-card .ic-text.ic-block-'+fk+' .ic-qty{position:absolute!important;right:0!important;bottom:0!important;color:var(--primary-background-color)!important;font-size:0.8em!important;padding:1px 5px!important;border-radius:4px 0 0 0!important}'
        IC_CSS += 'ha-card .ic-text.ic-block-'+fk+' .ig-item .ic-qty{padding-right:0!important}'
        IC_CSS += 'ha-card [data-old-webkit] .ic-text.ic-block-{} .ic-qty{{font-weight:950!important;font-family:HarmonyOS Sans SC,system-ui,Impact,sans-serif!important;-webkit-text-stroke:0.5px rgb({},{},{})!important}}'.format(fk, r, g, b)
    IC_CSS += 'ha-card .ic-text.ic-auto-block .ic-qty{-webkit-text-stroke:2px var(--primary-text-color)!important}'
    IC_CSS += 'ha-card .ic-text.ic-block-_default:not(.ic-auto-block) .ic-qty{-webkit-text-stroke:2px var(--ic-block-bg)!important}'
    IC_CSS += 'ha-card .ic-block-img{position:absolute!important;right:2px!important;top:50%!important;transform:translateY(-50%)!important;width:30px!important;height:30px!important;object-fit:contain!important;border-radius:0 4px 4px 0!important;flex-shrink:0!important}'
    IC_CSS += 'ha-card .ic-text[class*="ic-block-"]:has(.ic-block-img){padding-right:34px!important}'
    for sid, sm in server_map.items():
        r = int(sm['color'][1:3], 16); g = int(sm['color'][3:5], 16); b = int(sm['color'][5:7], 16)
        IC_CSS += 'ha-card .ic-text.ic-linear-'+sid+' .ic-badge{background:rgba('+str(r)+','+str(g)+','+str(b)+',0.15)!important;color:'+sm['color']+'!important}'
    for fk, fv in fixed_styles_map.items():
        fc = fv.get('color', '#666')
        if not fc or fc == 'auto': fc = '#666666'
        r = int(fc[1:3], 16); g = int(fc[3:5], 16); b = int(fc[5:7], 16)
        IC_CSS += 'ha-card .ic-text.ic-linear-'+fk+' .ic-badge{background:rgba('+str(r)+','+str(g)+','+str(b)+',0.15)!important;color:'+(fc if fk != '_default' else 'var(--primary-text-color)')+'!important}'
    IC_CSS += 'ha-card .ic-badge{display:inline-block!important;padding:1px 6px!important;border-radius:10px!important;font-size:0.75em!important;background:color-mix(in srgb,var(--primary-color) 25%,transparent)!important;color:var(--primary-text-color)!important;line-height:1.5!important}'
    IC_CSS += 'ha-card .ic-badge-num{border-radius:3px!important;display:inline-flex!important;justify-content:center!important;width:16px!important;white-space:nowrap!important}'
    IC_CSS += 'ha-card .ic-badge{vertical-align:middle!important}'
    IC_CSS += 'ha-card .ic-badge-num{vertical-align:middle!important}'
    IC_CSS += 'ha-card .ic-text[class*="ic-block-"] .ic-badge-hollow{background:color-mix(in srgb,var(--primary-background-color) 20%,transparent)!important;color:var(--primary-background-color)!important}'
    IC_CSS += 'ha-card .ic-text[class*="ic-block-"][class*="ic-auto-block"] .ic-badge-hollow{color:var(--primary-text-color)!important;background:color-mix(in srgb,var(--primary-text-color) 15%,transparent)!important}'
    for sid, sm in server_map.items():
        IC_CSS += 'ha-card .ic-linear-'+sid+' .mdi,ha-card .ic-linear-'+sid+' ha-icon{color:'+sm['color']+'!important}'
    for sid, sm in server_map.items():
        IC_CSS += 'ha-card .ic-text.ic-block-'+sid+'{background:'+sm['color']+'!important;border-radius:6px!important;padding:2px 6px!important;color:var(--primary-background-color)!important}'
    for sid in server_map:
        IC_CSS += 'ha-card .ic-text.ic-block-'+sid+' .mdi,ha-card .ic-text.ic-block-'+sid+' ha-icon{color:var(--primary-background-color)!important}'
    for sid, sm in server_map.items():
        r = int(sm['color'][1:3], 16); g = int(sm['color'][3:5], 16); b = int(sm['color'][5:7], 16)
        IC_CSS += 'ha-card .info-card-block.ic-block-'+sid+'{background:rgba('+str(r)+','+str(g)+','+str(b)+',0.08)!important}'
    for fk, fv in fixed_styles_map.items():
        fc = fv.get('color', '#666')
        if not fc or fc == 'auto': fc = '#666666'
        if fk == '_default':
            IC_CSS += 'ha-card .ic-linear-_default .mdi,ha-card .ic-linear-_default ha-icon{color:var(--primary-text-color)!important}'
        else:
            IC_CSS += 'ha-card .ic-linear-'+fk+' .mdi,ha-card .ic-linear-'+fk+' ha-icon{color:'+fc+'!important}'
        if fk == '_default':
            IC_CSS += 'ha-card .ic-text.ic-block-_default{background:color-mix(in srgb,var(--primary-text-color) 10%,transparent)!important;border-radius:6px!important;padding:2px 6px!important;color:var(--primary-text-color)!important}'
        else:
            IC_CSS += 'ha-card .ic-text.ic-block-'+fk+'{background:'+fc+'!important;border-radius:6px!important;padding:2px 6px!important;color:var(--primary-background-color)!important}'
        if fk == '_default':
            IC_CSS += 'ha-card .ic-text.ic-block-_default .mdi,ha-card .ic-text.ic-block-_default ha-icon{color:var(--primary-text-color)!important}'
        else:
            IC_CSS += 'ha-card .ic-text.ic-block-'+fk+' .mdi,ha-card .ic-text.ic-block-'+fk+' ha-icon{color:var(--primary-background-color)!important}'
        if fk == '_default':
            IC_CSS += 'ha-card .info-card-block.ic-block-_default{background:color-mix(in srgb,var(--primary-text-color) 5%,transparent)!important}'
        else:
            r = int(fc[1:3], 16); g = int(fc[3:5], 16); b = int(fc[5:7], 16)
            IC_CSS += 'ha-card .info-card-block.ic-block-'+fk+'{background:rgba('+str(r)+','+str(g)+','+str(b)+',0.08)!important}'
    # ig-* icon group rules (single source, shared by preview_server)
    IC_CSS += 'ha-card .ig-title-badge{display:inline-flex!important;align-items:center!important;padding:2px 6px!important;border-radius:6px!important;background:color-mix(in srgb,var(--primary-color) 15%,transparent)!important;color:var(--primary-text-color)!important;line-height:1.5!important}'
    IC_CSS += 'ha-card .ig-row-wrapper{font-size:0.9em!important}'
    IC_CSS += 'ha-card .ig-title-row ha-icon{flex-shrink:0!important;align-self:center!important}'
    IC_CSS += 'ha-card .ig-title-row > span{display:inline-flex!important;align-items:center!important}'
    IC_CSS += 'ha-card .ig-title-badge ha-icon{flex-shrink:0!important}'
    IC_CSS += 'ha-card .ig-title-line{border:none!important;margin:0!important;border-top:1px solid var(--primary-text-color)!important;opacity:0.15!important}'
    IC_CSS += 'ha-card .ig-row-wrapper::after{content:\'\'!important;display:block!important;width:100%!important;border-top:1px solid var(--primary-text-color)!important;opacity:0.15!important;margin-top:6px!important}'
    IC_CSS += 'ha-card .ig-row-wrapper[class*="ic-linear-"]::after{display:none!important}'
    IC_CSS += 'ha-card .ig-row-wrapper.ig-empty::after{display:none!important}'
    for sid, sm in server_map.items():
        r = int(sm['color'][1:3], 16); g = int(sm['color'][3:5], 16); b = int(sm['color'][5:7], 16)
        IC_CSS += 'ha-card .ig-row-wrapper.ic-linear-'+sid+' .ig-title-badge{color:'+sm['color']+'!important;background:rgba('+str(r)+','+str(g)+','+str(b)+',0.15)!important}'
        IC_CSS += 'ha-card .ig-row-wrapper.ic-linear-'+sid+' .ig-title-line{border-top-color:'+sm['color']+'!important;opacity:0.4!important}'
        IC_CSS += 'ha-card .ig-row-wrapper.ic-linear-'+sid+'::after{border-top-color:'+sm['color']+'!important;opacity:0.4!important}'
    IC_CSS += 'ha-card .ig-title-row ha-icon,ha-card .ig-title-badge ha-icon{color:inherit!important}'
    # ig-* icon image rules (migrated from old inline CSS in preview_server.py)
    IC_CSS += 'ha-card .icon-group{gap:8px!important}'
    IC_CSS += 'ha-card .ig-item{position:relative!important;display:inline-flex!important;flex-shrink:0!important}'
    IC_CSS += 'ha-card .ig-img{width:28px!important;height:28px!important;object-fit:contain!important;border-radius:4px!important}'
    IC_CSS += 'ha-card .ig-item .ic-qty{position:absolute!important;right:-2px!important;bottom:-2px!important;font-size:0.65em!important;white-space:nowrap!important;word-break:normal!important;padding-right:0!important}'
    IC_CSS += 'ha-card .ig-img.ic-auto-dark{filter:none!important}'
    IC_CSS += 'ha-card .ig-img.ic-auto-light{filter:none!important}'
    IC_CSS += '[data-theme="dark"] .ig-img.ic-auto-dark{filter:invert(1)!important}'
    IC_CSS += '[data-theme="light"] .ig-img.ic-auto-light{filter:invert(1)!important}'
    return IC_CSS


# -------------------------------------------------------
# CSS modules — composed into card-type-specific stylesheets
# -------------------------------------------------------

# Card-level rules (all card types)
CARD_CORE_CSS = """ha-card {
  box-shadow: none !important;
  padding: 0px !important;
  background: transparent !important;
  font-size: var(--paper-font-body1_-_font-size, 14px) !important;
  font-family: var(--paper-font-body1_-_font-family, 'Roboto', sans-serif) !important;
  color: var(--primary-text-color) !important;
}
ha-card h2 {
  font-family: inherit !important;
  font-weight: bold !important;
  margin: 0 0 16px 0 !important;
  color: var(--primary-text-color) !important;
  line-height: 1.3 !important;
}
ha-card img {
  flex-shrink: 0 !important;
}
ha-card .tb-divider, .tb-divider {
  border: none !important;
  margin: 12px 0 !important;
}
/* Use --div-color / --div-opacity custom props for overrides; fallback to primary-text-color */
ha-card .tb-div-solid, .tb-div-solid {
  border-top: 1px solid var(--div-color, var(--primary-text-color)) !important;
  opacity: var(--div-opacity, 0.15) !important;
}
ha-card .tb-div-dashed, .tb-div-dashed {
  border-top: 1px dashed var(--div-color, var(--primary-text-color)) !important;
  opacity: var(--div-opacity, 0.15) !important;
}
ha-card .tb-div-double, .tb-div-double {
  border-top: 3px double var(--div-color, var(--primary-text-color)) !important;
  opacity: var(--div-opacity, 0.18) !important;
}
ha-card .tb-div-wavy, .tb-div-wavy {
  position: relative !important;
  height: 10px !important;
  overflow: hidden !important;
  opacity: var(--div-opacity, 0.2) !important;
}
ha-card .tb-div-wavy::after, .tb-div-wavy::after {
  content: '' !important;
  position: absolute !important;
  left: 0 !important;
  right: 0 !important;
  top: 0 !important;
  height: 10px !important;
  background-color: var(--div-color, var(--primary-text-color)) !important;
  -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 10'%3E%3Cpath d='M0 5 Q 12.5 0, 25 5 T 50 5 T 75 5 T 100 5 T 125 5 T 150 5 T 175 5 T 200 5' fill='none' stroke='black' stroke-width='2.5'/%3E%3C/svg%3E") !important;
  mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 10'%3E%3Cpath d='M0 5 Q 12.5 0, 25 5 T 50 5 T 75 5 T 100 5 T 125 5 T 150 5 T 175 5 T 200 5' fill='none' stroke='black' stroke-width='2.5'/%3E%3C/svg%3E") !important;
  -webkit-mask-repeat: repeat-x !important;
  mask-repeat: repeat-x !important;
  -webkit-mask-size: 50px 10px !important;
  mask-size: 50px 10px !important;
}
"""

BASE_RAW_CSS = """/* Theme variables removed; using direct values below */ ha-card {
  box-shadow: none !important;
  padding: 0px !important;
  font-size: var(--paper-font-body1_-_font-size, 14px) !important;
  font-family: var(--paper-font-body1_-_font-family, 'Roboto', sans-serif) !important;
  background: transparent !important;
} ha-card table {
  border-collapse: collapse !important;
  table-layout: fixed !important;
} ha-card th, ha-card td {
  padding: 8px !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
} ha-card .sticky {
  position: sticky !important;
} ha-card thead th {
  z-index: 20 !important;
  border-top: 0 !important;
} ha-card thead th:first-child {
  z-index: 30 !important;
} ha-card tbody td:first-child {
  z-index: 10 !important;
} ha-card h2, ha-card h3 {
  font-family: inherit !important;
  font-weight: bold !important;
  margin: 0 0 8px 0 !important;
  line-height: 1.3 !important;
} ha-card img {
  flex-shrink: 0 !important;
} .svg-white-fill path {
  fill: #ffffff !important;
  stroke: #000 !important;
} /* 透明度工具类 */ .opacity-10 { opacity: 0.1 !important; } .opacity-20 { opacity: 0.2 !important; } .opacity-30 { opacity: 0.3 !important; } .opacity-40 { opacity: 0.4 !important; } .opacity-50 { opacity: 0.5 !important; } .opacity-60 { opacity: 0.6 !important; } .opacity-70 { opacity: 0.7 !important; } .opacity-80 { opacity: 0.8 !important; } .opacity-90 { opacity: 0.9 !important; } .opacity-100 { opacity: 1 !important; } /* svg操作icon - 描边样式 */ .icon-svg-action {
  stroke: #000 !important;
  stroke-width: 3px !important;
  paint-order: stroke fill !important;
  stroke-linejoin: round !important;
  stroke-linecap: round !important;
} .icon-svg-action path {
  vector-effect: non-scaling-stroke !important;
} /* badge内SVG描边，宽度为action的一半 */ .icon-svg-badge {
  stroke: #000 !important;
  stroke-width: 0px !important;
  paint-order: stroke fill !important;
  stroke-linejoin: round !important;
  stroke-linecap: round !important;
} .icon-svg-badge path {
  vector-effect: non-scaling-stroke !important;
}
/* flex容器中的25px图标防止被拉伸 */ .flex img[width="25"] {
  align-self: flex-start !important;
} .no-wrap {
  flex-wrap: nowrap !important;
  white-space: nowrap !important;
  margin-right: -75px;
} ha-card .border {
  border-width: 0px 1px 1px 0px !important;
  border-color: var(--app-theme-color) !important;
} ha-card .production-time-column {
  /* 时间标签列 */
} /* 表头时间图标 */ .production-time-header-icon {
  display: inline-block !important;
  vertical-align: middle !important;
  fill: rgb(255, 255, 255) !important;
  position: relative !important;
  top: -1px !important;
} .production-time-header-icon path {
  fill: rgb(255, 255, 255) !important;
} /* 时间标签容器（绝对定位，类似device-container） */ .time-container {
  position: absolute !important;
  top: 0 !important;
  height: 100% !important;
  display: inline-flex !important;
  flex-direction: row !important;
  gap: 4px !important;
  vertical-align: top !important;
  justify-content: center !important;
  align-items: center !important;
  text-align: center !important;
} /* 时间标签元素：撑满容器高度并居中 */ .time-container .production-time {
  height: calc(100% - 16px) !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  flex-direction: column !important;
  overflow: hidden !important;
} /* 时间标签td需要相对定位作为绝对定位的参考 */ #base-table tbody td.production-time-column {
  position: relative !important;
  width: 0% !important;
  min-width: fit-content !important;
  white-space: nowrap !important;
} /* #base-table tbody td:nth-child(4) {
  width: 0% !important;
  min-width: fit-content !important;
  white-space: nowrap !important;
} */ ha-card tbody td {
  line-height: 1.4 !important;
  vertical-align: top !important;
  font-size: var(--paper-font-body1_-_font-size, 12px) !important;
} ha-card .borderr-top {
  border-top-left-radius: 8px !important;
  border-top-right-radius: 8px !important;
  border-bottom-left-radius: 0 !important;
  border-bottom-right-radius: 0 !important;
  height: 100% !important;
} #section-longhe-body .borderr-top, #section-yingling-body .borderr-top {
  height: auto !important;
} ha-card .borderr-none {
  border-top-left-radius: 0 !important;
  border-top-right-radius: 0 !important;
  border-bottom-left-radius: 0 !important;
  border-bottom-right-radius: 0 !important;
  height: 100% !important;
} ha-card .borderr-bottom {
  border-top-left-radius: 0 !important;
  border-top-right-radius: 0 !important;
  border-bottom-left-radius: var(--ha-card-border-radius, 12px) !important;
  border-bottom-right-radius: var(--ha-card-border-radius, 12px) !important;
  height: 100% !important;
} ha-card .borderr-middle {
  border-top-left-radius: 0 !important;
  border-top-right-radius: 0 !important;
  height: 100% !important;
} ha-card thead th:first-child, ha-card tbody td:first-child { } ha-card thead th:nth-child(n+2), ha-card tbody td:nth-child(n+2) {
  width: 0px !important;
  min-width: 0px !important;
  white-space: normal !important;
} #base-table > tbody > tr > td.production-time-column {
  width: 0% !important;
  min-width: 42px !important;
  white-space: nowrap !important;
} ha-card blockquote {
  border-left: 3px solid #ccc !important;
  padding-left: 8px !important;
  margin: 0 !important;
} img.extinct-material {
  filter: drop-shadow(0 0 1px #d1ecf1) drop-shadow(0 0 2px #0099cc) drop-shadow(0 0 3px #0099cc);
} .icon-badge-ext svg path {
  fill: none !important;
} .icon-badge-ext svg path:first-child {
  fill: #ffffff !important;
} .icon-badge-ext svg path:last-child {
  fill: #0099cc !important;
} .icon-badge-scorched svg path {
  fill: none !important;
} .icon-badge-scorched svg path:first-child {
  fill: #ffffff !important;
} .icon-badge-scorched svg path:last-child {
  fill: #ffb81c !important;
} img.scorched-material {
  filter: drop-shadow(0 0 1px #fff3cd) drop-shadow(0 0 2px #ffb81c) drop-shadow(0 0 3px #ffb81c);
} #base-table {
  table-layout: auto !important;
  width: 100% !important;
  background: var(--ha-card-background, var(--card-background-color, #fff)) !important;
} #base-table tbody td:has(.device-container) {
  width: 0% !important;
  min-width: 60px !important;
} #base-table thead th:nth-child(n+2), #base-table tbody td:nth-child(n+2) {
  min-width: 0 !important;
  white-space: normal !important;
  overflow-wrap: break-word !important;
} #base-table blockquote {
  border-left: 3px solid #ccc !important;
  padding-left: 8px !important;
  margin: 0 !important;
  border-top: 3px solid transparent !important;
  border-bottom: 3px solid transparent !important;
} .quote {
  border-left: 3px solid #ccc !important;
  padding-left: 8px !important;
  margin: 0 !important;
} .quote-spaced {
  margin-top: 8px !important;
} .text-bold {
  font-weight: bold !important;
} .text-orange {
  color: rgb(237, 116, 12) !important;
} .text-green {
  color: rgb(92, 141, 7) !important;
} .text-blue {
  color: rgb(47, 75, 218) !important;
} .text-whiter {
  color: #fff !important;
  text-shadow:
    0 1px 0 rgba(0, 0, 0, 0.35),
    0 -1px 0 rgba(0, 0, 0, 0.35),
    1px 0 0 rgba(0, 0, 0, 0.35),
    -1px 0 0 rgba(0, 0, 0, 0.35);
} .text-right-sm {
  font-size: 12px !important;
  text-align: right !important;
} /* 英灵殿标题 */ .base-title-header {
  background-color: #4CAF50 !important;
  color: rgb(255, 255, 255) !important;
  font-size: 18px !important;
  font-weight: bold !important;
} /* 绿色表头 */ .header-green {
  background-color: #4CAF50 !important;
  color: rgb(255, 255, 255) !important;
} /* 浅绿色表头 */ .header-primary {
  background-color: rgba(76, 175, 80, 0.3) !important;
  color: rgb(255, 255, 255) !important;
} /* 设备-耗材容器 */ .device-container {
  display: inline-flex !important;
  flex-direction: row !important;
  align-items: stretch !important;
  gap: 4px !important;
  vertical-align: top !important;
} /* 纵向布局的容器需要撑满高度 */ .device-container:has(.materials-box-inner-vertical) {
  width: 100% !important;
  height: 100% !important;
} /* 设备图标容器，上下左右留距 */ .device-icon-wrapper {
  padding: 6px !important;
  display: flex !important;
  align-items: center !important;
  position: relative !important;
} /* 设备图标保持原始比例，不变形 */ .device-icon-wrapper img {
  width: 30px !important;
  height: 30px !important;
  object-fit: contain !important;
  flex-shrink: 0 !important;
} /* 框内主行容器（替代内联 style） */ .materials-box-inner {
  display: flex !important;
  gap: 0 !important;
  width: 100% !important;
  height: 100% !important;
} /* 框内右侧纵向容器（替代内联 style） */ .box-right-column {
  flex: 1 1 auto !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 0 !important;
  position: relative !important;
} /* Tag中透明分隔线 */ .tag-divider {
  width: 1px !important;
  height: 15px !important;
  background-color: transparent !important;
  border-right: 1px solid rgba(138, 143, 141, 0.2) !important;
  flex-shrink: 0 !important;
  margin: 0 6px !important;
} /* 耗材容器 */ .materials-wrapper {
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  gap: 4px !important;
} /* 耗材盒子 */ .materials-box {
  border: none !important;
  border-radius: 4px !important;
  background-color: rgba(138, 143, 141, 0.1) !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  overflow: hidden !important;
  height: 100% !important;
  position: relative !important;
} /* Tag图标容器（上半部分，底色较深；左动作右地点） */ .tag-icons {
  display: flex !important;
  flex-wrap: nowrap !important;
  gap: 0 !important;
  justify-content: space-between !important;
  align-items: center !important;
  padding: 6px 8px !important;
  background-color: rgba(138, 143, 141, 0.3) !important;
  width: 100% !important;
} /* Tag与耗材中图标统一为15px，避免被裁切 */ .tag-icons img, .materials-icons img, .tag-icons svg {
  width: 15px !important;
  height: 15px !important;
  flex: 0 0 auto !important;
} .tag-icons, .materials-icons { box-sizing: border-box !important; } /* 统一动作图标颜色（与其它设备一致） */ .tag-icons svg path {
  fill: #666;
} /* 统一动作图标描边颜色 */ .tag-icons svg, .tag-icons svg * {
  stroke: #666;
} /* 耗材图标容器（下半部分） */ .materials-icons {
  display: flex !important;
  flex-wrap: wrap !important;
  gap: 4px !important;
  justify-content: center !important;
  padding: 6px 8px !important;
} .icon-stack-group {
  display: inline-flex;
  flex-wrap: nowrap;
  gap: 0.25rem;
} /* 小图标竖向堆叠容器（图标+微注释） */ .icon-stack {
  position: relative !important;
  display: inline-flex !important;
  flex-direction: column !important;
  align-items: center !important;
  gap: 1px !important;
  /* cursor: pointer !important;
  width: 30px !important; */
} /* 图标右上角浮层徽章 */ .icon-badge {
  position: absolute !important;
  left: 0 !important;
  right: 0 !important;
  top: 0 !important;
  transform: none !important;
  margin-top: 0 !important;
  width: 30px !important;
  height: 30px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  z-index: 1 !important;
} .icon-badge-15, .icon-badge-20, .icon-badge-25 {
  width: 25px !important;
  height: 25px !important;
} .icon-badge::after {
  content: '' !important;
  position: absolute !important;
  inset: 0 !important;
  background-color: rgba(0, 0, 0, 0) !important;
  border-radius: 2px !important;
  pointer-events: none !important;
  z-index: 0 !important;
  -webkit-mask-image: var(--icon-url) !important;
  mask-image: var(--icon-url) !important;
  -webkit-mask-repeat: no-repeat !important;
  mask-repeat: no-repeat !important;
  -webkit-mask-position: center !important;
  mask-position: center !important;
  -webkit-mask-size: 30px 30px !important;
  mask-size: 30px 30px !important;
  mask-mode: match-source !important;
} .icon-badge-15::after {
  -webkit-mask-size: 15px 15px !important;
  mask-size: 15px 15px !important;
  opacity: 1 !important;
} .icon-badge-20::after {
  -webkit-mask-size: 20px 20px !important;
  mask-size: 20px 20px !important;
  opacity: 1 !important;
} .icon-badge-25::after {
  -webkit-mask-size: 25px 25px !important;
  mask-size: 25px 25px !important;
  opacity: 1 !important;
} .icon-badge svg, .icon-badge img {
  width: 15px !important;
  height: 15px !important;
  position: relative !important;
  z-index: 1 !important;
  fill: #fff !important;
} .icon-badge-15 svg, .icon-badge-20 svg, .icon-badge-25 svg {
  width: 25px !important;
  height: 25px !important;
  opacity: 0.4 !important;
  z-index: -1 !important;
} .icon-badge img {
  filter: drop-shadow(0 0 2px #fff) !important;
} .icon-badge svg path {
  fill: #ffffff !important;
} .icon-badge-15 svg path, .icon-badge-20 svg path, .icon-badge-25 svg path {
  fill: gray !important;
  stroke: white !important;
} .icon-badge-bio::after {
  background-color: #666 !important;
} .icon-badge-bio-gigantoraptor::after {
  background-color: #666 !important;
  -webkit-mask-size: 118% 100% !important;
  mask-size: 118% 100% !important;
} .icon-badge-bio-human::after {
  background-color: #666 !important;
  -webkit-mask-size: 114% 114% !important;
  mask-size: 114% 114% !important;
} .bio-count-tag-bottom {
  position: absolute !important;
  right: 2px !important;
  bottom: 28px !important;
  color: rgba(138, 143, 141, 0.7) !important;
  font-size: 10px !important;
  line-height: 1 !important;
  white-space: nowrap !important;
  pointer-events: none !important;
} .bio-capacity-tag-bottom {
  position: absolute !important;
  left: 2px !important;
  bottom: 28px !important;
  color: rgba(138, 143, 141, 0.7) !important;
  font-size: 10px !important;
  line-height: 1 !important;
  white-space: nowrap !important;
  pointer-events: none !important;
} .materials-box:not(:has(.h-divider)) .bio-capacity-tag-bottom {
  bottom: 2px !important;
} .bio-capacity-tag-bottom sub, .bio-capacity-tag-bottom-horizontal sub {
  vertical-align: baseline !important;
  font-size: 0.8em !important;
  line-height: 1 !important;
  bottom: 0em !important;
} .bio-count-tag-bottom-horizontal {
  position: absolute !important;
  right: 2px !important;
  bottom: 2px !important;
  color: rgba(138, 143, 141, 0.7) !important;
  font-size: 10px !important;
  line-height: 1 !important;
  white-space: nowrap !important;
  pointer-events: none !important;
} .bio-capacity-tag-bottom-horizontal {
  position: absolute !important;
  left: 2px !important;
  bottom: 2px !important;
  color: rgba(138, 143, 141, 0.7) !important;
  font-size: 10px !important;
  line-height: 1 !important;
  white-space: nowrap !important;
  pointer-events: none !important;
} .materials-box-inner:not(:has(.materials-icons)) .device-icon-wrapper {
  padding: 6px 6px 12px 6px !important;
} .materials-box-inner:not(:has(.materials-icons)) .device-icon-wrapper:not(.device-icon-wrapper-vertical) {
  padding: 12px 6px !important;
} .device-repair-badge {
  position: absolute !important;
  left: 2px !important;
  top: 2px !important;
  display: flex !important;
  align-items: center !important;
  gap: 0.5px !important;
  color: rgba(138, 143, 141, 0.6) !important;
  font-size: 10px !important;
  line-height: 1 !important;
  white-space: nowrap !important;
  pointer-events: none !important;
} .device-repair-badge sup {
  font-size: 0.8em !important;
  line-height: 1 !important;
  vertical-align: top !important;
  top: 0 !important;
} .device-repair-badge svg { } .device-repair-badge svg path {
  fill: rgba(138, 143, 141, 0.6) !important;
} /* 隐藏带有 bio 徽章的图标 */ .icon-stack:has(.icon-badge-bio) > img, .icon-stack:has([class*="icon-badge-bio-"]) > img {
  visibility: hidden !important;
} .icon-grid-inline {
  display: inline-flex;
  flex-wrap: wrap;
  vertical-align: top;
} .icon-grid-item {
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: flex-start !important;
  line-height: 1 !important;
  width: 20px !important;
  flex: 0 0 20px !important;
} .icon-grid-item svg {
  display: block !important;
} .icon-grid-count {
  font-size: 10px !important;
  color: rgb(138, 143, 141) !important;
  opacity: 1;
  line-height: 1 !important;
} /* Wiki链接样式 */ .wiki-link {
  display: inline-flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
  width: 30px !important;
  color: #1a73e8 !important;
  text-decoration: none !important;
} .wiki-link img {
  display: block !important;
} .wiki-link-line {
  margin-top: 1px !important;
  width: 5px !important;
  height: 5px !important;
  border-radius: 50% !important;
  background: #1a73e8 !important;
} /* 分隔圆点（不撑开布局，居中悬浮） */ .divider-dot {
  position: relative !important;
  height: 0 !important;
  flex-shrink: 0 !important;
} .divider-dot::before {
  content: '' !important;
  position: absolute !important;
  left: 50% !important;
  top: 0 !important;
  transform: translate(-50%, -50%) !important;
  width: 5px !important;
  height: 5px !important;
  border-radius: 50% !important;
  background: #1a73e8 !important;
  pointer-events: none !important;
} /* Gigantoraptor：蓝点绝对定位并可见，整个盒子可点击 */
.materials-box.egg-toggle .divider-dot {
  display: none !important;
} .materials-box.egg-toggle .h-divider {
  position: relative !important;
} .materials-box.egg-toggle .h-divider::after {
  content: '' !important;
  position: absolute !important;
  left: 50% !important;
  top: 2px !important;
  transform: translate(-50%, -50%) !important;
  width: 5px !important;
  height: 5px !important;
  border-radius: 50% !important;
  background: #1a73e8 !important;
  opacity: 1 !important;
  pointer-events: none !important;
} /* 默认显示果子与蓝点 */ .materials-box.egg-toggle .egg-icon {
  display: none !important;
  width: 15px !important;
  height: 15px !important;
  object-fit: contain !important;
} .materials-box.egg-toggle .action-icon {
  display: block !important;
}
/* 下蛋生物蛋图标发光颜色 */ .item-glow-gray {
  filter: drop-shadow(0 0 1px #cccccc) drop-shadow(0 0 2px #cccccc) drop-shadow(0 0 4px #cccccc) !important;
} .item-glow-green {
  filter: drop-shadow(0 0 1px #22905d) drop-shadow(0 0 2px #22905d) drop-shadow(0 0 4px #22905d) !important;
} .item-glow-blue {
  filter: drop-shadow(0 0 1px #3459af) drop-shadow(0 0 2px #3459af) drop-shadow(0 0 4px #3459af) !important;
} .item-glow-purple {
  filter: drop-shadow(0 0 1px #904e81) drop-shadow(0 0 2px #904e81) drop-shadow(0 0 4px #904e81) !important;
} .item-glow-yellow {
  filter: drop-shadow(0 0 1px #d6ca24) drop-shadow(0 0 2px #d6ca24) drop-shadow(0 0 4px #d6ca24) !important;
} .item-glow-cyan {
  filter: drop-shadow(0 0 1px #64d4e0) drop-shadow(0 0 2px #64d4e0) drop-shadow(0 0 4px #64d4e0) !important;
}
/* 垂直排列的tag-icons（用于多个动作图标） */ .tag-icons-vertical {
  display: flex !important;
  flex-direction: column !important;
  gap: 2px !important;
} .tag-icons-vertical .tag-divider {
  width: 100% !important;
  height: 1px !important;
  border-right: none !important;
  border-bottom: 1px solid rgba(138, 143, 141, 0.2) !important;
  margin: 2px 0 !important;
} /* Wind Turbine 修复比例浮层 */ .with-modal {
  position: relative !important;
} /* 全屏遮罩，点击关闭 */ .modal-overlay {
  display: none !important;
} /* 低调 tooltip 浮层 */ .modal-tooltip {
  position: absolute !important;
  display: none !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  height: 27px !important;
  background: rgba(138, 143, 141, 0.1) !important;
  padding: 0 8px !important;
  z-index: 901 !important;
  white-space: nowrap !important;
  font-size: 12px !important;
  text-align: center !important;
  align-items: center !important;
} /* 移除箭头 */ .modal-tooltip::after {
  display: none !important;
} /* 浮层左侧图标 */ .modal-icon {
  position: absolute !important;
  display: none !important;
  top: 0 !important;
  right: calc(100% + 0px) !important;
  width: 17px !important;
  height: 17px !important;
  background: rgba(138, 143, 141, 0.1) !important;
  border-bottom-left-radius: 6px !important;
  padding: 0 !important;
  z-index: 901 !important;
  align-items: center !important;
  justify-content: center !important;
  flex-shrink: 0 !important;
} .modal-icon svg {
  width: 60% !important;
  height: 60% !important;
  fill: rgba(138, 143, 141, 0.5) !important;
} /* PC 端：悬停显示 */ @media (hover: hover) {
  .with-modal:hover .modal-tooltip {
    display: flex !important;
  }
  .with-modal:hover .modal-icon {
    display: flex !important;
  }
  .with-modal:hover .tag-icons {
    opacity: 0 !important;
  }
  .with-modal:hover .divider-dot {
    opacity: 0 !important;
  }
  /* Web 端：悬停隐藏背景+果子+蓝点，显示蛋 */
  .materials-box.egg-toggle:hover .egg-icon {
    display: block !important;
  }
  .materials-box.egg-toggle:hover .action-icon {
    display: none !important;
  }
  .materials-box.egg-toggle:hover .h-divider::after {
    opacity: 0 !important;
  }
  .materials-box.egg-toggle:hover .bio-count-tag-bottom {
    opacity: 0 !important;
  }
  .materials-box.egg-toggle:hover .bio-count-tag-bottom-horizontal {
    opacity: 0 !important;
  }
  .materials-box.egg-toggle:hover .action-icon-wrapper {
    background-color: transparent !important;
  }
  /* egg-toggle-container.with-modal 的 hover 效果 */
  .egg-toggle-container.with-modal:hover .egg-icon {
    display: block !important;
  }
  .egg-toggle-container.with-modal:hover .action-icon {
    display: none !important;
  }
  .egg-toggle-container.with-modal:hover .h-divider::after {
    opacity: 0 !important;
  }
  .egg-toggle-container.with-modal:hover .bio-count-tag-bottom {
    opacity: 0 !important;
  }
  .egg-toggle-container.with-modal:hover .bio-count-tag-bottom-horizontal {
    opacity: 0 !important;
  }
  .egg-toggle-container.with-modal:hover .action-icon-wrapper {
    background-color: transparent !important;
  }
  /* with-modal 本身的 hover 效果（tooltips） */
  .with-modal:hover .modal-tooltip {
    display: flex !important;
  }
  .with-modal:hover .modal-icon {
    display: flex !important;
  }
  .with-modal:hover .tag-icons {
    opacity: 0 !important;
  }
  .with-modal:hover .divider-dot {
    opacity: 0 !important;
  }
  /* Keep repair time badge visible during hover */
  .with-modal:hover .device-repair-badge {
    opacity: 1 !important;
    z-index: 902 !important;
  }
} /* 移动端：点击显示，保持可见，点外部关闭 */ @media (hover: none) {
  /* 按下时立刻显示 */
  .with-modal:active .modal-tooltip {
    display: flex !important;
    opacity: 1 !important;
  }
  .with-modal:active .modal-icon {
    display: flex !important;
    opacity: 1 !important;
  }
  .with-modal:active .tag-icons,
  .with-modal:active .divider-dot {
    opacity: 0 !important;
  }
  /* 抬起后保持显示，直到点击外部 */
  .with-modal:focus-within .modal-tooltip {
    display: flex !important;
    opacity: 1 !important;
  }
  .with-modal:focus-within .modal-icon {
    display: flex !important;
    opacity: 1 !important;
  }
  .with-modal:focus-within .tag-icons,
  .with-modal:focus-within .divider-dot {
    opacity: 0 !important;
  }
  /* Keep repair time badge visible during mobile interaction */
  .with-modal:active .device-repair-badge,
  .with-modal:focus-within .device-repair-badge {
    opacity: 1 !important;
    z-index: 902 !important;
  }
  /* egg-toggle 与 with-modal 结合的交互 */
  .egg-toggle-container.with-modal .egg-icon {
    display: none !important;
  }
  .egg-toggle-container.with-modal .action-icon {
    display: block !important;
  }
  .egg-toggle-container.with-modal .h-divider::after {
    opacity: 1 !important;
  }
  .egg-toggle-container.with-modal .action-icon-wrapper {
    background-color: rgba(138, 143, 141, 0.3) !important;
  }
  /* 点击显示蛋，隐藏动作图标+蓝点+背景 */
  .egg-toggle-container.with-modal:active .egg-icon {
    display: block !important;
  }
  .egg-toggle-container.with-modal:active .action-icon {
    display: none !important;
  }
  .egg-toggle-container.with-modal:active .h-divider::after {
    opacity: 0 !important;
  }
  .egg-toggle-container.with-modal:active .bio-count-tag-bottom {
    opacity: 0 !important;
  }
  .egg-toggle-container.with-modal:active .bio-count-tag-bottom-horizontal {
    opacity: 0 !important;
  }
  .egg-toggle-container.with-modal:active .action-icon-wrapper {
    background-color: transparent !important;
  }
  /* focus-within 保持显示蛋 */
  .egg-toggle-container.with-modal:focus-within .egg-icon {
    display: block !important;
  }
  .egg-toggle-container.with-modal:focus-within .action-icon {
    display: none !important;
  }
  .egg-toggle-container.with-modal:focus-within .h-divider::after {
    opacity: 0 !important;
  }
  .egg-toggle-container.with-modal:focus-within .bio-count-tag-bottom {
    opacity: 0 !important;
  }
  .egg-toggle-container.with-modal:focus-within .bio-count-tag-bottom-horizontal {
    opacity: 0 !important;
  }
  .egg-toggle-container.with-modal:focus-within .action-icon-wrapper {
    background-color: transparent !important;
  }
} #wind-turbine-repair:target ~ .with-modal .modal-tooltip {
  display: none !important;
} .modal-body {
  display: flex !important;
  width: 100% !important;
  gap: 8px !important;
  align-items: center !important;
  justify-content: center !important;
} .modal-body span {
  color: rgb(138, 143, 141) !important;
  font-size: 10px !important;
  display: inline-block !important;
  width: 3ch !important;
  text-align: center !important;
} .tiny-note {
  font-size: 10px !important;
  line-height: 1 !important;
  color: rgb(138, 143, 141) !important;
  opacity: 0.6 !important;
} .tiny-note.tiny-note-offset {
  margin-top: 31px !important;
} .tiny-note[data-abbr] {
  position: relative !important;
  color: transparent !important;
  height: 10px !important;
} .tiny-note[data-abbr]::after {
  content: attr(data-abbr) !important;
  color: rgb(138, 143, 141) !important;
  position: absolute !important;
  inset: 0 !important;
  align-items: center !important;
}
/* Rare Mushroom 圆点标记 */ .icon-stack:has([data-material="rare-mushroom"])::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) translateY(-5px);
  width: 4px;
  height: 4px;
  background-color: #9C27B0;
  box-shadow: 0 0 0 2px #ffffff;
  border-radius: 50%;
  z-index: 10;
  pointer-events: none;
}
/* 蔬菜类圆点标记 (Rockarrot, Savoroot, Longrass, Citronal, Focal Chili, Lazarus Chowder, Giant Bee Honey) */ .icon-stack:has([data-material="rockarrot"])::before, .icon-stack:has([data-material="savoroot"])::before, .icon-stack:has([data-material="longrass"])::before, .icon-stack:has([data-material="citronal"])::before, .icon-stack:has([data-material="focal-chili"])::before, .icon-stack:has([data-material="lazarus-chowder"])::before, .icon-stack:has([data-material="giant-bee-honey"])::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) translateY(-5px);
  width: 4px;
  height: 4px;
  background-color: #ffb81c;
  box-shadow: 0 0 0 2px #ffffff;
  border-radius: 50%;
  z-index: 10;
  pointer-events: none;
}
/* 堆叠标注容器 */ .stack-notation {
  display: flex !important;
  align-items: center !important;
  gap: 0px !important;
  margin-top: 0 !important;
} /* 堆叠图标 */ .stack-icon {
  width: 9px !important;
  height: 9px !important;
  color: rgb(138, 143, 141) !important;
  fill: rgb(138, 143, 141) !important;
  opacity: 0.6 !important;
  flex-shrink: 0 !important;
  transform: translateY(-0.5px) !important;
} /* 堆叠数字 */ .stack-number {
  font-size: 10px !important;
  line-height: 10px !important;
  color: rgb(138, 143, 141) !important;
  opacity: 0.6 !important;
} /* 地点标签 */ .location-label {
  background-color: rgb(138, 143, 141) !important;
  color: rgb(255, 255, 255) !important;
  padding: 2px 6px !important;
  font-size: 11px !important;
  border-radius: 3px !important;
  white-space: nowrap !important;
} /* 小标签：采用设备图标（动作/Tag区）背景色 */ .location-chip {
  display: inline-block !important;
  background-color: rgba(138, 143, 141, 0.1) !important; /* 与设备图标所在 .materials-box 一致，更浅 */
  color: inherit !important;
  padding: 4px 6px 3px 6px !important;
  font-size: 11px !important;
  border-radius: 3px !important;
  white-space: nowrap !important;
  margin-right: 4px !important;
} .location-chip.idle {
  background-color: rgba(138, 143, 141, 0.06) !important;
  color: rgba(138, 143, 141, 0.7) !important;
  outline: 1px dashed rgba(138, 143, 141, 0.3) !important;
  outline-offset: -1px !important;
} /* 产出时间标签：竖排，靠右，拉通高度 */ .location-chip.production-time {
  margin-left: auto !important;
  margin-right: 0 !important;
  /* margin-top: -42px !important; */
  padding: 0 5px !important;
  font-size: 10px !important;
  flex-shrink: 0 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  writing-mode: vertical-rl !important;
  text-orientation: mixed !important;
  color: rgb(255, 255, 255) !important;
  white-space: nowrap !important;
  background-color: transparent !important;
  color: rgba(138, 143, 141, 0.7) !important;
  border: 1px dashed rgba(138, 143, 141, 0.3) !important;
  transform: rotate(180deg) !important;
} /* 数量调整按钮 */ .qty-btn {
  background-color: transparent !important;
  border: 1px solid rgba(138, 143, 141, 0.1) !important;
  border-radius: 3px !important;
  block-size: 100% !important; /* 跟随容器高度自适应 */
  aspect-ratio: 1 !important;
  min-width: 24px !important;
  min-height: 24px !important;
  max-width: 41px !important;
  max-height: 41px !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  cursor: pointer !important;
  font-size: 18px !important;
  line-height: 1 !important;
  color: #1a73e8 !important;
  padding: 0 !important;
  transition: all 0.2s !important;
  flex-shrink: 0 !important;
} .qty-btn:hover {
  background-color: rgba(138, 143, 141, 0.2) !important;
  border-color: rgba(138, 143, 141, 0.3) !important;
} .qty-btn:active {
  background-color: rgba(138, 143, 141, 0.3) !important;
} /* 禁用态（opacity:0.3）不响应指针事件，不显示选中效果 */ .qty-btn[style*="opacity:0.3"] {
  pointer-events: none !important;
  cursor: default !important;
} /* 按钮容器右对齐 */ /* 让包含按钮的td成为定位容器 */ td:has(.qty-btn-group) {
  position: relative !important;
  padding-right: 90px !important; /* 预留按钮组宽度，与当前尺寸一致 */
} /* 按钮容器绝对定位，扣除上下内边距以撑满高度 */ .qty-btn-group {
  position: absolute !important;
  inset: 8px 8px auto auto !important;
  block-size: calc(100% - 16px) !important; /* 拉满单元格高度，按钮自适应 */
  display: inline-flex !important;
  gap: 0 !important;
  align-items: stretch !important;
  justify-content: flex-end !important;
} /* 左按钮：保留左圆角，移除右圆角 */ .qty-btn:first-child {
  border-top-right-radius: 0 !important;
  border-bottom-right-radius: 0 !important;
} /* 右按钮：保留右圆角，移除左圆角 */ .qty-btn:last-child {
  border-top-left-radius: 0 !important;
  border-bottom-left-radius: 0 !important;
  margin-left: -1px !important; /* 与左按钮右边框重叠，避免双线 */
} /* 垂直分隔线（拉通，无间隔） */ .v-divider {
  width: 0 !important;
  align-self: stretch !important;
  flex-shrink: 0 !important;
  border-left: 1px solid rgba(138, 143, 141, 0.3) !important;
  border-right: none !important;
  border-top: none !important;
  border-bottom: none !important;
} /* 当右侧列只有tag-icons（无耗材）时，让tag背景色拉通高度 */ .box-right-column > .tag-icons:only-child {
  flex: 1 !important;
} /* 纵向布局：动作在设备下方 */ .materials-box-inner-vertical {
  flex-direction: column !important;
  align-items: center !important;
  gap: 0 !important;
  flex: 1 !important;
} /* 纵向布局的设备图标：上下左右边距一致 */ .device-icon-wrapper-vertical {
  padding: 6px !important;
  flex-shrink: 0 !important;
} .h-divider {
  height: 1px !important;
  background-color: transparent !important;
  align-self: stretch !important;
  flex-grow: 1 !important;
  width: 100% !important;
  border:none !important;
} .action-icon-wrapper {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  padding: 6px !important;
  width: 100% !important;
  background-color: rgba(138, 143, 141, 0.3) !important;
  flex-shrink: 0 !important;
} .action-icon-wrapper svg {
  width: 15px !important;
  height: 15px !important;
} .action-icon-wrapper svg path {
  fill: #666 !important;
} .action-icon-wrapper svg, .action-icon-wrapper svg * {
  stroke: #666 !important;
} /* 产出列时钟图标容器 */ td:has(.production-clock-icon) {
  position: relative !important;
  padding-right: 28px !important;
} /* 产出列时钟图标 */ .production-clock-icon {
  position: absolute !important;
  inset: 50% 8px auto auto !important;
  transform: translateY(-50%) !important;
} .production-clock-icon path {
  fill: #666 !important;
} /* 低可视化的动作图标（例如Cooking Pot无需点火） */ .action-icon-wrapper.low-visual svg {
  opacity: 0.35 !important;
  filter: grayscale(1) contrast(0.9) !important;
} .action-icon-wrapper.low-visual svg path, .action-icon-wrapper.low-visual svg * {
  color: rgb(47, 75, 218) !important;
  stroke: rgba(138, 143, 141, 0.3) !important;
} /* borderr-none 表：按第一列分组隔行着色（含rowspan继承） */ ha-card .borderr-none tbody > tr td {
  background-color: transparent !important;
} /* 存储表（thead colspan=3）：普通隔行 */ ha-card .borderr-none table:has(> thead th[colspan="3"]) tbody > tr:nth-child(even) td {
  background-color: var(--primary-background-color, #f5f5f5) !important;
} /* 设备表（非colspan=3）：以设备列为分组起点，仅设备行着色 */ /* 禁用态（opacity:0.3 或 opacity: 0.3）不响应指针事件，不显示选中效果，字体回灰 */ .qty-btn[style*="opacity:0.3"], .qty-btn[style*="opacity: 0.3"] {
  pointer-events: none !important;
  cursor: default !important;
  color: rgba(138, 143, 141, 0.5) !important;
} .qty-btn[style*="opacity:0.3"]:hover, .qty-btn[style*="opacity: 0.3"]:hover, .qty-btn[style*="opacity:0.3"]:active, .qty-btn[style*="opacity: 0.3"]:active {
  background-color: transparent !important;
  border-color: rgba(138, 143, 141, 0.1) !important;
} /* Fix: Make SVG icons inside qty-btn non-interactive so clicks reach the button */ .qty-btn svg, .qty-btn svg * {
  pointer-events: none !important;
} ha-card .borderr-none table:not(:has(> thead th[colspan="3"])) tbody > tr:nth-child(even of :has(> td:first-child > .device-container)) td {
  background-color: var(--primary-background-color, #f5f5f5) !important;
} /* 设备表：rowspan 续行继承偶数组颜色（续行不含device-container），计数基准与主行一致 */ ha-card .borderr-none table:not(:has(> thead th[colspan="3"])) tbody > tr:nth-child(even of :has(> td:first-child > .device-container)):has(> td:first-child[rowspan]) + tr:not(:has(> td:first-child > .device-container)) td {
  background-color: var(--primary-background-color, #f5f5f5) !important;
} ha-card .borderr-none table:not(:has(> thead th[colspan="3"])) tbody > tr:nth-child(even of :has(> td:first-child > .device-container)):has(> td:first-child[rowspan]) + tr:not(:has(> td:first-child > .device-container)) + tr:not(:has(> td:first-child > .device-container)) td {
  background-color: var(--primary-background-color, #f5f5f5) !important;
} ha-card .borderr-none table:not(:has(> thead th[colspan="3"])) tbody > tr:nth-child(even of :has(> td:first-child > .device-container)):has(> td:first-child[rowspan]) + tr:not(:has(> td:first-child > .device-container)) + tr:not(:has(> td:first-child > .device-container)) + tr:not(:has(> td:first-child > .device-container)) td {
  background-color: var(--primary-background-color, #f5f5f5) !important;
} ha-card .borderr-none table:not(:has(> thead th[colspan="3"])) tbody > tr:nth-child(even of :has(> td:first-child > .device-container)):has(> td:first-child[rowspan]) + tr:not(:has(> td:first-child > .device-container)) + tr:not(:has(> td:first-child > .device-container)) + tr:not(:has(> td:first-child > .device-container)) + tr:not(:has(> td:first-child > .device-container)) td {
  background-color: var(--primary-background-color, #f5f5f5) !important;
} ha-card .borderr-none table:not(:has(> thead th[colspan="3"])) tbody > tr:nth-child(even of :has(> td:first-child > .device-container)):has(> td:first-child[rowspan]) + tr:not(:has(> td:first-child > .device-container)) + tr:not(:has(> td:first-child > .device-container)) + tr:not(:has(> td:first-child > .device-container)) + tr:not(:has(> td:first-child > .device-container)) + tr:not(:has(> td:first-child > .device-container)) td {
  background-color: var(--primary-background-color, #f5f5f5) !important;
} ha-card .borderr-none table:not(:has(> thead th[colspan="3"])) tbody > tr:nth-child(even of :has(> td:first-child > .device-container)):has(> td:first-child[rowspan]) + tr:not(:has(> td:first-child > .device-container)) + tr:not(:has(> td:first-child > .device-container)) + tr:not(:has(> td:first-child > .device-container)) + tr:not(:has(> td:first-child > .device-container)) + tr:not(:has(> td:first-child > .device-container)) + tr:not(:has(> td:first-child > .device-container)) td {
  background-color: var(--primary-background-color, #f5f5f5) !important;
} ha-card .borderr-none table:not(:has(> thead th[colspan="3"])) tbody > tr:nth-child(even of :has(> td:first-child > .device-container)):has(> td:first-child[rowspan]) + tr:not(:has(> td:first-child > .device-container)) + tr:not(:has(> td:first-child > .device-container)) + tr:not(:has(> td:first-child > .device-container)) + tr:not(:has(> td:first-child > .device-container)) + tr:not(:has(> td:first-child > .device-container)) + tr:not(:has(> td:first-child > .device-container)) + tr:not(:has(> td:first-child > .device-container)) td {
  background-color: var(--primary-background-color, #f5f5f5) !important;
}
/* borderr-none表的第一列居中对齐 */ ha-card .borderr-none tbody > tr > td:has(.device-container) {
  vertical-align: middle !important;
} ha-card .borderr-none tbody > tr > td:has(.device-container) > div.device-container {
  justify-content: center !important;
  align-items: center !important;
  height: 100% !important;
} /* 设备表第一列：让td和内部容器撑满高度 */ ha-card .borderr-none table:not(:has(> thead th[colspan="3"])) tbody > tr > td:has(.device-container) {
  vertical-align: stretch !important;
} /* 仅纵向布局使用绝对定位撑满高度 */ /* 有动作图标且无rowspan的纵向框：固定高度86px */ ha-card .borderr-none table:not(:has(> thead th[colspan="3"])) tbody > tr:has(.materials-box-inner-vertical):has(.action-icon-wrapper):not(:has([rowspan])) {
  height: 93px !important;
} /* 无动作图标且无rowspan的纵向框：固定高度59px */ ha-card .borderr-none table:not(:has(> thead th[colspan="3"])) tbody > tr:has(.materials-box-inner-vertical):not(:has(.action-icon-wrapper)):not(:has([rowspan])) {
  height: 66px !important;
} /* 有rowspan的纵向框：不固定高度 */ ha-card .borderr-none table:not(:has(> thead th[colspan="3"])) tbody > tr > td:first-child:has(.materials-box-inner-vertical) {
  position: relative !important;
} ha-card .borderr-none table:not(:has(> thead th[colspan="3"])) tbody > tr > td:first-child:has(.materials-box-inner-vertical) > div {
  position: absolute !important;
  top: 0 !important;
  bottom: 0 !important;
  left: 0 !important;
  right: 0 !important;
} ha-card .borderr-none table:not(:has(> thead th[colspan="3"])) tbody > tr > td:first-child:has(.materials-box-inner-vertical) .materials-box {
  height: calc(100% - 16px) !important;
} .borderr-none table:not(:has(> thead th[colspan="3"])) tbody > tr > td:first-child:has(.materials-box-inner-vertical) .materials-box {
  height: calc(100% - 16px) !important;
}
/* 存储表（有colspan="3"的表）的纵向框规则 */ /* 存储表第一列纵向框：撑满高度 */ ha-card .borderr-none table:has(> thead th[colspan="3"]) tbody > tr > td:has(.device-container) {
  vertical-align: stretch !important;
} /* 存储表：有动作图标且无rowspan的纵向框：固定高度86px */ ha-card .borderr-none table:has(> thead th[colspan="3"]) tbody > tr:has(.materials-box-inner-vertical):has(.action-icon-wrapper):not(:has([rowspan])) {
  height: 86px !important;
} /* 存储表：无动作图标且无rowspan的纵向框：固定高度59px */ ha-card .borderr-none table:has(> thead th[colspan="3"]) tbody > tr:has(.materials-box-inner-vertical):not(:has(.action-icon-wrapper)):not(:has([rowspan])) {
  height: 59px !important;
} /* 存储表纵向框：相对定位容器 */ ha-card .borderr-none table:has(> thead th[colspan="3"]) tbody > tr > td:first-child:has(.materials-box-inner-vertical) {
  position: relative !important;
} ha-card .borderr-none table:has(> thead th[colspan="3"]) tbody > tr > td:first-child:has(.materials-box-inner-vertical) > div {
  position: absolute !important;
  top: 0 !important;
  bottom: 0 !important;
  left: 0 !important;
  right: 0 !important;
} ha-card .borderr-none table:has(> thead th[colspan="3"]) tbody > tr > td:first-child:has(.materials-box-inner-vertical) .materials-box {
  height: calc(100% - 16px) !important;
} .borderr-none table:has(> thead th[colspan="3"]) tbody > tr > td:first-child:has(.materials-box-inner-vertical) .materials-box {
  height: calc(100% - 16px) !important;
} /* 空行样式 */ ha-card tr.empty-row {
  height: var(--ha-card-border-radius, 12px) !important;
} ha-card .borderr-none tbody tr.empty-row:last-child > td {
  padding: 0 !important;
  border: none !important;
  background-color: var(--primary-background-color, #f5f5f5) !important;
  border-bottom-left-radius: var(--ha-card-border-radius, 12px) !important;
  border-bottom-right-radius: var(--ha-card-border-radius, 12px) !important;
} ha-card .borderr-none table:has(> tbody > tr.empty-row:last-child) {
  border-bottom-left-radius: var(--ha-card-border-radius, 12px) !important;
  border-bottom-right-radius: var(--ha-card-border-radius, 12px) !important;
}
@supports (-webkit-touch-callout: none) {

  /* 1) 固定布局（用 #base-table 压过你原先的 table-layout:auto !important） */
  #base-table{
    table-layout: fixed !important;
    width: 100% !important;
  }

  /* 2) 锁首列宽度 */
  #base-table th:first-child,
  #base-table td:first-child{
    width: 72px !important;
    min-width: 72px !important;
    max-width: 72px !important;
  }

  /* 2.3) 锁定表头第4列宽度 */
  #base-table thead th:nth-child(4) {
    width: 42px !important;
    min-width: 42px !important;
    max-width: 42px !important;
  }

  /* 2.5) 锁定时间标签列宽度 */
  #base-table tbody tr td.production-time-column {
    width: 42px !important;
    min-width: 42px !important;
    max-width: 42px !important;
  }

  /* 3) 关键：撤销你原来对第2、3列 width:0 的压缩 */
  ha-card #base-table thead th:nth-child(n+2):not(:nth-child(4)),
  ha-card #base-table tbody td:nth-child(n+2):not(.production-time-column){
    width: auto !important;
    min-width: 1px !important;   /* 给 Safari 一个“不要为0”的暗示 */
  }

  /* 4) 可选：避免第二、三列内容被挤到不可见 */
  ha-card #base-table tbody td:nth-child(n+2):not(.production-time-column){
    overflow: visible !important;
  }


  /* iPad / iOS WebView 触控环境 */
  @media (hover: none) and (pointer: coarse) {

    /* 1) 先把“闪一下”的来源彻底禁掉：:active 不允许显示 tooltip/icon */
    .with-modal:active .modal-tooltip,
    .with-modal:active .modal-icon {
      display: none !important;
      opacity: 0 !important;
    }

    /* 2) 同时保证 :active 时不要把 tag-icons 隐藏（避免闪烁时视觉跳变） */
    .with-modal:active .tag-icons,
    .with-modal:active .divider-dot {
      opacity: 1 !important;
    }

    /* 3) 只允许 focus-within 触发稳定显示（双击后通常会进入这个状态） */
    .with-modal:focus-within .modal-tooltip {
      display: flex !important;
      opacity: 1 !important;
    }
    .with-modal:focus-within .modal-icon {
      display: flex !important;
      opacity: 1 !important;
    }
    .with-modal:focus-within .tag-icons,
    .with-modal:focus-within .divider-dot {
      opacity: 0 !important;
    }
    /* Keep repair time badge visible on iPad/iOS */
    .with-modal:focus-within .device-repair-badge {
      opacity: 1 !important;
      z-index: 902 !important;
    }

    /* 4) 小优化：取消 iOS 点按高亮与焦点轮廓（可选） */
    .with-modal {
      -webkit-tap-highlight-color: transparent !important;
      outline: none !important;
    }
    .with-modal:focus {
      outline: none !important;
    }
  }

}
.location-chip-wrapper {
  display: inline-flex;
  align-items: center;
  margin-right: 4px;
} .location-chip-left {
  margin-right: 0 !important;
  border-radius: 4px 0 0 4px !important;
} .location-chip-badge {
  background-color: rgba(138, 143, 141, 0.4);
  padding: 2px 4px;
  margin: 0;
  border-radius: 0 4px 4px 0;
  font-weight: 900;
  font-size: 11px;
  color: #e6e6e6;
  display: flex;
  align-items: center;
}
.icon-mask {
  display: inline-block;
  background-color: currentColor;
  -webkit-mask-image: var(--icon-url);
  mask-image: var(--icon-url);
  -webkit-mask-repeat: no-repeat;
  mask-repeat: no-repeat;
  -webkit-mask-position: center;
  mask-position: center;
  -webkit-mask-size: contain;
  mask-size: contain;
} .icon-mask-15 {
  width: 15px;
  height: 15px;
} .icon-mask-20 {
  width: 20px;
  height: 20px;
} .icon-mask-25 {
  width: 25px;
  height: 25px;
} .icon-mask-30 {
  width: 30px;
  height: 30px;
}
/* Kibble / Food 选择器样式 */ .kibble-selector, .food-selector {
    position: relative;
}
/* 确保td不裁剪浮层 */ td:has(.kibble-selector), td:has(.food-selector) {
    overflow: visible !important;
}
/* 确保table和父容器不裁剪浮层 */ .relative.overflow-auto:has(.kibble-selector), .relative.overflow-auto:has(.food-selector) {
    overflow: visible !important;
}
.kibble-modal, .food-modal {
    position: absolute;
    top: -8px;
    left: -8px;
    z-index: 1000;
    background: var(--primary-background-color);
    border: 1px solid rgba(138, 143, 141, 0.1);
    border-radius: 4px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    padding: 4px;
    width: auto;
    min-width: max-content;
    height: auto;
    max-height: none !important;
    display: none;
}
/* 根据Kibble序号调整modal位置，使当前Kibble选项对齐图标 */ tr[data-kibble="extraordinary"] .kibble-modal {
    top: -10px;  /* 第1个选项 */
}
tr[data-kibble="exceptional"] .kibble-modal {
    top: -52px;  /* 第2个选项: -10px - 42px */
}
tr[data-kibble="superior"] .kibble-modal {
    top: -94px;  /* 第3个选项: -10px - 42px*2 */
}
tr[data-kibble="regular"] .kibble-modal {
    top: -136px;  /* 第4个选项: -10px - 42px*3 */
}
tr[data-kibble="simple"] .kibble-modal {
    top: -178px;  /* 第5个选项: -10px - 42px*4 */
}
tr[data-kibble="basic"] .kibble-modal {
    top: -220px;  /* 第6个选项: -10px - 42px*5 */
}
/* 根据Food序号调整modal位置，使当前Food选项对齐图标 */ tr[data-food="Filling Meat Burger"] .food-modal {
    top: -10px;  /* 第1个选项 */
}
tr[data-food="Filling Dry Burger"] .food-modal {
    top: -52px;  /* 第2个选项: -10px - 42px */
}
tr[data-food="Nourishing Meat Steak"] .food-modal {
    top: -94px;  /* 第3个选项: -10px - 42px*2 */
}
tr[data-food="Nourishing Jerky"] .food-modal {
    top: -136px;  /* 第4个选项: -10px - 42px*3 */
}
tr[data-food="Energy Cake"] .food-modal {
    top: -178px;  /* 第5个选项: -10px - 42px*4 */
}
.kibble-selector .icon-stack:hover .kibble-modal, .kibble-selector .icon-stack:focus-within .kibble-modal, .food-selector .icon-stack:hover .food-modal, .food-selector .icon-stack:focus-within .food-modal {
    display: block;
} /* 桌面：用 !important 覆盖 food/kibble-option 选后设置的内联 display:none */ @media (hover: hover) and (pointer: fine) {
  .food-selector .icon-stack:hover .food-modal,
  .food-selector .icon-stack:focus-within .food-modal,
  .kibble-selector .icon-stack:hover .kibble-modal,
  .kibble-selector .icon-stack:focus-within .kibble-modal {
    display: block !important;
  }
}
.kibble-list, .food-list {
    display: flex;
    flex-direction: column;
    gap: 2px;
    width: 100%;
}
.kibble-option, .food-option {
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: center;
    gap: 4px;
    padding: 5px 3px;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;
}
.kibble-option:hover, .food-option:hover {
    background-color: var(--ha-card-background);
}
.kibble-option img, .food-option img {
    flex-shrink: 0;
    /* width: 30px;
    height: 30px; */
}
.kibble-option span, .food-option span {
    display: none;
}
/* Kibble Reset Button */ .kibble-reset-btn {
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: center;
    gap: 4px;
    padding: 5px 3px;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s;
    background-color: transparent;
}
.kibble-reset-btn:hover {
    background-color: var(--ha-card-background);
}
.kibble-reset-btn svg {
    width: 20px;
    height: 20px;
    fill: #666;
    flex-shrink: 0;
}
/* Kibble list divider */ .kibble-list-divider {
    width: 100%;
    height: 1px;
    background-color: rgba(138, 143, 141, 0.1);
    margin: 2px 0;
}
.modal-icon {
    position: absolute;
    top: -4px;
    right: -4px;
    width: 16px;
    height: 16px;
    opacity: 0.6;
}
.modal-icon svg {
    width: 100%;
    height: 100%;
}
/* Hide ×0 quantity icons in all Kibble rows */ .icon-stack.hide-zero, .icon-grid-item.hide-zero {
    display: none !important;
    visibility: hidden !important;
    width: 0 !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
}
/* ── 响应式列宽 ── */ @media (min-width: 768px) {
  /* 仅多列内容表（有第2个 th）：固定布局 */
  #base-table:has(thead th:nth-child(2)) {
    table-layout: fixed !important;
  }
  /* 首列锁宽 */
  #base-table:has(thead th:nth-child(2)) th:first-child,
  #base-table:has(thead th:nth-child(2)) td:first-child {
    width: 72px !important;
    min-width: 72px !important;
    max-width: 72px !important;
  }
  /* 末列（时间列）锁宽 */
  #base-table:has(.production-time-column) thead th:nth-child(4),
  #base-table:has(.production-time-column) tbody td.production-time-column {
    width: 42px !important;
    min-width: 42px !important;
    max-width: 42px !important;
  }
  /* 内容列：width: auto → fixed layout 下均分剩余空间 */
  #base-table:has(thead th:nth-child(2)) thead th:nth-child(n+2):not(:nth-child(4)),
  #base-table:has(thead th:nth-child(2)) tbody td:nth-child(n+2):not(.production-time-column) {
    width: auto !important;
    min-width: 0 !important;
  }
}
@media (max-width: 767px) {
  /* 窄屏：内容列固定最小宽度，触发水平滚动 */
  #base-table:has(thead th:nth-child(2)) thead th:nth-child(n+2):not(:nth-child(4)),
  #base-table:has(thead th:nth-child(2)) tbody td:nth-child(n+2):not(.production-time-column) {
    min-width: 140px !important;
  }
}
/* ── 其它生物：首行独立横滑（仅手机） ── */ @media (max-width: 767px) {
  .bio-row-h-scroll {
    overflow-x: auto;
    width: 0;
    min-width: 100%;
  }
  .bio-row-h-scroll > .flex {
    flex-wrap: nowrap;
    min-width: max-content;
  }
}
/* ── Accordion ── */ .accordion-body.collapsed { display: none; } /* ── Section Tabs ── */ .section-tab-bar { display: flex; padding: 4px 16px; justify-content: center; align-items: center; border-radius: 8px 8px 0 0; } .section-tab {
  padding: 4px 16px;
  cursor: pointer;
  user-select: none;
  font-weight: 600;
  font-size: 0.9em;
  color: rgba(255,255,255,0.5);
} .section-tab + .section-tab { border-left: 1px solid rgba(255,255,255,0.4); } .section-tab.tab-active { color: rgb(255, 255, 255); } .section-tab:not(.tab-active):hover { color: rgba(255,255,255,0.85); }
/* 图标自动反色：暗主题深色图反白，亮主题浅色图反色 */
img.ic-auto-light { filter: none; }
img.ic-auto-dark { filter: none; }
[data-theme="dark"] img.ic-auto-dark { filter: invert(1); }
[data-theme="light"] img.ic-auto-light { filter: invert(1); }
"""

# Table-level rules (any tab with tabular content — reference_table, mixed_content)
TABLE_CORE_CSS = """ha-card table {
  border-collapse: collapse !important;
  table-layout: fixed !important;
}
ha-card th, ha-card td {
  padding: 8px !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}
ha-card .sticky {
  position: sticky !important;
}
ha-card thead th {
  z-index: 20 !important;
  border-top: 0 !important;
}
ha-card .border {
  border-width: 0px 1px 1px 0px !important;
  border-color: var(--app-theme-color) !important;
}
ha-card tbody td {
  line-height: 1.4 !important;
  vertical-align: top !important;
  font-size: var(--paper-font-body1_-_font-size, 12px) !important;
}
ha-card .borderr {
  border-top-left-radius: 8px !important;
  border-top-right-radius: 8px !important;
  border-bottom-left-radius: var(--ha-card-border-radius, 12px) !important;
  border-bottom-right-radius: var(--ha-card-border-radius, 12px) !important;
  height: var(--collect-table-height, 82vh) !important;
}
/* Generic table styling */
ha-card .gen-table thead th {
  background-color: var(--secondary-background-color) !important;
  font-weight: 600;
}
ha-card .gen-table tbody tr:nth-child(odd) td {
  background-color: transparent !important;
}
ha-card .gen-table tbody tr:nth-child(even) td {
  background-color: var(--primary-background-color, rgba(0,0,0,0.05)) !important;
}
/* First column sticky + background */
ha-card .gen-table thead th:first-child,
ha-card .gen-table tbody td:first-child {
  position: sticky !important;
  left: 0 !important;
  background-color: var(--secondary-background-color) !important;
}
ha-card .gen-table thead th:first-child { z-index: 30 !important; }
ha-card .gen-table tbody td:first-child { z-index: 10 !important; }
ha-card .gen-table tbody tr:nth-child(even) td:first-child {
  background-color: var(--secondary-background-color) !important;
}
"""

# Full shared = card + table (used for tabs that need both)
SHARED_CSS = CARD_CORE_CSS + TABLE_CORE_CSS



# -------------------------------------------------------
# Expandable Detail CSS — card-style rounded blocks with map theme colors
# -------------------------------------------------------

# -------------------------------------------------------
# HTML renderers (output HTML body only, matching old CSS patterns)
# -------------------------------------------------------
def render_server_rules(data):
    tabs = data.get('tabs', [])
    if not tabs: return '<p>暂无服务器规则数据。</p>'
    parts = ['<div class="flex flex-col">']
    for tab in tabs:
        parts.append(f'<h3 style="margin:12px 0 4px">{esc(tab.get("name",""))}</h3>')
        parts.append(render_tab_html(tab))
    parts.append('</div>')
    return '\n'.join(parts)

def strip_and_append_empty_rows(html):
    """Remove all existing empty-row tr elements, then append one before the LAST </tbody> in each section."""
    import re
    # Strip all existing empty-row tr elements
    html = re.sub(r'<tr\s+class="empty-row"\s*>\s*<td>\s*</td>\s*</tr>', '', html)
    # Find each accordion-body section and process independently
    def process_section(sec_html):
        last_tbody = sec_html.rfind('</tbody>')
        if last_tbody != -1:
            sec_html = sec_html[:last_tbody] + '<tr class="empty-row"><td></td></tr>' + sec_html[last_tbody:]
        return sec_html
    # Split by accordion-body start tags, process each section's inner body
    parts = re.split(r'(<div[^>]*class="accordion-body[^"]*"[^>]*>)', html)
    if len(parts) == 1:
        return process_section(html)
    result = [parts[0]]
    for i in range(1, len(parts), 2):
        result.append(parts[i])  # the accordion-body opening tag
        body_html = parts[i+1] if i+1 < len(parts) else ''
        # Find the closing </div> that matches this accordion-body
        body_end = body_html.rfind('</div>')
        if body_end != -1:
            inner = body_html[:body_end]
            rest = body_html[body_end:]
            result.append(process_section(inner) + rest)
        else:
            result.append(process_section(body_html))
    return ''.join(result)

def render_tab_html(tab):
    """Render a single tab's content to HTML."""
    ttype = tab.get('type',''); parts = []
    # All other types get flex flex-col wrapper
    parts.append('<div class="flex flex-col">')
    if ttype == 'reference_table':
        cols = tab.get('columns',[]); rows = tab.get('rows',[])
        parts.append('<div class="borderr relative overflow-auto border border-gray-300"><table class="gen-table table-fixed border-collapse w-full min-w-max"><thead class="sticky top-0 z-20"><tr>')
        for col in cols: parts.append(f'<th class="border border-gray-300 p-2 text-center whitespace-nowrap">{esc(col)}</th>')
        parts.append('</tr></thead><tbody>')
        for row in rows:
            parts.append('<tr>')
            vals = row.values() if isinstance(row, dict) else [row]
            for val in vals: parts.append(f'<td class="border border-gray-300 p-2 text-left align-top">{esc(str(val))}</td>')
            parts.append('</tr>')
        parts.append('</tbody></table></div>')
    elif ttype == 'mixed_content':
        # Check if this tab has a map_filter
        has_map_filter=any(b.get('block_type')=='map_filter' for b in tab.get('content_blocks',[]))
        # Collect active server IDs from all blocks (for dynamic filter buttons)
        active_maps=set()
        if has_map_filter:
            for blk in tab.get('content_blocks',[]):
                bbt=blk.get('block_type','')
                if bbt=='info_card':
                    fm=blk.get('filter_maps','')
                    if fm: active_maps.update(fm.split(','))
                    for desc in blk.get('descriptions',[]):
                        if isinstance(desc,dict) and desc.get('server'):
                            active_maps.add(desc['server'])
                        sst=desc.get('server_states',{}) if isinstance(desc,dict) else {}
                        for k,v in sst.items():
                            if v in (1,2):
                                active_maps.add(k)
                    # Block-level server_states
                    blk_sst = blk.get('server_states',{})
                    for k,v in blk_sst.items():
                        if v in (1,2):
                            active_maps.add(k)


            active_maps.discard('')
            active_maps.difference_update(FIXED_STYLES_MAP.keys())
        for block in tab.get('content_blocks',[]):
            bt=block.get('block_type','')
            if bt=='text':
                style=block.get('style','default')
                collapsed=block.get('collapsed', False)
                css=''
                if style=='warning': css='background:rgba(230,168,23,0.2);border-left:3px solid #e6a817;padding:8px 12px;border-radius:4px;margin:8px 0'
                elif style=='danger': css='background:rgba(239,83,80,0.2);border-left:3px solid #ef5350;padding:8px 12px;border-radius:4px;margin:8px 0'
                content = esc(block.get('text',''))
                if collapsed:
                    parts.append(f'<details style="{css};cursor:pointer"><summary style="font-weight:600;color:var(--primary-text-color);padding:4px 0">📝 注意事项</summary><div style="margin-top:8px">{content}</div></details>')
                else:
                    parts.append(f'<div style="{css}">{content}</div>')
            elif bt=='divider':
                line_style = block.get('style','solid')
                if line_style == 'dotted': line_style = 'dashed'  # dotted removed, fallback
                div_color = block.get('color','auto')
                div_title = block.get('title','')
                div_title_bold = block.get('title_bold',False)
                color_style = f'--div-color:{div_color};--div-opacity:1' if div_color and div_color != 'auto' else '--div-color:var(--primary-text-color)'
                if div_title:
                    title_html = f'<strong>{esc(div_title)}</strong>' if div_title_bold else esc(div_title)
                    title_color = f'color:{div_color};' if div_color and div_color != 'auto' else 'color:var(--primary-text-color);'
                    parts.append(f'<div style="display:flex;align-items:center;gap:10px;margin:12px 0"><hr class="tb-divider tb-div-{line_style}" style="flex:1;min-width:0;{color_style}" /><span style="white-space:nowrap;font-size:0.85em;{title_color}">{title_html}</span><hr class="tb-divider tb-div-{line_style}" style="flex:1;min-width:0;{color_style}" /></div>')
                else:
                    parts.append(f'<hr class="tb-divider tb-div-{line_style}" style="{color_style}" />')
            elif bt=='table':
                if block.get('title'): parts.append(f'<h4 style="margin:12px 0 4px">{esc(block["title"])}</h4>')
                bcols=block.get('columns',[])
                parts.append('<div class="borderr relative overflow-auto border border-gray-300"><table class="gen-table table-fixed border-collapse w-full min-w-max"><thead class="sticky top-0 z-20"><tr>')
                for col in bcols: parts.append(f'<th class="border border-gray-300 p-2 text-center whitespace-nowrap">{esc(col)}</th>')
                parts.append('</tr></thead><tbody>')
                for row in block.get('rows',[]):
                    parts.append('<tr>')
                    for key,val in row.items():
                        is_img = key.endswith('_icon') or key.endswith('图片') or key.endswith('图标') or key.endswith('图')
                        if is_img and val: parts.append(f'<td class="border border-gray-300 p-2 text-center align-top"><img src="{esc(val)}" style="width:40px;height:40px;object-fit:contain" loading="lazy" /></td>')
                        else: parts.append(f'<td class="border border-gray-300 p-2 text-left align-top">{esc(str(val))}</td>')
                    parts.append('</tr>')
                parts.append('</tbody></table></div>')
            elif bt=='info_card':
                ic_title = block.get('title', '')
                ic_descs = block.get('descriptions', [])
                # Backward compat: old 'body' string
                if not ic_descs and block.get('body'):
                    ic_descs = [{'text': block['body'], 'bold': False, 'color': ''}]
                ic_icon = (block.get('images', [{}])[0] or {}).get('image_url', '') if block.get('images') else ''

                ic_hl = block.get('highlight', '')
                qc = block.get('quote_color', 'auto')
                if qc and qc != 'auto':
                    qc_style = ' style="border-left-color:{} !important"'.format(qc)
                else:
                    qc_style = ''
                # Auto-compute filter_maps from descriptions' server attributes (incl server_states)
                ic_fmaps=block.get('filter_maps','')
                if not ic_fmaps and has_map_filter:
                    fmaps=set()
                    for desc in ic_descs:
                        if isinstance(desc,dict):
                            if desc.get('server'):
                                fmaps.add(desc['server'])
                            sst=desc.get('server_states',{})
                            if sst:
                                for k in sst:
                                    if sst[k] in (1,2):
                                        fmaps.add(k)
                    # Block-level server_states
                    blk_sst = block.get('server_states',{})
                    for k,v in blk_sst.items():
                        if v in (1,2):
                            fmaps.add(k)
                    ic_fmaps=','.join(sorted(fmaps))
                ext='' if not has_map_filter else ' filterable'
                eattrs='' if not has_map_filter else ' data-filter-maps="{}"'.format(ic_fmaps)
                _ic_img = (block.get('images', [{}])[0] or {})
                if _ic_img.get('image_auto_color_mode') and _ic_img.get('image_auto_color_mode') != 'off':
                    ac_mode = _ic_img.get('image_auto_color_mode')
                else:
                    ac_mode = 'off'
                if ac_mode != 'off':
                    lum = _ic_img.get('image_native_luminance')
                    is_rev = (ac_mode == 'reverse')
                    if lum is not None and lum != 0.5:
                        use_lum = (1 - lum) if is_rev else lum
                        auto_cls = ' ic-auto-light' if use_lum > 0.5 else ' ic-auto-dark'
                    else:
                        auto_cls = ' ic-auto-dark'
                    mode_cls = ' ic-mode-reverse' if is_rev else ' ic-mode-normal'
                else:
                    auto_cls = ''
                    mode_cls = ''
                _block_qty = _ic_img.get('quantity', 0)
                # Block-level server_states (for card bg + title mdi)
                blk_states = block.get('server_states', {})
                blk_active = None; blk_st = 0
                for k,v in blk_states.items():
                    if v > 0: blk_active = k; blk_st = v
                blk_cls = ''
                if blk_active:
                    if blk_st == 1:
                        blk_cls = ' ic-linear-{}'.format(blk_active)
                    elif blk_st == 2:
                        blk_cls = ' ic-block-{}'.format(blk_active)
                # Title color from block data
                ic_title_color = block.get('title_color', 'auto')
                title_color_style = ''
                if ic_title_color and ic_title_color != 'auto':
                    title_color_style = ' style="color:{};"'.format(ic_title_color)
                parts.append('<div class="info-card-block{}{}" data-map="{}"{}{}>'.format(ext,blk_cls,ic_hl,eattrs,qc_style))
                if ic_icon:
                    _qty_html = '<span class="ic-qty">{}</span>'.format('\u00d7'+str(_block_qty)) if _block_qty else ''
                    if mode_cls:
                        parts.append('<span class="ic-icon-wrap{}" style="position:relative;display:inline-flex;flex-shrink:0"><img src="{}" class="ic-icon{}" loading="lazy" />{}</span>'.format(mode_cls, esc(ic_icon), auto_cls, _qty_html))
                    else:
                        parts.append('<span class="ic-icon-wrap" style="position:relative;display:inline-flex;flex-shrink:0"><img src="{}" class="ic-icon{}" loading="lazy" />{}</span>'.format(esc(ic_icon), auto_cls, _qty_html))
                parts.append('<div class="ic-body" style="display:flex;flex-wrap:wrap;gap:4px;align-items:center">')
                parts.append('<div class="ic-title" style="flex-basis:100%">')

                # Block-level map mdi icon for linear/block states (_default skips)
                if blk_active and blk_active != '_default':
                    _bstyle = _lookup_style(blk_active)
                    _bicon = _bstyle.get('icon','mdi:map')
                    _bcolor = _bstyle.get('color','')
                    if blk_st == 1:
                        parts.append('<ha-icon icon="{}" style="--mdc-icon-size:16px;width:16px;height:16px;margin-right:4px;color:{}"></ha-icon>'.format(_bicon, _bcolor))
                    elif blk_st == 2:
                        parts.append('<ha-icon icon="{}" style="--mdc-icon-size:16px;width:16px;height:16px;margin-right:4px;color:{}"></ha-icon>'.format(_bicon, _bcolor))
                # Card title: extract leading mdi, then ^ numbering, [] badges, inline mdi
                _title_mdi = re.match(r'mdi:([\w-]+)', ic_title, re.ASCII)
                if _title_mdi:
                    _title_icon = '<ha-icon icon="mdi:{}" style="color:inherit;--mdc-icon-size:16px;width:16px;height:16px;margin-right:4px;flex-shrink:0"></ha-icon>'.format(_title_mdi.group(1))
                    _title_text = ic_title[_title_mdi.end():].strip()
                else:
                    _title_icon = ''
                    _title_text = ic_title
                _title_is_hat = _title_text.startswith('^')
                if _title_is_hat:
                    _title_text = _title_text[1:].lstrip()
                    _title_text = '<span class="ic-badge ic-badge-num">1</span> ' + _render_badges(_render_mdi_inline(_title_text), False)
                else:
                    _title_text = _render_badges(_render_mdi_inline(_title_text), False)
                parts.append('<span{}>{}{}</span>'.format(title_color_style, _title_icon, _title_text))
                parts.append('</div>')
                _details_mark = len(parts)  # insertion point for <details> if no fold
                # Auto-detect: block has fold → collapsible
                ic_collapse = any(isinstance(d, dict) and d.get('type') == 'fold' for d in ic_descs)
                # Find fold marker index
                _fold_idx = -1
                if ic_collapse:
                    for _fi, _fd in enumerate(ic_descs):
                        if isinstance(_fd, dict) and _fd.get('type') == 'fold':
                            _fold_idx = _fi; break
                _details_opened = False
                # Pre-count ^-prefixed descriptions for auto-numbering within this block
                _hat_n = 0
                for desc in ic_descs:
                    if isinstance(desc, dict) and desc.get('type') in ('br', 'icon_group', 'fold', 'copy_key'):
                        continue
                    _dt = desc.get('text', '') if isinstance(desc, dict) else str(desc)
                    if _dt.startswith('^'):
                        _hat_n += 1
                _hat_idx = 0
                for desc in ic_descs:
                    if isinstance(desc, dict) and desc.get('type') == 'fold':
                        if ic_collapse and not _details_opened:
                            parts.append('<details name="ic-acc" ontoggle="if(this.open)this.parentElement.querySelectorAll(&quot;details[name=ic-acc]&quot;).forEach(s=>{if(s!==this)s.open=false})" style="cursor:pointer;margin:0;padding:0;width:100%"><summary class="ic-sum-top" style="display:block;font-size:0.65em;background:rgba(128,128,128,0.12);border:1px solid var(--border);border-radius:10px;padding:1px 7px;margin-bottom:2px;list-style:none;cursor:pointer;width:100%;box-sizing:border-box">···</summary><div style="display:flex;flex-wrap:wrap;gap:4px;align-items:center;width:100%">')
                            _details_opened = True
                        continue
                    if isinstance(desc, dict) and desc.get('type') == 'br':
                        parts.append('<div class="ic-br" style="flex-basis:100%;height:0"></div>')
                        continue
                    if isinstance(desc, dict) and desc.get('type') == 'icon_group':
                        ig_icons = desc.get('icons', [])
                        ig_title = desc.get('title', '')
                        dserver = desc.get('server', '')
                        srv_states = desc.get('server_states', {})
                        if not srv_states and dserver:
                            srv_states = {dserver: 2}
                        linear_maps = [k for k,v in srv_states.items() if v == 1]
                        block_maps = [k for k,v in srv_states.items() if v == 2]
                        # Build wrapper
                        _has_icons = any(icon.get('image_url', '') for icon in ig_icons)
                        _empty_cls = '' if _has_icons else ' ig-empty'
                        # No title + no icons → pure separator line
                        if not ig_title and not _has_icons and not block_maps:
                            parts.append('<hr style="flex-basis:100%;width:100%;border:none;border-top:1px solid var(--primary-text-color);opacity:0.15;margin:4px 0" />')
                            continue
                        if block_maps:
                            for bm in block_maps:
                                parts.append('<div class="ic-text ic-block-{}" style="flex-direction:column;align-items:flex-start!important">'.format(bm))
                        elif linear_maps:
                            parts.append(('<div class="ig-row-wrapper ic-linear-{}' + _empty_cls + '" style="flex-basis:100%;width:100%">').format(linear_maps[0]))
                        else:
                            parts.append(('<div class="ig-row-wrapper' + _empty_cls + '" style="flex-basis:100%;width:100%">').format())
                        # Title row
                        if ig_title:
                            title_icon_html = ''
                            _ig_title_text = ig_title
                            # Check for explicit mdi: prefix in title
                            _ig_mdi = re.match(r'mdi:([\w-]+)', ig_title, re.ASCII)
                            if _ig_mdi:
                                title_icon_html = '<ha-icon icon="mdi:{}" style="color:inherit;--mdc-icon-size:14px;width:14px;height:14px;margin-right:2px"></ha-icon>'.format(_ig_mdi.group(1))
                                _ig_title_text = ig_title[_ig_mdi.end():].strip()
                            elif linear_maps:
                                sm = _lookup_style(linear_maps[0])
                                icon = sm.get('icon', 'mdi:map')
                                title_icon_html = '<ha-icon icon="{}" style="color:inherit;--mdc-icon-size:14px;width:14px;height:14px;margin-right:2px"></ha-icon>'.format(icon)
                            elif block_maps:
                                sm = _lookup_style(block_maps[0])
                                icon = sm.get('icon', 'mdi:map')
                                title_icon_html = '<ha-icon icon="{}" style="color:inherit;--mdc-icon-size:14px;width:14px;height:14px;margin-right:2px"></ha-icon>'.format(icon)
                            # ^ aut numbering + [] badges (same as description lines)
                            _ig_is_hat = _ig_title_text.startswith('^')
                            if _ig_is_hat:
                                _hat_idx += 1
                                _ig_title_text = _ig_title_text[1:].lstrip()
                                hat_cls = 'ic-badge ic-badge-num ic-badge-hollow' if block_maps else 'ic-badge ic-badge-num'
                                _ig_title_text = '<span class="' + hat_cls + '">' + str(_hat_idx) + '</span> ' + _render_badges(_render_mdi_inline(_ig_title_text), bool(block_maps))
                            else:
                                _ig_title_text = _render_badges(_render_mdi_inline(_ig_title_text), bool(block_maps))
                            if block_maps:
                                # Block mode: no hr, text inherits white color from .ic-text.ic-block-{sid}
                                parts.append('<div class="ig-title-row" style="display:flex;align-items:center;gap:8px;margin:0 0 4px 0">')
                                parts.append('<span style="white-space:nowrap">{}{}</span>'.format(title_icon_html, _ig_title_text))
                                parts.append('</div>')
                            else:
                                parts.append('<div class="ig-title-row" style="display:flex;align-items:center;gap:8px;margin:4px 0">')
                                parts.append('<span class="ig-title-badge" style="white-space:nowrap">{}{}</span>'.format(title_icon_html, _ig_title_text))
                                parts.append('<hr class="ig-title-line" style="flex:1;min-width:0" />')
                                parts.append('</div>')
                        # Icon row (only render if has valid icons)
                        _ig_html = ''
                        for icon in ig_icons:
                            iu = icon.get('image_url', '')
                            if not iu:
                                continue
                            iq = icon.get('quantity', 0)
                            iac = icon.get('image_auto_color_mode', 'off')
                            ilum = icon.get('image_native_luminance')
                            ac_cls = ''
                            mode_cls = ''
                            if iac != 'off':
                                is_rev = (iac == 'reverse')
                                if ilum is not None and ilum != 0.5:
                                    use_lum = (1 - ilum) if is_rev else ilum
                                    ac_cls = ' ic-auto-light' if use_lum > 0.5 else ' ic-auto-dark'
                                else:
                                    ac_cls = ' ic-auto-dark'
                                mode_cls = ' ic-mode-reverse' if is_rev else ' ic-mode-normal'
                            qty = '<span class="ic-qty">x{}</span>'.format(iq) if iq else ''
                            _ig_html += '<span class="ig-item{}" style="position:relative;display:inline-flex;flex-shrink:0">{}{}</span>'.format(mode_cls, '<img src="' + esc(iu) + '" class="ig-img' + ac_cls + '" style="width:28px;height:28px;object-fit:contain;border-radius:4px" onerror="this.remove()" />', qty)
                        if _ig_html:
                            parts.append('<span class="ig-row" style="display:inline-flex;flex-wrap:wrap;gap:6px;align-items:center">' + _ig_html + '</span>')
                        parts.append('</div>')  # close wrapper (ic-text or ig-row-wrapper)
                        continue
                    # ---- copy_key: clickable copy button ----
                    if isinstance(desc, dict) and desc.get('type') == 'copy_key':
                        ck_label = desc.get('label', '复制')
                        ck_value = desc.get('value', '')
                        esc_label = ck_label.replace('\\', '\\\\').replace("'", "\\'")
                        esc_value = ck_value.replace('\\', '\\\\').replace("'", "\\'").replace('"', '&quot;').replace('\n', '\\n')
                        parts.append('<button class="ic-copy-key" onclick="event.stopPropagation();var t=\'{}\';var s=this.querySelector(\'span\');var o=s.textContent;s.textContent=\'已复制\';if(navigator.clipboard&&navigator.clipboard.writeText){{navigator.clipboard.writeText(t).catch(function(){{var ta=document.createElement(\'textarea\');ta.value=t;ta.style.cssText=\'position:fixed;opacity:0\';document.body.appendChild(ta);ta.select();ta.setSelectionRange(0,99999);document.execCommand(\'copy\');document.body.removeChild(ta);}});}}else{{var ta=document.createElement(\'textarea\');ta.value=t;ta.style.cssText=\'position:fixed;opacity:0\';document.body.appendChild(ta);ta.select();ta.setSelectionRange(0,99999);document.execCommand(\'copy\');document.body.removeChild(ta);}}setTimeout(function(){{s.textContent=o;}},3000);" style="padding:2px 6px;border-radius:6px;border:none;background:#0288d1;color:var(--primary-background-color);cursor:pointer;font-size:0.9em;font-weight:400;line-height:1.5;white-space:nowrap" title="点击复制"><ha-icon icon="mdi:content-copy" style="color:var(--primary-background-color);--mdc-icon-size:13px;width:13px;height:13px;flex-shrink:0;margin-right:2px"></ha-icon><span>{}</span></button>'.format(esc_value, _render_mdi_inline(ck_label)))
                        continue
                    dtext = desc.get('text', '') if isinstance(desc, dict) else str(desc)
                    # Flag ^ prefix for auto-numbering (badge rendered later after block_maps known)
                    _is_hat = dtext.startswith('^')
                    if _is_hat:
                        _hat_idx += 1
                    dbold = desc.get('bold', False) if isinstance(desc, dict) else False
                    dcolor = desc.get('color', '') if isinstance(desc, dict) else ''
                    dopacity = desc.get('opacity', 1.0) if isinstance(desc, dict) else 1.0
                    dserver = desc.get('server', '') if isinstance(desc, dict) else ''
                    # 3-state: server_states per-map (0=off, 1=linear, 2=block)
                    srv_states = desc.get('server_states', {}) if isinstance(desc, dict) else {}
                    if not srv_states and dserver:
                        srv_states = {dserver: 2}  # backward compat
                    states_json = json.dumps(srv_states) if srv_states else '{}'
                    # Build linear/block CSS classes
                    linear_maps = [k for k,v in srv_states.items() if v == 1]
                    block_maps = [k for k,v in srv_states.items() if v == 2]
                    ic_cls = 'ic-text'
                    if linear_maps:
                        ic_cls += ' ' + ' '.join('ic-linear-'+m for m in linear_maps)
                    if block_maps:
                        ic_cls += ' ' + ' '.join('ic-block-'+m for m in block_maps)
                    if '_default' in block_maps and (not dcolor or dcolor == 'auto'):
                        ic_cls += ' ic-auto-block'
                    dstyle = ''
                    if dbold: dstyle += 'font-weight:bold;'
                    if not block_maps:
                        if dcolor and dcolor not in ('#000000', 'auto'):
                            dstyle += 'color:{};'.format(dcolor)
                        elif linear_maps:
                            _lm_color = _lookup_style(linear_maps[0]).get('color', '')
                            if _lm_color and _lm_color != 'auto':
                                dstyle += 'color:{};'.format(_lm_color)
                    if block_maps and '_default' in block_maps:
                        if dcolor and dcolor != 'auto':
                            dstyle += '--ic-block-bg:{};background:{}!important;color:var(--primary-background-color)!important;'.format(dcolor, dcolor)

                    if dopacity != 1.0: dstyle += 'opacity:{};'.format(dopacity)
                    if dstyle: dstyle = ' style="{}"'.format(dstyle)
                    # Server icon prefix (show highest-priority map icon)
                    srv_icon = ''
                    _show_maps = block_maps + linear_maps
                    if _show_maps:
                        _sid = _show_maps[0]
                        # _hint/_warn/_remark always show icon; _default only if mdi: prefix
                        if _sid in ('_hint', '_warn', '_remark'):
                            _style = _lookup_style(_sid)
                            _icon = _style.get('icon','mdi:map')
                            _mdi_ov = re.match(r'^mdi:([\w-]+)', dtext, re.ASCII)
                            if _mdi_ov:
                                _icon = 'mdi:' + _mdi_ov.group(1)
                                dtext = dtext[_mdi_ov.end():].strip()
                            srv_icon = '<ha-icon icon="{}" style="--mdc-icon-size:14px;width:14px;height:14px;margin-right:2px;color:{}"></ha-icon>'.format(_icon, _style.get('color','var(--primary-text-color)'))
                        elif _sid == '_default':
                            # _default: no icon unless user adds mdi:xxx prefix
                            _mdi_ov = re.match(r'^mdi:([\w-]+)', dtext, re.ASCII)
                            if _mdi_ov:
                                _icon = 'mdi:' + _mdi_ov.group(1)
                                dtext = dtext[_mdi_ov.end():].strip()
                                srv_icon = '<ha-icon icon="{}" style="--mdc-icon-size:14px;width:14px;height:14px;margin-right:2px;color:var(--primary-text-color)"></ha-icon>'.format(_icon)
                        else:
                            _style = _lookup_style(_sid)
                            _icon = _style.get('icon','mdi:map')
                            srv_icon = '<ha-icon icon="{}" style="--mdc-icon-size:14px;width:14px;height:14px;margin-right:2px;color:{}"></ha-icon>'.format(_icon, _style.get('color','var(--primary-text-color)'))
                    elif dserver:
                        _style = _lookup_style(dserver)
                        _icon = _style.get('icon','mdi:map')
                        srv_icon = '<ha-icon icon="{}" style="--mdc-icon-size:14px;width:14px;height:14px;margin-right:2px;color:{}"></ha-icon>'.format(_icon, _style.get('color','var(--primary-text-color)'))
                    dserver_attr=' data-server="{}" data-server-states=\'{}\''.format(dserver, states_json)
                    _dimg = ''
                    _dimg_url = (desc.get('images', [{}])[0] or {}).get('image_url','')
                    _qty = (desc.get('images', [{}])[0] or {}).get('quantity', 0) or desc.get('quantity', 0)
                    _qty_tag = '<span class="ic-qty">×{}</span>'.format(_qty) if _qty else ''
                    if _dimg_url:
                        _dac_mode = (desc.get('images', [{}])[0] or {}).get('image_auto_color_mode','off')
                        _dac_lum = (desc.get('images', [{}])[0] or {}).get('image_native_luminance')
                        _dac_cls = ''
                        _dac_mode_cls = ''
                        if _dac_mode != 'off':
                            _is_rev = (_dac_mode == 'reverse')
                            if _dac_lum is not None and _dac_lum != 0.5:
                                _use_lum = (1 - _dac_lum) if _is_rev else _dac_lum
                                _dac_cls = ' ic-auto-light' if _use_lum > 0.5 else ' ic-auto-dark'
                            else:
                                _dac_cls = ' ic-auto-dark'
                            _dac_mode_cls = ' ic-mode-reverse' if _is_rev else ' ic-mode-normal'
                        _img_tag = '<img src="{}" class="ic-desc-img{}" onerror="this.remove()" />'.format(esc(_dimg_url), _dac_cls)
                        if block_maps:
                            _img_tag = '<img src="{}" class="ic-block-img{}" onerror="this.remove()" />'.format(esc(_dimg_url), _dac_cls)
                        if _dac_mode_cls:
                            if block_maps:
                                _img_tag = '<img src="{}" class="ic-block-img{}{}" onerror="this.remove()" />'.format(esc(_dimg_url), _dac_cls, _dac_mode_cls)
                            else:
                                _img_tag = '<span class="ic-desc-wrap{}" style="position:relative;display:inline-flex;flex-shrink:0">{}</span>'.format(_dac_mode_cls, _img_tag)
                        _dimg = _img_tag + _qty_tag
                    else:
                        _dimg = _qty_tag
                    # Compute rendered text (after block_maps is known for _render_badges)
                    if _is_hat:
                        hat_cls = 'ic-badge ic-badge-num ic-badge-hollow' if block_maps else 'ic-badge ic-badge-num'
                        dtext_rendered = '<span class="' + hat_cls + '">' + str(_hat_idx) + '</span> ' + _render_badges(_render_mdi_inline(dtext[1:].lstrip()), bool(block_maps))
                    else:
                        dtext_rendered = _render_badges(_render_mdi_inline(dtext), bool(block_maps))
                    parts.append('<div class="{}"{{}}{{}}>{{}}{{}}{{}}</div>'.format(ic_cls).format(dstyle, dserver_attr, srv_icon, dtext_rendered, _dimg))
                if ic_collapse:
                    if not _details_opened:
                        # No fold marker: old behavior — everything in <details>
                        parts.insert(_details_mark, '<details name="ic-acc" ontoggle="if(this.open)this.parentElement.querySelectorAll(&quot;details[name=ic-acc]&quot;).forEach(s=>{if(s!==this)s.open=false})" style="cursor:pointer;margin:0;padding:0;width:100%"><summary class="ic-sum-top" style="display:block;font-size:0.65em;background:rgba(128,128,128,0.12);border:1px solid var(--border);border-radius:10px;padding:1px 7px;margin-bottom:2px;list-style:none;cursor:pointer;width:100%;box-sizing:border-box">···</summary><div style="display:flex;flex-wrap:wrap;gap:4px;align-items:center;width:100%">')
                    parts.append('<span class="ic-sum-end" style="font-size:0.65em;background:rgba(128,128,128,0.12);border:1px solid var(--border);border-radius:10px;padding:1px 7px;margin-top:2px;flex-basis:100%;cursor:pointer" onclick="event.stopPropagation();var d=this.closest(\'details\');var root=d.getRootNode();root.querySelectorAll(\'details[name=ic-acc]\').forEach(function(o){o.open=false});">···</span></div></details>')
                parts.append('</div>')
                parts.append('</div>')
            elif bt=='map_filter':
                # Dynamic filter buttons based on actual server references in this tab

                filter_js=(
                    "var s=this;var r=s.getRootNode();"
                    "if(s._w){s.checked=false;s._w=false;s.parentElement.classList.remove('active');"
                    "r.querySelectorAll('.filter-label').forEach(function(l){l.style.setProperty('opacity','','')});"
                    "r.querySelectorAll('.filterable,.ic-text[data-server-states],.ic-br').forEach(function(e){e.style.setProperty('display','','')});"
                    "return}"
                    "r.querySelectorAll('.filter-radio').forEach(function(o){o._w=false;o.parentElement.classList.remove('active')});"
                    "r.querySelectorAll('.filter-label').forEach(function(l){l.style.setProperty('opacity','0.5','important')});"
                    "s._w=true;s.parentElement.classList.add('active');s.parentElement.style.setProperty('opacity','1','important');"
                    "r.querySelectorAll('.filterable').forEach(function(e){var fm=e.getAttribute('data-filter-maps')||'';var v=!fm||fm.indexOf(s.value)>=0;e.style.setProperty('display',v?'':'none',v?'':'important')});"

                    "r.querySelectorAll('.ic-text[data-server-states]').forEach(function(e){var pf=e.closest('.filterable');if(pf&&(pf.classList.contains('ic-block-'+s.value)||pf.classList.contains('ic-linear-'+s.value))){e.style.setProperty('display','','');return}var ss=JSON.parse(e.getAttribute('data-server-states')||'{}');var st=(ss[s.value]||0);if(st===0){e.style.setProperty('display','none','important')}else{e.style.setProperty('display','','');if(st===1){e.classList.add('ic-linear-'+s.value)}else{e.classList.add('ic-block-'+s.value)}}});"
                    "r.querySelectorAll('.ic-br').forEach(function(e){var nxt=e.nextElementSibling;while(nxt&&nxt.nodeType===1&&!nxt.classList.contains('ic-text')&&!nxt.classList.contains('ic-br'))nxt=nxt.nextElementSibling;var prev=e.previousElementSibling;while(prev&&prev.nodeType===1&&!prev.classList.contains('ic-text')&&!prev.classList.contains('ic-br'))prev=prev.previousElementSibling;var nxtOk=nxt&&nxt.classList.contains('ic-text')&&nxt.style.getPropertyValue('display')!=='none';var prevOk=prev&&prev.classList.contains('ic-text')&&prev.style.getPropertyValue('display')!=='none';var show=nxtOk&&prevOk;e.style.setProperty('display',show?'':'none',show?'':'important')})"
                )
                if not active_maps:
                    parts.append('<div class="filter-bar" style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;border:2px dashed var(--border);border-radius:8px;padding:8px 12px;color:var(--secondary-text-color);font-size:.85em;justify-content:center">暂无地图标记 — 为板块/描述指定归属服务器后出现筛选按钮</div>')
                else:
                    parts.append('<div class="filter-bar" style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px">')
                    for srv_id in sorted(active_maps):
                        icn=SERVER_MAP.get(srv_id,{}).get('icon','mdi:server')
                        label=SERVER_MAP.get(srv_id,{}).get('label',srv_id)
                        parts.append('<label class="filter-label" data-map="{}"><input type="radio" name="map-filter" class="filter-radio" value="{}" onclick="{}"><ha-icon icon="{}"></ha-icon> {}</label>'.format(srv_id,srv_id,filter_js,icn,label))
                    parts.append('</div>')
            elif bt=='server_grid':
                # Render a server_grid block
                cols=block.get('columns',[])
                items=block.get('items',[])
                fl=block.get('first_col_label','补给品')
                hfc=block.get('hide_first_col',False)
                tid='server-matrix' if hfc else 'supply-table'
                tcl='gen-table server-matrix' if hfc else 'table-fixed border-collapse w-full min-w-max'
                parts.append('<div class="borderr relative overflow-auto border border-gray-300"><table id="{}" class="{}">'.format(tid,tcl))
                parts.append('<thead class="sticky top-0 z-20"><tr>')
                if not hfc:
                    parts.append('<th class="sticky left-0 z-30 border border-gray-300 p-2 text-center whitespace-nowrap">{}</th>'.format(fl))
                for col in cols:
                    icon=col.get('icon','mdi:server')
                    label=esc(col.get('label',''))
                    mid=col.get('server','')
                    parts.append('<th class="border border-gray-300 p-2 text-center whitespace-nowrap" data-map="{}"><label class="col-head" title="切换：隐藏该列中的空行"><input type="checkbox" class="col-toggle" hidden /><ha-icon icon="{}"></ha-icon> {}</label></th>'.format(mid,icon,label))
                parts.append('</tr></thead><tbody>')
                for item in items:
                    parts.append('<tr>')
                    if not hfc:
                        iu=item.get('icon_url','')
                        ius=item.get('icon_urls',[iu] if iu else [])
                        mi=item.get('mdi_icon','')
                        parts.append('<td class="sticky left-0 z-10 border border-gray-300 p-2 text-center whitespace-nowrap">')
                        parts.append('<label class="row-head"><input type="checkbox" class="row-toggle" hidden />')
                        if mi: parts.append('<ha-icon icon="{}"></ha-icon>'.format(mi))
                        for u in ius:
                            if u: parts.append('<img src="{}" width="40" height="40" />'.format(esc(u)))
                        parts.append('</label></td>')
                    for col in cols:
                        sid=col.get('server','')
                        locs=item.get('locations',{}).get(sid,[])
                        if locs:
                            parts.append('<td class="border border-gray-300 p-2 text-left align-top" data-map="{}">'.format(sid))
                            for loc in locs:
                                loc_name=esc(loc.get('name',''))
                                loc_img=loc.get('image_url','')
                                loc_badge=loc.get('badge','')
                                loc_bt=loc.get('badge_type','badge-warning')
                                parts.append('{}<br />'.format(loc_name))
                                if loc_img: parts.append('<div class="flex flex-wrap gap-1 items-start mb-2"><img src="{}" /></div>'.format(esc(loc_img)))
                                if loc_badge: parts.append('<span class="badge badge-sm {} mt-1">{}</span>'.format(loc_bt,esc(loc_badge)))
                            parts.append('</td>')
                        else:
                            parts.append('<td class="border border-gray-300 p-2 text-left align-top"></td>')
                    parts.append('</tr>')
                parts.append('</tbody></table></div>')
            elif bt=='expandable_detail':
                md=block.get('map',{}) or {}
                sd=block.get('spot',{}) or {}
                od=block.get('output',{}) or {}
                fd=block.get('flow',{}) or {}
                mt=md.get('text','')
                mh=md.get('highlight','')
                st=sd.get('text','')
                iu=od.get('icon_url','') if isinstance(od,dict) else ''
                mi=SERVER_MAP.get(mh,{}).get('icon','mdi:map-marker')
                blks=fd.get('blocks',[]) if isinstance(fd,dict) else []
                hb=bool(blks)
                eext='' if not has_map_filter else ' filterable'
                eeattrs='' if not has_map_filter else ' data-filter-maps="{}"'.format(block.get('filter_maps',''))
                parts.append('<details class="exp-block{}" data-map="{}"{}>'.format(eext,mh,' open' if not hb else '',eeattrs))
                parts.append('<summary class="exp-summary">')
                if iu:
                    parts.append('<img src="{}" class="exp-icon" loading="lazy" />'.format(esc(iu)))
                else:
                    parts.append('<div class="exp-icon" style="display:flex;align-items:center;justify-content:center"><ha-icon icon="mdi:help-circle"></ha-icon></div>')
                parts.append('<div class="exp-info">')
                parts.append('<div class="exp-title"><ha-icon icon="{}"></ha-icon> {}</div>'.format(mi,esc(st)))
                # Output descriptions (multi-description)
                out_descs = od.get('descriptions', []) if isinstance(od, dict) else []
                if not out_descs and isinstance(od, dict) and od.get('name'):
                    out_descs = [{'text': od['name'], 'bold': False, 'color': ''}]
                for ddesc in out_descs:
                    dtext = ddesc.get('text', '') if isinstance(ddesc, dict) else str(ddesc)
                    dbold = ddesc.get('bold', False) if isinstance(ddesc, dict) else False
                    dopacity = ddesc.get('opacity', 1.0) if isinstance(ddesc, dict) else 1.0
                    dstyle = 'margin:2px 0;font-size:0.9em'
                    if dbold: dstyle += ';font-weight:bold'
                    if dopacity != 1.0: dstyle += ';opacity:{}'.format(dopacity)
                    parts.append('<div style="{}">{}</div>'.format(dstyle, esc(dtext)))
                if mt: parts.append('<div class="exp-subtitle">{}</div>'.format(esc(mt)))
                parts.append('</div>')
                if hb: parts.append('<span class="exp-arrow">▼</span>')
                parts.append('</summary>')
                if hb:
                    parts.append('<div class="exp-body">')
                    for blk in blks:
                        if blk.get('type')=='text':
                            bt_t=blk.get('text','')
                            parts.append('<p style="margin:4px 0">{}</p>'.format(esc(bt_t)))
                        elif blk.get('type')=='ol':
                            parts.append('<ol>')
                            for step in blk.get('steps',[]):
                                if isinstance(step,dict) and 'html' in step:
                                    sh=step.get('html','')
                                    parts.append('<li>{}</li>'.format(sh))
                                else:
                                    parts.append('<li>{}</li>'.format(esc(str(step))))
                            parts.append('</ol>')
                        elif blk.get('type')=='md_hl':
                            parts.append('<span class="{}">{}</span>'.format(blk.get('class',''),blk.get('text','')))
                        elif blk.get('type')=='strong':
                            parts.append('<strong>{}</strong>'.format(blk.get('text','')))
                    parts.append('</div>')
                parts.append('</details>')
    elif ttype == 'farming_table':
        cols=tab.get('columns',[]); rows=tab.get('rows',[])
        parts.append('<div class="borderr relative overflow-auto border border-gray-300"><table class="gen-table table-fixed border-collapse w-full min-w-max"><thead class="sticky top-0 z-20"><tr>')
        for col in cols: parts.append(f'<th class="border border-gray-300 p-2 text-center whitespace-nowrap">{esc(col)}</th>')
        parts.append('</tr></thead><tbody>')
        for row in rows:
            parts.append('<tr>')
            for key,val in row.items():
                if key.endswith('_icon') and val: parts.append(f'<td class="border border-gray-300 p-2 text-center align-top"><img src="{esc(val)}" /></td>')
                else: parts.append(f'<td class="border border-gray-300 p-2 text-left align-top">{esc(str(val))}</td>')
            parts.append('</tr>')
        parts.append('</tbody></table></div>')
    parts.append('</div>')
    return strip_and_append_empty_rows('\n'.join(parts))






def render_farming_table(tab):
    """Render farming/采集 table with rowspan, clamp-toggle, map-badge, and step lists."""
    columns = tab.get('columns', [])
    rows = tab.get('rows', [])
    parts = ['<div class="flex flex-col">']
    parts.append('<div class="borderr relative overflow-auto border border-gray-300">')
    parts.append('<table class="table-fixed border-collapse w-full min-w-max">')
    parts.append('<thead class="sticky top-0 z-20"><tr>')
    for col in columns:
        parts.append(f'<th class="border border-gray-300 p-2 text-center whitespace-nowrap">{esc(col)}</th>')
    parts.append('</tr></thead><tbody>')

    map_remaining = 0
    spot_remaining = 0

    for row in rows:
        parts.append('<tr>')

        # Map cell
        map_data = row.get('map')
        if map_data is None:
            # Cell omitted due to rowspan
            pass
        elif map_data == {} or not isinstance(map_data, dict):
            parts.append('<td class="border border-gray-300 p-2"></td>')
        else:
            text = map_data.get('text', '')
            rspan = map_data.get('rowspan')
            highlight = map_data.get('highlight')
            classes = ['border', 'border-gray-300', 'p-2', 'text-center', 'align-top', 'col-map']
            no_badge = highlight in ('neutral', 'col-neutral')
            if no_badge:
                classes.append('col-neutral')
            attrs = f' class="{" ".join(classes)}"'
            if rspan:
                attrs += f' rowspan="{rspan}"'
                map_remaining = rspan - 1
            if highlight and not no_badge:
                attrs += f' data-map="{highlight}"'
            parts.append(f'<td{attrs}>')
            if highlight and not no_badge:
                # Map server ID to icon
                icon=SERVER_MAP.get(highlight,{}).get('icon','mdi:server')
                parts.append(f'<div class="map-badge"><ha-icon icon="{icon}"></ha-icon><div>{esc(text)}</div></div>')
            else:
                parts.append(esc(text))
            parts.append('</td>')
        if map_remaining > 0:
            map_remaining -= 1

        # Spot cell
        spot_data = row.get('spot')
        if spot_data is None:
            pass
        elif spot_data == {} or not isinstance(spot_data, dict):
            parts.append('<td class="border border-gray-300 p-2"></td>')
        else:
            text = spot_data.get('text', '')
            rspan = spot_data.get('rowspan')
            highlight = spot_data.get('highlight')
            classes = ['border', 'border-gray-300', 'p-2', 'text-left', 'align-top', 'col-spot']
            no_badge_s = highlight in ('neutral', 'col-neutral')
            if no_badge_s:
                classes.append('neutral')
            attrs = f' class="{" ".join(classes)}"'
            if rspan:
                attrs += f' rowspan="{rspan}"'
                spot_remaining = rspan - 1
            if highlight and not no_badge_s:
                attrs += f' data-map="{highlight}"'
            parts.append(f'<td{attrs}>{esc(text)}</td>')
        if spot_remaining > 0:
            spot_remaining -= 1

        # Output cell
        output_data = row.get('output', {})
        icon_url = output_data.get('icon_url', '') if isinstance(output_data, dict) else ''
        font_sb = ' font-semibold' if (isinstance(output_data, dict) and output_data.get('font_semibold')) else ''
        parts.append(f'<td class="border border-gray-300 p-2 align-top col-output{font_sb}">')
        if icon_url:
            parts.append(f'<img src="{esc(icon_url)}" alt="" />')
        parts.append('</td>')

        # Flow cell — render content blocks in order
        flow_data = row.get('flow', {})
        if isinstance(flow_data, dict):
            blocks = flow_data.get('blocks', [])
            parts.append('<td class="border border-gray-300 p-2 text-left align-top col-flow">')

            if not blocks:
                pass
            elif len(blocks) == 1 and blocks[0]['type'] == 'text':
                # Single plain text — no clamp needed
                parts.append(esc(blocks[0]['text']))
            else:
                # Multiple blocks or single non-text block — use clamp-wrap
                parts.append('<label class="clamp-wrap">')
                parts.append('<input type="checkbox" class="clamp-toggle" />')
                parts.append('<div class="clamp-content">')
                for block in blocks:
                    if block['type'] == 'text':
                        parts.append(esc(block['text']))
                    elif block['type'] == 'ol':
                        parts.append('<ol>')
                        for step in block['steps']:
                            if isinstance(step, dict) and 'html' in step:
                                parts.append(f'<li>{step["html"]}</li>')
                            else:
                                parts.append(f'<li>{esc(str(step))}</li>')
                        parts.append('</ol>')
                    elif block['type'] == 'md_hl':
                        parts.append(f'<span class="{block["class"]}">{block["text"]}</span>')
                    elif block['type'] == 'strong':
                        parts.append(f'<strong>{block["text"]}</strong>')
                parts.append('</div>')
                parts.append('<span class="clamp-btn" aria-hidden="true"></span>')
                parts.append('</label>')
            parts.append('</td>')
        else:
            parts.append('<td class="border border-gray-300 p-2 text-left align-top col-flow"></td>')

        parts.append('</tr>')

    parts.append('</tbody></table></div>')
    parts.append('</div>')
    return '\n'.join(parts)


# Version stamp
VERSION = 'v20260611-1'

# -------------------------------------------------------
if __name__ == "__main__":
    _pf = '/config/www/asa-data/_bl_step.txt'
    def _log_step(msg, mode='a'):
        with open(_pf, mode) as f:
            from datetime import datetime
            f.write(f"{datetime.now().strftime('%H:%M:%S')} {msg}\n")
    _log_step("INIT", 'w')
    # -------------------------------------------------------
    with open(os.path.join(DATA_DIR, 'server_rules.json'), 'r', encoding='utf-8') as f:
        sr_data = json.load(f)
    with open(os.path.join(DATA_DIR, 'tribe_ops.json'), 'r', encoding='utf-8') as f:
        to_data = json.load(f)
    with open(os.path.join(DATA_DIR, 'asa_base_quick_ref.json'), 'r', encoding='utf-8') as f:
        bq_data = json.load(f)
    _log_step("DATA_OK")

    lovelace_path = '/config/lovelace' if os.path.exists('/config') else r'A:\NetSarang\Xftp 8\Temporary\lovelace'
    lovelace_ll_path = '/config/lovelace.lovelace' if os.path.exists('/config') else r'A:\NetSarang\Xftp 8\Temporary\lovelace.lovelace'
    # Read from HA's storage first to capture any manual edits (HA UI writes here)
    storage_src = '/config/.storage/lovelace.lovelace' if os.path.exists('/config') else lovelace_path
    _log_step('READING_' + storage_src.replace('/','_')[-30:])
    with open(storage_src, 'r', encoding='utf-8') as f:
        lovelace = json.load(f)
    _log_step('LOVELACE_LOADED')
    views = lovelace['data']['config']['views']
    _log_step('VIEWS_OK')
    # Build timestamp footer for all ASA pages
    build_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    BLD_FOOTER = f'<div style="text-align:right;opacity:0.12;font-size:0.6em;margin-top:20px;user-select:none">build {build_ts}</div>'
    # -------------------------------------------------------
    # Decoupled view management: path-based, non-ASA views preserved as-is
    ASA_BUILD_PATHS = {
        'asa-server-rules',
        'info_whiterober',
        'base_isl', 'base_sco', 'base_cen', 'base_abe',
        'base_ast', 'base_ext', 'base_rag', 'base_val',
        'base_los', 'base_gen', 'base_bob',
    }
    non_asa_views = []
    asa_built_views = []
    for v in views:
        p = v.get('path', '')
        if p in ASA_BUILD_PATHS:
            pass  # Will be rebuilt from JSON data, not preserved
        elif v != {}:
            non_asa_views.append(v)
    _log_step('VIEWS_UPDATED')

    # --- Helper: content card matching OLD pattern ---
    def make_content_card(html_content, tab_type=None, tab=None):
        if tab_type == 'mixed_content' and tab:
            # Compose CSS from block types present
            block_types = {b.get('block_type','') for b in tab.get('content_blocks',[])}
            has_map_filter = 'map_filter' in block_types
            has_icon_group = any(
                isinstance(d, dict) and d.get('type') == 'icon_group'
                for b in tab.get('content_blocks', [])
                for d in b.get('descriptions', [])
            )
            active_maps = set()
            if has_map_filter:
                for blk in tab.get('content_blocks',[]):
                    bbt = blk.get('block_type','')
                    if bbt == 'info_card':
                        fm = blk.get('filter_maps','')
                        if fm: active_maps.update(fm.split(','))
                        for desc in blk.get('descriptions',[]):
                            if isinstance(desc,dict) and desc.get('server'):
                                active_maps.add(desc['server'])
                            sst = desc.get('server_states',{}) if isinstance(desc,dict) else {}
                            for k,v in sst.items():
                                if v in (1,2):
                                    active_maps.add(k)
                        blk_sst = blk.get('server_states',{})
                        for k,v in blk_sst.items():
                            if v in (1,2):
                                active_maps.add(k)

                active_maps.discard('')
            css = CARD_CORE_CSS + TABLE_CORE_CSS

            if 'map_filter' in block_types:
                css += 'ha-card .filter-bar{display:flex!important;flex-wrap:wrap!important;gap:0!important;margin-bottom:12px!important}'
                css += 'ha-card .filter-radio{position:absolute!important;opacity:0!important;width:0!important;height:0!important}'
                css += 'ha-card .filter-label{display:inline-flex!important;align-items:center!important;gap:4px!important;padding:4px 12px!important;border-radius:16px!important;border:1px solid var(--divider-color)!important;font-size:.85em!important;cursor:pointer!important;user-select:none!important;line-height:1.4!important;white-space:nowrap!important;min-height:28px!important;margin-right:6px!important;margin-bottom:8px!important}'
                for sid, sm in SERVER_MAP.items():
                    css += 'ha-card .filter-label[data-map='+sid+']{background:'+sm['color']+'!important;color:var(--primary-background-color)!important;border-color:'+sm['color']+'!important}'
                css += 'ha-card .filter-label{transition:opacity .2s!important}'
                css += 'ha-card .filter-label ha-icon{pointer-events:none!important}'
                css += 'ha-card:has(.filter-radio[value=\"\"]:checked) .filterable{display:flex!important}'
                for sid in SERVER_MAP:
                    css += 'ha-card:has(.filter-radio[value=\"'+sid+'\"]:checked) .filterable{display:none!important}'
                    css += 'ha-card:has(.filter-radio[value=\"'+sid+'\"]:checked) .filterable[data-filter-maps*='+sid+']{display:flex!important}'
            if 'info_card' in block_types:
                IC_CSS = make_ic_css(SERVER_MAP, FIXED_STYLES_MAP)
                css += IC_CSS
            # copy_key button
            css += 'ha-card .ic-copy-key{display:inline-flex!important;align-items:center!important;gap:4px!important;padding:2px 6px!important;border-radius:6px!important;border:none!important;background:#0288d1!important;color:var(--primary-background-color)!important;cursor:pointer!important;font-size:0.9em!important;font-weight:400!important;line-height:1.5!important;transition:filter 0.2s!important}'
            css += 'ha-card .ic-copy-key:hover{filter:brightness(1.15)!important}'
            css += 'ha-card .ic-copy-key ha-icon{color:var(--primary-background-color)!important}'


        elif tab_type in ('reference_table', 'mixed_content'):
            css = CARD_CORE_CSS + TABLE_CORE_CSS
        else:
            css = CARD_CORE_CSS

        css += ' ha-card ha-icon{line-height:0!important}'
        css += ' ha-card div.flex.flex-col>div:not([class]){margin-top:0!important}'

        inner_card = {
            "entity": "",
            "content": html_content,
            "ignore_line_breaks": True,
            "always_update": False,
            "parse_jinja": True,
            "code_editor": "Ace",
            "entities": [],
            "bindings": [],
            "actions": [],
            "plugins": {"daisyui": {"enabled": True, "url": "https://cdn.jsdelivr.net/npm/daisyui@latest/dist/full.css", "theme": "dark", "overrideCardBackground": False}, "tailwindElements": {"enabled": False}},
            "debounceChangePeriod": 500,
            "type": "custom:tailwindcss-template-card",
            "card_mod": {"style": css}
        }

        return {
            "type": "custom:mod-card",
            "card_mod": {"style": "ha-card {\n  box-shadow: none !important;\n  background: transparent !important;\n}\n"},
            "card": inner_card
        }

    # Tab button (matching old format exactly)
    def make_tab_button(tab_name, tab_desc, entity_id='input_select.info_tribe_tab'):
        return {
            "type": "custom:button-card",
            "tap_action": {
                "action": "call-service",
                "service": "input_select.select_option",
                "service_data": {"entity_id": entity_id, "option": tab_name}
            },
            "only_custom_fields": True,
            "styles": {
                "card": [
                    {"background": f"[[[ return states['{entity_id}'].state === '{tab_name}' ? '#16a34a' : 'var(--card-background-color, #1e1e1e)'; ]]]"},
                    {"color": f"[[[ return states['{entity_id}'].state === '{tab_name}' ? '#fff' : 'var(--primary-text-color, #ddd)'; ]]]"},
                    {"font-weight": "bold"}, {"border-radius": "8px"},
                    {"min-width": "70px"}, {"max-width": "200px"}, {"width": "auto"},
                    {"box-shadow": "none"}, {"transition": "background 0.2s"},
                    {"padding": "12px 12px"}, {"margin-right": "0px"},
                    {"display": "flex"}, {"flex-direction": "column"},
                    {"align-items": "stretch"}, {"text-align": "left"}, {"line-height": "18px"}
                ],
                "custom_fields": {
                    "tabcontent": [
                        {"display": "flex"}, {"flex-direction": "column"},
                        {"align-items": "stretch"}, {"width": "100%"}, {"text-align": "left"}
                    ]
                }
            },
            "custom_fields": {
                "tabcontent": f"[[[\n  return `\n    <div style=\"font-size:1em;font-weight:bold;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-align:left;\">\n      {tab_name}\n    </div>\n    <div style=\"font-size:12px;font-weight:normal;margin-top:4px;white-space:nowrap;max-width:100%;overflow:hidden;text-overflow:ellipsis;text-align:right;\">\n      {tab_desc}\n    </div>\n  `;\n]]]"
            },
            "card_mod": {"style": "#tabcontent {\n  grid-area: unset !important;\n}\n"}
        }

    # 1. SERVER RULES → views[40] — tabbed layout, same as tribe ops
    sr_tabs = sr_data.get('tabs', [])
    sr_tab_buttons = [make_tab_button(t['name'], t.get('description',''), 'input_select.info_server_rules_tab') for t in sr_tabs]
    sr_tab_cards = []
    for t in sr_tabs:
        tname = t['name']
        ttype = t.get('type','')
        t_html = render_tab_html(t)
        # Inject inline theme detection (MutationObserver on html style, threshold=50 for visionOS)
        t_html = '<img src=x onerror="var d=this.parentElement;function A(){var b=getComputedStyle(document.documentElement).getPropertyValue(\'--primary-background-color\');var m=b.match(/\\d+/g);if(m){d.setAttribute(\'data-theme\',(0.299*m[0]+0.587*m[1]+0.114*m[2])<50?\'dark\':\'light\')}}A();new MutationObserver(A).observe(document.documentElement,{attributes:true,attributeFilter:[\'style\']});var m=navigator.userAgent.match(/Chrome\/(\d+)/);if(m&&parseInt(m[1])<120)d.setAttribute(\'data-old-webkit\',\'\')" style=display:none>'+t_html
        t_html += BLD_FOOTER
        t_html += '<img src=x onerror="var p=this.parentElement;setTimeout(function(){p.querySelectorAll(\'details[name=ic-acc]\').forEach(function(d){d.addEventListener(\'toggle\',function(e){if(d.open)p.querySelectorAll(\'details[name=ic-acc]\').forEach(function(s){if(s!==d)s.open=false})})})},200)" style=display:none>'
        cond = {
            "type": "conditional",
            "conditions": [{"condition": "state", "entity": "input_select.info_server_rules_tab", "state": tname}],
            "card": make_content_card(t_html, tab_type=ttype, tab=t),
            "grid_options": {"columns": 24, "rows": "auto"}
        }
        sr_tab_cards.append(cond)
        print(f'  SR Tab [{tname}] ({ttype}): {len(t_html)} chars')

    sr_ts = datetime.now().strftime('%H:%M:%S')
    sr_stack_cards = [
        {
            "type": "custom:mod-card",
            "card_mod": {"style": ":host { display: block !important; overflow-x: auto !important; white-space: nowrap !important; padding-bottom: 8px; } ha-card { backdrop-filter: none !important; -webkit-backdrop-filter: none !important; background: rgba(0,0,0,0) !important; box-shadow: none !important; }"},
            "card": {"type": "horizontal-stack", "cards": sr_tab_buttons}
        }
    ] + sr_tab_cards

    asa_built_views.append({
        "visible": False,
        "subview": True,
        "title": f'服务器规则',
        "path": "asa-server-rules",
        "theme": "Material You",
        "sections": [{
            "type": "grid",
            "column_span": 2,
            "cards": [{
                "type": "vertical-stack",
                "grid_options": {"columns": "full"},
                "cards": sr_stack_cards
            }]
        }]
    })
    print(f'Server rules: REBUILT with {len(sr_tab_buttons)} tabs + {len(sr_tab_cards)} cards + timestamp {sr_ts}')
    _log_step('SR_OK')

    # 2. INFO_WHITEROBER → views[41]
    tabs = to_data.get('tabs', [])
    tab_buttons = [make_tab_button(t['name'], t.get('description','')) for t in tabs]

    # Generate all tab conditional cards
    tab_cards = []
    for t in tabs:
        tname = t['name']
        ttype = t['type']
        t_html = render_tab_html(t)
        # Inject inline theme detection (MutationObserver on html style, threshold=50 for visionOS)
        t_html = '<img src=x onerror="var d=this.parentElement;function A(){var b=getComputedStyle(document.documentElement).getPropertyValue(\'--primary-background-color\');var m=b.match(/\\d+/g);if(m){d.setAttribute(\'data-theme\',(0.299*m[0]+0.587*m[1]+0.114*m[2])<50?\'dark\':\'light\')}}A();new MutationObserver(A).observe(document.documentElement,{attributes:true,attributeFilter:[\'style\']});var m=navigator.userAgent.match(/Chrome\/(\d+)/);if(m&&parseInt(m[1])<120)d.setAttribute(\'data-old-webkit\',\'\')" style=display:none>'+t_html
        t_html += BLD_FOOTER
        t_html += '<img src=x onerror="var p=this.parentElement;setTimeout(function(){p.querySelectorAll(\'details[name=ic-acc]\').forEach(function(d){d.addEventListener(\'toggle\',function(e){if(d.open)p.querySelectorAll(\'details[name=ic-acc]\').forEach(function(s){if(s!==d)s.open=false})})})},200)" style=display:none>'
        cond = {
            "type": "conditional",
            "conditions": [{"condition": "state", "entity": "input_select.info_tribe_tab", "state": tname}],
            "card": make_content_card(t_html, tab_type=ttype, tab=t),
            "grid_options": {"columns": 24, "rows": "auto"}
        }
        tab_cards.append(cond)
        print(f'  Tab [{tname}] ({ttype}): {len(t_html)} chars')

    # Generate fresh timestamp
    ts = datetime.now().strftime('%H:%M:%S')

    # Build cards: tab bar + all generated conditional cards
    stack_cards = [
        # Tab bar
        {
            "type": "custom:mod-card",
            "card_mod": {"style": ":host { display: block !important; overflow-x: auto !important; white-space: nowrap !important; padding-bottom: 8px; } ha-card { backdrop-filter: none !important; -webkit-backdrop-filter: none !important; background: rgba(0,0,0,0) !important; box-shadow: none !important; }"},
            "card": {"type": "horizontal-stack", "cards": tab_buttons}
        }
    ] + tab_cards

    asa_built_views.append({
        "visible": False,
        "subview": True,
        "title": f'部落运维速查',
        "path": "info_whiterober",
        "theme": "Material You",
        "sections": [{
            "type": "grid",
            "column_span": 2,
            "cards": [{
                "type": "vertical-stack",
                "grid_options": {"columns": "full"},
                "cards": stack_cards
            }]
        }]
    })
    print(f'info_whiterober: REBUILT with {len(tab_buttons)} tabs + {len(tab_cards)} cards + timestamp {ts}')
    _log_step('INFO_OK')

    # 3. BASE VIEWS → views[50:61] (11 servers, one view each)
    bq_servers = bq_data.get('servers', {})
    # New format compatibility: {tabs:[...]} → {servers:{Isl:{tabs:[...]}}}
    if not bq_servers and bq_data.get('tabs'):
        bq_servers = {'Isl': {'tabs': bq_data['tabs']}}

    def make_raw_card(html_content):
        return {
            "type": "custom:mod-card",
            "card_mod": {"style": "ha-card {\n  box-shadow: none !important;\n}\n"},
            "card": {
                "entity": "", "content": html_content, "ignore_line_breaks": True,
                "always_update": False, "parse_jinja": True, "code_editor": "Ace",
                "entities": [], "bindings": [], "actions": [],
                "plugins": {"daisyui": {"enabled": True, "url": "https://cdn.jsdelivr.net/npm/daisyui@latest/dist/full.css", "theme": "dark", "overrideCardBackground": False}, "tailwindElements": {"enabled": False}},
                "debounceChangePeriod": 500,
                "type": "custom:tailwindcss-template-card",
                "card_mod": {"style": CARD_CORE_CSS + BASE_RAW_CSS}
            }
        }

    BASE_SERVER_MAP = {
        'Isl': {'idx': 8,  'title': '孤岛基地速查',     'path': 'base_isl'},
        'Sco': {'idx': 9,  'title': '焦土基地速查',     'path': 'base_sco'},
        'Cen': {'idx': 10, 'title': '核心岛基地速查',   'path': 'base_cen'},
        'Abe': {'idx': 11, 'title': '畸变基地速查',     'path': 'base_abe'},
        'Ast': {'idx': 12, 'title': '繁星基地速查',     'path': 'base_ast'},
        'Ext': {'idx': 13, 'title': '灭绝基地速查',     'path': 'base_ext'},
        'Rag': {'idx': 14, 'title': '仙境基地速查',     'path': 'base_rag'},
        'Val': {'idx': 15, 'title': '瓦尔盖罗基地速查', 'path': 'base_val'},
        'Los': {'idx': 16, 'title': '失落地基地速查',   'path': 'base_los'},
        'Gen': {'idx': 17, 'title': '创世模拟基地速查', 'path': 'base_gen'},
        'Bob': {'idx': 18, 'title': '俱乐部基地速查',   'path': 'base_bob'},
    }

    def build_section_html(tab_data):
        """Build HTML from tab's sections array, including section-tab-bar."""
        sections = tab_data.get('sections', [])
        if not sections:
            return tab_data.get('html', '<p>暂无数据</p>')
        parts = ['<div class="section-tab-bar base-title-header">']
        for i, sec in enumerate(sections):
            active = ' tab-active' if i == 0 else ''
            sid = 'section-' + str(i)
            onclick_js = (
                f"(function(el){{"
                f"var bar=el.closest('.section-tab-bar');"
                f"var root=bar?bar.parentNode:(el.getRootNode?el.getRootNode():document);"
                f"var bodies=root.querySelectorAll('.accordion-body');"
                f"for(var k=0;k<bodies.length;k++)bodies[k].classList.add('collapsed');"
                f"var cur=root.querySelector('#{sid}-body');if(cur)cur.classList.remove('collapsed');"
                f"var tabs=root.querySelectorAll('.section-tab');"
                f"for(var k=0;k<tabs.length;k++)tabs[k].classList.remove('tab-active');"
                f"el.classList.add('tab-active');"
                f"}})(this)"
            )
            parts.append(f'<div class="section-tab{active}" onclick="{onclick_js}">{sec.get("name","")}</div>')
        parts.append('</div>')
        for i, sec in enumerate(sections):
            sid = 'section-' + str(i)
            collapsed = '' if i == 0 else ' collapsed'
            parts.append(f'<div id="{sid}-body" class="accordion-body borderr-none{collapsed}">{sec.get("html","")}</div>')
        return '\n'.join(parts)

    TJS = '<img src=x onerror="var d=this.parentElement;function A(){var b=getComputedStyle(document.documentElement).getPropertyValue(\'--primary-background-color\');var m=b.match(/\\d+/g);if(m){d.setAttribute(\'data-theme\',(0.299*m[0]+0.587*m[1]+0.114*m[2])<50?\'dark\':\'light\')}}A();new MutationObserver(A).observe(document.documentElement,{attributes:true,attributeFilter:[\'style\']})" style=display:none>'

    bq_ts = datetime.now().strftime('%H:%M:%S')
    base_count = 0
    for sid, cfg in BASE_SERVER_MAP.items():
        srv = bq_servers.get(sid, {})
        tabs = srv.get('tabs', [])
        if not tabs:
            # Placeholder: named view without content (avoids "未命名视图")
            asa_built_views.append({
                "visible": False,
                "subview": True,
                "title": f"{cfg['title']}",
                "path": cfg['path'],
                "theme": "Material You",
                "sections": [{"type": "grid", "cards": []}]
            })
            base_count += 1
            continue
        bq_tab_buttons = [make_tab_button(t.get('name','?'), t.get('description',''), 'input_select.info_tribe_tab') for t in tabs]
        bq_tab_cards = []
        for t in tabs:
            tname = t.get('name','?')
            ttype = t.get('type', '')
            if ttype == 'mixed_content':
                t_html = render_tab_html(t)
                css = CARD_CORE_CSS
                css += make_ic_css(SERVER_MAP, FIXED_STYLES_MAP)
                t_html = TJS + css + t_html
            else:
                t_html = build_section_html(t) if t.get('sections') else t.get('html', '<p>暂无数据</p>')
                t_html = TJS + t_html if '<img src=x' not in t_html else t_html
                t_html += BLD_FOOTER
                t_html += '<img src=x onerror="var p=this.parentElement;setTimeout(function(){p.querySelectorAll(\'details[name=ic-acc]\').forEach(function(d){d.addEventListener(\'toggle\',function(e){if(d.open)p.querySelectorAll(\'details[name=ic-acc]\').forEach(function(s){if(s!==d)s.open=false})})})},200)" style=display:none>'
            bq_tab_cards.append({
                "type": "conditional",
                "conditions": [{"condition": "state", "entity": "input_select.info_tribe_tab", "state": tname}],
                "card": make_raw_card(t_html),
                "grid_options": {"columns": 24, "rows": "auto"}
            })
        bq_stack = [{
            "type": "custom:mod-card",
            "card_mod": {"style": ":host { display: block !important; overflow-x: auto !important; white-space: nowrap !important; padding-bottom: 8px; } ha-card { backdrop-filter: none !important; -webkit-backdrop-filter: none !important; background: rgba(0,0,0,0) !important; box-shadow: none !important; }"},
            "card": {"type": "horizontal-stack", "cards": bq_tab_buttons}
        }] + bq_tab_cards
        asa_built_views.append({
            "visible": False,
            "subview": True,
            "title": f"{cfg['title']}",
            "path": cfg['path'],
            "theme": "Material You",
            "sections": [{
                "type": "grid",
                "column_span": 2,
                "cards": [{
                    "type": "vertical-stack",
                    "grid_options": {"columns": "full"},
                    "cards": bq_stack
                }]
            }]
        })
        base_count += 1
        print(f'  base_{sid}: REBUILT with {len(bq_tab_buttons)} tabs + {len(bq_tab_cards)} cards')
    print(f'Base views: REBUILT {base_count} server views + timestamp {bq_ts}')
    _log_step('BASES_OK')

    # -------------------------------------------------------
    # Merge: non-ASA views first, then ASA rebuilt views
    final_views = non_asa_views + asa_built_views
    lovelace['data']['config']['views'] = final_views
    print(f'Views: {len(non_asa_views)} non-ASA preserved + {len(asa_built_views)} ASA rebuilt = {len(final_views)} total')

    # SAVE — auto-detect environment (server vs local dev)
    lovelace_path = '/config/lovelace' if os.path.exists('/config') else r'A:\NetSarang\Xftp 8\Temporary\lovelace'
    lovelace_ll_path = '/config/lovelace.lovelace' if os.path.exists('/config') else r'A:\NetSarang\Xftp 8\Temporary\lovelace.lovelace'
    storage_path = '/config/.storage/lovelace' if os.path.exists('/config') else None
    storage_ll_path = '/config/.storage/lovelace.lovelace' if os.path.exists('/config') else None

    with open(lovelace_path, 'w', encoding='utf-8') as f:
        json.dump(lovelace, f, ensure_ascii=False, indent=2)
    with open(lovelace_path, 'r', encoding='utf-8') as f:
        raw = f.read()
    with open(lovelace_ll_path, 'w', encoding='utf-8') as f:
        f.write(raw)
    # On server, also update .storage/ files so HA picks up changes
    if storage_path:
        with open(storage_path, 'w', encoding='utf-8') as f:
            json.dump(lovelace, f, ensure_ascii=False, indent=2)
        with open(storage_ll_path, 'w', encoding='utf-8') as f:
            json.dump(lovelace, f, ensure_ascii=False, indent=2)
        print('(updated .storage/lovelace + .storage/lovelace.lovelace)')
    print(f'\nSaved: {len(raw)} bytes, {len(final_views)} views')
    _log_step('SAVED_OK')
