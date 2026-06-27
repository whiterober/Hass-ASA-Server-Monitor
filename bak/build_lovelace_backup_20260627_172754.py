"""Build lovelace with embedded HTML from JSON data using tailwindcss-template-card."""
import json, os
from datetime import datetime

# Server: /config/www/asa-data (absolute, avoids symlink issues). Local: ./data
_SERVER_DATA = '/config/www/asa-data'
DATA_DIR = _SERVER_DATA if os.path.isdir(_SERVER_DATA) else os.path.join(os.path.dirname(__file__), 'data')

def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

# Single source of truth for all server metadata
SERVER_MAP = {
    'Isl':{'label':'孤岛','icon':'mdi:island','color':'#4CAF50'},
    'Sco':{'label':'焦土','icon':'mdi:volcano','color':'#FF5722'},
    'Cen':{'label':'核心岛','icon':'mdi:diamond-stone','color':'#009688'},
    'Abe':{'label':'畸变','icon':'mdi:radioactive','color':'#9C27B0'},
    'Ext':{'label':'灭绝','icon':'mdi:meteor','color':'#00BCD4'},
    'Ast':{'label':'繁星','icon':'mdi:star-four-points','color':'#FF9800'},
    'Rag':{'label':'仙境','icon':'mdi:lighthouse-on','color':'#E91E63'},
    'Val':{'label':'瓦尔盖罗','icon':'mdi:forest','color':'#4E9F62'},
    'Bob':{'label':'俱乐部','icon':'mdi:party-popper','color':'#FFC107'},
    'Los':{'label':'失落地','icon':'mdi:castle','color':'#607D8B'},
}
FIXED_STYLES_MAP = {
    '_hint':{'label':'提示','icon':'mdi:information','color':'#2196F3'},
    '_warn':{'label':'警告','icon':'mdi:alert','color':'#FF9800'},
}
def _lookup_style(key):
    return SERVER_MAP.get(key) or FIXED_STYLES_MAP.get(key) or {}


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
ha-card .tb-divider {
  border: none !important;
  margin: 12px 0 !important;
}
/* Use primary-text-color at per-line opacity: dark=white~15%, light=black~15% — works in both themes */
ha-card .tb-div-solid {
  border-top: 1px solid var(--primary-text-color) !important;
  opacity: 0.15 !important;
}
ha-card .tb-div-dashed {
  border-top: 1px dashed var(--primary-text-color) !important;
  opacity: 0.15 !important;
}
ha-card .tb-div-double {
  border-top: 3px double var(--primary-text-color) !important;
  opacity: 0.18 !important;
}
ha-card .tb-div-wavy {
  position: relative !important;
  height: 10px !important;
  overflow: hidden !important;
  opacity: 0.2 !important;
}
ha-card .tb-div-wavy::after {
  content: '' !important;
  position: absolute !important;
  left: 0 !important;
  right: 0 !important;
  top: 0 !important;
  height: 10px !important;
  background-color: var(--primary-text-color) !important;
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
"""

# Table-level rules (any tab with tabular content — reference_table, mixed_content, server_grid, farming_table)
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
/* Generic table styling — matches server_grid / farming_table visuals */
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

SERVER_GRID_CSS = SHARED_CSS + """/* 左上角单元格需要最高z-index */
ha-card thead th:first-child {
  z-index: 30 !important;
}
ha-card tbody td:first-child {
  z-index: 10 !important;
}

/* 隔列背景色 */
ha-card tbody td:nth-child(2n) {
  background-color: transparent !important;
}
ha-card tbody td:nth-child(2n+1):not(:first-child) {
  background-color: var(--primary-background-color, #f5f5f5) !important;
}

/* 首列 */
ha-card thead th:first-child,
ha-card tbody td:first-child {
  width: 60px !important;
  min-width: 60px !important;
  background-color: var(--secondary-background-color, #f5f5f5) !important;
  text-align: center !important;
}
ha-card tbody td:first-child img {
  display: block !important;
  margin-left: auto !important;
  margin-right: auto !important;
  width: 40px !important;
  height: 40px !important;
}

/* 其他列图片 */
ha-card tbody td:not(:first-child) img {
  width: 30px !important;
  height: 30px !important;
}

/* 列宽 */
ha-card thead th:nth-child(n+2),
ha-card tbody td:nth-child(n+2) {
  width: 120px !important;
  min-width: 120px !important;
  white-space: normal !important;
}

/* 数据行最小高度 — 容纳大图标 */
ha-card #supply-table tbody td {
  height: 56px;
}

/* 表头配色 — based on server map, not column position */
ha-card .gen-table thead th[data-map="Isl"],
ha-card #supply-table thead th[data-map="Isl"] { background-color: #4CAF50 !important; color: #fff !important; }
ha-card .gen-table thead th[data-map="Sco"],
ha-card #supply-table thead th[data-map="Sco"] { background-color: #FF5722 !important; color: #fff !important; }
ha-card .gen-table thead th[data-map="Cen"],
ha-card #supply-table thead th[data-map="Cen"] { background-color: #009688 !important; color: #fff !important; }
ha-card .gen-table thead th[data-map="Abe"],
ha-card #supply-table thead th[data-map="Abe"] { background-color: #9C27B0 !important; color: #fff !important; }
ha-card .gen-table thead th[data-map="Ext"],
ha-card #supply-table thead th[data-map="Ext"] { background-color: #00BCD4 !important; color: #fff !important; }

/* 交互：纯CSS行/列筛选 + 选中高亮 */
ha-card #supply-table thead th label.col-head {
  display: flex;
  width: 100%;
  height: 100%;
  gap: .25rem;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  user-select: none;
  position: absolute;
  top: 0;
  left: 0;
  padding: 8px;
  z-index: 21;
}
ha-card #supply-table thead th {
  position: relative;
}
ha-card #supply-table thead {
  position: sticky !important;
  top: 0 !important;
  z-index: 20 !important;
}
ha-card #supply-table thead th:first-child label {
  z-index: 29 !important;
}
ha-card #supply-table thead th,
ha-card #supply-table thead th *,
ha-card #supply-table tbody td:first-child,
ha-card #supply-table tbody td:first-child * {
  outline: none !important; box-shadow: none !important;
}
ha-card #supply-table tbody td:first-child {
  position: sticky !important;
  left: 0 !important;
  z-index: 10 !important;
}
ha-card #supply-table tbody td:first-child .row-head {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  cursor: pointer;
  position: absolute;
  top: 0;
  left: 0;
  z-index: 20;
  padding: 8px;
}
ha-card #supply-table tbody td:first-child .row-head img {
  pointer-events: none;
}
ha-card #supply-table thead th .col-head ha-icon {
  pointer-events: none;
}

/* 行高亮 */
ha-card #supply-table tbody > tr:has(> td:first-child .row-toggle:checked) > td:not(:first-child) {
  background-color: var(--collect-sel-bg, rgba(3, 169, 244, .15)) !important;
}

/* 列高亮 */
ha-card #supply-table:has(thead > tr > th:nth-child(2) .col-toggle:checked) tbody td:nth-child(2) { background-color: var(--collect-sel-bg, rgba(3, 169, 244, .15)) !important; }
ha-card #supply-table:has(thead > tr > th:nth-child(3) .col-toggle:checked) tbody td:nth-child(3) { background-color: var(--collect-sel-bg, rgba(3, 169, 244, .15)) !important; }
ha-card #supply-table:has(thead > tr > th:nth-child(4) .col-toggle:checked) tbody td:nth-child(4) { background-color: var(--collect-sel-bg, rgba(3, 169, 244, .15)) !important; }
ha-card #supply-table:has(thead > tr > th:nth-child(5) .col-toggle:checked) tbody td:nth-child(5) { background-color: var(--collect-sel-bg, rgba(3, 169, 244, .15)) !important; }
ha-card #supply-table:has(thead > tr > th:nth-child(6) .col-toggle:checked) tbody td:nth-child(6) { background-color: var(--collect-sel-bg, rgba(3, 169, 244, .15)) !important; }

/* 列首开关：隐藏空行 */
ha-card #supply-table:has(thead > tr > th:nth-child(2) .col-toggle:checked) tbody > tr:has(> td:nth-child(2):not(:has(*))) { display: none !important; }
ha-card #supply-table:has(thead > tr > th:nth-child(2) .col-toggle:checked) tbody > tr:has(> td:nth-child(2):empty) { display: none !important; }
ha-card #supply-table:has(thead > tr > th:nth-child(2) .col-toggle:checked) tbody > tr:has(> td:nth-child(2).is-empty) { display: none !important; }
ha-card #supply-table:has(thead > tr > th:nth-child(3) .col-toggle:checked) tbody > tr:has(> td:nth-child(3):not(:has(*))) { display: none !important; }
ha-card #supply-table:has(thead > tr > th:nth-child(3) .col-toggle:checked) tbody > tr:has(> td:nth-child(3):empty) { display: none !important; }
ha-card #supply-table:has(thead > tr > th:nth-child(3) .col-toggle:checked) tbody > tr:has(> td:nth-child(3).is-empty) { display: none !important; }
ha-card #supply-table:has(thead > tr > th:nth-child(4) .col-toggle:checked) tbody > tr:has(> td:nth-child(4):not(:has(*))) { display: none !important; }
ha-card #supply-table:has(thead > tr > th:nth-child(4) .col-toggle:checked) tbody > tr:has(> td:nth-child(4):empty) { display: none !important; }
ha-card #supply-table:has(thead > tr > th:nth-child(4) .col-toggle:checked) tbody > tr:has(> td:nth-child(4).is-empty) { display: none !important; }
ha-card #supply-table:has(thead > tr > th:nth-child(5) .col-toggle:checked) tbody > tr:has(> td:nth-child(5):not(:has(*))) { display: none !important; }
ha-card #supply-table:has(thead > tr > th:nth-child(5) .col-toggle:checked) tbody > tr:has(> td:nth-child(5):empty) { display: none !important; }
ha-card #supply-table:has(thead > tr > th:nth-child(5) .col-toggle:checked) tbody > tr:has(> td:nth-child(5).is-empty) { display: none !important; }
ha-card #supply-table:has(thead > tr > th:nth-child(6) .col-toggle:checked) tbody > tr:has(> td:nth-child(6):not(:has(*))) { display: none !important; }
ha-card #supply-table:has(thead > tr > th:nth-child(6) .col-toggle:checked) tbody > tr:has(> td:nth-child(6):empty) { display: none !important; }
ha-card #supply-table:has(thead > tr > th:nth-child(6) .col-toggle:checked) tbody > tr:has(> td:nth-child(6).is-empty) { display: none !important; }

/* Server-matrix: no label column — equalize all columns */
ha-card #server-matrix {
  width: 100% !important;
}
ha-card #server-matrix thead th:first-child,
ha-card #server-matrix tbody td:first-child,
ha-card #server-matrix tbody tr:nth-child(odd) td:first-child,
ha-card #server-matrix tbody tr:nth-child(even) td:first-child {
  position: static !important;
  left: auto !important;
  z-index: auto !important;
}
ha-card #server-matrix thead th,
ha-card #server-matrix tbody td {
  width: auto !important;
  min-width: auto !important;
}
ha-card #server-matrix tbody td img {
  width: 40px !important;
  height: 40px !important;
}
"""

FARMING_TABLE_CSS = SHARED_CSS + """/* 产出列居中 */
ha-card tbody td.col-output { text-align: center !important; vertical-align: middle !important; }
ha-card tbody td.col-output img { display: block !important; margin-left: auto !important; margin-right: auto !important; }

ha-card tbody td img {
  width: 40px !important;
  height: auto !important;
  min-width: 40px !important;
}

/* 表头 */
ha-card thead th {
  border-top: 0 !important;
  background-color: var(--secondary-background-color, #f5f5f5) !important;
  color: inherit !important;
}
ha-card thead th:nth-child(1) { width: 50px !important; min-width: 50px !important; font-weight: 700 !important; }
ha-card thead th:nth-child(2) { width: 80px !important; min-width: 80px !important; }
ha-card thead th:nth-child(3) { width: 60px !important; min-width: 60px !important; }
ha-card thead th:nth-child(4) { width: 190px !important; min-width: 190px !important; }

/* 地图列 */
ha-card tbody td.col-map {
  text-align: center !important;
  vertical-align: middle !important;
  padding-top: 10px !important;
  padding-bottom: 10px !important;
  font-weight: 600 !important;
}
ha-card .map-badge { display: grid !important; place-items: center !important; row-gap: 4px !important; }
ha-card .map-badge ha-icon { width: 20px !important; height: 20px !important; }

/* 采集点列 */
ha-card tbody td.col-spot { text-align: center !important; vertical-align: middle !important; color: #000 !important; }

/* 服务器主题色 */
ha-card td.col-map[data-map="Isl"] { background-color: #4CAF50 !important; color: #fff !important; }
ha-card td.col-spot[data-map="Isl"] { background-color: #81C784 !important; }
ha-card td.col-map[data-map="Sco"] { background-color: #FF5722 !important; color: #fff !important; }
ha-card td.col-spot[data-map="Sco"] { background-color: #FF8A65 !important; }
ha-card td.col-map[data-map="Abe"] { background-color: #9C27B0 !important; color: #fff !important; }
ha-card td.col-spot[data-map="Abe"] { background-color: #BA68C8 !important; }
ha-card td.col-map[data-map="Ext"] { background-color: #00BCD4 !important; color: #fff !important; }
ha-card td.col-spot[data-map="Ext"] { background-color: #4DD0E1 !important; }

ha-card td.col-map.col-neutral { background-color: #424242 !important; color: #fff !important; }
ha-card td.col-spot.neutral { background-color: #9e9e9e !important; color: #000 !important; }

/* 流程/产出隔行着色 */
ha-card tbody tr:nth-child(odd) td.col-flow,
ha-card tbody tr:nth-child(odd) td.col-output { background-color: transparent !important; }
ha-card tbody tr:nth-child(even) td.col-flow,
ha-card tbody tr:nth-child(even) td.col-output { background-color: var(--primary-background-color, #f5f5f5) !important; }

/* 可折叠大段文本 */
ha-card td .clamp-wrap { display: block !important; }
ha-card td .clamp-toggle { display: none !important; }
ha-card td .clamp-content {
  display: -webkit-box !important;
  -webkit-box-orient: vertical !important;
  -webkit-line-clamp: 1 !important;
  overflow: hidden !important;
}
ha-card td .clamp-toggle:checked + .clamp-content {
  display: block !important;
  -webkit-line-clamp: initial !important;
  overflow: visible !important;
}
ha-card td .clamp-btn {
  display: inline-block !important;
  margin-top: 6px !important;
  color: var(--primary-color) !important;
  cursor: pointer !important;
  font-size: 12px !important;
  user-select: none !important;
}
ha-card td .clamp-toggle:not(:checked) ~ .clamp-btn::after { content: '≚'; }
ha-card td .clamp-toggle:checked ~ .clamp-btn::after { content: '≙'; }

/* Markdown 高亮块 */
ha-card td .md-hl {
  display: block !important;
  margin: 6px 0 !important;
  padding: 6px 8px !important;
  border-left: 3px solid var(--primary-color) !important;
  background-color: var(--secondary-background-color, rgba(0,0,0,0.06)) !important;
  border-radius: 4px !important;
}
ha-card td .md-hl.md-hl-1 { border-left-color: var(--primary-color) !important; }
ha-card td .md-hl.md-hl-2 { border-left-color: var(--accent-color, #FF9800) !important; }
ha-card td .md-hl.md-hl-3 { border-left-color: var(--info-color, #03A9F4) !important; }

/* 内联提示 */
ha-card td .hl-dot { font-weight: 700 !important; }
ha-card td .hl-dot.hl-1 { color: var(--primary-color) !important; }
ha-card td .hl-dot.hl-2 { color: var(--accent-color, #FF9800) !important; }
ha-card td .hl-dot.hl-3 { color: var(--info-color, #03A9F4) !important; }

/* 列表缩进 */
ha-card td .clamp-content ol { margin: 0 !important; padding-left: 0 !important; list-style: decimal inside !important; }
ha-card td .clamp-content li { margin: 0 0 6px 0 !important; }
"""

# -------------------------------------------------------
# Expandable Detail CSS — card-style rounded blocks with map theme colors
# -------------------------------------------------------
EXPANDABLE_DETAIL_CSS = SHARED_CSS + """ha-card .exp-block {
  border-radius: 12px !important;
  border-left: 4px solid !important;
  margin-bottom: 8px !important;
  overflow: hidden !important;
}
ha-card .exp-block[data-map="Isl"] { border-color: #4CAF50 !important; background: rgba(76,175,80,0.1) !important; }
ha-card .exp-block[data-map="Sco"] { border-color: #FF5722 !important; background: rgba(255,87,34,0.1) !important; }
ha-card .exp-block[data-map="Cen"] { border-color: #009688 !important; background: rgba(0,150,136,0.1) !important; }
ha-card .exp-block[data-map="Abe"] { border-color: #9C27B0 !important; background: rgba(156,39,176,0.1) !important; }
ha-card .exp-block[data-map="Ext"] { border-color: #00BCD4 !important; background: rgba(0,188,212,0.1) !important; }

/* Info card — static rounded card (non-expandable) */
ha-card .info-card-block {
  border-radius: 12px !important;
  border-left: 4px solid !important;
  margin-bottom: 8px !important;
  padding: 12px !important;
  display: flex !important;
  align-items: flex-start !important;
  gap: 12px !important;
}
ha-card .info-card-block[data-map="Isl"] { border-color: #4CAF50 !important; background: transparent !important; }
ha-card .info-card-block[data-map="Sco"] { border-color: #FF5722 !important; background: transparent !important; }
ha-card .info-card-block[data-map="Cen"] { border-color: #009688 !important; background: transparent !important; }
ha-card .info-card-block[data-map="Abe"] { border-color: #9C27B0 !important; background: transparent !important; }
ha-card .info-card-block[data-map="Ext"] { border-color: #00BCD4 !important; background: transparent !important; }
ha-card .info-card-block .ic-icon {
  width: 48px !important;
  height: 48px !important;
  flex-shrink: 0 !important;
  object-fit: contain !important;
  border-radius: 8px !important;
  background: rgba(255,255,255,0.05) !important;
}
ha-card .info-card-block .ic-body { flex: 1 !important; min-width: 0 !important; }
ha-card .info-card-block .ic-body .ic-title { font-weight: 600 !important; font-size: 1.05em !important; margin-bottom: 4px !important; display: flex; align-items: center; gap: 4px; }
ha-card .info-card-block .ic-body .ic-title ha-icon { flex-shrink: 0; }
ha-card .info-card-block .ic-body .ic-title .ic-emoji { flex-shrink: 0; font-size: 1.2em; }
ha-card .info-card-block .ic-body .ic-text { font-size: 0.9em !important; line-height: 1.5 !important; }
ha-card .info-card-block .ic-sum-end { display: none; }
ha-card .info-card-block details[open] .ic-sum-top { display: none !important; }
ha-card .info-card-block details[open] .ic-sum-end { display: block !important; }
ha-card .info-card-block ha-icon.ic-auto-color { color: var(--primary-text-color) !important; fill: var(--primary-text-color) !important; }
ha-card .info-card-block img.ic-auto-color { filter: var(--ic-icon-filter, none); }

ha-card .exp-summary {
  display: flex !important;
  align-items: center !important;
  gap: 12px !important;
  padding: 12px !important;
  cursor: pointer !important;
  list-style: none !important;
}
ha-card .exp-summary::-webkit-details-marker { display: none !important; }

ha-card .exp-summary .exp-icon {
  width: 56px !important;
  height: 56px !important;
  flex-shrink: 0 !important;
  object-fit: contain !important;
  border-radius: 8px !important;
  background: rgba(255,255,255,0.05) !important;
}
ha-card .exp-summary .exp-info {
  flex: 1 !important;
  min-width: 0 !important;
}
ha-card .exp-summary .exp-info .exp-title {
  font-weight: 600 !important;
  font-size: 1.05em !important;
  display: flex !important;
  align-items: center !important;
  gap: 6px !important;
}
ha-card .exp-summary .exp-info .exp-subtitle {
  font-size: 0.9em !important;
  color: var(--secondary-text-color) !important;
  margin-top: 2px !important;
}
ha-card .exp-summary .exp-arrow {
  flex-shrink: 0 !important;
  font-size: 1.2em !important;
  color: var(--secondary-text-color) !important;
  transition: transform 0.2s !important;
}
ha-card details[open] .exp-summary .exp-arrow {
  transform: rotate(180deg) !important;
}

ha-card .exp-body {
  padding: 0 12px 12px 80px !important;
  border-top: 1px solid var(--divider-color, rgba(255,255,255,0.1)) !important;
}
ha-card .exp-body ol {
  margin: 0 !important;
  padding-left: 20px !important;
}
ha-card .exp-body li {
  margin: 4px 0 !important;
  line-height: 1.5 !important;
}

/* Supply card — matches info-card style, per-server map colors */
ha-card .supply-card {
  border-radius: 12px !important;
  border-left: 4px solid var(--divider-color, rgba(255,255,255,0.2)) !important;
  margin-bottom: 8px !important;
  padding: 12px !important;
  display: flex !important; gap: 12px !important;
  background: var(--primary-background-color) !important;
}
ha-card .supply-card .sc-icon {
  width: 48px !important; height: 48px !important;
  flex-shrink: 0 !important; object-fit: contain !important;
  border-radius: 8px !important;
}
ha-card .supply-card .sc-body { flex: 1 !important; min-width: 0 !important; }
ha-card .supply-card .sc-body .sc-title { font-weight: 600 !important; font-size: 1.05em !important; margin-bottom: 6px !important; }
ha-card .supply-card .sc-body .sc-servers { display: flex !important; flex-wrap: wrap !important; gap: 6px 12px !important; }
ha-card .supply-card .sc-body .sc-srv { display: flex !important; align-items: center !important; gap: 4px !important; font-size: 0.85em !important; }
ha-card .supply-card .sc-body .sc-srv img { width: 20px !important; height: 20px !important; object-fit: contain !important; border-radius: 2px !important; }
/* Per-server map colors for supply card server tags */
ha-card .supply-card .sc-srv[data-map=\"Isl\"] { color: #4CAF50 !important; }
ha-card .supply-card .sc-srv[data-map=\"Sco\"] { color: #FF5722 !important; }
ha-card .supply-card .sc-srv[data-map=\"Cen\"] { color: #009688 !important; }
ha-card .supply-card .sc-srv[data-map=\"Abe\"] { color: #9C27B0 !important; }
ha-card .supply-card .sc-srv[data-map=\"Ext\"] { color: #00BCD4 !important; }

/* Map filter — CSS-only via radio:checked inside label */
ha-card .filter-bar { display: flex !important; flex-wrap: wrap !important; gap: 0 !important; margin-bottom: 12px !important; }
ha-card .filter-radio { position: absolute !important; opacity: 0 !important; width: 0 !important; height: 0 !important; }
ha-card .filter-label {
  display: inline-flex !important; align-items: center !important; gap: 4px !important;
  padding: 4px 12px !important; border-radius: 16px !important;
  border: 1px solid var(--divider-color, rgba(255,255,255,0.2)) !important;
  background: var(--primary-background-color) !important; color: var(--secondary-text-color) !important;
  font-size: 0.85em !important; cursor: pointer !important; user-select: none !important;
  line-height: 1.4 !important; white-space: nowrap !important; min-height: 28px !important;
}
ha-card .filter-bar .filter-label { margin-right: 6px !important; }
ha-card .filter-label ha-icon { pointer-events: none !important; }
ha-card .filter-label.active { box-shadow: 0 0 0 2px var(--primary-text-color) !important; }
/* Map theme colors for filter labels */
ha-card .filter-label[data-map="Isl"] { background: #4CAF50 !important; color: #fff !important; border-color: #4CAF50 !important; }
ha-card .filter-label[data-map="Sco"] { background: #FF5722 !important; color: #fff !important; border-color: #FF5722 !important; }
ha-card .filter-label[data-map="Cen"] { background: #009688 !important; color: #fff !important; border-color: #009688 !important; }
ha-card .filter-label[data-map="Abe"] { background: #9C27B0 !important; color: #fff !important; border-color: #9C27B0 !important; }
ha-card .filter-label[data-map="Ext"] { background: #00BCD4 !important; color: #fff !important; border-color: #00BCD4 !important; }
ha-card .filter-radio[value=""]:checked ~ .filterable { display: flex !important; }
ha-card .filter-radio[value="Isl"]:checked ~ .filterable { display: none !important; }
ha-card .filter-radio[value="Isl"]:checked ~ .filterable[data-filter-maps*="Isl"] { display: flex !important; }
ha-card .filter-radio[value="Sco"]:checked ~ .filterable { display: none !important; }
ha-card .filter-radio[value="Sco"]:checked ~ .filterable[data-filter-maps*="Sco"] { display: flex !important; }
ha-card .filter-radio[value="Cen"]:checked ~ .filterable { display: none !important; }
ha-card .filter-radio[value="Cen"]:checked ~ .filterable[data-filter-maps*="Cen"] { display: flex !important; }
ha-card .filter-radio[value="Abe"]:checked ~ .filterable { display: none !important; }
ha-card .filter-radio[value="Abe"]:checked ~ .filterable[data-filter-maps*="Abe"] { display: flex !important; }
ha-card .filter-radio[value="Ext"]:checked ~ .filterable { display: none !important; }
ha-card .filter-radio[value="Ext"]:checked ~ .filterable[data-filter-maps*="Ext"] { display: flex !important; }
"""

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
    if ttype == 'raw_html':
        # raw_html tabs already have their own wrapper — use as-is
        return tab.get('html', '')
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
    elif ttype == 'server_list':
        for srv in tab.get('servers',[]):
            sname=srv.get('name',''); scount=srv.get('count',''); locs=srv.get('locations',[])
            parts.append(f'<div style="margin:12px 0"><h3 style="margin:0 0 8px">{esc(sname)} <small style="color:var(--secondary-text-color)">{esc(scount)}</small></h3>')
            if locs:
                parts.append('<ul style="margin:0;padding-left:20px">')
                for loc in locs:
                    limg=loc.get('image_url','')
                    if limg: parts.append(f'<li style="margin-bottom:4px"><img src="{esc(limg)}" style="max-width:200px;max-height:80px;display:block;margin:4px 0" loading="lazy" />{esc(loc.get("name",""))}</li>')
                    else: parts.append(f'<li>{esc(loc.get("name",""))}</li>')
                parts.append('</ul>')
            else: parts.append('<p style="color:var(--secondary-text-color);font-size:0.85em">暂无地点数据</p>')
            parts.append('</div>')
    elif ttype == 'card_grid':
        cols=tab.get('columns',4); cards=tab.get('cards',[])
        parts.append(f'<div class="card-grid" style="grid-template-columns:repeat({cols},1fr)">')
        for card in cards:
            parts.append('<div class="info-card">')
            if card.get('image_url'): parts.append(f'<img src="{esc(card["image_url"])}" loading="lazy" />')
            parts.append(f'<div class="card-name">{esc(card.get("name",""))}</div>')
            if card.get('feature'): parts.append(f'<div class="card-feature">{esc(card["feature"])}</div>')
            parts.append('</div>')
        parts.append('</div>')
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
                elif bbt=='supply_card':
                    fm=blk.get('filter_maps','')
                    if fm: active_maps.update(fm.split(','))
                    items=blk.get('items',[]) if blk.get('items') else ([blk.get('item')] if blk.get('item') else [])
                    for item in items:
                        if item:
                            for sid in item.get('locations',{}).keys():
                                active_maps.add(sid)
                elif bbt=='expandable_detail':
                    fm=blk.get('filter_maps','')
                    if fm: active_maps.update(fm.split(','))
            active_maps.discard('')
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
                color_style = f'border-color:{div_color};opacity:1' if div_color and div_color != 'auto' else ''
                if div_title:
                    title_html = f'<strong>{esc(div_title)}</strong>' if div_title_bold else esc(div_title)
                    parts.append(f'<div style="display:flex;align-items:center;gap:10px;margin:12px 0"><hr class="tb-divider tb-div-{line_style}" style="flex:1;min-width:0;{color_style}" /><span style="white-space:nowrap;font-size:0.85em">{title_html}</span></div>')
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
                ic_icon = block.get('icon_url', '')
                ic_mdi = block.get('mdi_icon', '')
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
                auto_cls = ' ic-auto-color' if block.get('icon_auto_color') else ''
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
                    parts.append('<img src="{}" class="ic-icon{}" loading="lazy" />'.format(esc(ic_icon), auto_cls))
                parts.append('<div class="ic-body" style="display:flex;flex-wrap:wrap;gap:4px;align-items:center">')
                parts.append('<div class="ic-title" style="flex-basis:100%">')
                if ic_mdi:
                    if ic_mdi.startswith('mdi:'):
                        parts.append('<ha-icon icon="{}" class="{}"></ha-icon> '.format(ic_mdi, auto_cls))
                    else:
                        parts.append('<span class="ic-emoji">{}</span> '.format(esc(ic_mdi)))
                # Block-level map mdi icon for linear/block states
                if blk_active:
                    _bstyle = _lookup_style(blk_active)
                    _bicon = _bstyle.get('icon','mdi:map')
                    _bcolor = _bstyle.get('color','')
                    if blk_st == 1:
                        parts.append('<i class="mdi {}" style="font-size:16px;vertical-align:middle;margin-right:4px;color:{}"></i>'.format(_bicon.replace('mdi:','mdi-'), _bcolor))
                    elif blk_st == 2:
                        parts.append('<i class="mdi {}" style="font-size:16px;vertical-align:middle;margin-right:4px;color:{}"></i>'.format(_bicon.replace('mdi:','mdi-'), _bcolor))
                parts.append('<span{}>{}</span>'.format(title_color_style, esc(ic_title)))
                parts.append('</div>')
                ic_collapse = block.get('collapse_descriptions', False)
                if ic_collapse:
                    parts.append('<details name="ic-acc" style="cursor:pointer;margin:0;padding:0;width:100%"><summary class="ic-sum-top" style="display:block;font-size:0.65em;background:rgba(128,128,128,0.12);border:1px solid var(--border);border-radius:10px;padding:1px 7px;margin-bottom:2px;list-style:none;cursor:pointer;width:100%;box-sizing:border-box">···</summary><div style="display:flex;flex-wrap:wrap;gap:4px;align-items:center;width:100%">')
                for desc in ic_descs:
                    if isinstance(desc, dict) and desc.get('type') == 'br':
                        parts.append('<div style="flex-basis:100%;height:0"></div>')
                        continue
                    dtext = desc.get('text', '') if isinstance(desc, dict) else str(desc)
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
                    dstyle = ''
                    if dbold: dstyle += 'font-weight:bold;'
                    if dcolor and dcolor not in ('#000000', 'auto') and not block_maps: dstyle += 'color:{};'.format(dcolor)
                    if dopacity != 1.0: dstyle += 'opacity:{};'.format(dopacity)
                    if dstyle: dstyle = ' style="{}"'.format(dstyle)
                    # Server icon prefix (show highest-priority map icon)
                    srv_icon = ''
                    _show_maps = block_maps + linear_maps
                    if _show_maps and has_map_filter:
                        _sid = _show_maps[0]
                        _style = _lookup_style(_sid)
                        _icon = _style.get('icon','mdi:map')
                        _clr = _style.get('color','')
                        srv_icon = '<i class="mdi {}" style="font-size:14px;vertical-align:middle;margin-right:2px;color:oklch(var(--pc))"></i>'.format(_icon.replace('mdi:','mdi-'))
                    elif dserver:
                        _style = _lookup_style(dserver)
                        _icon = _style.get('icon','mdi:map')
                        srv_icon = '<i class="mdi {}" style="font-size:14px;vertical-align:middle;margin-right:2px;color:oklch(var(--pc))"></i>'.format(_icon.replace('mdi:','mdi-'))
                    dserver_attr=' data-server="{}" data-server-states=\'{}\''.format(dserver, states_json)
                    parts.append('<div class="{}"{{}}{{}}>{{}}{{}}</div>'.format(ic_cls).format(dstyle, dserver_attr, srv_icon, esc(dtext)))
                if ic_collapse:
                    parts.append('<span class="ic-sum-end" style="font-size:0.65em;background:rgba(128,128,128,0.12);border:1px solid var(--border);border-radius:10px;padding:1px 7px;margin-top:2px;flex-basis:100%;cursor:pointer" onclick="event.stopPropagation();var d=this.closest(\'details\');var root=d.getRootNode();root.querySelectorAll(\'details[name=ic-acc]\').forEach(function(o){o.open=false});">···</span></div></details>')
                parts.append('</div>')
                parts.append('</div>')
            elif bt=='supply_card':
                sc_cols=block.get('columns',[])
                # Support both single item and legacy items array
                sc_items=block.get('items',[]) if block.get('items') else [block.get('item')] if block.get('item') else []
                for item in sc_items:
                    if not item: continue
                    sc_name=esc(item.get('name',''))
                    sc_icon=item.get('icon_url','')
                    # Auto-compute filter_maps from location data
                    sc_fmaps=block.get('filter_maps','')
                    if not sc_fmaps and has_map_filter:
                        fmaps=set()
                        for sid,locs in item.get('locations',{}).items():
                            if locs: fmaps.add(sid)
                        sc_fmaps=','.join(sorted(fmaps))
                    sext='' if not has_map_filter else ' filterable'
                    sattrs='' if not has_map_filter else ' data-filter-maps="{}"'.format(sc_fmaps)
                    parts.append('<div class="supply-card{}"{}>'.format(sext,sattrs))
                    if sc_icon:
                        parts.append('<img src="{}" class="sc-icon" loading="lazy" />'.format(esc(sc_icon)))
                    parts.append('<div class="sc-body">')
                    parts.append('<div class="sc-title">{}</div>'.format(sc_name))
                    parts.append('<div class="sc-servers">')
                    for col in sc_cols:
                        sid=col.get('server','')
                        icon=col.get('icon','mdi:server')
                        label=col.get('label','')
                        locs=item.get('locations',{}).get(sid,[])
                        if locs:
                            parts.append('<div class="sc-srv" data-map="{}">'.format(sid))
                            parts.append('<ha-icon icon="{}"></ha-icon> '.format(icon))
                            for loc in locs:
                                loc_img=loc.get('image_url','')
                                loc_name=esc(loc.get('name',''))
                                if loc_img:
                                    parts.append('<img src="{}" /> '.format(esc(loc_img)))
                                if loc_name:
                                    parts.append(loc_name)
                            parts.append('</div>')
                    parts.append('</div></div></div>')
            elif bt=='map_filter':
                # Dynamic filter buttons based on actual server references in this tab

                filter_js=(
                    "var s=this;var r=s.getRootNode();"
                    "if(s._w){s.checked=false;s._w=false;s.parentElement.classList.remove('active');"
                    "r.querySelectorAll('.filterable,.sc-srv,.ic-text[data-server-states]').forEach(function(e){e.style.setProperty('display','','')});"
                    "return}"
                    "r.querySelectorAll('.filter-radio').forEach(function(o){o._w=false;o.parentElement.classList.remove('active')});"
                    "s._w=true;s.parentElement.classList.add('active');"
                    "r.querySelectorAll('.filterable').forEach(function(e){var fm=e.getAttribute('data-filter-maps')||'';var v=!fm||fm.indexOf(s.value)>=0;e.style.setProperty('display',v?'':'none',v?'':'important')});"
                    "r.querySelectorAll('.sc-srv').forEach(function(e){var pf=e.closest('.filterable');if(pf&&(pf.classList.contains('ic-block-'+s.value)||pf.classList.contains('ic-linear-'+s.value))){e.style.setProperty('display','','');return}var v=e.getAttribute('data-map')===s.value;e.style.setProperty('display',v?'':'none',v?'':'important')});"
                    "r.querySelectorAll('.ic-text[data-server-states]').forEach(function(e){var pf=e.closest('.filterable');if(pf&&(pf.classList.contains('ic-block-'+s.value)||pf.classList.contains('ic-linear-'+s.value))){e.style.setProperty('display','','');return}var ss=JSON.parse(e.getAttribute('data-server-states')||'{}');var st=(ss[s.value]||0);if(st===0){e.style.setProperty('display','none','important')}else{e.style.setProperty('display','','');if(st===1){e.classList.add('ic-linear-'+s.value)}else{e.classList.add('ic-block-'+s.value)}}})"
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
            elif bt=='card_grid':
                cols=block.get('columns',4)
                cards=block.get('cards',[])
                parts.append('<div class="card-grid" style="grid-template-columns:repeat({},1fr)">'.format(cols))
                for card in cards:
                    parts.append('<div class="info-card">')
                    if card.get('image_url'): parts.append('<img src="{}" loading="lazy" />'.format(esc(card['image_url'])))
                    parts.append('<div class="card-name">{}</div>'.format(esc(card.get('name',''))))
                    if card.get('feature'): parts.append('<div class="card-feature">{}</div>'.format(esc(card['feature'])))
                    parts.append('</div>')
                parts.append('</div>')
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
    elif ttype == 'server_grid':
        columns=tab.get('columns',[]); items=tab.get('items',[])
        parts.append('<div class="borderr relative overflow-auto border border-gray-300"><table id="supply-table" class="table-fixed border-collapse w-full min-w-max"><thead class="sticky top-0 z-20"><tr>')
        parts.append('<th class="sticky left-0 z-30 border border-gray-300 p-2 text-center whitespace-nowrap">补给品</th>')
        for col in columns:
            parts.append(f'<th class="border border-gray-300 p-2 text-center whitespace-nowrap"><label class="col-head" title="切换：隐藏该列中的空行"><input type="checkbox" class="col-toggle" hidden /><ha-icon icon="mdi:server"></ha-icon> {esc(col["label"])}</label></th>')
        parts.append('</tr></thead><tbody>')
        for item in items:
            parts.append('<tr>')
            icon_url=item.get('icon_url','')
            parts.append(f'<td class="sticky left-0 z-10 border border-gray-300 p-2 text-center whitespace-nowrap"><label class="row-head"><input type="checkbox" class="row-toggle" hidden />')
            if icon_url: parts.append(f'<img src="{esc(icon_url)}" width="40" height="40" />')
            parts.append('</label></td>')
            for col in columns:
                server_id=col.get('server',''); locs=item.get('locations',{}).get(server_id,[])
                parts.append('<td class="border border-gray-300 p-2 text-left align-top">')
                for loc in locs:
                    parts.append(f'{esc(loc.get("name",""))}<br />')
                    if loc.get('image_url'): parts.append(f'<div class="flex flex-wrap gap-1 items-start mb-2"><img src="{esc(loc["image_url"])}" /></div>')
                    badge=loc.get('badge',''); badge_type=loc.get('badge_type','badge-warning')
                    if badge: parts.append(f'<span class="badge badge-sm {badge_type} mt-1">{esc(badge)}</span>')
                parts.append('</td>')
            parts.append('</tr>')
        parts.append('</tbody></table></div>')
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
    elif ttype == 'raw_html':
        parts.append(tab.get('html',''))
    parts.append('</div>')
    return strip_and_append_empty_rows('\n'.join(parts))


def render_server_grid(tab):
    """Render supply/补给 table matching old page HTML exactly."""
    columns = tab.get('columns', [])
    items = tab.get('items', [])
    first_col_label = tab.get('first_col_label', '补给品')
    hide_first_col = tab.get('hide_first_col', False)
    parts = ['<div class="flex flex-col">']
    parts.append('  <div class="borderr relative overflow-auto border border-gray-300">')
    table_id = 'server-matrix' if hide_first_col else 'supply-table'
    table_class = 'gen-table server-matrix' if hide_first_col else 'table-fixed border-collapse w-full min-w-max'
    parts.append(f'    <table id="{table_id}" class="{table_class}">')
    parts.append('      <thead class="sticky top-0 z-20">')
    parts.append('        <tr>')
    if not hide_first_col:
        parts.append(f'          <th class="sticky left-0 z-30 border border-gray-300 p-2 text-center whitespace-nowrap">{first_col_label}</th>')
    for col in columns:
        icon = col.get('icon', 'mdi:server')
        label = esc(col.get('label', ''))
        map_id = col.get('server', '')
        parts.append(f'          <th class="border border-gray-300 p-2 text-center whitespace-nowrap" data-map="{map_id}"><label class="col-head" title="切换：隐藏该列中的空行"><input type="checkbox" class="col-toggle" hidden /><ha-icon icon="{icon}"></ha-icon> {label}</label></th>')
    parts.append('        </tr>')
    parts.append('      </thead>')
    parts.append('      <tbody>')
    for item in items:
        parts.append('        <tr>')
        if not hide_first_col:
            icon_url = item.get('icon_url', '')
            icon_urls = item.get('icon_urls', [icon_url] if icon_url else [])
            mdi_icon = item.get('mdi_icon', '')
            parts.append('          <td class="sticky left-0 z-10 border border-gray-300 p-2 text-center whitespace-nowrap">')
            parts.append('            <label class="row-head" title="切换：隐藏本行为空的整列"><input type="checkbox" class="row-toggle" hidden />')
            if mdi_icon:
                parts.append(f'              <ha-icon icon="{mdi_icon}"></ha-icon>')
            for u in icon_urls:
                if u:
                    parts.append(f'              <img src="{esc(u)}" width="40" height="40" />')
            parts.append('            </label>')
            parts.append('          </td>')
        for col in columns:
            server_id = col.get('server', '')
            locs = item.get('locations', {}).get(server_id, [])
            if locs:
                parts.append(f'          <td class="border border-gray-300 p-2 text-left align-top" data-map="{server_id}">')
                # Each location: name<br/> then image+badge div (matching old page pattern)
                for loc in locs:
                    name = esc(loc.get('name', ''))
                    img_url = loc.get('image_url', '')
                    img_urls = loc.get('image_urls', [img_url] if img_url else [])
                    badge = loc.get('badge', '')
                    badge_type = loc.get('badge_type', 'badge-warning')
                    parts.append(f'            {name}<br />')
                    if img_urls or badge:
                        parts.append('            <div class="flex flex-wrap gap-1 items-start">')
                        parts.append('              <div class="flex flex-col items-start">')
                        for u in img_urls:
                            if u:
                                parts.append(f'                <img src="{esc(u)}" />')
                        if badge:
                            parts.append(f'                <span class="badge badge-sm {badge_type} mt-1">{esc(badge)}</span>')
                        parts.append('              </div>')
                        parts.append('            </div>')
                parts.append('          </td>')
            else:
                parts.append('          <td class="border border-gray-300 p-2 text-left align-top"></td>')
        parts.append('        </tr>')
    parts.append('      </tbody>')
    parts.append('    </table>')
    parts.append('  </div>')
    parts.append('</div>')
    return '\n'.join(parts)


def render_expandable_detail(tab):
    """Render expandable detail blocks with large output icons and map theming."""
    rows = tab.get('rows', [])
    parts = ['<div class="flex flex-col gap-2">']

    for row in rows:
        map_data = row.get('map', {}) or {}
        spot_data = row.get('spot', {}) or {}
        output_data = row.get('output', {}) or {}
        flow_data = row.get('flow', {}) or {}

        map_text = map_data.get('text', '')
        map_hl = map_data.get('highlight', '')
        spot_text = spot_data.get('text', '')
        icon_url = output_data.get('icon_url', '') if isinstance(output_data, dict) else ''
        mdi = SERVER_MAP.get(map_hl,{}).get('icon','mdi:map-marker')
        blocks = flow_data.get('blocks', []) if isinstance(flow_data, dict) else []

        has_body = bool(blocks)
        parts.append(f'<details class="exp-block" data-map="{map_hl}"{" open" if not has_body else ""}>')
        parts.append('<summary class="exp-summary">')

        # Large output icon
        if icon_url:
            parts.append(f'<img src="{esc(icon_url)}" class="exp-icon" loading="lazy" />')
        else:
            parts.append('<div class="exp-icon" style="display:flex;align-items:center;justify-content:center"><ha-icon icon="mdi:help-circle"></ha-icon></div>')

        # Map + spot info
        parts.append('<div class="exp-info">')
        parts.append(f'<div class="exp-title"><ha-icon icon="{mdi}"></ha-icon> {esc(spot_text)}</div>')
        if map_text:
            parts.append(f'<div class="exp-subtitle">{esc(map_text)}</div>')
        parts.append('</div>')

        if has_body:
            parts.append('<span class="exp-arrow">▼</span>')

        parts.append('</summary>')

        # Flow body
        if has_body:
            parts.append('<div class="exp-body">')
            for block in blocks:
                if block['type'] == 'text':
                    bt = block.get('text', '')
                    bold = block.get('bold', False)
                    color = block.get('color', '')
                    style = 'margin:4px 0'
                    if bold: style += ';font-weight:bold'
                    if color: style += ';color:{}'.format(color)
                    parts.append(f'<p style="{style}">{esc(bt)}</p>')
                elif block['type'] == 'ol':
                    parts.append('<ol>')
                    for step in block.get('steps', []):
                        if isinstance(step, dict) and 'html' in step:
                            sh = step.get('html', '')
                            parts.append(f'<li>{sh}</li>')
                        else:
                            parts.append(f'<li>{esc(str(step))}</li>')
                    parts.append('</ol>')
                elif block['type'] == 'md_hl':
                    bc = block.get('class', '')
                    bt2 = block.get('text', '')
                    parts.append(f'<span class="{bc}">{bt2}</span>')
                elif block['type'] == 'strong':
                    bt3 = block.get('text', '')
                    parts.append(f'<strong>{bt3}</strong>')
            parts.append('</div>')

        parts.append('</details>')

    parts.append('</div>')
    return '\n'.join(parts)


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
    # -------------------------------------------------------
    with open(os.path.join(DATA_DIR, 'asa_server_rules.json'), 'r', encoding='utf-8') as f:
        sr_data = json.load(f)
    with open(os.path.join(DATA_DIR, 'tribe_ops.json'), 'r', encoding='utf-8') as f:
        to_data = json.load(f)
    with open(os.path.join(DATA_DIR, 'asa_base_quick_ref.json'), 'r', encoding='utf-8') as f:
        bq_data = json.load(f)

    lovelace_path = '/config/lovelace' if os.path.exists('/config') else r'A:\NetSarang\Xftp 8\Temporary\lovelace'
    lovelace_ll_path = '/config/lovelace.lovelace' if os.path.exists('/config') else r'A:\NetSarang\Xftp 8\Temporary\lovelace.lovelace'
    with open(lovelace_path, 'r', encoding='utf-8') as f:
        lovelace = json.load(f)
    views = lovelace['data']['config']['views']

    # --- Helper: content card matching OLD pattern ---
    def make_content_card(html_content, tab_type=None, tab=None):
        if tab_type == 'mixed_content' and tab:
            # Compose CSS from block types present
            block_types = {b.get('block_type','') for b in tab.get('content_blocks',[])}
            has_map_filter = 'map_filter' in block_types
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
                    elif bbt == 'supply_card':
                        fm = blk.get('filter_maps','')
                        if fm: active_maps.update(fm.split(','))
                    elif bbt == 'expandable_detail':
                        fm = blk.get('filter_maps','')
                        if fm: active_maps.update(fm.split(','))
                active_maps.discard('')
            css = CARD_CORE_CSS
            if block_types & {'server_grid','table','reference_table'}:
                css += TABLE_CORE_CSS
            if 'server_grid' in block_types:
                css = SERVER_GRID_CSS  # includes SHARED_CSS
            if 'expandable_detail' in block_types:
                css += EXPANDABLE_DETAIL_CSS.replace(SHARED_CSS, '')
            if 'supply_card' in block_types or 'map_filter' in block_types:
                css += 'ha-card .supply-card{border-radius:12px!important;border-left:4px solid var(--divider-color)!important;margin-bottom:8px!important;padding:12px!important;display:flex!important;gap:12px!important;background:var(--primary-background-color)!important}'
                css += 'ha-card .supply-card .sc-icon{width:48px!important;height:48px!important;flex-shrink:0!important;object-fit:contain!important;border-radius:8px!important}'
                css += 'ha-card .supply-card .sc-body{flex:1!important;min-width:0!important}'
                css += 'ha-card .supply-card .sc-body .sc-title{font-weight:600!important;font-size:1.05em!important;margin-bottom:6px!important}'
                css += 'ha-card .supply-card .sc-body .sc-servers{display:flex!important;flex-wrap:wrap!important;gap:6px 12px!important}'
                css += 'ha-card .supply-card .sc-body .sc-srv{display:flex!important;align-items:center!important;gap:4px!important;font-size:.85em!important}'
                css += 'ha-card .supply-card .sc-body .sc-srv img{width:20px!important;height:20px!important;object-fit:contain!important;border-radius:2px!important}'
                css += 'ha-card .supply-card .sc-srv[data-map=Isl]{color:#4CAF50!important}'
                css += 'ha-card .supply-card .sc-srv[data-map=Sco]{color:#FF5722!important}'
                css += 'ha-card .supply-card .sc-srv[data-map=Cen]{color:#009688!important}'
                css += 'ha-card .supply-card .sc-srv[data-map=Abe]{color:#9C27B0!important}'
                css += 'ha-card .supply-card .sc-srv[data-map=Ext]{color:#00BCD4!important}'
                css += 'ha-card .filter-bar{display:flex!important;flex-wrap:wrap!important;gap:0!important;margin-bottom:12px!important}'
                css += 'ha-card .filter-radio{position:absolute!important;opacity:0!important;width:0!important;height:0!important}'
                css += 'ha-card .filter-label{display:inline-flex!important;align-items:center!important;gap:4px!important;padding:4px 12px!important;border-radius:16px!important;border:1px solid var(--divider-color)!important;font-size:.85em!important;cursor:pointer!important;user-select:none!important;line-height:1.4!important;white-space:nowrap!important;min-height:28px!important;margin-right:6px!important}'
                css += 'ha-card .filter-label[data-map=Isl]{background:#4CAF50!important;color:var(--primary-background-color)!important;border-color:#4CAF50!important}'
                css += 'ha-card .filter-label[data-map=Sco]{background:#FF5722!important;color:var(--primary-background-color)!important;border-color:#FF5722!important}'
                css += 'ha-card .filter-label[data-map=Cen]{background:#009688!important;color:var(--primary-background-color)!important;border-color:#009688!important}'
                css += 'ha-card .filter-label[data-map=Abe]{background:#9C27B0!important;color:var(--primary-background-color)!important;border-color:#9C27B0!important}'
                css += 'ha-card .filter-label[data-map=Ext]{background:#00BCD4!important;color:var(--primary-background-color)!important;border-color:#00BCD4!important}'
                css += 'ha-card .filter-label.active{box-shadow:0 0 0 2px var(--primary-text-color)!important}'
                css += 'ha-card .filter-label ha-icon{pointer-events:none!important}'
                css += 'ha-card:has(.filter-radio[value=\"\"]:checked) .filterable{display:flex!important}'
                css += 'ha-card:has(.filter-radio[value=\"Isl\"]:checked) .filterable{display:none!important}'
                css += 'ha-card:has(.filter-radio[value=\"Isl\"]:checked) .filterable[data-filter-maps*=Isl]{display:flex!important}'
                css += 'ha-card:has(.filter-radio[value=\"Sco\"]:checked) .filterable{display:none!important}'
                css += 'ha-card:has(.filter-radio[value=\"Sco\"]:checked) .filterable[data-filter-maps*=Sco]{display:flex!important}'
                css += 'ha-card:has(.filter-radio[value=\"Cen\"]:checked) .filterable{display:none!important}'
                css += 'ha-card:has(.filter-radio[value=\"Cen\"]:checked) .filterable[data-filter-maps*=Cen]{display:flex!important}'
                css += 'ha-card:has(.filter-radio[value=\"Abe\"]:checked) .filterable{display:none!important}'
                css += 'ha-card:has(.filter-radio[value=\"Abe\"]:checked) .filterable[data-filter-maps*=Abe]{display:flex!important}'
                css += 'ha-card:has(.filter-radio[value=\"Ext\"]:checked) .filterable{display:none!important}'
                css += 'ha-card:has(.filter-radio[value=\"Ext\"]:checked) .filterable[data-filter-maps*=Ext]{display:flex!important}'
            if 'info_card' in block_types:
                IC_CSS = 'ha-card .info-card-block{border-radius:12px!important;border-left:4px solid!important;margin-bottom:8px!important;padding:12px!important;display:flex!important;align-items:flex-start!important;gap:12px!important}'
                IC_CSS += 'ha-card .info-card-block[data-map=Isl]{border-color:#4CAF50!important;background:transparent!important}'
                IC_CSS += 'ha-card .info-card-block[data-map=Sco]{border-color:#FF5722!important;background:transparent!important}'
                IC_CSS += 'ha-card .info-card-block[data-map=Cen]{border-color:#009688!important;background:transparent!important}'
                IC_CSS += 'ha-card .info-card-block[data-map=Abe]{border-color:#9C27B0!important;background:transparent!important}'
                IC_CSS += 'ha-card .info-card-block[data-map=Ext]{border-color:#00BCD4!important;background:transparent!important}'
                IC_CSS += 'ha-card .info-card-block .ic-icon{width:48px!important;height:48px!important;flex-shrink:0!important;object-fit:contain!important;border-radius:8px!important;background:transparent!important}'
                IC_CSS += 'ha-card .info-card-block .ic-body{flex:1!important;min-width:0!important}'
                IC_CSS += 'ha-card .info-card-block .ic-body .ic-title{font-weight:600!important;font-size:1.05em!important;margin-bottom:4px!important;display:flex;align-items:center;gap:4px}'
                IC_CSS += 'ha-card .info-card-block .ic-body .ic-title ha-icon{flex-shrink:0}'
                IC_CSS += 'ha-card .info-card-block .ic-body .ic-text{font-size:.9em!important;line-height:1.5!important}'
                IC_CSS += 'ha-card .info-card-block .ic-sum-end{display:none}'
                IC_CSS += 'ha-card .info-card-block details[open] .ic-sum-top{display:none!important}'
                IC_CSS += 'ha-card .info-card-block details[open] .ic-sum-end{display:block!important}'
                IC_CSS += 'ha-card .info-card-block ha-icon.ic-auto-color{color:var(--primary-background-color)!important;fill:var(--primary-text-color)!important}'
                IC_CSS += 'ha-card .info-card-block img.ic-auto-color{filter:var(--ic-icon-filter,none)}'
                css += IC_CSS
                # 3-state map filter: linear (icon color) + block (background) per-map
                if has_map_filter and active_maps:
                    for m in sorted(active_maps):
                        mc = SERVER_MAP.get(m,{}).get('color','#888')
                        css += 'ha-card .ic-linear-'+m+' .mdi,ha-card .ic-linear-'+m+' ha-icon{color:'+mc+'!important}'
                        css += 'ha-card .ic-block-'+m+'{background:'+mc+'!important;border-radius:6px!important;padding:2px 6px!important;color:var(--primary-background-color)!important}'
                        css += 'ha-card .ic-block-'+m+' .mdi,ha-card .ic-block-'+m+' ha-icon{color:var(--primary-background-color)!important}'
                # Fixed styles (always available): hint + warning
                for fk, fv in FIXED_STYLES_MAP.items():
                    fc = fv['color']
                    css += 'ha-card .ic-linear-'+fk+' .mdi,ha-card .ic-linear-'+fk+' ha-icon{color:'+fc+'!important}'
                    css += 'ha-card .ic-block-'+fk+'{background:'+fc+'!important;border-radius:6px!important;padding:2px 6px!important;color:var(--primary-background-color)!important}'
                    css += 'ha-card .ic-block-'+fk+' .mdi,ha-card .ic-block-'+fk+' ha-icon{color:var(--primary-background-color)!important}'
            if 'card_grid' in block_types:
                css += 'ha-card .info-card{background:var(--primary-background-color);border-radius:8px;overflow:hidden;text-align:center;padding:0 0 8px 0}ha-card .info-card img{width:100%;aspect-ratio:1;object-fit:cover}ha-card .card-name{font-weight:600;margin:4px 0}ha-card .card-feature{font-size:0.85em;color:var(--secondary-text-color)}ha-card .card-grid{display:grid;gap:12px}'
        elif tab_type == 'server_grid':
            css = SERVER_GRID_CSS
        elif tab_type == 'expandable_detail':
            css = EXPANDABLE_DETAIL_CSS
        elif tab_type == 'farming_table':
            css = FARMING_TABLE_CSS
        elif tab_type in ('reference_table', 'mixed_content'):
            css = CARD_CORE_CSS + TABLE_CORE_CSS
        else:
            css = CARD_CORE_CSS

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
            "plugins": {"daisyui": {"enabled": True, "url": "https://cdn.jsdelivr.net/npm/daisyui@latest/dist/full.css", "theme": "dark - dark", "overrideCardBackground": False}, "tailwindElements": {"enabled": False}},
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

    # 1. SERVER RULES (views[8]) — tabbed layout, same as tribe ops
    sr_tabs = sr_data.get('tabs', [])
    sr_tab_buttons = [make_tab_button(t['name'], t.get('description',''), 'input_select.info_server_rules_tab') for t in sr_tabs]
    sr_tab_cards = []
    for t in sr_tabs:
        tname = t['name']
        ttype = t.get('type','')
        t_html = render_tab_html(t)
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

    views[8] = {
        "title": f'服务器规则 SYNC-{sr_ts}',
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
    }
    print(f'Server rules: REBUILT with {len(sr_tab_buttons)} tabs + {len(sr_tab_cards)} cards + timestamp {sr_ts}')

    # 2. INFO_WHITEROBER (views[6])
    tabs = to_data.get('tabs', [])
    tab_buttons = [make_tab_button(t['name'], t.get('description','')) for t in tabs]

    # Generate all tab conditional cards
    tab_cards = []
    for t in tabs:
        tname = t['name']
        ttype = t['type']
        if ttype == 'server_grid':
            t_html = render_server_grid(t)
        elif ttype == 'expandable_detail':
            t_html = render_expandable_detail(t)
        elif ttype == 'farming_table':
            t_html = render_farming_table(t)
        else:
            t_html = render_tab_html(t)
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

    info_view = views[6]
    info_view['title'] = f'部落运维速查 SYNC-{ts}'
    # Remove column_span from view level (it goes at section level)
    info_view.pop('column_span', None)

    # Build cards: tab bar + all generated conditional cards
    stack_cards = [
        # Tab bar
        {
            "type": "custom:mod-card",
            "card_mod": {"style": ":host { display: block !important; overflow-x: auto !important; white-space: nowrap !important; padding-bottom: 8px; } ha-card { backdrop-filter: none !important; -webkit-backdrop-filter: none !important; background: rgba(0,0,0,0) !important; box-shadow: none !important; }"},
            "card": {"type": "horizontal-stack", "cards": tab_buttons}
        }
    ] + tab_cards

    # Section with column_span: 2 AT SECTION LEVEL (matching old page pattern)
    info_view['sections'] = [{
        "type": "grid",
        "column_span": 2,
        "cards": [{
            "type": "vertical-stack",
            "grid_options": {"columns": "full"},
            "cards": stack_cards
        }]
    }]
    print(f'info_whiterober: REBUILT with {len(tab_buttons)} tabs + {len(tab_cards)} cards + timestamp {ts}')

    # 3. BASE_WHITEROBER (views[7]) - match old base_whiterober_old structure exactly
    bq_servers = bq_data.get('servers', {})

    # Raw HTML card — match old view exactly (daisyui enabled, CARD_CORE_CSS)
    def make_raw_card(html_content):
        return {
            "type": "custom:mod-card",
            "card_mod": {"style": "ha-card {\n  box-shadow: none !important;\n}\n"},
            "card": {
                "entity": "", "content": html_content, "ignore_line_breaks": True,
                "always_update": False, "parse_jinja": True, "code_editor": "Ace",
                "entities": [], "bindings": [], "actions": [],
                "plugins": {"daisyui": {"enabled": True, "url": "https://cdn.jsdelivr.net/npm/daisyui@latest/dist/full.css", "theme": "dark - dark", "overrideCardBackground": False}, "tailwindElements": {"enabled": False}},
                "debounceChangePeriod": 500,
                "type": "custom:tailwindcss-template-card",
                "card_mod": {"style": CARD_CORE_CSS + BASE_RAW_CSS}
            }
        }

    # Tab buttons: 英灵殿 + 孤岛号
    bq_tab_buttons = [
        make_tab_button('英灵殿', '设备·存储·消耗', 'input_select.info_tribe_tab'),
        make_tab_button('孤岛号', '设备·存储·消耗', 'input_select.info_tribe_tab')
    ]

    # Isl server tabs[0] = 英灵殿, tabs[1] = 孤岛号 (empty for now)
    isl = bq_servers.get('Isl', {})
    isl_tabs = isl.get('tabs', [])
    yl_data = (isl_tabs[0] or {}) if len(isl_tabs) > 0 else {}
    gh_data = (isl_tabs[1] or {}) if len(isl_tabs) > 1 else {}

    def build_section_html(tab_data):
        """Build HTML from tab's sections array, including section-tab-bar."""
        sections = tab_data.get('sections', [])
        if not sections:
            # Fallback: use raw html field directly
            return tab_data.get('html', '<p>暂无数据</p>')
        # Build section-tab-bar
        parts = ['<div class="section-tab-bar base-title-header">']
        for i, sec in enumerate(sections):
            active = ' tab-active' if i == 0 else ''
            sid = 'section-' + str(i)
            # Robust accordion: use closest() to find parent container,
            # then query within it (works in both Shadow DOM and regular DOM).
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

    yl_html = build_section_html(yl_data) if yl_data.get('sections') else yl_data.get('html', '<p>暂无数据</p>')
    gh_html = build_section_html(gh_data) if gh_data.get('sections') else gh_data.get('html', '<p>暂无数据</p>')

    bq_tab_cards = [
        {"type": "conditional", "conditions": [{"condition": "state", "entity": "input_select.info_tribe_tab", "state": "英灵殿"}],
         "card": make_raw_card(yl_html), "grid_options": {"columns": 24, "rows": "auto"}},
        {"type": "conditional", "conditions": [{"condition": "state", "entity": "input_select.info_tribe_tab", "state": "孤岛号"}],
         "card": make_raw_card(gh_html), "grid_options": {"columns": 24, "rows": "auto"}}
    ]

    bq_ts = datetime.now().strftime('%H:%M:%S')
    bq_stack_cards = [{
        "type": "custom:mod-card",
        "card_mod": {"style": ":host { display: block !important; overflow-x: auto !important; white-space: nowrap !important; padding-bottom: 8px; } ha-card { backdrop-filter: none !important; -webkit-backdrop-filter: none !important; background: rgba(0,0,0,0) !important; box-shadow: none !important; }"},
        "card": {"type": "horizontal-stack", "cards": bq_tab_buttons}
    }] + bq_tab_cards

    views[7] = {
        "title": f'老板部落基地速查 SYNC-{bq_ts}',
        "path": "base_whiterober",
        "theme": "Material You",
        "sections": [{
            "type": "grid",
            "column_span": 2,
            "cards": [{
                "type": "vertical-stack",
                "grid_options": {"columns": "full"},
                "cards": bq_stack_cards
            }]
        }]
    }
    print(f'base_whiterober: REBUILT with 2 tab buttons + {len(bq_tab_cards)} conditional cards + timestamp {bq_ts}')

    # 4. Keep old views (9,10) untouched - they reference original lovelace-old
    print(f'Old views preserved: views[9]={views[9].get("title")}, views[10]={views[10].get("title")}')

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
    print(f'\nSaved: {len(raw)} bytes, {len(views)} views')
