
/* ===== v72：该物种 Wiki 速查（数据懒加载 CF 静态表 wiki_dex.json） =====
   · 入口复用「操作」按钮样式（.lb-tipb.lb-bar-btn），逻辑同样读 LB.curClass
   · 数据按需 fetch（48 KB / gzip 12.8 KB），不占首屏
   · 键位图标改调项目 lbKeyChipHtml()，不再自带一份 LB_KEYSVG */
// v72b：data = 当前物种的「合并视图」（index + 单物种）；idx = 共享表+物种清单；sp = 单物种缓存
// v72g：纯后端按需抓取＋分级轮询
var LB_WIKI_API = 'https://data.whiterober.ccwu.cc/api/wiki/';
var LB_WIKI = { idx:null, sp:{}, data:null, p:null, pIdx:null, cur:'', tab:0, err:null, progress:null, mode:'', mapId:'' };   // v5875：mode='map' 时分派到地图 Wiki（复用同一面板）
/* v5739（用户口径）：「技巧」排在「生成指令」之前；「生成指令」改名「生成」。
   · 技巧 = dododex 玩家分享心得（按点赞排序），本轮先占位（renderTips），
     抓取 + 后端共享翻译缓存后续批次接入（见 方案_技巧TAB_v1.md）
   · 注意：tab 用**索引**分发（见 lbWikiRender），新增/移位后必须同步改 `_T === n` 链 */
var LB_WIKI_TABS = ['概览','驯服','繁殖','采集','收割','技能','经验','技巧','生成','装备'];   // v5826（用户口径「有鞍或有附件的物种加一个装备 TAB」）：末尾追加，零索引位移
/* ===== v5807（用户口径）：虚线黄框 .tc-note → 标题栏问号图标的自定义 tips =====
   · 黄框本体已被 CSS 隐藏（不占版面），文本仍在 DOM 里
   · 正文每次变化后把本浮窗内所有 .tc-note 的纯文本合并写入 #lbWikiHelp/#lbWikiItemHelp 的 data-tip
   · 没有黄框 ⇒ 图标 hidden（不出现空悬停） */
function tcSyncNotes(bodyId, helpId){
  try{
    var body = document.getElementById(bodyId), help = document.getElementById(helpId);
    if (!body || !help) return;
    var ns = body.querySelectorAll('.tc-note'), parts = [];
    for (var i = 0; i < ns.length; i++){
      var t = String(ns[i].textContent || '').replace(/\s+/g, ' ').trim();
      if (t && parts.indexOf(t) < 0) parts.push(t);
    }
    if (!parts.length){ help.setAttribute('hidden', 'hidden'); help.removeAttribute('data-tip'); return; }
    help.removeAttribute('hidden');
    help.setAttribute('data-tip', parts.join(' ｜ '));
  }catch(e){}
}
function tcSyncNotesAll(){ tcSyncNotes('lbWikiBody', 'lbWikiHelp'); tcSyncNotes('lbWikiItemBody', 'lbWikiItemHelp'); }
/* ===== v5808（用户口径）：wiki 内的 .tc-tip 气泡改走统一 tips 引擎 #lbTipBox =====
   · 原 ::after 气泡是 absolute 居中，移动端贴近边缘会被裁（已 display:none）
   · 这里把 .tc-tip 的 data-tip 交给 #lbTipBox：固定定位 + 左右钳制 + 自动换行，内容永远完整
   · 桌面：悬停显示/离开收起；移动：点按显示，滚动或点别处收起 */
(function(){
  if (window.__tcTipBridge) return; window.__tcTipBridge = 1;
  function inWiki(el){
    try{ return !!(el && el.closest && (el.closest('#lbWikiOverlay') || el.closest('#lbWikiItemOverlay'))); }catch(e){ return false; }
  }
  function tipOf(ev){
    try{
      var t = ev && ev.target; if (!t || !t.closest) return null;
      var e = t.closest('.tc-tip');
      if (!e || !inWiki(e)) return null;
      return (e.getAttribute('data-tip') || '') ? e : null;
    }catch(e2){ return null; }
  }
  function show(el){
    try{
      el.setAttribute('title', el.getAttribute('data-tip') || '');
      if (window.lbTipShowEl) window.lbTipShowEl(el);
    }catch(e3){}
  }
  function hide(){ try{ if (window.lbTipHide) window.lbTipHide(); }catch(e4){} }
  document.addEventListener('mouseover', function(ev){ var e = tipOf(ev); if (e) show(e); }, true);
  document.addEventListener('mouseout', function(ev){ if (tipOf(ev)) hide(); }, true);
  document.addEventListener('touchstart', function(ev){ var e = tipOf(ev); if (e) show(e); else hide(); }, { capture: true, passive: true });
  document.addEventListener('scroll', function(){ hide(); }, true);
  document.addEventListener('click', function(ev){ if (!tipOf(ev)) hide(); }, true);
})();
(function(){
  try{
    var mo = new MutationObserver(function(){ tcSyncNotesAll(); });
    ['lbWikiBody', 'lbWikiItemBody'].forEach(function(id){
      var el = document.getElementById(id);
      if (el) mo.observe(el, { childList: true, subtree: true, characterData: true });
    });
  }catch(e0){}
})();
/* v5796（用户口径「收割 TAB 整个隐藏，意义不大」）：索引原样保留（分发逻辑仍按 4 走），
   只在渲染 tab 条时过滤掉「收割」+ lbWikiTabIdx() 兜底回落「采集」，
   任何入口（旧链接 / 记忆态 LB_WIKI.tab=4）都进不到收割页。 */
var LB_WIKI_TAB_HIDE = { 4: 1 };

function lbWikiEl(id){ return document.getElementById(id); }

function lbWikiOpen(){
  /* v162（用户口径）：取物种对齐项目范式（同 lbRouteOpen）——**只读 LB.curClass**。
     旧写法 LB_WIKI.cur || LB.curClass：LB_WIKI.cur 是「面板上次打开的物种」，一旦有值就永远压过当前选中物种，
     且后面 LB_WIKI.cur = cls 把旧值又写回 ⇒ 自我锁定，切物种后打开仍是上一个物种的数据。 */
  var cls = '';
  try { cls = String(LB.curClass || ''); } catch (e) {}
  if (!cls) {
    // v72a：物品模式不再误报「请先选择一个物种」
    var _it = null;
    try { _it = LB.pickItem || null; } catch (eI) {}
    if (_it) { try { lbToast('物品 Wiki 暂未收录（当前仅物种速查）'); } catch (eT1) {} return; }
    try { lbToast('请先选择一个物种'); } catch (e2) {}
    return;
  }
  LB_WIKI.cur = cls;
  LB_WIKI.mode = '';   // v5875：物种入口打开时切回物种模式
  // v72c：切物种必须清空合并视图 —— 否则 lbWikiRender 会用上一个物种的数据渲染（报错 / 串物种）
  LB_WIKI.data = null;
  LB_WIKI.err = null;
  LB_WIKI.itemFB = null;   // v5848：切物种必须清掉上一个物种的物品回退缓存
  try { LB_WT_TRIED = {}; } catch (eWTR) {}   /* v6029：打开/切物种时清空一次性标记，允许重新尝试拉取 AI 整理结果 */
  var ov = lbWikiEl('lbWikiOverlay');
  if (!ov) return;
  ov.classList.add('show');
  lbWikiLayoutWatch();   // v5756：布局修正（隐藏无序号小标题 / 徽章移到文案块下方）
  lbWikiRender();
  lbWikiEnsure().then(function(){ lbWikiRender(); })
    .catch(function(e){ LB_WIKI.err = e; lbWikiRender(); });
}

function lbWikiClose(){
  var ov = lbWikiEl('lbWikiOverlay');
  if (ov) ov.classList.remove('show');
}

/* v6107（用户口径）：网络错误后的「重试」—— 清掉错误态/缓存的残缺数据，重新走一次完整拉取 */
function lbWikiRetry(){
  var cls = '';
  try { cls = String((LB_WIKI && LB_WIKI.cur) || ''); } catch (e0) {}
  try {
    LB_WIKI.err = null;
    LB_WIKI.data = null;
    LB_WIKI.itemFB = null;
    LB_WIKI.progress = null;
    if (cls) { try { delete LB_WIKI.sp[cls]; } catch (e1) { LB_WIKI.sp[cls] = null; } }
    try { LB_WT_TRIED = {}; } catch (e2) {}
  } catch (e3) {}
  if (!cls) return;
  try { lbWikiOpen(cls); } catch (e4) {}
}

/* v6107（用户口径「wiki 要在浮窗右上角 tips 中显示取到了哪几个源的数据」）：
   三源状态：wikily / wiki.gg(ark) / dododex(技巧)；另列出已取到的数据块。
   注意：data-tip 走 CSS content:attr()，需 .lw-multi 的 white-space:pre-line 才能保留换行。 */
function lbWikiSrcTip(){
  var el = document.getElementById('lbWikiSrcHelp');
  if (!el) return;
  var d = null, D = {};
  try { d = LB_WIKI.data || null; } catch (e0) { d = null; }
  if (d) {
    /* v6107 修正：拼装后的 LB_WIKI.data.DATA / OVERVIEW 都是**按物种键分组的字典**
       （lbWikiRender 里写的是 (LB_WIKI.data.OVERVIEW || {})[_wk]），
       直接读 D.slug 会拿到 undefined ⇒ 误显示「—」。这里先按键取，取不到再当扁平结构。 */
    var _k = '';
    try { _k = String(CUR || lbWikiKey(LB_WIKI.cur) || ''); } catch (eK) { _k = ''; }
    var _all = d.DATA || {};
    try { D = (_k && _all && _all[_k]) ? _all[_k] : (_all || {}); } catch (eK2) { D = _all || {}; }
    if (D && typeof D === 'object' && !D.slug && !D._arkSlug) {
      /* 再兜一层：可能是 {物种: {...}} 但键名不同（大小写/全名），取第一个含 slug 的值 */
      try {
        var _ks = Object.keys(_all || {});
        for (var _i = 0; _i < _ks.length && _i < 20; _i++) {
          var _v = _all[_ks[_i]];
          if (_v && typeof _v === 'object' && (_v.slug || _v._arkSlug)) { D = _v; break; }
        }
      } catch (eK3) {}
    }
  }
  if (!d) { el.setAttribute('hidden', 'hidden'); el.removeAttribute('data-tip'); return; }
  var isArk = (String(D._src || '').toLowerCase() === 'ark');
  var slugW = String(D.slug || '');
  var wikilyOk = !!slugW && !isArk;
  var arkOk = !!(D._arkSlug || D._arkVer);
  var dodoOk = false;
  try { dodoOk = (typeof lbTipsHasResult === 'function') ? !!lbTipsHasResult() : false; } catch (e1) {}
  if (!dodoOk) { try { dodoOk = !!(LB_TIPS && LB_TIPS.ready); } catch (e2) {} }
  var blocks = [];
  try {
    ['HOME','OVERVIEW','TAME','BREED','BREED_DESC','GATHER','HARVEST','ABIL','EXP','SPAWN','ITEMS'].forEach(function (b) {
      var v = d[b];
      if (!v) return;
      if (typeof v === 'object' && v._fail) return;
      blocks.push(b);
    });
  } catch (e3) {}
  var L = [];
  L.push('数据来源');
  L.push('· wikily     ' + (wikilyOk ? ('已取到（' + slugW + '）') : (isArk ? '未取到（已回退 wiki.gg）' : '—')));
  L.push('· wiki.gg    ' + (arkOk ? ('已取到（' + String(D._arkSlug || 'ark') + '）') : '—'));
  L.push('· dododex    ' + (dodoOk ? '已取到（技巧）' : '—'));
  if (blocks.length) L.push('已取块：' + blocks.join(' / '));
  el.removeAttribute('hidden');
  el.classList.add('lw-multi');
  el.setAttribute('data-tip', L.join('\n'));
  el.setAttribute('aria-label', '数据来源：wikily ' + (wikilyOk ? '有' : '无') + ' · wiki.gg ' + (arkOk ? '有' : '无') + ' · dododex ' + (dodoOk ? '有' : '无'));
}

/* ===== v6109（用户口径「Freeze / Heal 为啥没被翻译」）：技能名/说明的**英文兜底翻译** =====
   · 触发条件：HOME.skills 里 zh 或 desc **完全不含中文**（= wikily 中文站自己漏翻）
   · 数据源：复用项目已有 AI 通道（lbAiCfgGet + /chat/completions），不新增后端接口
   · 缓存：localStorage 'lbWikiSkillZh' = { "<中文名||说明>": {zh, desc} }，上限 200 条，跨物种复用
   · 失败：静默保留英文原文，仅 ?debug=1 时打日志；不阻塞、不弹错 */
var LB_SKILL_ZH_KEY = 'lbWikiSkillZh';
var LB_SKILL_ZH_MAX = 200;
var LB_SKILL_ZH = null;
var LB_SKILL_ZH_BUSY = null;

function lbHasZh(s){ return /[\u4e00-\u9fff]/.test(String(s == null ? '' : s)); }

function lbSkillZhCache(){
  if (LB_SKILL_ZH) return LB_SKILL_ZH;
  LB_SKILL_ZH = {};
  try {
    var raw = localStorage.getItem(LB_SKILL_ZH_KEY);
    if (raw){ var o = JSON.parse(raw); if (o && typeof o === 'object') LB_SKILL_ZH = o; }
  } catch (e0) {}
  return LB_SKILL_ZH;
}

function lbSkillZhSave(){
  try {
    var c = lbSkillZhCache(), ks = Object.keys(c);
    if (ks.length > LB_SKILL_ZH_MAX) ks.slice(0, ks.length - LB_SKILL_ZH_MAX).forEach(function (k) { delete c[k]; });
    localStorage.setItem(LB_SKILL_ZH_KEY, JSON.stringify(c));
  } catch (e0) {}
}

/* 当前物种的 HOME.skills（兼容按物种分组 / 扁平两种结构） */
function lbSkillHome(){
  try {
    var d = LB_WIKI.data || {};
    var k = String(CUR || lbWikiKey(LB_WIKI.cur) || '');
    var H = d.HOME || {};
    if (H && H[k] && typeof H[k] === 'object') return H[k];
    if (H && (H.skills || H.abilIntro)) return H;
  } catch (e0) {}
  return null;
}

/* 需要补译的技能条目（zh 或 desc 无中文） */
function lbSkillZhNeed(){
  var out = [];
  try {
    var hm = lbSkillHome();
    var sk = (hm && hm.skills) || [];
    for (var i = 0; i < sk.length; i++){
      var s = sk[i] || {};
      var zh = String(s.zh || ''), ds = String(s.desc || '');
      if (!zh && !ds) continue;
      if (lbHasZh(zh) && (!ds || lbHasZh(ds))) continue;          // 已是中文，跳过
      out.push({ i: i, en: zh, enDesc: ds, key: zh + '||' + ds });
    }
  } catch (e0) {}
  return out;
}

/* 把缓存译文套回 HOME.skills，返回改动条数 */
function lbSkillZhApply(){
  var n = 0;
  try {
    var hm = lbSkillHome();
    var sk = (hm && hm.skills) || [];
    var c = lbSkillZhCache();
    for (var i = 0; i < sk.length; i++){
      var s = sk[i] || {};
      var e = c[String(s.zh || '') + '||' + String(s.desc || '')];
      if (!e) continue;
      if (e.zh && !lbHasZh(s.zh)){ s.zh = e.zh; n++; }
      if (e.desc && !lbHasZh(s.desc)){ s.desc = e.desc; n++; }
    }
  } catch (e0) {}
  return n;
}

/* 异步补译；cb(changed) —— 只有真的改了才 true */
function lbSkillZhEnsure(cb){
  var done = function (v) { if (cb) { try { cb(!!v); } catch (eD) {} } };
  var need = lbSkillZhNeed();
  if (!need.length){ done(false); return; }
  var c = lbSkillZhCache();
  var todo = need.filter(function (x) { return !c[x.key]; });
  if (!todo.length){ done(lbSkillZhApply() > 0); return; }
  if (LB_SKILL_ZH_BUSY) return;
  var cfg = null; try { cfg = lbAiCfgGet(); } catch (e1) { cfg = null; }
  if (!cfg || !cfg.token) { done(false); return; }

  LB_SKILL_ZH_BUSY = 1;
  var batch = todo.slice(0, 8);
  var meta = document.getElementById('lbWikiMeta');
  if (meta){ meta.style.display = ''; meta.textContent = '技能名补译中…'; }
  var SYS = '你是 ARK: Survival Ascended 的中文译员。把用户给出的英文技能名与说明翻成简体中文：'
    + '技能名 2-8 字，说明一句话讲清机制与限制；专有名词按游戏内通用叫法。'
    + '只输出 JSON：{"items":[{"zh":"中文技能名","desc":"中文说明"}]}，条数与顺序与输入一致。';
  var usr = batch.map(function (x, i) {
    return (i + 1) + '. 名称：' + x.en + (x.enDesc ? ('\n   说明：' + x.enDesc) : '');
  }).join('\n');

  fetch(String(cfg.base || LB_AI_BASE).replace(/\/+$/, '') + '/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + cfg.token },
    body: JSON.stringify({
      model: lbAiNormModel(cfg.model),
      messages: [{ role: 'system', content: SYS }, { role: 'user', content: usr }],
      temperature: 0.2, max_tokens: 1200,
      thinking: { type: 'disabled' },
      response_format: { type: 'json_object' }
    })
  }).then(function (r) { return r.text().then(function (tx) { return { s: r.status, t: tx }; }); })
    .then(function (x) {
      LB_SKILL_ZH_BUSY = null;
      if (meta){ meta.textContent = ''; meta.style.display = 'none'; }
      if (x.s !== 200) { try { if (LB_DEBUG) console.log('skillZh http ' + x.s); } catch (eL) {} done(false); return; }
      var j = null; try { j = JSON.parse(x.t); } catch (e2) {}
      var ch = (j && j.choices && j.choices[0]) ? j.choices[0] : null;
      var m = (ch && ch.message) ? ch.message : null;
      var content = (m && m.content) ? String(m.content) : '';
      var o = null; try { o = lbAiParseJson(content); } catch (e3) {}
      if (!o && m && m.reasoning_content) { try { o = lbAiParseJson(String(m.reasoning_content)); } catch (e4) {} }
      var items = (o && (o.items || o.abil)) || (Array.isArray(o) ? o : []);
      if (!items || !items.length) { done(false); return; }
      for (var i = 0; i < batch.length && i < items.length; i++){
        var it = items[i] || {};
        var zh2 = String(it.zh || '').trim(), ds2 = String(it.desc || '').trim();
        if (!zh2 || !lbHasZh(zh2)) continue;           // 模型没给中文 → 不缓存（下轮再试）
        c[batch[i].key] = { zh: zh2, desc: lbHasZh(ds2) ? ds2 : '' };
      }
      lbSkillZhSave();
      done(lbSkillZhApply() > 0);
    })
    .catch(function () {
      LB_SKILL_ZH_BUSY = null;
      if (meta){ meta.textContent = ''; meta.style.display = 'none'; }
      done(false);
    });
}

/* ===== v153：后端已抓 wiki 缓存清单（客户端下载后端缓存，非静态表）=====
   GET /api/wiki/index -> {ok, count, species:{ 短名: 中文名 }}
   species[短名] 非空 = 已有数据；缺键或空串 = 尚未抓取 / 抓取失败 */
var LB_WIKI_IDX_API = null;
var LB_WIKI_IDX_API_P = null;
function lbWikiIndexApi(force){
  if (LB_WIKI_IDX_API && !force) return Promise.resolve(LB_WIKI_IDX_API);
  if (LB_WIKI_IDX_API_P) return LB_WIKI_IDX_API_P;
  var u = String(LB_WIKI_API || '').replace(/\/api\/wiki\/?$/, '/api/wiki/index');
  LB_WIKI_IDX_API_P = fetch(u + '?t=' + Date.now(), { cache: 'no-store' })
    .then(function(r){ if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(function(j){ LB_WIKI_IDX_API = (j && j.species) || {}; LB_WIKI_IDX_API_P = null; return LB_WIKI_IDX_API; })
    .catch(function(e){ LB_WIKI_IDX_API_P = null; throw e; });
  return LB_WIKI_IDX_API_P;
}
/* v5862（用户口径「明明用ai整理过了 入口还是虚线」）：
   物种在 wikily 无页面（载具/器械）但后端已有 AI 整理结果（/api/dino/wikitext 的 ready=true）时，
   入口不该恒判「暂无详细资料」⇒ 虚线。这里缓存「已探到 ready」的 slug（小写）。 */
var LB_WT_AI_PROBE = {};   // slug(小写) -> 1 ：已知有 AI 整理结果
var LB_WT_AI_TRY = {};     // slug(小写) -> 1 ：已发起过探测（防重入 / 防轮询）
function lbWikiHasData(cls){
  /* v156（用户口径）：候选键走**项目统一物种对照表**，不自造归一
     · 项目权威：ASA-values.json（ASB_DB）的 species[].name + blueprintPath
       入口 = lbSpName(cls) -> {zh(中文), eng(ASB 英文名)}
     · 短名 lbWikiKey() 仅作第一候选；ASB 英文名作第二候选
       （后端缓存按 slug 落盘，如 Ankylo 短名失败、Ankylosaurus 有数据） */
  var c0 = String(cls || '');
  if (!c0) return false;
  var cands = [], k0 = '';
  try { k0 = String(lbWikiKey(c0) || ''); } catch(e) {}
  if (k0) cands.push(k0);
  try {
    var nm = lbSpName(c0);                                       // 项目统一对照表（ASB 权威名）
    if (nm && nm.eng && cands.indexOf(String(nm.eng)) < 0) cands.push(String(nm.eng));
  } catch(e) {}
  // ① 本次会话已抓 —— 必须是有效数据（DATA.zh 非空），失败记录不算
  for (var i = 0; i < cands.length; i++){
    var sp = (LB_WIKI.sp && LB_WIKI.sp[cands[i]]) || null;
    if (sp && String((sp.DATA || {}).zh || '').length) return true;
  }
  /* ③ v5862（用户口径「明明用ai整理过了 入口还是虚线」）：
     后端 AI 整理结果已就绪也算「有资料」—— 载具在 wikily 无页面，
     但整理后概览/装备/技巧都有内容，入口不能恒虚线。
     整理缓存的 slug 是小写（如 battlerig），而 cands 是 BattleRig ⇒ 必须小写比对。 */
  for (var q = 0; q < cands.length; q++){
    var _cq = String(cands[q] || '').toLowerCase();
    if (_cq && LB_WT_AI_PROBE[_cq]) return true;
  }
  // ② 后端缓存清单 /api/wiki/index
  var m = LB_WIKI_IDX_API;
  if (!m) return false;
  for (var j = 0; j < cands.length; j++){
    if (m[cands[j]] && String(m[cands[j]]).length) return true;
  }
  return false;
}

// v72b：拆分加载 —— index.json（共享表+物种清单，约 14KB 一次性）+ wiki/<物种>.json（约 11KB，点哪个下哪个）
function lbWikiEnsureIndex(){
  if (LB_WIKI.idx) return Promise.resolve(LB_WIKI.idx);
  if (LB_WIKI.pIdx) return LB_WIKI.pIdx;
  LB_WIKI.pIdx = fetch('wiki/index.json?t=' + Date.now(), { cache: 'no-store' })
    .then(function(r){ if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(function(j){ LB_WIKI.idx = j; LB_WIKI.pIdx = null; return j; })
    .catch(function(e){ LB_WIKI.pIdx = null; throw e; });
  return LB_WIKI.pIdx;
}
// v72g：后端按需抓取（首次约 4 秒出概览；之后走缓存）
// v77：分级渲染 —— 后端首步（首页）抓到 OVERVIEW 就先用起来，其余 tab 后台补齐
function lbWikiTakePartial(key, payload){
  try{
    if (!payload || !payload.data) return false;
    var ov = payload.data.OVERVIEW || {};
    // v84：后端 OVERVIEW 是扁平结构 {intro:[],tips:[],stats:[],bp:''}，
    //   原来遍历 Object.keys(ov) 再取 ov[k].intro（把数组当对象）⇒ 永远 false ⇒ 分级渲染不触发。
    var has = !!(ov.intro && ov.intro.length);
    if (!has) {
      // 兼容已按物种分组的结构（OVERVIEW[物种] = {intro:[]}）
      try {
        var _ok = lbWikiKey(key);
        var _oo = ov[_ok];
        if (_oo && _oo.intro && _oo.intro.length) has = true;
      } catch (eJ) {}
    }
    if (!has) return false;
    if (LB_WIKI.sp[key] === payload.data) return false;
    LB_WIKI.sp[key] = payload.data;
    LB_WIKI.data = lbWikiAssemble(key);
    try { lbWikiRender(); } catch(e){}
    return true;
  }catch(e){ return false; }
}

function lbWikiEnsureSpecies(key){
  key = String(key || '');
  if (!key) return Promise.reject(new Error('no species key'));
  if (LB_WIKI.sp[key]) return Promise.resolve(LB_WIKI.sp[key]);
  var api = LB_WIKI_API + encodeURIComponent(key);
  /* v6107（用户口径「浮窗卡在 0/5 不动」）：错误必须分类型，否则网络抖动会被当成
     「该物种 wikily 没页面」⇒ 走进物品回退 ⇒ 停在「正在初始化」。
       net     = 网络/超时（应显示错误 + 重试按钮）
       nosite  = 后端明确说没页面（才允许走物品回退） */
  var _tag = function(e, kind){ try { if (e && !e.lbKind) e.lbKind = kind; } catch (e0) {} return e; };
  return fetch(api + '?t=' + Date.now(), { cache: 'no-store' })
    .then(function(r){ if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(function(j){
      if (j.status === 'ready' && j.data) { LB_WIKI.sp[key] = j.data; LB_WIKI.progress = null; return j.data; }
      if (j.status === 'error') throw _tag(new Error(j.err || '加载失败'), 'nosite');
      lbWikiTakePartial(key, j);   // v77：已有概览就先渲染（不等全部抓完）
      // fetching / partial → 轮询
      LB_WIKI.progress = { key: key, done: j.done || 0, total: j.total || 6 };
      try { lbWikiRender(); } catch (e0) {}
      return new Promise(function(resolve, reject){
        /* v6107（雪鸮实测：后端单步 fetch HOME 就耗 79 秒）——
           ① 失败计数与成功分离：网络失败连续 6 次（≈12s 起）立即报错，不再硬等
           ② 退避：2s → 4s → 6s … 上限 8s
           ③ 总时长上限 40 次(80s) → 90 次(180s)：后端冷抓 5 个块可能要 2~3 分钟
           ④ 任一成功响应即 fails=0（“慢但活着”不会误判为断网） */
        var tries = 0, fails = 0, timer = null;
        var stop = function(err){
          if (timer) { clearTimeout(timer); timer = null; }
          LB_WIKI.progress = null;
          if (err) reject(err);
        };
        var tick = function(){
          tries++;
          fetch(api + '/progress?t=' + Date.now(), { cache: 'no-store' })
            .then(function(r){ if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
            .then(function(p){
              fails = 0;
              if (p.status === 'ready' && p.data) {
                LB_WIKI.sp[key] = p.data; stop(null); resolve(p.data); return;
              }
              if (p.status === 'error') { stop(_tag(new Error(p.err || '加载失败'), 'nosite')); return; }
              var _prevDone = (LB_WIKI.progress && LB_WIKI.progress.done) || 0;
              var _changed = false;
              try { _changed = !!lbWikiTakePartial(key, p); } catch (eTP) { _changed = false; }
              LB_WIKI.progress = { key: key, done: p.done || 0, total: p.total || 6 };
              if (_changed || _prevDone !== (p.done || 0)) {
                try { lbWikiRender(); } catch (e1) {}
              }
              if (tries > 90) { stop(_tag(new Error('加载超时（后端仍在抓取，请稍后重试）'), 'net')); return; }
              timer = setTimeout(tick, 2000);
            })
            .catch(function(eX){
              fails++;
              if (fails >= 6) { stop(_tag(new Error('数据服务连接失败（已重试 ' + fails + ' 次）'), 'net')); return; }
              if (tries > 90) { stop(_tag(new Error('加载超时'), 'net')); return; }
              timer = setTimeout(tick, Math.min(8000, 2000 * fails));
            });
        };
        timer = setTimeout(tick, 2000);
      });
    })
    .catch(function(eZ){ throw _tag(eZ, 'net'); });
}
// index + 单物种 → 合并视图（渲染层一直读这个结构，零改动）
var LB_WIKI_SPECIES_KEYS = ['DATA','TAME','BREED','BREED_DESC','GATHER','HARVEST','ABIL','EXP','SPAWN','OVERVIEW','HOME'];
function lbWikiAssemble(key){
  var idx = LB_WIKI.idx || {};
  var sp = (LB_WIKI.sp && LB_WIKI.sp[key]) || null;
  if (!sp) return null;
  var d = {};
  Object.keys(idx).forEach(function(k){
    if (k === '_species' || k === '_v') return;
    d[k] = idx[k];
  });
  LB_WIKI_SPECIES_KEYS.forEach(function(k){
    var box = (d[k] && typeof d[k] === 'object') ? d[k] : {};
    if (sp[k] !== undefined) box[key] = sp[k];
    d[k] = box;
  });
  return d;
}
// v72b：该物种有没有 wiki（查 index 清单，不需等数据）
function lbWikiHas(cls){
  // v153：改为真实判定 —— 后端缓存清单 /api/wiki/index 里有该物种且中文名非空
  //   原写法 `!!lbWikiKey(cls)` 恒 true（lbWikiKey 最后 return s1 || cls）⇒ 入口永远实心蓝
  return lbWikiHasData(cls);
}
// 兼容旧调用：保证 index + 当前物种都就绪
function lbWikiEnsure(){
  return lbWikiEnsureIndex().then(function(){
    var k = lbWikiKey(LB_WIKI.cur);
    return lbWikiEnsureSpecies(k).then(function(){
      LB_WIKI.data = lbWikiAssemble(k);
      return LB_WIKI.data;
    });
  });
}

// LB.curClass 是物种类名（如 Rex_Character_BP_C），wiki_dex 的 key 是短名（Rex）
// 依次尝试：原样 → 去 _Character_BP_C / _C 后缀 → 物种库 name
function lbWikiKey(cls){
  cls = String(cls || '');
  if (!cls) return '';
  var D = (LB_WIKI.data && LB_WIKI.data.DATA) || {};
  var S = (LB_WIKI.idx && LB_WIKI.idx._species) || {};   // v72b：清单也能判定
  if (D[cls] || S[cls]) return cls;
  var s1 = cls.replace(/_Character_BP_C$/, '').replace(/_Character_BP$/, '').replace(/_C$/, '');
  if (D[s1] || S[s1]) return s1;
  try {
    var sp = (typeof findSpeciesByClass === 'function') ? findSpeciesByClass(cls) : null;
    if (sp && sp.name && (D[sp.name] || S[sp.name])) return sp.name;
  } catch (e) {}
  // 还没有数据时，至少给出短名供后续比对
  return s1 || cls;
}

function lbWikiCur(){
  var d = LB_WIKI.data;
  if (!d) return null;
  return (d.DATA || {})[lbWikiKey(LB_WIKI.cur)] || null;
}
// v72c：当前物种数据是否已就绪（区分「loading」与「未收录」）
function lbWikiSpReady(){
  var k = lbWikiKey(LB_WIKI.cur);
  return !!(k && LB_WIKI.sp && LB_WIKI.sp[k] && LB_WIKI.data);
}

/* ===== P2 兼容层：原型页模块级全局 → 项目 LB_WIKI.data（唯一数据源）===== */
var WIKI_DEX = null, DATA = null, TAME = null, FOODS = null, EXP = null, WIKI_HOME = null,
    TAME_COMBOS = null, ROLES = null, TAME_WEAPONS = null, TAME_AMMO = null,
    TAME_W_INST = null, OVERVIEW = null, BREED = null, BREED_DESC = null,
    GATHER = null, HARVEST = null, ABIL = null, SPAWN = null, SPAWN_TPL = null,
    SPAWN_LV = null, ITEMS = null, EXP_QUALITY = null, CUR = '';

function lbWikiBind(){
  var d = LB_WIKI.data;
  if (!d) return;
  WIKI_DEX = d;
  DATA = d.DATA || {}; TAME = d.TAME || {}; FOODS = d.FOODS || {};
  EXP = d.EXP || {}; TAME_COMBOS = d.TAME_COMBOS || {}; ROLES = d.ROLES || {};
  TAME_WEAPONS = d.TAME_WEAPONS || {}; TAME_AMMO = d.TAME_AMMO || {};
  TAME_W_INST = d.TAME_W_INST || {}; OVERVIEW = d.OVERVIEW || {};
  WIKI_HOME = d.HOME || {};   // v95：各 tab 前置文案（后端 HOME[key].tameIntro 等）
  BREED = d.BREED || {}; BREED_DESC = d.BREED_DESC || {}; GATHER = d.GATHER || {};
  HARVEST = d.HARVEST || {}; ABIL = d.ABIL || {}; SPAWN = d.SPAWN || {};
  SPAWN_TPL = d.SPAWN_TPL || {}; SPAWN_LV = d.SPAWN_LV || {};
  ITEMS = d.ITEMS || {}; EXP_QUALITY = d.EXP_QUALITY || {};
  TC_TIPS = d.TC_TIPS || {};
  CUR = lbWikiKey(LB_WIKI.cur);
  // v72h：后端只回文案 → stats / bp 用项目物种数据自算（与静态版口径一致）
  try {
    var ovBox = d.OVERVIEW || (d.OVERVIEW = {});
    var ov = ovBox[CUR] || (ovBox[CUR] = {});
    // v84：后端 OVERVIEW 是扁平的（intro/tips 在顶层），必须搬进按物种分组的 ov，
    //   否则 renderOverview 的 OV[CUR].intro 恒空 ⇒ 概述段落永远显示"（无概述段落）"。
    if ((!ov.intro || !ov.intro.length) && ovBox.intro && ovBox.intro.length) ov.intro = ovBox.intro;
    if ((!ov.tips || !ov.tips.length) && ovBox.tips && ovBox.tips.length) ov.tips = ovBox.tips;
    if (!ov.stats || !ov.stats.length) {
      var sp = (typeof findSpeciesByClass === 'function') ? findSpeciesByClass(String(LB_WIKI.cur || LB.curClass || '')) : null;
      var fsr = sp && sp.fullStatsRaw;
      if (fsr) {
        // v125：属性名走项目唯一源 LB_STAT_LABELS_DINO（由 renderPreviewContent 的 statLabels 提升为全局）
        var IDX = [[0, 'health'], [1, 'stamina'], [2, 'torpidity'], [3, 'oxygen'],
                   [4, 'food'], [7, 'weight'], [8, 'melee_damage_multiplier'], [9, 'speed_multiplier']];
        var _SL = (typeof LB_STAT_LABELS_DINO !== 'undefined') ? LB_STAT_LABELS_DINO : {};
        ov.stats = IDX.map(function (x) {
          var e = fsr[x[0]];
          return [_SL[x[1]] || x[1], e ? e[0] : null, e ? e[1] : null];
        });
      }
    }
    if (!ov.bp) {
      var sp2 = (typeof findSpeciesByClass === 'function') ? findSpeciesByClass(String(LB_WIKI.cur || LB.curClass || '')) : null;
      if (sp2 && sp2.blueprintPath) ov.bp = sp2.blueprintPath;
    }
    OVERVIEW = ovBox;
  } catch (eS) {}

  // v72i：驯服 setup / 繁殖参数 —— 项目 values.json 已齐备，不用抓
  try {
    var _sp0 = (typeof findSpeciesByClass === 'function') ? findSpeciesByClass(String(LB_WIKI.cur || LB.curClass || '')) : null;
    // ① 驯服 setup（8 个系数）
    if (_sp0 && !(TAME[CUR] && TAME[CUR].setup)) {
      var tm = _sp0.taming || null;
      var fsr0 = _sp0.fullStatsRaw || [];
      if (tm && fsr0.length >= 5 && tm.affinityNeeded0 != null) {
        TAME[CUR] = {
          zh: ((DATA[CUR] || {}).zh) || '',
          setup: {
            req: tm.affinityNeeded0,
            per_level: tm.affinityIncreasePL,
            ineff: tm.tamingIneffectiveness,
            rate: (tm.foodConsumptionBase || 0) * (tm.foodConsumptionMult || 0),
            torpor_base: fsr0[2][0],
            torpor_inc: fsr0[2][1],
            food_base: fsr0[4][0],
            torpor_rate: tm.torporDepletionPS0
          },
          diet: []
        };
        d.TAME = TAME;
      }
    }
    // ③ 生成指令（蓝图路径项目有 → 配合共享表 SPAWN_TPL 生成全部命令）
    if (_sp0 && !SPAWN[CUR] && _sp0.blueprintPath) {
      var _bpPath = String(_sp0.blueprintPath);
      // v72n：蓝图短名优先用当前物种类名（blueprintPath 可能是变体/任务版，如 Ankylo_Character_BP_STA）
      var _cls0 = String(LB.curClass || '');
      var _bpShort = (_cls0 && /_Character_BP(_C)?$/.test(_cls0))
        ? _cls0.replace(/_C$/, '') + '_C'
        : _bpPath.split('.')[0].split('/').pop() + '_C';
      var _bpStd = _bpPath;
      if (_cls0) {
        _bpStd = _bpPath;
      }
      SPAWN[CUR] = {
        title: (DATA[CUR] || {}).zh || '',
        intro: [],
        main: 'admincheat GMSummon "' + _bpShort + '" 150',
        bp: _bpShort,
        bpPath: _bpPath,
        saddles: []
      };
      d.SPAWN = SPAWN;
    }
    // v73c：后端直出富数据适配层（skills/damage/caps/saddles/xpKill/tamingFoods）
    // v5850：同 F1 —— 后端扁平 HOME（{tameIntro:[...]}）也要能读
    var _hm = (d.HOME && (d.HOME[CUR] || ((d.HOME.tameIntro || d.HOME.abilIntro || d.HOME.harvestIntro || d.HOME.expIntro || d.HOME.spawnIntro) ? d.HOME : null))) || null;
    if (_hm) {
      // ① 经验：击杀经验用 xpKill（旧版误取鞍的 xp）；鞍列表用 saddles
      if (_hm.xpKill) {
        var _sadU = (_hm.saddles || []).map(function(sa){ return { zh: sa.zh || '', base: sa.xp || 0, lv: '' }; });
        if (!(EXP[CUR] && EXP[CUR].base && EXP[CUR].baseIsKill)) {
          EXP[CUR] = { base: _hm.xpKill, saddle: _sadU, baseIsKill: 1 };
          d.EXP = EXP;
        } else if (_sadU.length && !((EXP[CUR].saddle || []).length)) {
          EXP[CUR].saddle = _sadU; d.EXP = EXP;
        }
      }
      // ② 食性（v125：中文由后端 dietZh 给出，前端不再硬编码映射）
      if (_hm.diet || _hm.dietZh) {
        TAME[CUR] = TAME[CUR] || {};
        TAME[CUR].dietZh = _hm.dietZh || _hm.diet || '';
      }
      if ((_hm.tamingFoods || []).length) {
        var _fz = _hm.tamingFoods, _fk = [];
        var _foodTbl = (typeof FOODS !== 'undefined' && FOODS) ? FOODS : {};
        // v125：原 TC_FOOD_ALIAS 已删除 —— FOODS 表自带 zh，直接按 zh 反查（查不到就不设，wikiFoods 兜底）
        _fz.forEach(function(zh){
          var hit = '';
          Object.keys(_foodTbl).forEach(function(k){
            if (!hit && _foodTbl[k] && _foodTbl[k].zh === zh) hit = k;
          });
          if (!hit) { Object.keys(_foodTbl).forEach(function(k){ if (!hit && k === zh) hit = k; }); }
          if (hit) _fk.push(hit);
        });
        TAME[CUR] = TAME[CUR] || {};
        if (_fk.length) TAME[CUR].diet = _fk;
        TAME[CUR].dietZhList = _fz;
      }
      // v114：wiki 原始食物表（口数/时间/等级）→ TAME.wikiFoods，供 tcCalc 直接渲染
      if ((_hm.tameFoods || []).length) {
        TAME[CUR] = TAME[CUR] || {};
        TAME[CUR].wikiFoods = _hm.tameFoods;
        /* v5732（用户口径「不用完整食物列表，前3即可」）：后端 tamingFoods 只给「最佳」1 项，
           而 tameFoods（口数表）有约 3 项 ⇒ 把后者命中的 FOODS 键也并入 diet（去重、wiki 最佳优先），
           食物对照表即从 1 行变 3 行。 */
        try{
          var _ft0 = (typeof FOODS !== 'undefined' && FOODS) ? FOODS : {};
          var _d0 = (TAME[CUR].diet || []).slice();
          (_hm.tameFoods || []).forEach(function(x){
            var zh = String((x && x.zh) || '').trim();
            if (!zh) return;
            var hit = '';
            Object.keys(_ft0).forEach(function(k){ if (!hit && _ft0[k] && _ft0[k].zh === zh) hit = k; });
            if (hit && _d0.indexOf(hit) < 0) _d0.push(hit);
          });
          if (_d0.length) TAME[CUR].diet = _d0;
        }catch(eM){}
      }
      // v264：驯服引导文案 -> 用于区分「无法驯服」与「未收录」
      if ((_hm.tameIntro || []).length) {
        TAME[CUR] = TAME[CUR] || {};
        TAME[CUR].tameIntro = _hm.tameIntro;
      }
      if (TAME[CUR]) d.TAME = TAME;
      // ③ 技能：abilities + damage -> skills(键位/基础伤害/材质) + videos
      if ((_hm.skills || []).length) {
        var _dg = _hm.damage || {};
        var _skTbl = [], _vids = [], _matN = [];
        _hm.skills.forEach(function(x, i2){
          var dv = (_dg[String(x.id)] || [])[0] || {};
          var mats = (dv.tiers || []).filter(function(t){ return t && t.value; }).map(function(t){
            if (_matN.indexOf(t.label) < 0) _matN.push(t.label);
            return { zh: t.label, v: t.value };
          });
          _skTbl.push({ zh: x.zh, key: x.key || '', dmg: dv.base || '', mult: '', mats: mats });
          if (x.video) {
            _vids.push({ id: i2 + 1, zh: x.zh, title: x.zh, video: x.video,
                         poster: x.poster || '', desc: x.desc || '', key: x.key || '', kind: x.kind || '' });
          }
        });
        ABIL[CUR] = { skills: _skTbl, videos: _vids,
                      mats: _matN.map(function(n){ return { zh: n }; }),
                      resist: [], notes: [], hitRaw: '' };
        d.ABIL = ABIL;
      }
      // ④ 采集加成（首页采集能力段：树脂 10x / 木材 10x …）
      if ((_hm.caps || []).length) {
        GATHER[CUR] = {
          about: '', caps: _hm.caps.map(function(c){ return { zh: c.zh, ic: '', mult: c.mult }; }),
          nodes: [], nodeRes: [], params: null, noNode: true
        };
        d.GATHER = GATHER;
      }
      // ⑤ 收割：保留后端表格直出
      if (d.HARVEST && d.HARVEST[CUR] && (d.HARVEST[CUR].tables || []).length && !(HARVEST[CUR] && HARVEST[CUR].rawTables)) {
        HARVEST[CUR] = { corpse: {}, perRes: [], tools: {}, drops: [], bound: [], noRecord: true,
                         rawTables: d.HARVEST[CUR].tables, rawTitles: d.HARVEST[CUR].titles || [] };
        d.HARVEST = HARVEST;
      }
    }
    // ② 繁殖参数
    if (_sp0 && !BREED[CUR]) {
      var br = _sp0.breeding || null;
      if (br && (br.incubationTime != null || br.gestationTime != null)) {
        BREED[CUR] = {
          inc: br.incubationTime || br.gestationTime || 0,
          mat: br.maturationTime || 0,
          tMin: br.eggTempMin || 0,
          tMax: br.eggTempMax || 0,
          food: 0
        };
        d.BREED = BREED;
      }
    }
  } catch (eTB) {}
}

/* ===== P2：概览 + 驯服 渲染（源码取自 _preview_wiki.html，已加 lbWikiBody 容器改动）===== */
/* ===== EXP_LV ===== */
var EXP_LV = 150, EXP_KILLS = 1;   // v20：目标类型 / 额外加成 / 鞍品质 定义见经验 tab 区块

/* ===== TAME_KIND_W ===== */
var TAME_KIND_W = '武器';

/* ===== TAME_KIND_A ===== */
var TAME_KIND_A = '弹药';

/* ===== TC_LV ===== */
var TC_LV = 150;      // 目标等级

/* ===== TC_SP 来源（v128）=====
   v125 前：var TC_SP = 6（硬编码）
   v128：一律实读孤岛服 GameUserSettings.ini 的 TamingSpeedMultiplier
         数据源 = /api/cfg_rules（与「服务器规则」面板同源，不再硬编码） */
var TC_SP = 0;              // 0 = 尚未取到
var TC_SP_SRC = '';         // 展示来源
var LB_TAME_SP_TRIED = false;
function lbCfgPickVal(doc, key){
  var it = (doc && doc.items) || [], k = String(key || '').toLowerCase();
  for (var i = 0; i < it.length; i++){
    if (String(it[i].key || '').toLowerCase() === k){
      var v = parseFloat(it[i].value);
      if (!isNaN(v) && v > 0) return v;
    }
  }
  return null;
}
function lbTameSpeedSync(){
  if (TC_SP > 0) return TC_SP;
  var c = null;
  try { c = (typeof lbCfgCacheGet === 'function') ? lbCfgCacheGet('Isl', 'GUS') : null; } catch(e) {}
  var v = lbCfgPickVal(c && c.doc, 'TamingSpeedMultiplier');
  if (v !== null){ TC_SP = v; TC_SP_SRC = '孤岛 GUS 实读'; }
  return TC_SP;
}
function lbTameSpeedEnsure(cb){
  if (TC_SP > 0){ if (cb) { try { cb(TC_SP); } catch(e) {} } return TC_SP; }
  lbTameSpeedSync();
  if (TC_SP > 0){ if (cb) { try { cb(TC_SP); } catch(e) {} } return TC_SP; }
  if (!LB_TAME_SP_TRIED && typeof lbCfgFetchOne === 'function'){
    LB_TAME_SP_TRIED = true;
    try {
      lbCfgFetchOne('Isl', 'GUS').then(function(full){
        if (!full || !full.items) return;
        try { lbCfgCachePut('Isl', 'GUS', full); } catch(e){}
        var v = lbCfgPickVal(full, 'TamingSpeedMultiplier');
        if (v !== null){ TC_SP = v; TC_SP_SRC = '孤岛 GUS 实读'; if (cb) { try { cb(TC_SP); } catch(e) {} } }
      }).catch(function(){});
    } catch(e){}
  }
  return TC_SP;
}

/* ===== v5811（根因修复）：经验倍率 EXP_XP = 孤岛 GUS 的 XPMultiplier =====
   原「经验」tab 直接用了 TC_SP，而 TC_SP = TamingSpeedMultiplier（**驯服速度**倍率），
   ⇒ 页面标注的「服务器 N×」「XPMultiplier = N」全是错的；且 TC_SP 初值 0、未取到时
   per 恒 0 ⇒ 单次经验 0、升到 100 级需 Infinity。这里独立一套读取（同 lbBreedMultEnsure 范式）。 */
var EXP_XP = 0;              // 0 = 尚未取到
var EXP_XP_SRC = '';
var LB_XP_CFG_TRIED = false;
function lbXpMulPick(doc){ return lbCfgPickVal(doc, 'XPMultiplier'); }
function lbXpMulSync(){
  if (EXP_XP > 0) return EXP_XP;
  var c = null;
  try { c = (typeof lbCfgCacheGet === 'function') ? lbCfgCacheGet('Isl', 'GUS') : null; } catch(e) {}
  var v = lbXpMulPick(c && c.doc);
  if (v !== null){ EXP_XP = v; EXP_XP_SRC = '孤岛 GUS 实读'; }
  return EXP_XP;
}
function lbXpMulEnsure(cb){
  if (EXP_XP > 0){ if (cb) { try { cb(EXP_XP); } catch(e) {} } return EXP_XP; }
  lbXpMulSync();
  if (EXP_XP > 0){ if (cb) { try { cb(EXP_XP); } catch(e) {} } return EXP_XP; }
  if (!LB_XP_CFG_TRIED && typeof lbCfgFetchOne === 'function'){
    LB_XP_CFG_TRIED = true;
    try {
      lbCfgFetchOne('Isl', 'GUS').then(function(full){
        if (!full || !full.items) return;
        try { lbCfgCachePut('Isl', 'GUS', full); } catch(e){}
        var v = lbXpMulPick(full);
        if (v !== null){ EXP_XP = v; EXP_XP_SRC = '孤岛 GUS 实读'; if (cb) { try { cb(EXP_XP); } catch(e) {} } }
      }).catch(function(){});
    } catch(e){}
  }
  return EXP_XP;
}

/* ===== v125：原 TC_OWN 假库存表已删除 → 一律走项目 lbItemOwnCnt() ===== */
function lbTameOwn(key){
  // key 可能是 FOODS 英文键（Raw Meat 等），也可能是中文
  try{
    if (typeof lbItemOwnCnt !== 'function') return 0;
    var cls = (typeof lbItemClsByZh === 'function') ? lbItemClsByZh(key) : '';
    if (!cls) cls = key;
    return Number(lbItemOwnCnt(cls)) || 0;
  }catch(e){ return 0; }
}
function lbDinoOwnCnt(){ return -1; }   // 项目无「我的某物种数量」接口 → -1 表示未知

/* ===== CUR_ROLE ===== */
var CUR_ROLE = 0;

/* ===== v125：原 TC_BP_COL 已删除 → 一律走项目 lbBpStageCol() ===== */

/* ===== TC_TIPS ===== */
var TC_TIPS = {};   // 由 lbWikiBind() 绑定

/* ===== v160：原 TC_MDI（手写 3 条 SVG path）已删 → 一律走项目 LB_MDI_SVG（L15706） ===== */

/* ===== TC_CN ===== */
/* v5936（资讯折叠后最多 20 条需要编号）：原数组只有 ①~⑦ 且 **0-based**（TC_CN[0] = ①），
   资讯侧曾按 1-based 传参 ⇒ 整体错位一位（实测首条显示 ②）。这里扩展到 ①~⑳；
   wiki 侧既有调用不受影响（仅多出可用序号）。 */
var TC_CN = ['\u2460','\u2461','\u2462','\u2463','\u2464','\u2465','\u2466','\u2467','\u2468','\u2469',
              '\u246a','\u246b','\u246c','\u246d','\u246e','\u246f','\u2470','\u2471','\u2472','\u2473'];

/* ===== v125：原 TC_ICON 已删除 → 一律走 lbItemClsByZh() ===== */

/* ===== v130：TC_NARC / TC_DART ===== */
/* v125 前：40 / 240（源码自标「待核」，属自造数字）
   v130：项目无此数据源 → 置 0（=未收录），计算与展示均自动隐藏，绝不用假数字凑数 */
var TC_NARC = 0;
var TC_DART = 0;

/* ===== v76：图标统一走项目链（lbResURL 分包 / lbItemIconUrl 物品类名）===== */
// 把任意图片 URL 转成分包 blob（项目 lbResURL），失败回落原 URL
function lbWikiIc(u){
  if(!u) return '';
  try{ if(typeof lbResURL === 'function') return lbResURL(u) || u; }catch(e){}
  return u;
}
// 物品类名 -> 图标（项目 lbItemIconUrl：item_zh.icon -> LB_ITEM_ICON_URL -> lbPackURL 分包）
// 兼容：传进来已是 http/blob 时按 URL 处理
function lbWikiIcCls(cls){
  // v147：删除 fallbackUrl —— 项目链失败即返回空，绝不回落到任何外部 URL
  var v = String(cls || '');
  if(v.indexOf('http') === 0 || v.indexOf('blob:') === 0) return lbWikiIc(v);
  var u = '';
  try{ if(v && typeof lbItemIconUrl === 'function') u = lbItemIconUrl(v) || ''; }catch(e){ u = ''; }
  return u;
}

/* ===== v125：原 TC_RES_CLS（16 条硬编码）已删除 → 一律走 lbItemClsByZh()（项目 item_zh.json 3077 条）===== */

/* v121：wiki 译名 -> 项目译名（仅处理两边译名不同的；能直连的一律走项目表，不列在此） */
/* v125：wiki 译名 -> 项目译名。
   只保留**实测两边译名不同**的（其余一律 lbItemClsByZh 直连，禁止在此新增）。
   依据：tmp/_v120.py 用项目 item_zh.json 反查确认。 */
var LB_WIKI_ZH_ALIAS = { '几丁质': '甲壳素' };

/* v121：中文 -> 项目物品类名（**全量走项目 LB_ITEM_ZH**，不硬编码）
   命中优先级：① 中文直接就是类名 ② 项目表 zh 精确等值 ③ 别名翻译后再查 */
function lbItemClsByZh(zh){
  zh = String(zh || '').trim();
  if (!zh) return '';
  var T = (typeof LB_ITEM_ZH !== 'undefined') ? LB_ITEM_ZH : null;
  if (T && T[zh]) return zh;                                  // ① 类名即中文键
  if (!T || !Object.keys(T).length) {
    try { if (typeof lbItemZhLoad === 'function') lbItemZhLoad(); } catch (e) {}
    return '';
  }
  var sig = 'z' + Object.keys(T).length;
  if (!LB._zh2cls || LB._zh2clsSig !== sig) {
    var m = {};
    Object.keys(T).forEach(function(k){
      var t = T[k] || {};
      var z = String(t.zh || '').trim();
      if (!z) return;
      var cur = m[z];
      // 同一个中文有多个类名时，优先取「有图标」且「键更短」的
      if (!cur) { m[z] = k; return; }
      var ci = (T[cur] || {}).icon, ti = t.icon;
      if ((!ci && ti) || (!!ci === !!ti && k.length < cur.length)) m[z] = k;
    });
    LB._zh2cls = m; LB._zh2clsSig = sig;
  }
  if (LB._zh2cls[zh]) return LB._zh2cls[zh];                  // ② 项目表精确命中
  var al = LB_WIKI_ZH_ALIAS[zh];                              // ③ 别名
  if (al && LB._zh2cls[al]) return LB._zh2cls[al];
  return '';
}

/* v293：wikily slug -> 项目物品类名（**全量走项目 LB_ITEM_ZH.en**，不硬编码、不靠中文译名）
   原因：wikily 中文译名与项目不一致（wikily「电子元件」= 项目「电路元件」），
         靠中文名反查会断；slug 是机器标识（electronics / cementing-paste），两边永远一致。
   命中：slug 规范化后与 LB_ITEM_ZH[cls].en 规范化后等值（metal-ingot -> Metal Ingot）。 */
function lbItemClsBySlug(slug){
  var s = String(slug || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  if (!s) return '';
  var T = (typeof LB_ITEM_ZH !== 'undefined') ? LB_ITEM_ZH : null;
  if (!T || !Object.keys(T).length) {
    try { if (typeof lbItemZhLoad === 'function') lbItemZhLoad(); } catch (e) {}
    return '';
  }
  var sig = 's' + Object.keys(T).length;
  if (!LB._en2cls || LB._en2clsSig !== sig) {
    var m = {};
    Object.keys(T).forEach(function (k) {
      var t = T[k] || {};
      var en = String(t.en || '').toLowerCase().replace(/[^a-z0-9]/g, '');
      if (!en) return;
      var cur = m[en];
      if (!cur) { m[en] = k; return; }
      // 同一英文名多类名时：优先「有图标」且「键更短」
      var ci = (T[cur] || {}).icon, ti = t.icon;
      if ((!ci && ti) || (!!ci === !!ti && k.length < cur.length)) m[en] = k;
    });
    LB._en2cls = m; LB._en2clsSig = sig;
  }
  return LB._en2cls[s] || '';
}

/* v160：原 lbWikiResIc 已删（死代码，调用 0 次）——图标唯一入口为 lbWikiResIcon() */

/* v5793（用户口径「附件没有复用项目对应逻辑吧」）：wiki 名字/图标解析补 LB_ZH_ALIAS 通道 ——
   别名表（木材→木头 / 丝绸→蚕丝 / 丝→蚕丝 …）原本只喂 AI 翻译链路，
   渲染侧 lbWikiZhName / lbWikiResIcon 完全没查，导致「丝」「木材」既无正名也无图标 */
function lbWikiAliasOf(s){
  var x = String(s === null || s === undefined ? '' : s).trim();
  if (!x) return '';
  try {
    var A = (typeof LB_ZH_ALIAS !== 'undefined') ? LB_ZH_ALIAS : null;
    if (A && A[x]) return String(A[x]);
  } catch (e) {}
  return '';
}

/* ===== v145：图标唯一入口（项目链）=====
   路径：中文/英文名 -> lbItemClsByZh / lbItemClsByEn -> 类名
        -> lbItemIconRel(cls)（= item_zh.icon -> LB_ITEM_ICON_URL -> 原始相对路径）
        -> 渲染时经 lbWikiIc() 分包
   绝不使用任何外链 CDN、绝不返回空串而让上层显示占位符 */
function lbWikiResIcon(name){
  var s = String(name === null || name === undefined ? '' : name).trim();
  if (!s) return '';
  var cls = '';
  try { cls = lbItemClsByZh(s); } catch(e) {}
  if (!cls) { try { cls = lbItemClsByEn(s); } catch(e) {} }
  if (!cls){                                  // v5793：别名兜底（通行叫法 → 表内正名）
    var _a = lbWikiAliasOf(s);
    if (_a){
      try { cls = lbItemClsByZh(_a); } catch(e2) {}
      if (!cls) { try { cls = lbItemClsByEn(_a); } catch(e3) {} }
    }
  }
  if (!cls) return '';
  var rel = '';
  try { if (typeof lbItemIconRel === 'function') rel = lbItemIconRel(cls) || ''; } catch(e) {}
  if (!rel) { try { if (typeof lbItemIcon === 'function') rel = lbItemIcon(cls) || ''; } catch(e) {} }
  return rel ? lbWikiIc(rel) : '';
}

/* ===== v130：wiki 资源名 -> 项目中文名（唯一入口）=====
   ① 中文 -> lbItemClsByZh（项目 item_zh.json 3077 条 zh 反查）
   ② 英文名 / 类名 -> LB._en2cls（用 item_zh.json 的 en / enev 字段建索引，非硬编码）
   ③ 类名 -> lbItemZh(cls) 取项目中文名
   查不到原样返回（绝不编） */
function lbItemClsByEn(en){
  en = String(en || '').trim();
  if (!en) return '';
  var T = (typeof LB_ITEM_ZH !== 'undefined') ? LB_ITEM_ZH : null;
  if (!T || !Object.keys(T).length) {
    try { if (typeof lbItemZhLoad === 'function') lbItemZhLoad(); } catch (e) {}
    return '';
  }
  if (T[en]) return en;                                  // 已是类名
  var sig = 'e' + Object.keys(T).length;
  if (!LB._en2cls || LB._en2clsSig !== sig) {
    var m = {};
    Object.keys(T).forEach(function(k){
      var t = T[k] || {};
      var cands = [t.en, t.enev];
      for (var ci2 = 0; ci2 < cands.length; ci2++){
        var e = String(cands[ci2] || '').trim().toLowerCase();
        if (!e) continue;
        var cur = m[e];
        if (!cur) { m[e] = k; continue; }
        var ic1 = (T[cur] || {}).icon, ic2 = t.icon;
        if ((!ic1 && ic2) || (!!ic1 === !!ic2 && k.length < cur.length)) m[e] = k;
      }
    });
    LB._en2cls = m; LB._en2clsSig = sig;
  }
  return LB._en2cls[en.toLowerCase()] || '';
}
function lbWikiZhName(s){
  var raw = String(s === null || s === undefined ? '' : s).trim();
  if (!raw) return '';
  var T = (typeof LB_ITEM_ZH !== 'undefined') ? LB_ITEM_ZH : null;
  var a = lbWikiAliasOf(raw);            // v5793：别名通道
  var look = raw, cls = '';
  try { cls = lbItemClsByZh(raw); } catch(e) {}
  if (!cls) { try { cls = lbItemClsByEn(raw); } catch(e) {} }
  if (!cls && a){
    look = a;
    try { cls = lbItemClsByZh(a); } catch(e2) {}
    if (!cls) { try { cls = lbItemClsByEn(a); } catch(e3) {} }
  }
  if (cls && typeof lbItemZh === 'function'){
    var z = '';
    try { z = lbItemZh(cls) || ''; } catch(e) {}
    if (z) return z;
  }
  if (T && T[look] && T[look].zh) return String(T[look].zh);   // look 本身就是类名
  return a || raw;                                             // 别名有值但查不到类名 ⇒ 至少显示正名
}

/* ===== v125：原 TC_GH_ICON 已删除 → 一律走 lbItemClsByZh() ===== */

/* ===== v160：原 SVG_GEAR / SVG_BOX / SVG_POS 已删 =====
   实测与项目 LB_MDI_SVG 完全重复：
     SVG_GEAR = mdi-cog（path 一致）、SVG_BOX = mdi-tent（path 逐字相同）、SVG_POS = mdi-map-marker-multiple（path 一致）
   用处直接改为 lbMdiSvg() */

/* ===== TC_SHOT_NOTE ===== */
var TC_SHOT_NOTE = '射速按 5s/发（含瞄准与装填的实战节奏）';

/* ===== tcIco ===== */
function tcIco(name){
  // v160：改走项目图标表 LB_MDI_SVG（与全站 SVG 图标同源），不再自带一份
  var key = 'mdi-' + String(name || '').toLowerCase();
  var d = (typeof LB_MDI_SVG !== 'undefined' && LB_MDI_SVG[key]) ? LB_MDI_SVG[key] : '';
  if (!d) d = (typeof LB_MDI_SVG !== 'undefined' && LB_MDI_SVG['mdi-check']) || '';
  return '<svg class="tc-ic" viewBox="0 0 24 24" aria-hidden="true"><path d="' + d + '"/></svg>';
}

/* ===== tcNum ===== */
function tcNum(n){ return String(Math.round(n || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }

/* ===== tcDur ===== */
function tcDur(s){
  s = Math.max(0, Math.round(s || 0));
  var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60;
  return (h ? h + 'h ' : '') + ((h || m) ? m + 'm ' : '') + x + 's';
}

/* ===== tcPct ===== */
function tcPct(n){ return (Math.round(n * 100) / 100).toFixed(2); }

/* ===== tcTile ===== */
function tcTile(k, v, s, hot){
  return '<div class="tc-tile' + (hot ? ' hot' : '') + '"><div class="tc-tile-k">' + k + '</div>'
    + '<div class="tc-tile-v">' + v + '</div>' + (s ? '<div class="tc-tile-s">' + s + '</div>' : '') + '</div>';
}

/* ===== tcHStr ===== */
function tcHStr(n, t, em){
  var c = TC_CN[n] || '';
  return '<div class="tc-h">' + c + ' ' + t + (em ? '<em>' + em + '</em>' : '') + '</div>';
}

/* ===== tcIconHtml ===== */
function tcIconHtml(en, icon){
  // v145：图标一律走项目链（en 可为中文或英文名）；不再使用 FOODS[en].icon（CDN 外链）
  var u = lbWikiResIcon(en);
  if (!u) u = lbWikiResIcon(icon);
  if (!u && icon && /^(https?:|blob:|thumbs\/|icons\/)/.test(String(icon))) u = lbWikiIc(icon);
  return u ? '<img src="' + u + '" referrerpolicy="no-referrer" alt="" onerror="lbImgRetry(this)">'
           : '<span class="tc-ph">?</span>';
}

/* ===== tcEsc ===== */
function tcEsc(t){
  return String(t == null ? '' : t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/* ===== tcCopy ===== */
function tcCopy(btn){
  var el = document.getElementById(btn.getAttribute('data-src'));
  var txt = el ? el.textContent : '';
  var done = function(ok){
    btn.textContent = ok ? '已复制' : '复制失败';
    setTimeout(function(){ btn.textContent = '复制'; }, 1400);
  };
  try{ if(navigator.clipboard && navigator.clipboard.writeText){ navigator.clipboard.writeText(txt).then(function(){ done(true); }, function(){ done(false); }); return; } }catch(e1){}
  try{
    var ta = document.createElement('textarea'); ta.value = txt; ta.style.cssText = 'position:fixed;left:-9999px';
    document.body.appendChild(ta); ta.select();
    var ok = document.execCommand('copy'); ta.remove(); done(ok);
  }catch(e2){ done(false); }
}

/* ===== OV_PCT_FROM ===== */
var OV_PCT_FROM = 6;   // 第 7、8 行（近战伤害 / 移动速度）以百分比呈现

/* ===== ovNum ===== */
function ovNum(v){
  if(v === null || v === undefined) return '-';
  var n = Math.round(v * 100) / 100;
  return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

/* ===== ovPct ===== */
function ovPct(v){
  if(v === null || v === undefined) return '-';
  return (Math.round(v * 10000) / 100) + '%';
}

/* ===== ovEsc ===== */
function ovEsc(t){
  return String(t || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

/* ===== ovPara ===== */
function ovPara(t){
  t = String(t || '').trim();
  if(!t) return '';
  if(t.length > 40){
    var parts = t.split('。').map(function(x){ return x.trim(); }).filter(function(x){ return x.length > 0; });
    if(parts.length >= 2){
      return '<p class="ov-p">' + parts.map(function(x){ return ovEsc(x) + '。'; }).join('<br>') + '</p>';
    }
  }
  return '<p class="ov-p">' + ovEsc(t) + '</p>';
}

/* ===== renderOverview ===== */
function renderOverview(){
  var OV = OVERVIEW || {};
  var ov = OV[CUR];
  var body = document.getElementById('lbWikiBody');
  if(!ov){
    /* v5843（用户口径「附件 明明概览里永远有AI模块，怎么没显示概览」「「暂无概览数据」无需显示这段」）：
       无本地概览数据时不再整块 return，也不显示任何占位提示，只渲染底部 AI 模块外壳。 */
    var _h0 = '';
    try { lbTipsEnsure(); } catch (eTE0) {}
    try { _h0 = lbTipsAiWrapHtml(); } catch (eAI0) { _h0 = ''; }
    body.innerHTML = _h0;
    body.scrollTop = 0;
    return;
  }
  var TAMED = OV._tamedPct || [];
  var NA = (OV._tamedNA || {})[CUR] || [];
  var h = '';

  // ① 概述
  // v5745：优先用「AI 整理后重新分配」的版本，没有则回落 wikily 原文
  var intro = lbWtPick('ovIntro', ov.intro);
  // v5766（用户实测「附件几个经过AI整理的均没有预期样式」）：本块走独立渲染路径，不经过 wikiIntroHtml
  //   ⇒ 必须在这里自己消费 LB_WT_LAST_AI 并给容器打 .tc-ai，名词英文小字才会生效
  var _ovAI = LB_WT_LAST_AI; LB_WT_LAST_AI = 0;
  // v5834（用户口径「概览里不要强行填充，而是直接空置」）：无概述时整块不渲染
  if (intro.length){
    /* v6106（用户口径「既然最终不显示，为啥要渲染后再隐藏」）：
       「概述」小标题的判据**静态可知** —— 下一个兄弟恒为 .tc-intro
       ⇒ CSS `#lbWikiOverlay .tc-h:has(+ .tc-intro){display:none!important}` 永远隐藏它。
       原实现先渲染可见、再靠 60ms 后的 lbWikiLayoutFix() 擦除，而加载轮询每 2 秒重演一次
       ⇒ 标题“不断显影闪现”。改为**不生成该节点**（视觉零变化）。 */
    h += '<div class="tc-sec">';
    // v264：介绍文案改用色条块（与物品面板同一套 .lw-quote 样式）
    /* v5868：概述块与各 TAB 置顶文案块同一实现（.tc-intro）⇒ 自动获得 >5 行折叠 */
    h += '<div class="tc-intro' + (_ovAI ? ' tc-ai' : '') + '">';
    intro.forEach(function(t){ h += ovPara(t); });
    h += '</div></div>';
  }

  // ② 基础属性
  /* v5863（用户口径「附件这种 在没数据时 不是不应该显示么」）：
     wiki.gg stub 页面物种（如战车 BattleRig）拿不到 stats ⇒ 原来表头 + 底部说明照出，
     只剩一个空表。现在无 stats 时整块不渲染。 */
  if ((ov.stats || []).length){
  /* v6106：同上 —— 「基础属性」无 ① 编号且下一个兄弟是 <table>（非 .tc-intro）
     ⇒ lbWikiLayoutFix 恒判隐藏。判据静态可知 ⇒ 直接不生成，不再「先渲染后擦除」。 */
  h += '<div class="tc-sec">'
     + '<table class="tc-tb"><thead><tr><th>属性</th>'
     + '<th style="text-align:right">基础</th>'
     + '<th style="text-align:right">野生 +/级</th>'
     + '<th style="text-align:right">已驯服 +/级</th>'
     + '<th style="text-align:right">野生成长</th></tr></thead><tbody>';
  (ov.stats || []).forEach(function(r, k){
    var zh = r[0], base = r[1], pw = r[2];
    var pct = (k >= OV_PCT_FROM);
    var cBase = (base === null || base === undefined) ? '-' : (pct ? ovPct(base) : ovNum(base));
    var cWild = (base === null || base === undefined || pw === null || pw === undefined) ? '-'
              : (pct ? ('+' + ovPct(pw)) : ('+' + ovNum(base * pw)));
    var cTamed = (k < TAMED.length)
               ? (NA.indexOf(k) >= 0 ? '-' : ('+' + TAMED[k] + '%'))
               : '-';
    var cGrow = ovPct(pw);
    h += '<tr><td class="ov-k">' + ovEsc(zh) + '</td>'
       + '<td class="num">' + cBase + '</td>'
       + '<td class="num">' + cWild + '</td>'
       + '<td class="num">' + cTamed + '</td>'
       + '<td class="num">' + cGrow + '</td></tr>';
  });
  h += '</tbody></table>'
     + '<div class="tc-note">「已驯服 +/级」为游戏内按属性类型的<strong>全局常量</strong>（生命 5.4% · 体力/氧气/食物 10% · 重量 4% · 近战 1.7% · 移速 1%），与物种无关。</div>'
     + '</div>';
  }

  // ③ 技巧
  // v5746（用户口径）：原文整理跑过后，概览的技巧板块**整个隐藏**（内容已并入技巧页，不再回填）
  var tips = LB_WT.ready ? [] : (ov.tips || []);
  if(tips.length){
    /* v6106：同上 —— 「技巧」无 ① 编号且下一个兄弟是 <p>/<ul>（非 .tc-intro）
       ⇒ lbWikiLayoutFix 恒判隐藏。判据静态可知 ⇒ 直接不生成。 */
    h += '<div class="tc-sec">';
    if(tips.length === 1){
      h += ovPara(tips[0]);
    }else{
      h += '<ul class="ov-tips">';
      tips.forEach(function(t){ h += '<li>' + ovEsc(t) + '</li>'; });
      h += '</ul>';
    }
    h += '</div>';
  }

  /* v5834（用户口径「物种 wiki 技巧里的 AI 模块全部移到概览最下面」）：
     原 v5746 曾把概览的 AI 框删掉，现在按新口径**统一挪回概览底部**；
     整理结果本身仍留在「技巧」TAB。 */
  try { lbTipsEnsure(); } catch (eTE) {}
  h += lbTipsAiWrapHtml();
  body.innerHTML = h;
  body.scrollTop = 0;
}

/* ===== tcSentences ===== */
function tcSentences(html){
  var d = document.createElement('div');
  d.innerHTML = html;
  Array.prototype.forEach.call(d.querySelectorAll('p'), function(p){
    if(p.querySelector('*')) return;
    var t = (p.textContent || '').trim();
    if(t.length <= 40) return;
    var parts = t.split('。').map(function(s){ return s.trim(); }).filter(function(s){ return s.length > 0; });
    if(parts.length < 2) return;
    p.innerHTML = parts.map(function(s){ return s + '。'; }).join('<br>');
  });
  return d.innerHTML;
}

/* ===== tcCollapseIntro ===== */
function tcCollapseIntro(el, maxLines){
  if(!el) return;
  maxLines = maxLines || 5;
  var lines = [];
  Array.prototype.forEach.call(el.querySelectorAll('p'), function(p){
    String(p.innerHTML || '').split(/<br\s*\/?>/i).forEach(function(s){
      var t = s.trim();
      if(t) lines.push(t);
    });
  });
  if(!lines.length) return;
  var mk = function(s){ return '<div class="tc-line">' + s + '</div>'; };
  /* v5735（用户口径「不能超过 5 行，超过就折叠」）：
     原判据 = **段落数**（p / br 拆出的条数）。tameIntro 现为 5 段×每段 2~3 视觉行 ⇒ 5<=5 被判「不需折叠」，
     整块 8~9 行全铺开。改为**视觉行数估算**：容器约 886px、字号 12.5px ⇒ 每行约 62 个中文字，
     逐段 ceil(len/62) 累加，超过 maxLines 就折叠（前 N 行按视觉行累计取整段）。 */
  var CPL = 62;
  var plain = function(s){ return String(s).replace(/<[^>]*>/g, ''); };
  var vlines = 0;
  for (var li = 0; li < lines.length; li++){
    vlines += Math.max(1, Math.ceil(plain(lines[li]).length / CPL));
  }
  if (vlines <= maxLines){
    el.innerHTML = lines.map(mk).join('');
    return;
  }
  // 按视觉行累计取前 maxLines 行（整段为单位，避免把一句话劈两半）
  var headArr = [], restArr = [], acc = 0, cut = false;
  for (var lj = 0; lj < lines.length; lj++){
    var n = Math.max(1, Math.ceil(plain(lines[lj]).length / CPL));
    if (!cut && acc + n <= maxLines){ headArr.push(mk(lines[lj])); acc += n; }
    else { cut = true; restArr.push(mk(lines[lj])); }
  }
  if (!headArr.length){ headArr.push(mk(lines[0])); restArr = lines.slice(1).map(mk); }
  var head = headArr.join('');
  var rest = restArr.join('');
  var moreTxt = '展开全部（共 ' + vlines + ' 行）';
  el.innerHTML = head
    + '<div class="tc-more" style="display:none">' + rest + '</div>'
    + '<button class="tc-expand" data-more="' + moreTxt + '">' + moreTxt + '</button>';
  var btn = el.querySelector('.tc-expand');
  if(btn) btn.onclick = function(){
    var box = el.querySelector('.tc-more');
    if(!box) return;
    var closed = (box.style.display === 'none');
    box.style.display = closed ? '' : 'none';
    btn.textContent = closed ? '收起' : btn.getAttribute('data-more');
  };
}

/* ===== tcMountIntro ===== */
function tcMountIntro(){
  /* v5868（用户口径「除技巧TAB以外的 AI 整理内容都对齐置顶文案块」）：
     原写法 querySelector 只折叠页面里**第一个** .tc-intro，
     现在概览概述 / 装备要点 / 指南要点 / 官方要点都是 .tc-intro ⇒ 必须全量处理。
     顺带补上物品面板 #lbWikiItemBody。 */
  var els = document.querySelectorAll('#lbWikiBody .tc-intro, #lbWikiItemBody .tc-intro');
  for (var i = 0; i < els.length; i++){ try { tcCollapseIntro(els[i], 5); } catch (e) {} }
}

/* ===== tpDurSec（v131）=====
   wiki 食物表的时长文本（如「1分43秒」「43秒」）-> 秒 */
function tpDurSec(s){
  s = String(s || '');
  var m = s.match(/(\d+)\s*分\s*(\d+)\s*秒/);
  if (m) return (+m[1]) * 60 + (+m[2]);
  var m2 = s.match(/(\d+)\s*秒/);
  if (m2) return +m2[1];
  var m3 = s.match(/(\d+)\s*小时/);
  if (m3) return (+m3[1]) * 3600;
  return 0;
}

/* ===== tcMaxWild（v5730 用户口径） ===== */
/* 野生等级上限：Tek 变种（BionicRex_Character_BP_C 等）上限 180，普通 150。
   判定源 = 物种键 + 当前类名；识别不出 Tek 时**安全降级**为 150（绝不误放宽）。 */
function tcMaxWild(){
  try{
    var s = String((typeof LB_WIKI !== 'undefined' && LB_WIKI.cur) || '')
          + ' ' + String((typeof LB !== 'undefined' && LB.curClass) || '')
          + ' ' + String((typeof CUR !== 'undefined' && CUR) || '');
    if (/Bionic|Tek/i.test(s)) return 180;
  }catch(e){}
  return 150;
}

/* ===== tcRows ===== */
function tcRows(spOverride){
  var t = TAME[CUR]; if(!t) return null;
  var s = t.setup || t.s || {};
  var lv = Math.max(5, Math.min(tcMaxWild(), TC_LV));
  var A = (+s.req || 0) + (+s.per_level || 0) * Math.max(0, lv - 1);   // 总亲和度需求
  // v5716：spOverride 供「④ 部落塔」对比块用（传入含塔加成的倍率）；不传则用服务器裸倍率（原行为不变）
  var sp = (Number(spOverride) > 0) ? Number(spOverride) : (lbTameSpeedEnsure() || 0);
  if (sp <= 0) return null;                   // 倍率未取到 → 不算（绝不用假数字）
  var rate = +s.rate || 0.4167, ineff = +s.ineff || 1;
  var list = (t.diet || []).map(function(en){
    var f = FOODS[en] || {};
    var aff = +f.aff || 0, base = +f.base || 0;
    var qty = aff > 0 ? Math.ceil(A / (aff * 4 * sp)) : 0;                    // 口数
    var itv = rate > 0 ? base / (rate * sp) : 0;                             // 喂食间隔（秒）
    var time = qty > 0 ? Math.floor(qty * itv + 1) : 0;                      // 总时间
    var eff = (aff > 0 && qty > 0) ? (1 / (1 + ineff * qty / (aff * 4))) * 100 : 0;  // 效率
    var plus = Math.floor(lv * eff / 100 * 0.5);                             // 等级加成
    var _ic = lbWikiResIcon(f.zh || en) || lbWikiResIcon(en);            // v145：项目链，不用 FOODS[en].icon（CDN）
    var _zh = lbWikiZhName(f.zh || en) || (f.zh || en);
    return { en:en, zh:_zh, icon:_ic, icons:null, aff:aff, base:base, qty:qty,
             itv:itv, time:time, eff:eff, plus:plus, tlv:lv + plus,
             own:lbTameOwn(_zh) };   // v5701 BUG 修复：原来传 FOODS 英文键，lbItemClsByZh 只认中文 ⇒ own 恒为 0
  });
  /* v131：FOODS 静态表只有 26 条（肉 / 饲料），
     wiki 食物（几丁质 / 蜂蜜 / 腐肉 等）不在其中 ⇒ 以前只能降级显示 wiki 原始表。
     现用后端新增的 wikiFoods[].aff（wiki「亲和度 N」）按目标等级 + 实服倍率重算。 */
  if (!list.length && (t.wikiFoods || []).length) {
    list = t.wikiFoods.filter(function(w){ return (+w.aff || 0) > 0; }).map(function(w){
      var _aff = +w.aff || 0, _q0 = +w.qty || 0, _d0 = tpDurSec(w.dur);
      var _qty = _aff > 0 ? Math.ceil(A / (_aff * 4 * sp)) : 0;
      var _base = (_q0 > 0 && _d0 > 0 && rate > 0) ? (_d0 / _q0) * rate : 0;   // wiki 1× 结果反推基础间隔
      var _itv = (_base > 0 && rate > 0) ? _base / (rate * sp) : 0;
      var _time = (_qty > 0 && _itv > 0) ? Math.floor(_qty * _itv + 1) : 0;
      var _eff = (_aff > 0 && _qty > 0) ? (1 / (1 + ineff * _qty / (_aff * 4))) * 100 : 0;
      var _plus = Math.floor(lv * _eff / 100 * 0.5);
      return { en: w.zh, zh: lbWikiZhName(w.zh) || w.zh, icon: lbWikiResIcon(w.zh), icons: null,
               aff: _aff, base: _base, qty: _qty, itv: _itv, time: _time,
               eff: _eff, plus: _plus, tlv: lv + _plus, own: lbTameOwn(w.zh), src: 'wiki-aff' };
    });
  }
  list.sort(function(a, b){ return (b.eff - a.eff) || (a.time - b.time); });
  var torpor = Math.ceil((+s.torpor_base || 0) * (1 + (+s.torpor_inc || 0) * Math.max(0, lv - 1)));
  var wakeRate = (+s.torpor_rate || 0) * 4.2;
  // 「最合适」= 库存够的里效率最高；都不够则取效率最高
  var enough = list.filter(function(r){ return r.own >= r.qty && r.qty > 0; });
  var best = enough.length ? enough[0] : list[0];
  // 麻醉药口径（v5 修正）：只需补「驯服时长超出眩晕值续航」的部分，**不是**从零把眩晕值填满。
  //   眩晕值（满晕 torpor）在击晕那刻就是满的；全程按 wakeRate 自然衰减。
  //   衰减总量 <= 满晕值 ⇒ 全程不会醒 ⇒ 需补 0 支（对齐 wikily 原文「在此设置下无需更多」）。
  var bestTime = (best && best.time) || 0;
  var wakeTotal = wakeRate * bestTime;                     // 全程自然衰减
  var awakeIn = wakeRate > 0 ? torpor / wakeRate : 0;      // 满晕值能撑多少秒
  // v130：TC_NARC / TC_DART 未收录（0）时不算，避免用 40/240 个假常量
  var narc = TC_NARC > 0 ? Math.ceil(Math.max(0, wakeTotal - torpor) / TC_NARC) : 0;
  var narcStun = TC_NARC > 0 ? Math.ceil(torpor / TC_NARC) : 0;
  var narcDart = TC_DART > 0 ? Math.ceil(torpor / TC_DART) : 0;
  return { lv:lv, A:A, torpor:torpor, wakeRate:wakeRate, awakeIn:awakeIn, wakeTotal:wakeTotal,
           list:list, best:best, enoughAll:enough.length > 0,
           narc:narc, narcStun:narcStun, narcDart:narcDart };
}

/* ===== renderTame ===== */
/* v95：取某 tab 的前置文案（后端 HOME[CUR].xxx），失败返回 alt 或 [] */
function wikiTabIntro(field, alt){
  try {
    var H = WIKI_HOME || {};
    /* v5850（用户口径「能力 / 操作方法为啥都没取到」）：
       后端 ark/载具回退写的 HOME 是**扁平结构**（{tameIntro:[...], abilIntro:[...]}），
       而这里只认 HOME[物种] ⇒ 扁平结构永远取不到，置顶文案全丢。这里兼容两种形态。 */
    var hm = H[CUR] || ((H.tameIntro || H.abilIntro || H.harvestIntro || H.expIntro || H.spawnIntro) ? H : {});
    var v = hm[field];
    if (v && v.length) return v;
  } catch (e) {}
  return (alt && alt.length) ? alt : [];
}
/* v5892（用户口径「这种前面多了个 •」）：wikily 抓下来的原文把列表项转成了「• 文本」，
   而渲染已按条包 <p>（本身即块级段落）⇒ 行首圆点纯冗余。统一在此剥掉，物种 / 地图 Wiki 共用。 */
function lbWikiNoBullet(s){
  return String(s == null ? '' : s).replace(/^\s*[\u2022\u00b7\u2219\u25cf\u25aa]\s*/, '');
}
function wikiIntroHtml(arr){
  if (!arr || !arr.length) return '';
  // v5765（用户口径「我要是的 AI整理的部分才需要这样」）：只有 AI 整理结果才加 .tc-ai（名词英文小字只在此块内生效）
  var _ai = LB_WT_LAST_AI; LB_WT_LAST_AI = 0;
  return '<div class="tc-intro' + (_ai ? ' tc-ai' : '') + '">' + arr.map(function(t){ return '<p>' + lbWikiNoBullet(t) + '</p>'; }).join('') + '</div>';
}

function renderTame(){
  var t = TAME[CUR];
  var _ti = [];
  try { _ti = lbWtPick('tameIntro', wikiTabIntro('tameIntro')) || []; } catch (eT0) { _ti = []; }
  /* v5852（用户口径「这种通过制作的实体，在驯服里除了置顶的文案，其他都没必要显示吧」）：
     v5850 让 HOME 兼容扁平后，lbWikiBind 会建出 TAME[CUR] = {tameIntro:[...]}（只有文案），
     旧判断只看 TAME[CUR] 是否存在 ⇒ 把整套驯服计算器（徽章/滑块/建议/速览/备货/工具/塔/灵药）全渲染了。
     现在只有真有驯服计算数据（食性 / 系数 / 食物表）才渲染计算器。 */
  var _hasCalc = !!(t && ((t.diet && t.diet.length) || t.setup || (t.wikiFoods && t.wikiFoods.length)));
  if (!_hasCalc){
    if (_ti.length){
      document.getElementById('lbWikiBody').innerHTML = '<div class="tc">' + wikiIntroHtml(_ti) + '</div>';
      return;
    }
    document.getElementById('lbWikiBody').innerHTML = '<div class="loading">（该物种无驯服数据）</div>';
    return;
  }
  // v39：介绍前置到 .tc 内、徽章之前（顺序 = 描述 → 徽章 → 计算器）
  var intro = ((((DATA[CUR] || {}).tabHtml || {})['1'] || {}).html) || '';
  // v95：tabHtml 一直为空 → 用后端 HOME.tameIntro 兜底
  // v5780（用户口径「漏了置顶正文都应该 AI 整理」）：**AI 整理结果优先**。
  //   原实现「有 tabHtml 就直接用 tabHtml」把 AI 结果挡在门外 ⇒ 置顶正文永远拿不到 .tc-ai，
  //   于是既不标名词、也不做正名。现在反过来：有 AI 用 AI（走 wikiIntroHtml 带上 .tc-ai），没有才用原文。
  var _tameAi = lbWtPick('tameIntro', wikiTabIntro('tameIntro'));
  var introHtml = (_tameAi && _tameAi.length) ? wikiIntroHtml(_tameAi)
                : (intro ? ('<div class="tc-intro">' + tcSentences(intro) + '</div>') : '');
  var h = '<div class="tc">'
    + introHtml
    + '<div class="tc-top">'
    + '<span class="tc-badge">倍率 ' + (TC_SP > 0 ? (TC_SP + '×') : '读取中') + '</span>'
    + '<span class="tc-badge2">野生上限 ' + tcMaxWild() + '</span>'
    + '</div>'
    + '<div class="tc-ctrl"><label>目标等级</label>'
    + '<input type="range" min="5" max="' + tcMaxWild() + '" step="5" value="' + TC_LV + '" oninput="tcLvSet(this.value)">'
    + '<span class="tc-lv" id="tcLvV">' + TC_LV + '</span></div>'
    // v5733（用户口径）：「建议」上移为 ①，其余编号顺延；「食物对照」改为折叠块嵌入 ③ 你现在有多少
    + '<div class="tc-sec"><div class="tc-h">① 建议</div><div class="tc-adv" id="tcAdv"></div></div>'
    + '<div class="tc-sec"><div class="tc-h">② 速览<em>滑块一动即时重算</em></div>'
    + '<div class="tc-tiles" id="tcTiles"></div>'
    // v118：.tc-tiles 是 grid(minmax 132px)，表格必须放外面，否则被挤成 132px 并与相邻格重叠
    + '<div id="tcWikiFoods" style="margin-top:10px"></div></div>'
    + '<div class="tc-sec"><div class="tc-h">③ 驯服备货<em>我的库存：本人背包 + 我的部落容器</em></div><div class="tc-own" id="tcOwn"></div></div>'
    + '<div class="tc-sec"><div class="tc-h">④ 驯服工具<em>当前角色 · 最优武器弹药组合</em></div><div class="tc-tool" id="tcTool"></div></div>'
    + '<div class="tc-sec"><div class="tc-h">⑤ 部落塔<em>Tribe Tower · 驯服速度加成</em></div><div id="tcTower"></div></div>'
    + '<div class="tc-sec"><div class="tc-h">⑥ 血之灵药<em>Sanguine Elixir · 驯服进度 +30%</em></div><div id="tcElixir"></div></div>'
    + '</div>';
  // v39：介绍已在函数开头前置（.tc 内、徽章之前）
  document.getElementById('lbWikiBody').innerHTML = h;
  tcMountIntro();
  tcCalc();
}

/* ===== tcLvSet ===== */
function tcLvSet(v){
  // v5730（用户口径）：粒度 5 —— 对齐到 5 的倍数，上限随物种（Tek 180 / 普通 150）
  var mx = tcMaxWild();
  var n = Math.round((parseInt(v, 10) || 5) / 5) * 5;
  TC_LV = Math.max(5, Math.min(mx, n));
  document.getElementById('tcLvV').textContent = TC_LV;
  tcCalc();
}

/* ===== tcSpSet ===== */
function tcSpSet(v){
  TC_SP = v;
  document.querySelectorAll('#lbWikiBody .tc-pre').forEach(function(b, i){
    b.classList.toggle('on', (i === 0) === (v === 6));
  });
  tcCalc();
}

/* ===== v5702（用户口径）：示例值清理 =====
   原 wiki_dex.json 的 ROLES（角色「白某」+ 假库存）与 TAME_W_INST（假武器 rating27/耐久288）
   是原型页时代的 demo 数据，已全部废弃 → 改读真实库存 / 真实武器实例。
   短名→类名用**实测类名**（wiki_dex 里的中文是旧的：机械十字弓=制式弩、十字弓=十字弩、麻醉长矛箭=麻醉弩箭） */
var TC_W_CLS = { longneck:'OneShotRifle', tekbow:'TekBow', harpoon:'Harpoon',
                 fabxbow:'Crossbow_Fab', crossbow:'Crossbow', compound:'CompoundBow', bow:'Bow' };
var TC_A_CLS = { shock:'RefinedTranqDart', dart:'TranqDart',
                 tranqspear:'TranqSpearBolt', tranqarrow:'ArrowTranq' };
/* v5705（权威重建）：驯服武器/弹药组合表，取代 wiki_dex.json 的 TAME_COMBOS
     · 弹药 torpor/damage：ark.wiki.gg/wiki/Tranquilizer_Dart 的 Ammunition 对比表（原文抓取）
     · 武器射速：项目 /api/wiki_item/<cls> 的 PARSED.attrs —— Reload Duration + Time Between Shots，
       弹匣 >1 时按 Ammo Per Clip 摊平（制式弩 10 发弹匣 ⇒ 平均 1.1s/发）
     · 🔴 麻醉弩箭(Tranq Spear Bolt) 只能由 **鱼叉枪(Harpoon Launcher)** 发射，装不进制式弩
     · 泰克弓没有「泰克麻醉箭」这个物品（wiki 说 Tek Bow 用普通箭，对比表无此项）⇒ 整条删除 */
var TC_W_RATE = { longneck:4.6, fabxbow:1.1, crossbow:2.3, bow:1.3, compound:1.3, harpoon:3.0 };
/* v5708（用户口径）：武器环境适用性 —— 水下不能用长管步枪/弓/复合弓；鱼叉枪只在水中
     env: land = 仅陆地 · water = 仅水下 · both = 两栖通用 */
var TC_COMBOS = [
  { key:'rifle-shock', w:'longneck', a:'shock',      torpor:442,   dmg:26, env:'land'  },  // 长管步枪 + 强效麻醉镖
  { key:'rifle-dart',  w:'longneck', a:'dart',       torpor:221,   dmg:26, env:'land'  },  // 长管步枪 + 麻醉镖
  { key:'harpoon',     w:'harpoon',  a:'tranqspear', torpor:306,   dmg:36, env:'water' },  // 鱼叉枪   + 麻醉弩箭
  { key:'xbow',        w:'crossbow', a:'tranqarrow', torpor:157.5, dmg:35, env:'both'  },  // 十字弩   + 麻醉箭
  { key:'fabxbow',     w:'fabxbow',  a:'tranqarrow', torpor:157.5, dmg:35, env:'both'  },  // 制式弩   + 麻醉箭
  { key:'compound',    w:'compound', a:'tranqarrow', torpor:121.5, dmg:27, env:'land'  },  // 复合弓   + 麻醉箭
  { key:'bow',         w:'bow',      a:'tranqarrow', torpor:90,    dmg:20, env:'land'  }   // 弓       + 麻醉箭
];
/* v5708：水下生物清单（只能在水下击晕 —— 水下拉不开弓、枪械也打不出）
   判定：优先用 wikily 中文名关键词，其次类名兜底（ARK 类名与中文常不一致，如鱼龙 = Dolphin_Character_BP）
   两栖类（古巨龟/巨蛙/棘背龙/帝鳄/恐鳄/猪鳄/笠头螈/碳龟/巨龟）按**陆地**处理 —— 岸上就能打 */
/* v5709（用户口径·B）：手写中文清单永远会漏（ASA 新生物：古章鱼/海妖/旋齿鲨/潮汐兽/狮子鱼…）
   ⇒ 改为「类名词根全量 + 中文兜底」双轨，类名词根取自项目权威物种表 ASA-values.json（1144 物种）实扫
   陷阱：① 裸 `鲨` 会误伤「鲨齿龙」⇒ 只列 巨齿鲨/旋齿鲨
        ② `Ichthyo` 会误伤鱼鸟 Ichthyornis ⇒ 鱼龙走 `Dolphin`（其类名就是 Dolphin_Character_BP）
        ③ `Diplo` 会误伤梁龙 Diplodocus ⇒ 不用该词根
   两栖按陆地：古巨龟/巨蛙/棘背龙/帝鳄/恐鳄/猪鳄/笠头螈/碳龟/巨龟/巨蟹 —— 岸上就能打 */
var TC_AQ_RE = /章鱼|鱿|乌贼|海妖|沧龙|蛇颈龙|鱼龙|邓氏鱼|巨齿鲨|旋齿鲨|鲸|蝠鲼|广翅鲎|电鳗|滑齿龙|鮟鱇|灯笼鱼|剑射鱼|三叶虫|菊石|水母|利兹鱼|七鳃鳗|腔棘鱼|剑齿鲑|食人鱼|鲎|潮汐兽|狮子鱼|海德拉/;
var TC_AQ_CLS = /Mosa|Plesiosaur|Dolphin|Dunkle|Megalodon|Tuso|Squid|Octopus|Manta|Electrophorus|Eel|Basilosaurus|Liopleurodon|Angler|Ammonite|Trilobite|Cnidaria|Leedsichthys|Coel|Salmon|Piranha|Euryp|Lamprey|Xiphactinus|Shastasaurus|Kraken|Shark_Character|SpaceWhale|Lionfish|Hydra_|Helicoprion|Axolotl|RockwellTentacle/i;
function tcIsAquatic(){
  try{
    var z = String(((DATA || {})[CUR] || {}).zh || '');
    if (z && TC_AQ_RE.test(z)) return true;
    var c = String(LB_WIKI.cur || LB.curClass || '');
    if (c && TC_AQ_CLS.test(c)) return true;
  }catch(e){}
  return false;
}
function tcTargetHp(lv){
  // v5706（根因修复）：必须按目标等级算**实际血量** —— 只取 1 级基础值会把 150 级阿根廷巨鹰算成 365 血
  //   （实际 365 × (1 + 0.2 × 149) = 11242），导致「会打死」全线误报。
  //   OVERVIEW.stats[0] = ["生命值", base, 野生每级成长率]（与 tcRows 同一数据源）
  try{
    var ov = (OVERVIEW || {})[CUR] || {};
    var st = ov.stats || [];
    if (!st.length || !st[0]) return 0;
    var base = Number(st[0][1]) || 0, pw = Number(st[0][2]) || 0;
    var L = Number(lv) || 0;
    if (!L) return base;
    return base * (1 + pw * Math.max(0, L - 1));
  }catch(e){}
  return 0;
}
function tcClsOf(shortKey){
  var c = TC_W_CLS[shortKey] || TC_A_CLS[shortKey] || '';
  if (c) return c;
  var zh = ((TAME_WEAPONS || {})[shortKey] || (TAME_AMMO || {})[shortKey] || {}).zh || '';
  try{ return zh ? (lbItemClsByZh(zh) || '') : ''; }catch(e){ return ''; }
}
function tcWZh(shortKey){
  // v5703（用户口径·根治）：短名 → 类名 → lbItemZh 取项目统一中文（item_zh.json 唯一源），
  //   彻底不再依赖 wiki_dex.json 里的旧中文（机械十字弓/十字弓/麻醉长矛箭 均已过时）
  var cls = tcClsOf(shortKey);
  if (cls){ try{ var z = lbItemZh(cls); if (z) return z; }catch(e){} }
  return ((TAME_WEAPONS || {})[shortKey] || (TAME_AMMO || {})[shortKey] || {}).zh || shortKey;
}
function tcBestWeaponInst(shortKey){
  var cls = tcClsOf(shortKey); if (!cls) return null;
  var d = LB._cache && LB._cache.data; if (!d || !d.itemsByServer) return null;
  var tbase = ''; try{ tbase = String((lbItemMeta(cls) || {}).base || cls); }catch(e){ tbase = cls; }
  var best = null;
  Object.keys(d.itemsByServer).forEach(function(sv){
    var bc = (d.itemsByServer[sv] || {}).byCid || {};
    Object.keys(bc).forEach(function(cid){
      var arr = bc[cid] || [];
      for (var i = 0; i < arr.length; i++){
        var it = arr[i]; if (!it || it.isBlueprint) continue;
        var ic = String(it['class'] || '').replace(/_C_\d+$/, '').replace(/_C$/, '');
        // v5704（根因修复）：归一必须走 lbItemMeta().base —— lbCanonBase 对 `PrimalItem_Weapon*` 只剥
        //   `PrimalItem_`，会留下 Weapon 前缀（WeaponCrossbow_Fab ≠ Crossbow_Fab）⇒ 48 把制式弩全被跳过
        var mb = ''; try{ mb = String((lbItemMeta(ic) || {}).base || ''); }catch(e){ mb = ''; }
        var hit = (ic === cls) || (!!mb && mb === tbase);
        if (!hit) continue;
        // v5705（用户口径）：只认「我的」—— 背包按当前角色名、容器按所属部落（与库存数字同口径）
        try{ if (typeof lbMatIsMine === 'function' && !lbMatIsMine(sv, it)) continue; }catch(e){}
        var rr = Number(it.rating) || 0;
        if (!best || rr > best.r) best = { it: it, sv: sv, r: rr };
      }
    });
  });
  return best;
}
function tcMySpecies(){
  try{
    var cls = String(LB_WIKI.cur || LB.curClass || ''); if (!cls) return null;
    var d = LB._cache && LB._cache.data; if (!d || !d.recs) return null;
    var curPid = (typeof lbCurPid === 'function') ? lbCurPid() : '';
    var ps = curPid ? lbPlayerTribes(d.tribesByServer || {}, curPid) : null;
    var n = 0, lv = 0;
    (d.recs || []).forEach(function(r){
      if (!r || r.isEmpty) return;
      if (String(r.dinoClass || '') !== cls) return;
      if (ps && !lbIsPlayerRec(r, ps, curPid)) return;
      n++;
      var L2 = Number(r.level) || 0; if (L2 > lv) lv = L2;
    });
    return { n: n, lv: lv };
  }catch(e){ return null; }
}
/* ===== tcRoleInv ===== */
function tcRoleInv(){
  // v5702：改读真实全服库存（lbItemOwnCnt 已按「当前角色 + 所属部落」过滤）
  var inv = {}, keys = [];
  TC_COMBOS.forEach(function(cb){ keys.push(cb.w); keys.push(cb.a); });
  keys.forEach(function(k){
    if (inv[k]) return;
    var cls = tcClsOf(k), n = 0, svc = 0;
    if (cls){ try{ var o = lbItemOwnCnt(cls, true) || {}; n = Number(o.n) || 0; svc = Number(o.svc) || 0; }catch(e){} }
    inv[k] = { n: n, svc: svc, cls: cls, locs: (svc > 0 ? new Array(svc) : []) };
  });
  return inv;
}

/* ===== tcBestPair ===== */
function tcBestPair(r){
  // v5705：排序口径 = 「净增速」—— 扣掉射击期间 torpor 自然衰减
  //   每发净增 net = torpor - wakeRate × 射速；net <= 0 ⇒ 该组合永远打不晕，直接剔除
  //   再加致死闸：击晕总伤害 = 发数 × 每发伤害，>= 目标血量 ⇒ 会打死
  var inv = tcRoleInv();
  var wake = (r && r.wakeRate) ? r.wakeRate : 0;
  var target = (r && r.torpor) ? r.torpor : 0;
  var hp = tcTargetHp(r && r.lv);
  var out = [];
  var aq = tcIsAquatic();                            // v5708：水下生物只能弩/鱼叉枪；陆地禁用鱼叉枪
  TC_COMBOS.forEach(function(cb){
    var env = cb.env || 'land';
    if (aq && env === 'land') return;
    if (!aq && env === 'water') return;
    var w = inv[cb.w] || { n:0 }, a = inv[cb.a] || { n:0 };
    // v5709（用户口径）：**不再按库存过滤** —— 要的是「最佳组合」，不是「我有的组合」。
    //   库存只作标注（0 ⇒ 弹药 chip 标红「无库存」、武器无实例出虚线「无实例」卡）。
    var rate = TC_W_RATE[cb.w] || 5;
    var net = cb.torpor - wake * rate;              // 每发净增
    if (net <= 0) return;                           // 涨得还没掉得快 ⇒ 永远打不晕
    var shots = target > 0 ? Math.ceil(target / net) : 0;
    out.push({ cb:cb, rate:rate, net:net, shots:shots,
               totalDmg: shots * cb.dmg, perSec: net / rate,
               wn:w.n, an:a.n });
  });
  if (!out.length) return null;
  var safe = hp > 0 ? out.filter(function(x){ return x.totalDmg < hp; }) : out;
  var pool = safe.length ? safe : out;
  pool.sort(function(a,b){ return (b.perSec - a.perSec) || (a.shots - b.shots); });
  return { best: pool[0], list: pool, all: out, hp: hp, willKill: (hp > 0 && !safe.length) };
}

/* ===== tcWeaponCard ===== */
function tcWeaponCard(key, perKill, subHtml){
  // v5702（用户口径）：废弃 TAME_W_INST 示例武器，改读真实库存里的最优那把；右侧复用 lbOwnerTagMy 统一归属标签
  // v5708：+subHtml —— 弹药与「射速/发数/耐久够训」数据行塞进同一张卡；外层改 block 以便数据行整行铺开
  var wzh = tcWZh(key);
  var bst = tcBestWeaponInst(key);
  // v5709（用户口径）：组合已不按库存过滤 ⇒ 没实例也必须出卡，否则「最佳组合」会整条消失
  if (!bst){
    return '<div class="lb-breed-card" style="background:#1a1a24;border:1px dashed #475569;border-radius:8px;padding:6px 10px;margin-bottom:6px;font-size:12px">'
      + '<div style="display:flex;align-items:center;justify-content:space-between;gap:10px">'
      + '<div style="min-width:0">'
      + '<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#475569;margin-right:5px;vertical-align:1px"></span>'
      + '<b style="color:#fff"' + tcPickAttr(wzh) + '>' + wzh + '</b>'
      + ' <span style="background:#f8717122;border-radius:2px;padding:0 6px;color:#f87171">无实例</span>'
      + '</div><div style="flex-shrink:0;font-size:11px;color:#999;text-align:right"></div></div>'
      + (subHtml ? ('<div style="margin-top:5px;padding-top:5px;border-top:1px solid #ffffff12">' + subHtml + '</div>') : '')
      + '</div>';
  }
  var it = bst.it;
  var col = (typeof lbBpStageCol === 'function') ? lbBpStageCol(it.qidx) : '#b8b8b8';
  var rows = []; try{ rows = lbStatRows(String(it['class'] || ''), it.stats || [], String(it.kind || '')); }catch(e){ rows = []; }
  var dura = Number(it.durability) || 0;
  var attr = (rows || []).map(function(s, i){
    return '<span style="margin-right:6px;color:' + (i === 0 ? '#38bdf8' : '#999') + '">' + s.label + ' ' + s.txt + '</span>';
  }).join('');
  var canTame = (dura > 0 && perKill > 0) ? Math.floor(dura / perKill) : null;   // v5708：移到数据行集中展示
  // v5705：rec 与装备榜 lbRankRow 同构 —— 缺 _rankItem 时 lbSettlementOf 会走 dinoId 分支（武器没有 dinoId）
  //   ⇒ 聚落恒空；补上 _rankItem/tribeId/坐标 后再经 lbRealFacOf 换成设施真身，聚落与区域才显示
  var rec = { server: bst.sv,
              containerType: String(it.containerType || ''),
              containerClass: String(it.containerClass || ''),
              containerName: String(it.containerName || ''),
              containerId: String(it.containerId || ''),
              containerTribe: Number(it.containerTribe || 0),
              containerTribeName: String(it.containerTribeName || ''),
              containerOwnerPid: (it.containerOwnerPid !== undefined ? it.containerOwnerPid : undefined),
              ownerTribeId: Number(it.containerTribe || 0),
              tribeId: Number(it.containerTribe || 0),
              playerName: String(it.playerName || ''),
              containerX: Number(it.x) || 0, containerY: Number(it.y) || 0, containerZ: Number(it.z) || 0,
              x: Number(it.x) || 0, y: Number(it.y) || 0, z: Number(it.z) || 0,
              isEmpty: false, _rankItem: true };
  try{
    var _fr = (typeof lbRealFacOf === 'function') ? lbRealFacOf(rec) : null;
    if (_fr){
      rec.containerClass = String(_fr.containerClass || rec.containerClass);
      if (_fr.containerName) rec.containerName = String(_fr.containerName);
    }
  }catch(e0){}
  var owner = '';
  try{ owner = lbOwnerTagMy(rec, { noEn: true }) || ''; }catch(e){ owner = ''; }
  if (!owner){
    var _sn = bst.sv;
    try{ (LB.SERVERS || []).forEach(function(s){ if (s.abbr === bst.sv) _sn = s.name || s.abbr; }); }catch(e){}
    owner = '<span style="color:#f59e0b">' + lbMdiSvg('mdi-map', 12) + ' ' + _sn + '</span>';
  }
  var rate = Number(it.rating) || 0;
  return '<div class="lb-breed-card" style="background:#1a1a24;border:1px solid ' + col + ';border-radius:8px;padding:6px 10px;margin-bottom:6px;font-size:12px">'
    + '<div style="display:flex;align-items:center;justify-content:space-between;gap:10px">'
    + '<div style="min-width:0">'
    + '<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:' + col + ';margin-right:5px;vertical-align:1px"></span>'
    + '<b style="color:#fff"' + tcPickAttr(wzh) + '>' + wzh + '</b>'
    + (rate > 0 ? ' <span style="background:#7c3aed33;border-radius:2px;padding:0 6px;color:#c4b5fd">评分 ' + rate.toFixed(1) + '</span>' : '')
    + (attr ? '<br>' + attr : '')
    + '</div>'
    + '<div style="flex-shrink:0;font-size:11px;color:#999;text-align:right">' + owner + '</div>'
    + '</div>'
    // v5708（用户口径）：弹药 + 数据行与武器同框，数据行独立一行
    + (subHtml ? ('<div style="margin-top:5px;padding-top:5px;border-top:1px solid #ffffff12">' + subHtml + '</div>') : '')
    + '</div>';
}

/* ===== v5720（用户口径）：物品「点位面包屑」=====
   与「最优武器卡片右侧」**完全同源**（同一个 lbOwnerTagMy）：
     🗺️地图图标 + 容器名 + ⛺聚落名 + 📍区域名
   数据源：LB._cache.data.itemsByServer[sv].byCid[cid]（每容器内的物品数组）；
   口径：只算**当前角色拥有**（lbItemOwnKeep，与数量统计 lbItemOwnIndex 同一套过滤）；
   取「该物品**数量最多**的那个容器」。缓存键 = 数据版本 ts | 当前角色 pid。 */
LB._itemWhereIdx = LB._itemWhereIdx || null;
LB._itemWhereIdxKey = LB._itemWhereIdxKey || '';
function lbItemWhereIndex(){
  var ts = (LB._cache && LB._cache.ts) || 0;
  var D = LB._cache && LB._cache.data;
  var curPid = null; try{ curPid = lbCurPid(); }catch(e0){ curPid = null; }
  var _ck = String(ts) + '|' + String(curPid || '');
  if (LB._itemWhereIdx && LB._itemWhereIdxKey === _ck) return LB._itemWhereIdx;
  var map = {};
  var _ownCtx = null;
  try{ _ownCtx = lbItemOwnCtx(); }catch(e1){ _ownCtx = null; }
  if (D && D.itemsByServer){
    Object.keys(D.itemsByServer).forEach(function(sv){
      var ix = D.itemsByServer[sv] || {};
      var bc = ix.byCid || {};
      Object.keys(bc).forEach(function(cid){
        var arr = bc[cid] || [];
        if (!arr.length) return;
        var cnt = {};
        for (var i = 0; i < arr.length; i++){
          var x = arr[i]; if (!x) continue;
          try{ if (typeof lbIsEmptyItem === 'function' && lbIsEmptyItem(x)) continue; }catch(e){}
          try{ if (typeof lbItemOwnKeep === 'function' && !lbItemOwnKeep(x, sv, _ownCtx)) continue; }catch(e){}
          var cls = String(x['class'] || ''); if (!cls) continue;
          var k = ''; try{ k = lbItemAggKey(cls); }catch(e2){ k = cls; }
          if (!k) continue;
          var _q = (Number(x.quantity) || 0);
          if (_q <= 0) _q = 1;
          if (!cnt[k]){ cnt[k] = { n: 0, it: x }; }
          cnt[k].n += _q;
        }
        Object.keys(cnt).forEach(function(k){
          var cur = map[k];
          if (cur && cnt[k].n <= cur.n) return;
          var rec = { n: cnt[k].n, sv: sv, cid: cid, it: cnt[k].it };
          map[k] = rec;
          // 别名（词典短键口径），与 lbItemOwnIndex 的 en: 归一保持同一套
          var b = ''; try{ b = lbCanonBase((lbItemMeta(cnt[k].it['class']) || {}).base || ''); }catch(e3){ b = ''; }
          if (b && b !== k){ var a = map[b]; if (!a || rec.n > a.n) map[b] = rec; }
        });
      });
    });
  }
  LB._itemWhereIdx = map; LB._itemWhereIdxKey = _ck;
  return map;
}
// 生成面包屑（另起一行、右对齐）；查不到容器 / 没有库存 ⇒ 返回空串（不造假）
function tcItemWhereHtml(zh, inlineMode){
  var cls = ''; try{ cls = lbItemClsByZh(zh) || ''; }catch(e){ cls = ''; }
  if (!cls) return '';
  var k = ''; try{ k = lbItemAggKey(cls) || ''; }catch(e2){ k = ''; }
  if (!k) return '';
  var idx = null; try{ idx = lbItemWhereIndex(); }catch(e3){ idx = null; }
  var hit = idx && idx[k];
  if (!hit || !hit.it) return '';
  var it = hit.it;
  var rec = { server: hit.sv,
              containerType: String(it.containerType || ''),
              containerClass: String(it.containerClass || ''),
              containerName: String(it.containerName || ''),
              containerId: String(hit.cid || it.containerId || ''),
              containerTribe: Number(it.containerTribe || 0),
              ownerTribeId: Number(it.containerTribe || 0),
              tribeId: Number(it.containerTribe || 0),
              playerName: String(it.playerName || ''),
              containerX: Number(it.x) || 0, containerY: Number(it.y) || 0, containerZ: Number(it.z) || 0,
              x: Number(it.x) || 0, y: Number(it.y) || 0, z: Number(it.z) || 0,
              isEmpty: false, _rankItem: true };
  // 与 tcWeaponCard 完全一致：先经 lbRealFacOf 换成设施真身，再交由 lbOwnerTagMy 出标签
  try{
    var fr = (typeof lbRealFacOf === 'function') ? lbRealFacOf(rec) : null;
    if (fr){
      rec.containerClass = String(fr.containerClass || rec.containerClass);
      if (fr.containerName) rec.containerName = String(fr.containerName);
    }
  }catch(e4){}
  var tag = '';
  try{ tag = lbOwnerTagMy(rec, { noEn: true }) || ''; }catch(e5){ tag = ''; }
  if (!tag) return '';
  // v5730（用户口径）：原 title=面包屑全文与正文**完全一致**（冗余）⇒ 删除，不再显示浏览器原生 tooltip
  // v5726：inlineMode = chip 内「同一行右对齐」版（不另起一行、上间距 0）；否则为行内「另起一行右对齐」版
  if (inlineMode){
    return '<span class="tc-where" style="margin-left:auto;display:inline-block;text-align:right;font-size:11px;line-height:1.3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:62%;opacity:.9;flex-shrink:1">' + tag + '</span>';
  }
  return '<span class="tc-where" style="flex:1 0 100%;display:block;text-align:right;font-size:11px;line-height:1.55;margin-top:0;opacity:.9">' + tag + '</span>';
}
// 有面包屑时容器需允许换行
function tcWhereWrap(whereHtml, base){
  if (!whereHtml) return '';
  return ' style="' + (base || '') + 'flex-wrap:wrap"';
}
/* ===== v5717（用户口径）：wiki 内物品一律可点 → 关闭 wiki + 主页面选中该物品 =====
   范式与 lbPickerSelect / 草稿恢复完全一致：LB.pickItem={kind,base} → LB.curClass='' →
   lbRecordRecentItem → switchTab('latest') → lbView()。中文名走项目唯一源 lbItemClsByZh。 */
function tcPickByZh(zh){
  var z = String(zh == null ? '' : zh).trim();
  if (!z) return;
  var cls = '';
  try{ cls = lbItemClsByZh(z) || ''; }catch(e){ cls = ''; }
  if (!cls) return;                              // 项目物品表查不到 ⇒ 不响应（不制造假交互）
  var kind = '', base = cls;
  try{ var m = lbItemMeta(cls) || {}; kind = String(m.kind || ''); base = String(m.base || cls); }catch(e){}
  try{ if (typeof lbWikiClose === 'function') lbWikiClose(); }catch(e){}
  LB.pickItem = { kind: kind, base: base };
  LB.curClass = '';
  try{ if (typeof lbRecordRecentItem === 'function') lbRecordRecentItem(kind, base); }catch(e){}
  try{ if (typeof switchTab === 'function') switchTab('latest'); }catch(e){}
  try{ if (typeof lbView === 'function') lbView(); }catch(e){}
  try{ if (typeof lbRenderBreedBar === 'function') lbRenderBreedBar(); }catch(e){}
}
// 生成 onclick 属性（中文名查不到物品类名时不返回任何属性 ⇒ 该处保持不可点）
function tcPickAttr(zh){
  var z = String(zh == null ? '' : zh).trim();
  if (!z) return '';
  var ok = false;
  try{ ok = !!lbItemClsByZh(z); }catch(e){ ok = false; }
  if (!ok) return '';
  var esc = z.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '&quot;');
  // v5718：不带 title —— 目标元素常自带 title（如弹药品的"麻醉箭"），重复属性会让后者被忽略
  return ' onclick="event.stopPropagation();tcPickByZh(\'' + esc + '\')"';
}
/* ===== tcAmmoChip ===== */
function tcAmmoChip(key){
  var a = { zh: tcWZh(key), ic: '' };   // v5703：中文走项目源 lbItemZh（原 TAME_AMMO[key].zh 是 wiki_dex 旧值）
  var inv = tcRoleInv(), g = inv[key] || { n:0, svc:0, locs:[] };
  // v76：优先按项目物品类名取图（item_zh 口径），回退 index.json 的 ic（再过分包）
  var _ammoCls = { shock:'RefinedTranqDart', dart:'TranqDart',
                   tranqspear:'TranqSpearBolt', tranqarrow:'ArrowTranq' }[key] || '';
  var _ammoIc = lbWikiResIcon(a.zh) || lbWikiIcCls(_ammoCls);   // v147：不再用 a.ic（index ic 外链）
  var ic = _ammoIc
    ? '<img src="' + _ammoIc + '" style="width:16px;height:16px;object-fit:contain" onerror="lbImgRetry(this)">'
    : '<span style="width:16px;height:16px;display:inline-flex;align-items:center;justify-content:center;color:#64748b;font-size:11px;flex-shrink:0">?</span>';
  var _where2 = ''; try{ _where2 = tcItemWhereHtml(a.zh, true); }catch(e){ _where2 = ''; }
  // v5726/v5727（用户口径）：弹药卡**自适应独占一行**（无论有无面包屑），面包屑与左侧信息**同一行**、贴右对齐（不另起一行）
  // v5730（用户口径）：title=物品名 与正文完全一致（冗余）⇒ 删除
  return '<span class="lb-hf-chip" style="width:100%;max-width:100%;overflow:hidden"' + tcPickAttr(a.zh) + '>'
    + ic
    + '<span style="color:#cbd5e1">' + a.zh + '</span>'
    + '<span style="color:#475569;font-size:10px">·</span>'
    + '<span style="color:#94a3b8;font-size:11px">' + (g.svc || 0) + ' 服</span>'
    + '<span style="color:#475569;font-size:10px">·</span>'
    + (g.n > 0 ? ('<span style="color:#64748b">' + tcNum(g.n) + '</span>')
               : '<span style="color:#f87171;font-weight:600">无库存</span>')   // v5709：库存 0 红标（组合不再被过滤）
    + _where2
    + '</span>';
}

/* ===== tcToolsHtml ===== */
function tcToolsHtml(r){
  // v5707（用户口径）：不只给「效率最高」一个，而是三方案并排 —— 最快击晕 / 最少箭数 / 最低伤害
  var pr = tcBestPair(r);
  if(!pr) return '<div class="tc-adv" style="margin-bottom:6px">⚠️ 当前角色没有「武器 + 对应弹药」可用的击晕组合。</div>';
  var wake = (r && r.wakeRate) ? r.wakeRate : 0;
  var pool = (pr.list && pr.list.length) ? pr.list : [pr.best];
  var byFast = pool.slice().sort(function(a,b){ return (b.perSec - a.perSec) || (a.shots - b.shots); });
  var byFew  = pool.slice().sort(function(a,b){ return (a.shots - b.shots) || (b.perSec - a.perSec); });
  var byLow  = pool.slice().sort(function(a,b){ return (a.totalDmg - b.totalDmg) || (b.perSec - a.perSec); });
  var picks = [];
  var addPick = function(tag, x){
    if (!x) return;
    for (var i = 0; i < picks.length; i++){
      if (picks[i].x.cb.key === x.cb.key){
        if (picks[i].tags.indexOf(tag) < 0) picks[i].tags.push(tag);
        return;
      }
    }
    picks.push({ x:x, tags:[tag] });
  };
  addPick('最快击晕', byFast[0]);
  addPick('最少箭数', byFew[0]);
  addPick('最低伤害', byLow[0]);

  var out = '';
  picks.forEach(function(pk){
    var b = pk.x;
    var stopSec = (wake > 0 && b.cb.torpor > 0) ? Math.round(b.cb.torpor / wake) : 0;
    var kills = b.shots > 0 ? Math.floor((b.an || 0) / b.shots) : 0;
    // v5711（插件 exe 2026-10-30 新字段）：`durabilityPct` = **当前耐久比例**（0~1，-1 = 该物品无耐久属性）。
    //   旧字段 `durability` 源属性 `ItemDurability` 在存档里根本不存在（恒 0，全服实测 10 图 = 0 条），已弃用。
    //   用户口径：**只显示百分比**，不推绝对值（存档无「最大耐久」字段，绝对值只能靠 stats 换算，属推算）。
    //   但「够训几只」仍要用 上限 × 比例 才有意义 ⇒ 上限仍走 lbStatRows 取，仅在内部使用、不上屏。
    //   🔴 v5710 教训：必须**先算再拼 line** —— var 提升会让「先拼后算」拿到 undefined ⇒ 整段静默不渲染。
    var canT = null, duraV = 0, duraPct = -1;
    try{
      var _bst = tcBestWeaponInst(b.cb.w);
      if (_bst){
        var _p = _bst.it.durabilityPct;
        if (typeof _p === 'number' && isFinite(_p) && _p >= 0) duraPct = _p;
        var _rs = lbStatRows(String(_bst.it['class'] || ''), _bst.it.stats || [], String(_bst.it.kind || ''));
        for (var _ri = 0; _ri < (_rs || []).length; _ri++){
          if (_rs[_ri] && _rs[_ri].label === '耐久'){ duraV = Number(_rs[_ri].txt) || 0; break; }
        }
        // 蓝图为图纸、无真实耐久 ⇒ 不参与够训计算（插件限制：图纸 pct 恒 1.0）
        if (!_bst.it.isBlueprint && duraPct >= 0 && duraV > 0 && b.shots > 0){
          canT = Math.floor(duraV * duraPct / b.shots);
        }
      }
    }catch(e){}
    // v5728（用户口径）：原「射速 1.1s/发 · 单只 39 发 · 约 43s · 总伤害 … 」单行长文字可读性差
    //   → 拆成 5 个简易徽章，同类信息放同一个徽章内；每箭可停改用 tcDur() 动态格式（125 -> 2m 5s）
    var _bdg = function(k, v){
      return '<span class="tc-bdg"><span class="tc-bdg-k">' + k + '</span><span>' + v + '</span></span>';
    };
    // v5730（用户口径）：最快击晕/最少箭数/最低伤害 由纯紫字一行改为**主题色徽章**，并排到徽章行最前面
    var _tagHot = pk.tags.map(function(tg){ return '<span class="tc-bdg tc-bdg-hot">' + tg + '</span>'; }).join('');
    var line = _tagHot
      + _bdg('射击节奏', '射速 <b>' + b.rate.toFixed(1) + '</b>s/发 · 单只 <b>' + b.shots + '</b> 发 · 约 <b>'
                        + tcDur(Math.round(b.shots * b.rate)) + '</b>')
      + _bdg('伤害', '总伤 <b>' + tcNum(b.totalDmg) + '</b>'
                    + (pr.hp > 0 ? (' / 血量 <b>' + tcNum(pr.hp) + '</b>') : ''))
      + (stopSec > 0 ? _bdg('麻醉窗口', '每箭可停 <b>' + tcDur(stopSec) + '</b>') : '')
      + (b.an > 0
          ? _bdg('弹药', '<b>' + tcNum(b.an) + '</b> 发 ≈ 够训 <b>' + kills + '</b> 只'
                        + (kills === 0 && b.shots > 0 ? '<b style="color:#f87171">（不够一只）</b>' : ''))
          : _bdg('弹药', '<b style="color:#f87171">无库存</b>'))
      // v5711（用户口径·B）：耐久只显示**百分比**（当前耐久比例，插件原生值，不推算绝对值）；
      //   pct > 1 实测存在（最高 1.29）⇒ 数值不截断（否则误报成 100%）；-1/缺失 ⇒ 显示「—」不当 0% 处理
      + (duraPct >= 0
          ? _bdg('耐久', '<b>' + (duraPct * 100).toFixed(1) + '%</b>'
                        + (canT !== null ? (' · 够训 <b>' + canT + '</b> 只') : ''))
          : _bdg('耐久', '<b style="color:#888">—</b>'));
    // v5731（用户口径）：射速口径 ⓘ 悬浮**没必要显示** ⇒ 移除图标，徽章行直接以标签徽章开头
    var sub = '<div style="display:flex;flex-wrap:wrap;align-items:center;gap:8px">' + tcAmmoChip(b.cb.a) + '</div>'
            + '<div style="margin-top:5px;display:flex;flex-wrap:wrap;align-items:center;gap:5px">' + line + '</div>';
    out += '<div style="margin-bottom:10px">'
        + tcWeaponCard(b.cb.w, b.shots, sub)   // v5730：tags 已并入卡内徽章行，此处不再单列
        + '</div>';
  });

  var warn = '';
  if (pr.hp > 0 && pr.willKill){
    warn = '<div class="tc-adv" style="margin-top:2px;border-color:#f8717166;background:#f871711a">'
         + '⚠️ 可用组合的击晕总伤害都 ≥ 目标血量 <b>' + Math.round(pr.hp) + '</b> —— <b>会打死</b>。'
         + '建议换伤害更低的弹药，或先提升武器品质。</div>';
  } else if (pr.hp > 0 && pr.best.totalDmg >= pr.hp * 0.9){
    warn = '<div class="tc-adv" style="margin-top:2px;border-color:#f59e0b66;background:#f59e0b1a">'
         + '⚠️ 击晕总伤害 <b>' + Math.round(pr.best.totalDmg) + '</b> 已接近目标血量 <b>' + Math.round(pr.hp)
         + '</b>，打晕即停，别补枪。</div>';
  }
  return out + warn;
}

/* ===== tcCalc ===== */
/* ===== v5700：血之灵药（Sanguine Elixir）=====
   官方口径（ark.wiki.gg/wiki/Sanguine_Elixir）：
     · 使用后立即为任意生物的驯服进度 +30%（对婴儿则是留痕 +30%）
     · 每只生物限用一次（打醒再打晕也不能再用）
     · 4 小时腐坏，任何方式都无法延长；放快捷栏、看着生物使用
     · 配方 200 × 血袋，制作 5 秒
   ⇒ 进度 +30% = 剩余亲和度需求 ×0.7 ⇒ 口数/时间重算，效率按公式自然提高。 */
/* v5701（用户口径）：驯服 tab 物品名统一「中文 + 英文」，英文小字浅色弱化 */
function tcZhEn(zh, en){
  var e = String(en || '').trim();
  if (!e || !/[A-Za-z]/.test(e) || /[\u4e00-\u9fa5]/.test(e)) return String(zh || '');
  return String(zh || '') + '<span style="opacity:.5;font-size:10px;font-weight:400;margin-left:4px">' + e + '</span>';
}
function tcElixirOwn(){
  var a = 0, b = 0;
  try{ a = lbItemOwnCnt('PrimalItem_SanguineElixir') | 0; }catch(e){}
  try{ b = lbItemOwnCnt('Sanguine_Elixir') | 0; }catch(e){}
  return Math.max(a, b);
}
/* ===== v5716：部落塔（Tribe Tower）驯服速度加成 =====
   插件口径（报告 WorldProbe_部落塔加成_前端对接_20261030 §5）：
     · 每真实天 +1% 驯服速度，20 天封顶 +20%，再乘 TribeTowerBonusMultiplier（本站 M=2 ⇒ 上限 +40%）
     · 只对**塔所属部落成员**生效；塔必须处于激活中（towerAct>0 且 towerDeact=-1000）
     · 数据源：存档 facilities（v5714 透传）+ 后端 /api/world_clock 逆推世界时钟
   驯服 tab 固定按孤岛服倍率算（TC_SP 来源 = Isl GUS）⇒ 此处同样取 Isl 的塔 */
LB._tcTwAsked = LB._tcTwAsked || {};     // v5718：按服记录（sv -> 1），防重复触发时钟加载
// 单座塔的计算结果（不读 UI，纯数据）
function tcTowerCalc(w){
  var sv = String((w && w.sv) || '');
  var rr = (w && w._rec) || {};
  var act = Number(rr.towerAct) || 0;
  var deact = (rr.towerDeact === undefined || rr.towerDeact === null) ? -1000 : Number(rr.towerDeact);
  var out = { w: w, sv: sv, active: (act > 0 && deact === -1000), days: 0, ready: false, bs: null, tribe: '', act: act };
  try{
    var tb = ((LB._cache && LB._cache.data && LB._cache.data.tribesByServer) || {})[sv] || {};
    var tt = tb[String(rr.containerTribe || rr.ownerTribeId || '')];
    if (tt) out.tribe = String(tt.tribeName || tt.name || '');
  }catch(e){}
  if (out.active){
    var clk = LB._towerClock[sv] && LB._towerClock[sv].d;
    if (clk && clk.ok && typeof clk.fileWorldTime === 'number'){
      var dd = (clk.fileWorldTime - act) / 86400;
      if (dd >= 0 && dd <= 5000){
        out.days = dd;
        out.bs = lbTowerBonus(dd, lbTowerMult(sv));
        out.ready = true;
      }
    }
  }
  return out;
}
// 全部塔（排序：本页服务器孤岛优先 → 激活优先 → 天数降序）
function tcTowerRows(){
  var list = [];
  try{ list = (typeof lbMaintTribeTowers === 'function') ? lbMaintTribeTowers() : []; }catch(e){ list = []; }
  var rows = list.map(function(w){ return tcTowerCalc(w); });
  rows.sort(function(a, b){
    var sa = (a.sv === 'Isl') ? 0 : 1, sb = (b.sv === 'Isl') ? 0 : 1;
    if (sa !== sb) return sa - sb;
    if (a.active !== b.active) return a.active ? -1 : 1;
    return (b.days || 0) - (a.days || 0);
  });
  return rows;
}
// 当前页（孤岛）那条 —— 保留给其它模块调用
function tcTowerTame(){
  var rows = tcTowerRows();
  var cur = null;
  for (var i = 0; i < rows.length; i++){ if (rows[i].sv === 'Isl'){ cur = rows[i]; break; } }
  var out = { sv: 'Isl', active: false, pct: 0, days: 0, tribe: '', icon: '', ready: false, all: rows };
  if (!cur) return out;
  out.active = cur.active; out.days = cur.days; out.ready = cur.ready; out.tribe = cur.tribe;
  out.pct = (cur.bs && cur.bs.tame) ? cur.bs.tame : 0;
  out.icon = tcTowerIcon(cur.w && cur.w.cls);
  return out;
}
function tcTowerHtml(r){
  var el = document.getElementById('tcTower');
  if (!el) return;
  var rows = tcTowerRows();
  // 世界时钟：对「已激活但天数未知」的服各触发一次（TTL 3 分钟 + 按服记账，防 tcCalc 递归）
  var need = rows.filter(function(x){ return x.active && !x.ready && !LB._tcTwAsked[x.sv]; });
  if (need.length){
    need.forEach(function(x){ LB._tcTwAsked[x.sv] = 1; });
    var _i = 0;
    (function _next(){
      if (_i >= need.length){ try{ tcCalc(); }catch(e){} return; }
      var _sv = need[_i++].sv;
      try{ lbMaintTowerLoad(_sv, _next); }catch(e){ _next(); }
    })();
  }
  var cur = null;
  for (var k = 0; k < rows.length; k++){ if (rows[k].sv === 'Isl'){ cur = rows[k]; break; } }
  var _ico = tcTowerIcon(cur && cur.w ? cur.w.cls : '');
  var _stTxt, _stCls;
  if (!cur){ _stTxt = '此服无塔'; _stCls = 'tc-no'; }
  else if (!cur.active){ _stTxt = '无激活塔'; _stCls = 'tc-no'; }
  else if (!cur.ready){ _stTxt = '计算中'; _stCls = 'tc-ok'; }
  else { _stTxt = '+ ' + tcNum(cur.bs.tame) + '%'; _stCls = 'tc-ok'; }
  var h = '<div class="tc-own-r">'
        + (_ico ? ('<img src="' + _ico + '" referrerpolicy="no-referrer" onerror="lbImgRetry(this)">') : '')
        + '<span class="tc-own-n">' + tcZhEn('部落塔', 'Tribe Tower') + '</span>'
        // v5733（用户口径）：不显示所属部落
        + '<span class="' + _stCls + '">' + _stTxt + '</span></div>';
  var sp0 = lbTameSpeedEnsure() || 0;
  if (cur && cur.active && cur.ready && cur.bs && cur.bs.tame > 0 && sp0 > 0 && r && r.best){
    var r2 = null;
    try{ r2 = tcRows(sp0 * (1 + cur.bs.tame / 100)); }catch(e){ r2 = null; }
    if (r2 && r2.best){
      var b0 = r.best, b1 = r2.best;
      h += '<div class="tc-note">应用到正在驯服的生物 —— 实际倍率 <b>' + tcNum(sp0) + '×</b> × (1 + '
         + tcNum(cur.bs.tame) + '%) = <b style="color:#4ade80">'
         + (Math.round(sp0 * (1 + cur.bs.tame / 100) * 100) / 100) + '×</b></div>';
      h += '<table class="tc-tb" style="margin-top:8px"><thead><tr><th>项目</th>'
         + '<th class="num">无塔加成</th><th class="num">有塔 +' + tcNum(cur.bs.tame) + '%</th><th class="num">少/多</th></tr></thead><tbody>'
         + '<tr><td class="ov-k">' + lbAttr(b0.zh) + ' 口数</td>'
         + '<td class="num">×' + tcNum(b0.qty) + '</td>'
         + '<td class="num" style="color:#4ade80">×' + tcNum(b1.qty) + '</td>'
         + '<td class="num">-' + tcNum(Math.max(0, b0.qty - b1.qty)) + '</td></tr>'
         + '<tr><td class="ov-k">驯服时间</td>'
         + '<td class="num">' + tcDur(b0.time) + '</td>'
         + '<td class="num" style="color:#4ade80">' + tcDur(b1.time) + '</td>'
         + '<td class="num">-' + tcDur(Math.max(0, b0.time - b1.time)) + '</td></tr>'
         + '<tr><td class="ov-k">驯服效率</td>'
         + '<td class="num">' + tcPct(b0.eff) + '%</td>'
         + '<td class="num" style="color:#4ade80">' + tcPct(b1.eff) + '%</td>'
         + '<td class="num">+' + tcPct(Math.max(0, b1.eff - b0.eff)) + '%</td></tr>'
         + '<tr><td class="ov-k">驯服后等级</td>'
         + '<td class="num">' + tcNum(b0.tlv) + '</td>'
         + '<td class="num" style="color:#4ade80">' + tcNum(b1.tlv) + '</td>'
         + '<td class="num">+' + tcNum(Math.max(0, b1.tlv - b0.tlv)) + '</td></tr>'
         + '</tbody></table>';
    }
  } else if (cur && cur.active && !cur.ready){
    h += '<div class="tc-note">部落塔已激活，正在读取世界时钟以计算天数…</div>';
  } else if (cur && cur.active && cur.ready && cur.bs && !(cur.bs.tame > 0)){
    h += '<div class="tc-note">部落塔已激活，但激活时长不足 1 天，加成尚未生效（每真实天 +1%）。</div>';
  } else {
    h += '<div class="tc-note">没有<b>你部落</b>的激活部落塔 —— 激活后驯服速度最高 <b>+40%</b>。</div>';
  }
  if (rows.length){
    var _svName = function(svv){ try{ return (typeof LB.servName === 'function' && LB.servName(svv)) || svv; }catch(e){ return svv; } };
    var _actN = 0; try{ _actN = rows.filter(function(x){ return x.active; }).length; }catch(e2){ _actN = 0; }
    // v5726（用户口径·默认折叠）：折叠按钮复用「物品 wiki 获取」补给箱同款（details.lb-cfg-fold + .lb-fold-tri 三角）
    h += '<details class="lb-cfg-fold" style="margin-top:10px">'
       + '<summary class="lb-cfg-fold-sum" style="cursor:pointer;list-style:none;font-size:11px;color:#ccc;background:#1a1a24;border:1px solid #2a2a3a;border-radius:6px;padding:4px 8px;display:flex;align-items:center;gap:6px;flex-wrap:wrap">'
       + '<span class="lb-fold-tri"></span>'
       + '<span style="color:#e2e8f0;font-weight:600;font-size:12px">你的全部部落塔</span>'
       + '<span style="color:#64748b">' + rows.length + ' 座 · ' + _actN + ' 座激活</span>'
       + '</summary>'
       + '<div style="display:flex;flex-direction:column;gap:5px;margin-top:6px">';
    rows.forEach(function(x){
      var ic2 = tcTowerIcon(x.w && x.w.cls);
      var dtxt = x.ready ? (x.days >= 100 ? String(Math.floor(x.days)) : String(Math.round(x.days * 10) / 10)) : '';
      h += '<div style="display:flex;align-items:center;gap:7px;background:#ffffff05;border:1px solid #ffffff0d;border-radius:6px;padding:5px 9px;font-size:12px;flex-wrap:wrap">'
         + (ic2 ? ('<img src="' + ic2 + '" style="width:20px;height:20px;object-fit:contain;flex-shrink:0" onerror="lbImgRetry(this)">') : '')
         + '<span style="color:#94a3b8;font-size:11px;flex:0 0 auto">' + lbAttr(_svName(x.sv)) + '</span>'
         + '<span style="color:#e2e8f0;flex:0 0 auto">' + lbAttr(x.tribe || '（未知部落）') + '</span>'
         + '<span style="flex:1;min-width:6px"></span>'
         + (x.active
             ? (x.ready
                 ? ('<span style="color:#4ade80;font-size:11px">激活 ' + dtxt + ' 天</span>'
                    + '<span style="color:#a78bfa;font-size:11px;margin-left:6px">驯服 +' + tcNum(x.bs.tame) + '%</span>'
                    + '<span style="color:#38bdf8;font-size:11px;margin-left:6px">经验 +' + tcNum(x.bs.xp) + '%</span>'
                    + '<span style="color:#f59e0b;font-size:11px;margin-left:6px">元素 +' + tcNum(x.bs.elem) + '%</span>')
                 : '<span style="color:#f59e0b;font-size:11px">激活中 · 天数读取中</span>')
             : '<span style="color:#64748b;font-size:11px">未激活</span>')
         + '</div>';
    });
    h += '</div></details>';
  } else {
    h += '<div class="tc-note" style="margin-top:8px">当前角色名下没有部落塔。</div>';
  }
  h += '<details class="lb-cfg-fold" style="margin-top:8px">'
     + '<summary class="lb-cfg-fold-sum" style="cursor:pointer;list-style:none;font-size:11px;color:#ccc;background:#1a1a24;border:1px solid #2a2a3a;border-radius:6px;padding:4px 8px;display:flex;align-items:center;gap:6px;flex-wrap:wrap">'
     + '<span class="lb-fold-tri"></span>'
     + '<span style="color:#e2e8f0;font-weight:600;font-size:12px">说明</span>'
     + '<span style="color:#64748b">加成规则 · 生效条件</span>'
     + '</summary>'
     + '<ul class="ov-tips" style="margin-top:6px">'
     + '<li>每<b>真实天</b> +1%，<b>20 天封顶 +20%</b>；本站倍率 ×2 ⇒ 驯服/经验最高 <b>+40%</b>，元素每 30 天 +6%×2。</li>'
     + '<li>只对<b>塔所属部落的成员</b>生效 —— 别人部落的塔对你无效。</li>'
     + '<li>需塔处于<b>激活中</b>（放入元素并启动）；停用后加成归零。</li>'
     + '</ul></details>';
  el.innerHTML = h;
}
function tcElixirHtml(r){
  var own = tcElixirOwn(), _ic = '';
  try{ _ic = lbWikiResIcon('血之灵药') || ''; }catch(e){ _ic = ''; }
  var _wE = ''; try{ _wE = tcItemWhereHtml('血之灵药'); }catch(e){ _wE = ''; }
  var h = '<div class="tc-own-r"' + tcPickAttr('血之灵药') + tcWhereWrap(_wE) + '>'
    + (_ic ? ('<img src="' + _ic + '" referrerpolicy="no-referrer" onerror="lbImgRetry(this)">')
           : '')
    + '<span class="tc-own-n">' + tcZhEn('血之灵药', 'Sanguine Elixir') + '</span>'
    + '<span class="tc-own-q">我有 <b style="color:#e2e8f0">' + own + '</b> 个</span>'
    + '<span class="' + (own > 0 ? 'tc-ok' : 'tc-no') + '">'
    + (own > 0 ? (tcIco('check') + '可用') : (tcIco('close') + '暂无库存')) + '</span>'
    + _wE + '</div>';
  if (r && r.best && (+r.best.aff || 0) > 0 && r.A > 0){
    var b = r.best, aff = +b.aff || 0, sp = 0;
    try{ sp = lbTameSpeedEnsure() || 0; }catch(e){ sp = 0; }
    var ineff = 1;
    try{ ineff = +(((TAME[CUR] || {}).setup || {}).ineff) || 1; }catch(e){ ineff = 1; }
    if (sp > 0 && aff > 0){
      var A2 = r.A * 0.7;
      var qty2 = Math.ceil(A2 / (aff * 4 * sp));
      var time2 = (qty2 > 0 && b.itv > 0) ? Math.floor(qty2 * b.itv + 1) : 0;
      var eff2 = (qty2 > 0) ? (1 / (1 + ineff * qty2 / (aff * 4))) * 100 : 0;
      var plus2 = Math.floor(r.lv * eff2 / 100 * 0.5);
      // v5709（用户口径）：口数已够（灵药不减少口数）⇒ **不渲染对比表格**，只留一句说明
      if (qty2 >= b.qty) {
        h += '<div class="tc-note">本档只需 ' + b.qty + ' 口，灵药不减少口数（进度已够，喂满即完成）。</div>';
      } else {
        h += '<table class="tc-tb" style="margin-top:8px"><thead><tr><th>项目</th>'
           + '<th class="num">不用灵药</th><th class="num">用 1 个后</th><th class="num">少/多</th></tr></thead><tbody>'
           + '<tr><td class="ov-k">' + b.zh + ' 口数</td>'
           + '<td class="num">×' + tcNum(b.qty) + '</td>'
           + '<td class="num" style="color:#4ade80">×' + tcNum(qty2) + '</td>'
           + '<td class="num">-' + tcNum(Math.max(0, b.qty - qty2)) + '</td></tr>'
           + '<tr><td class="ov-k">驯服时间</td>'
           + '<td class="num">' + tcDur(b.time) + '</td>'
           + '<td class="num" style="color:#4ade80">' + tcDur(time2) + '</td>'
           + '<td class="num">-' + tcDur(Math.max(0, b.time - time2)) + '</td></tr>'
           + '<tr><td class="ov-k">驯服效率</td>'
           + '<td class="num">' + tcPct(b.eff) + '%</td>'
           + '<td class="num" style="color:#4ade80">' + tcPct(eff2) + '%</td>'
           + '<td class="num">+' + tcPct(Math.max(0, eff2 - b.eff)) + '%</td></tr>'
           + '<tr><td class="ov-k">驯服后等级</td>'
           + '<td class="num">' + tcNum(b.tlv) + '</td>'
           + '<td class="num" style="color:#4ade80">' + tcNum(r.lv + plus2) + '</td>'
           + '<td class="num">+' + tcNum(Math.max(0, plus2 - b.plus)) + '</td></tr>'
           + '</tbody></table>';
      }
    }
  }
  h += '<details class="lb-cfg-fold" style="margin-top:8px">'
    + '<summary class="lb-cfg-fold-sum" style="cursor:pointer;list-style:none;font-size:11px;color:#ccc;background:#1a1a24;border:1px solid #2a2a3a;border-radius:6px;padding:4px 8px;display:flex;align-items:center;gap:6px;flex-wrap:wrap">'
    + '<span class="lb-fold-tri"></span>'
    + '<span style="color:#e2e8f0;font-weight:600;font-size:12px">说明</span>'
    + '<span style="color:#64748b">效果 · 用法 · 腐坏 · 配方</span>'
    + '</summary>'
    + '<ul class="ov-tips" style="margin-top:6px">'
    + '<li>对正在驯服的生物用一次，驯服进度立即 <b>+30%</b>（对婴儿则是留痕 +30%）。</li>'
    + '<li>每只生物<b>限用一次</b> —— 打醒再打晕也不能再用。</li>'
    + '<li>腐坏 <b>4 小时</b>，放背包或保鲜箱都无法延长。</li>'
    + '<li>用法：放快捷栏，走到生物跟前<b>看着它</b>使用；配方 <b>200 × 血袋</b>，制作 5 秒。</li>'
    + '</ul></details>';
  var el = document.getElementById('tcElixir');
  if (el) el.innerHTML = h;
}

function tcCalc(){
  var r = tcRows();
  if(!r){
    var _bb = document.getElementById('tcTiles');
    if(_bb) _bb.innerHTML = '<div style="padding:10px 0;color:#f59e0b;font-size:12.5px">'
      + '正在读取孤岛服驯服倍率…取到后自动重算。</div>';
    lbTameSpeedEnsure(function(){ try { tcCalc(); } catch(e) {} });
    return;
  }
  var b = r.best;
  // v72k：该物种食物清单尚未收录（diet 为空）→ 友好降级，不抛错
  if (!b) {
    // v109：wiki 已给出食物名（TAME.dietZhList），只是本项目 FOODS 表无这些食物的效率数据
    //   → 直接列出清单，不再误报"尚未收录"
    var _dl = (((typeof TAME !== 'undefined' && TAME) ? TAME[CUR] : null) || {}).dietZhList || [];
    var _tb = document.getElementById('tcTiles');
    if (_tb) {
      var _tf = (((typeof TAME !== 'undefined' && TAME) ? TAME[CUR] : null) || {}).wikiFoods || [];
      // v118：表格放 #tcWikiFoods（tc-tiles 外面），tcTiles 里只放一行短提示
      var _box = document.getElementById('tcWikiFoods');
      var _put = function(html){
        if (_box) { _box.innerHTML = html; if (_tb) _tb.innerHTML = ''; }
        else if (_tb) { _tb.innerHTML = html; }   // 兜底：容器不存在时退回原位置
      };
      if (_tf.length) {
        // v114：wiki 自己给的口数/时间/等级（后端从 h2「驯服」段的 li 解析）→ 直接出表
        _put('<table class="tc-tb"><thead><tr><th>食物</th><th>口数</th>'
          + '<th>驯服时间</th><th>驯服后等级</th></tr></thead><tbody>'
          + _tf.map(function(x){
              return '<tr><th>' + tcGhChip(x.zh, '', x.best ? '最佳' : '', true) + '</th>'
                + '<td class="num">×' + (x.qty || '-') + '</td>'
                + '<td class="num">' + (x.dur || '-') + '</td>'
                + '<td class="num">' + (x.lvl ? ('+' + x.lvl) : '-') + '</td></tr>';
            }).join('') + '</tbody></table>'
          + '<div class="tc-adv" style="margin-top:8px">口数 / 时间 / 驯服后等级为该物种的标准值；'
          + '食物效率数据暂缺，故未按目标等级重算。</div>');
      } else if (_dl.length) {
        _put('<div style="display:flex;flex-wrap:wrap;gap:6px">'
          + _dl.map(function(zh){ return tcGhChip(zh, '', '', true); }).join('')
          + '</div><div class="tc-adv" style="margin-top:8px">驯服食物：<b>'
          + _dl.map(function(zh){ return lbWikiZhName(zh) || zh; }).join('</b> · <b>') + '</b>。效率 / 口数数据暂缺，故不计算耗量与时间。</div>');
      } else {
        // v264：区分「本就不能驯服」与「确实未收录」，不再一律报"尚未收录"
        var _tinf = (((typeof TAME !== 'undefined' && TAME) ? TAME[CUR] : null) || {});
        var _tintro = ' ' + ((_tinf.tameIntro || []).join(' ')) + ' ';
        if (/无法驯服|不能驯服|不可驯服/.test(_tintro)){
          _tb.innerHTML = '<div class="tc-adv">该物种<b>无法驯服</b>'
            + '（首领 / 特殊生物），不需要驯服食物。</div>';
        } else {
          _tb.innerHTML = '<div class="tc-adv">该物种的驯服食物尚未收录；'
            + '其余参数（眩晕值 / 饮食消耗 / 驯服效率）已就绪。</div>';
        }
      }
    }
    // v121：wiki 已有食物表时，② 给出最优食物需求，③ 说明是喂食驯服（不再误报"需要食物清单"）
    var _tf2 = (((typeof TAME !== 'undefined' && TAME) ? TAME[CUR] : null) || {}).wikiFoods || [];
    var _to = document.getElementById('tcOwn');
    if (_to) {
      if (_tf2.length) {
        var _bm = _tf2.filter(function(x){ return x.best; })[0] || _tf2[0];
        var _ownN = -1;
        try {
          var _cls = lbItemClsByZh(_bm.zh);
          if (_cls && typeof lbItemOwnCnt === 'function') _ownN = lbItemOwnCnt(_cls) | 0;
        } catch (eO) {}
        _to.innerHTML = '<div class="tc-adv">wiki 最优食物：<b>' + _bm.zh + '</b>，需 <b>×' + (_bm.qty || '-')
          + '</b>；驯服时间约 <b>' + (_bm.dur || '-') + '</b>。'
          + (_ownN >= 0 ? ('我的库存 <b>' + _ownN + '</b> 个' + (_ownN >= (_bm.qty || 0) ? '（够）' : '（不足）')) : '')
          + '</div>';
      } else {
        _to.innerHTML = '<div class="tc-adv">库存对比需要食物清单，暂不可用。</div>';
      }
    }
    var _tt = document.getElementById('tcTool');
    if (_tt) {
      if (_tf2.length) {
        _tt.innerHTML = '<div class="tc-adv">该物种通过<b>喂食</b>驯服（wiki 已给出所需口数与时间），'
          + '不需要击晕武器 / 麻醉弹药，故此处不推荐武器组合。</div>';
      } else {
        _tt.innerHTML = '<div class="tc-adv">驯服工具推荐需要食物清单，暂不可用。</div>';
      }
    }
    var _ta = document.getElementById('tcAdv');
    if (_ta) _ta.innerHTML = '已知参数：所需爱意值 <b>' + (function(){ try { return tcNum((TAME[CUR]||{}).setup.req); } catch(e){ return '-'; } })()
      + '</b>，爱意值每级递增 <b>' + (function(){ try { return tcNum((TAME[CUR]||{}).setup.per_level); } catch(e){ return '-'; } })()
      + '</b>，驯服不效率 <b>' + (function(){ try { return tcPct((TAME[CUR]||{}).setup.ineff); } catch(e){ return '-'; } })() + '%</b>。';
    tcElixirHtml(null);
    return;
  }
  var tile = tcTile;
  // v5730（用户口径）：最优食物 + 需要数量 合并为一张卡
  // v5732（用户口径）：副行内容**各自另起一行**（不是自动折行）
  var h = tile('最优食物', b.zh + ' ×' + tcNum(b.qty),
               '效率 ' + tcPct(b.eff) + '%<br>喂食间隔 ' + tcDur(b.itv), true)
        + tile('驯服时间', tcDur(b.time), '共 ' + b.qty + ' 口')
        // v5736（用户口径）：「眩晕值」+「需补麻醉药」合并为一张；「驯服后等级」+「升级后最高」合并为一张（6 张 -> 4 张）
        + tile('眩晕值 · 麻醉药', tcNum(r.torpor),
               '满晕 · 每秒 -' + (Math.round(r.wakeRate * 100) / 100)
               + '<br>' + tcDur(r.torpor / (r.wakeRate || 1)) + '后醒来'
               + '<br>' + (r.narc > 0
                   ? ('需补 ≈' + tcNum(r.narc) + ' 支（缺 ' + tcNum(r.wakeTotal - r.torpor) + '）')
                   : '麻醉药无需补充'),
               r.narc > 0)
        + tile('驯服后等级', String(b.tlv),
               '+' + b.plus + '（野生 ' + r.lv + '）'
               + '<br>最高 ' + (b.tlv + Math.floor(r.lv * 73 / 150)) + '（再 +' + Math.floor(r.lv * 73 / 150) + '）');
  document.getElementById('tcTiles').innerHTML = h;

  // ② 我的库存
  var own = '';
  var addOwn = function(en, name, need, have, icon, pickZh){
    var ok = have >= need;
    var _w = ''; try{ _w = tcItemWhereHtml(pickZh || ''); }catch(e){ _w = ''; }
    own += '<div class="tc-own-r"' + tcPickAttr(pickZh || '') + tcWhereWrap(_w) + '>' + tcIconHtml(en, icon)
      + '<span class="tc-own-n">' + name + '</span>'
      + '<span class="tc-own-q">需要 <b style="color:#e2e8f0">' + tcNum(need) + '</b> · 我有 ' + tcNum(have) + '</span>'
      + '<span class="' + (ok ? 'tc-ok' : 'tc-no') + '">' + (ok ? tcIco('check') + '够（余 ' + tcNum(have - need) + '）' : tcIco('close') + '缺 ' + tcNum(need - have)) + '</span>'
      + _w + '</div>';
  };
  addOwn(b.en, tcZhEn(b.zh, b.en), b.qty, b.own, b.icon, b.zh);
  // v5733（用户口径）：食物对照折叠块挂在「最优食物行」下方（位于麻醉药等非驯服度项之上）
  own += '<div id="tcFoodFold"></div>';
  if(r.narc > 0){
    addOwn('Narcotic', tcZhEn('麻醉药（驯服中）', 'Narcotic'), r.narc, lbTameOwn('麻醉药'), lbWikiIcCls(lbItemClsByZh('麻醉药')), '麻醉药');
  } else {
    var _wN = ''; try{ _wN = tcItemWhereHtml('麻醉药'); }catch(e2){ _wN = ''; }
    own += '<div class="tc-own-r"' + tcPickAttr('麻醉药') + tcWhereWrap(_wN) + '><img src="' + lbWikiResIcon('麻醉药') + '" referrerpolicy="no-referrer" onerror="lbImgRetry(this)">'
      + '<span class="tc-own-n">' + tcZhEn('麻醉药', 'Narcotic') + '</span>'
      + '<span class="tc-own-q">满晕 ' + tcNum(r.torpor) + ' · 驯服期 -' + tcNum(r.wakeTotal) + '</span>'
      + '<span class="tc-ok">' + tcIco('check') + '无需补充</span>'
      + _wN + '</div>';
  }
  // v5733（用户口径）：不显示「（替代）」食物行
  document.getElementById('tcOwn').innerHTML = own;
  document.getElementById('tcTool').innerHTML = tcToolsHtml(r);

  // ③ 建议
  var adv = '';
  if(r.enoughAll){
    adv += '<div>✅ <b>' + b.zh + '</b> 库存充足（需 ' + tcNum(b.qty) + '，我有 ' + tcNum(b.own) + '）—— 可直接开驯。</div>';
  } else {
    adv += '<div class="warn">⚠️ 最优食物 <b>' + b.zh + '</b> 库存不足：需 ' + tcNum(b.qty) + '，我有 ' + tcNum(b.own) + '，<b>缺 ' + tcNum(Math.max(0, b.qty - b.own)) + '</b>。</div>';
  }
  if(r.narc > 0){
    var _nO = lbTameOwn('麻醉药');
    adv += '<div>· 麻醉药：驯服期间需补 <b>' + tcNum(r.narc) + ' 支</b>，我有 ' + tcNum(_nO)
        + (r.narc > _nO ? '，<b class="warn">缺 ' + tcNum(r.narc - _nO) + '</b>' : '，<b>够</b>') + '。</div>';
  } else {
    adv += '<div>· 麻醉药：<b>全程无需补充</b> —— 眩晕值打满时是 ' + tcNum(r.torpor) + '，' + tcDur(b.time)
        + ' 里只掉 ' + tcNum(r.wakeTotal) + '，还剩 ' + tcNum(r.torpor - r.wakeTotal) + '，不会中途醒来。</div>';
  }
  // v5738（用户口径）：删除「击晕阶段…麻醉镖 ≈N 发 / 麻醉药 ≈N 支」——
  //   TC_NARC / TC_DART 全项目无权威源、已置 0 ⇒ 恒显示「≈0」，属假数字；
  //   而「④ 驯服工具」已按武器库存给出精确弹药数（发数 / 总伤害 / 够训几只），此处重复且误导。
  adv += '<div>· 时间：约 <b>' + tcDur(b.time) + '</b>（' + b.qty + ' 口 × ' + tcDur(b.itv) + '）；驯服后 <b>' + b.tlv + ' 级</b>（+' + b.plus + '）。</div>';
  // v5728（用户口径）：「同种生物」建议无意义，整段移除
  document.getElementById('tcAdv').innerHTML = adv;

  // 食物表
  var tb = '<thead><tr><th>食物</th><th style="text-align:right">数量</th><th style="text-align:right">驯服时间</th>'
         + '<th style="text-align:right">效率</th><th style="text-align:right">喂食间隔</th><th style="text-align:right">我有</th><th>状态</th></tr></thead><tbody>';
  r.list.forEach(function(x){
    var isBest = (x.en === b.en);
    var ok = x.own >= x.qty;
    tb += '<tr class="' + (isBest ? 'on' : '') + '">'
      // v5729（用户口径）：「食物对照」表内无需点位面包屑 —— 整表只看食物/数量/时间/效率
      + '<td' + tcPickAttr(x.zh) + '>' + tcIconHtml(x.en, x.icon) + tcZhEn(x.zh, x.en) + '</td>'
      + '<td class="num">×' + tcNum(x.qty) + '</td>'
      + '<td class="num">' + tcDur(x.time) + '</td>'
      + '<td class="num">' + tcPct(x.eff) + '%</td>'
      + '<td class="num">' + tcDur(x.itv) + '</td>'
      + '<td class="num">' + tcNum(x.own) + '</td>'
      + '<td class="' + (ok ? 'tc-ok' : 'tc-no') + '">' + (ok ? tcIco('check') + '够' : tcIco('close') + '缺 ' + tcNum(x.qty - x.own)) + '</td></tr>';
  });
  // v5733（用户口径）：食物对照整块折叠，挂到「③ 你现在有多少」最优食物行下方；默认收起
  var _fdEl = document.getElementById('tcFoodFold');
  if (_fdEl){
    var _sumSty = 'cursor:pointer;list-style:none;font-size:11px;color:#ccc;background:#1a1a24;border:1px solid #2a2a3a;border-radius:6px;padding:4px 8px;display:flex;align-items:center;gap:6px;flex-wrap:wrap';
    _fdEl.innerHTML = '<details class="lb-cfg-fold" style="margin:2px 0 0">'
      + '<summary class="lb-cfg-fold-sum" style="' + _sumSty + '">'
      + '<span class="lb-fold-tri"></span>'
      + '<span style="color:#e2e8f0;font-weight:600;font-size:12px">食物对照</span>'
      + '<span style="color:#64748b">全部 ' + ((r.list || []).length) + ' 种 · 按我的库存标记</span>'
      + '</summary>'
      + '<div style="max-height:340px;overflow:auto;border:1px solid #22222e;border-radius:8px;margin-top:6px">'
      + '<table class="tc-tb" id="tcFood"></table></div></details>';
  }
  var _tfEl = document.getElementById('tcFood');
  if (_tfEl) _tfEl.innerHTML = tb + '</tbody>';

  // v5716：部落塔（驯服速度加成 + 对比）
  tcTowerHtml(r);
  // v5700：血之灵药（库存 + 使用前后对比）
  tcElixirHtml(r);
}

/* 第二批新增数据块（原写法 var X = WIKI_DEX.X，由 lbWikiBind2 赋值）*/
var GATHER = null, HARVEST = null;

function lbWikiBind2(){
  var d = LB_WIKI.data;
  if (!d) return;
  GATHER = d.GATHER || {};
  HARVEST = d.HARVEST || {};
}

/* ===== BREED_MULT（v130）=====
   v125 前：var BREED_MULT = { mating:0.25, hatch:6, mature:6, cuddle:0.15, layEgg:1, imprint:3 }（硬编码）
   v130：一律实读孤岛服 Game.ini（/api/cfg_rules?server=Isl&file=GAME）
         0 = 尚未取到（界面显示「读取中」，不编数字） */
var BREED_MULT = { mating:0, hatch:0, mature:0, cuddle:0, layEgg:0, imprint:0 };
var BREED_MULT_SRC = '孤岛服实际配置';
var LB_BREED_CFG_TRIED = false;
/* v132：改名避免与项目全局冲突 —— 项目的 LB_BREED_KEYS（L26605 繁育属性键）/ lbBreedPick（L43056）不可占用 */
var LB_WIKI_BREED_KEYS = [
  ['mating',  'MatingIntervalMultiplier'],
  ['hatch',   'EggHatchSpeedMultiplier'],
  ['mature',  'BabyMatureSpeedMultiplier'],
  ['cuddle',  'BabyCuddleIntervalMultiplier'],
  ['imprint', 'BabyImprintAmountMultiplier'],
  ['layEgg',  'LayEggIntervalMultiplier']
];
function lbWikiBreedPick(doc){
  var got = 0;
  for (var i = 0; i < LB_WIKI_BREED_KEYS.length; i++){
    var v = lbCfgPickVal(doc, LB_WIKI_BREED_KEYS[i][1]);
    if (v !== null && v > 0){ BREED_MULT[LB_WIKI_BREED_KEYS[i][0]] = v; got++; }
  }
  return got;
}
function lbBreedMultSync(){
  if (BREED_MULT.hatch > 0) return BREED_MULT.hatch;
  var c = null;
  try { c = (typeof lbCfgCacheGet === 'function') ? lbCfgCacheGet('Isl', 'GAME') : null; } catch(e) {}
  if (lbWikiBreedPick(c && c.doc) > 0) BREED_MULT_SRC = '孤岛服实际配置';
  return BREED_MULT.hatch;
}
function lbBreedMultEnsure(cb){
  if (BREED_MULT.hatch > 0){ if (cb) { try { cb(); } catch(e) {} } return BREED_MULT.hatch; }
  lbBreedMultSync();
  if (BREED_MULT.hatch > 0){ if (cb) { try { cb(); } catch(e) {} } return BREED_MULT.hatch; }
  if (!LB_BREED_CFG_TRIED && typeof lbCfgFetchOne === 'function'){
    LB_BREED_CFG_TRIED = true;
    try {
      lbCfgFetchOne('Isl', 'GAME').then(function(full){
        if (!full || !full.items) return;
        try { lbCfgCachePut('Isl', 'GAME', full); } catch(e){}
        if (lbWikiBreedPick(full) > 0){
          BREED_MULT_SRC = '孤岛服实际配置';
          if (cb) { try { cb(); } catch(e) {} }
        }
      }).catch(function(){});
    } catch(e){}
  }
  return BREED_MULT.hatch;
}

/* ===== BREED_BASE（游戏默认基准，非服务器倍率）===== */
var BREED_BASE = { matingMinH:18, matingMaxH:48, cuddleH:8 };

/* ===== tcGhIco ===== */
function tcGhIco(url, sz){
  if(!url) return '';
  return '<img src="' + lbWikiIc(url) + '" style="width:' + (sz||16) + 'px;height:' + (sz||16) + 'px;object-fit:contain;vertical-align:-3px;margin-right:4px" onerror="this.style.display=\'none\'">';
}

/* ===== tcGhChip ===== */
function tcGhChip(zh, ic, tail, noWhere, icoSz, right){
  // v52：用正式项目的 .lb-hf-chip（不再自编圆角矩形）
  // v130：文字 + 图标全走项目表（lbWikiZhName / lbWikiResIc），不再直出 wiki 原名
  // v5728（用户口径）：noWhere=true 时不显示点位面包屑（食物对照用）
  // v5790（用户口径「图标放大到 24，左对齐的信息包括图标都要垂直居中」）：
  //   新增第 5 参 icoSz —— 独占一行的卡片传 24（chip 同步抬高、align-content:center 整体居中）；
  //   并排小 chip 不传，保持 16px / 28px 原状。
  var _nm = lbWikiZhName(zh) || zh;
  var _u = lbWikiResIcon(zh) || lbWikiResIcon(_nm);     // v147：只走项目链，ic 参数已废弃（保留兼容但不使用）
  var _isz = icoSz || 16, _big = (_isz > 16);
  /* v5792（用户口径「采集 中 卡片的面包屑不用另起一行，同行右对齐垂直居中」）：
     大图标卡（独占一行）走 tcItemWhereHtml 的 inlineMode（v5726 已有）——
     面包屑 margin-left:auto 右推、与图标/名称/数值同一行，靠 align-items:center 垂直居中；
     并排小 chip（掉落物 / 束缚方式 / 驯服食物）仍用另起一行版，避免挤成一条。 */
  var _w = ''; if (!noWhere){ try{ _w = tcItemWhereHtml(_nm, !!_big); }catch(e){ _w = ''; } }
  var _mh = _big ? 44 : 28;
  var _pd = _big ? '6px 10px' : '4px 8px';
  var _st = '';
  /* v5801（用户口径「右侧 2行 在没触发自动换行时 不允许撑高卡片；这两行在右侧要整体垂直居中」）：
     撤掉 v5797 的 flex-wrap:wrap（它让 right 独占一整行 ⇒ 卡片被撑高）；
     改为把「面包屑 + 节点产量」一起塞进 .tc-cap-rt 右侧竖排小列，
     两行总高约 33px < min-height 44px ⇒ 内容不换行时卡片高度保持不变。 */
  if (_big) _st = 'display:flex;flex-wrap:nowrap;align-items:center;height:auto;min-height:' + _mh + 'px;padding:' + _pd + ';overflow:visible';
  else if (_w) _st = 'flex-wrap:wrap;align-content:center;align-items:center;height:auto;min-height:' + _mh + 'px;padding:' + _pd + ';overflow:visible';
  return '<span class="lb-hf-chip"' + (_st ? (' style="' + _st + '"') : '') + tcPickAttr(_nm) + '>'
    + (_u ? tcGhIco(_u, _isz) : '') + '<span>' + _nm + '</span>'
    + (tail ? '<span style="color:#4ade80">' + tail + '</span>' : '')
    + (right ? ('<span class="tc-cap-rt">' + _w + right + '</span>') : _w)
    + '</span>';
}

/* ===== tcGhTile ===== */
function tcGhTile(k, v, sub){
  return '<div class="tc-tile"><div class="tc-tile-k">' + k + '</div>'
    + '<div class="tc-tile-v">' + v + '</div>'
    + (sub ? '<div class="tc-tile-s">' + sub + '</div>' : '') + '</div>';
}

/* ===== bdDur ===== */
function bdDur(v){
  if (typeof v !== 'number' || !v || v <= 0) return '';
  var h = Math.floor(v / 3600), m = Math.floor((v % 3600) / 60);
  if (h > 0) return h + '小时' + (m > 0 ? m + '分钟' : '整');
  return m + '分钟';
}

/* ===== bdText ===== */
function bdText(t){
  var b = BREED[CUR] || {};
  return String(t == null ? '' : t)
    .replace(/\{tMin\}/g, b.tMin == null ? '' : String(b.tMin))
    .replace(/\{tMax\}/g, b.tMax == null ? '' : String(b.tMax))
    .replace(/\{incText\}/g, bdDur(b.inc))
    .replace(/\{matText\}/g, bdDur(b.mat));
}

/* ===== renderGather ===== */
/* ===== v5796：采集加成卡片用的「该资源节点产量」查表 =====
   数据源 = 收割页 HARVEST[CUR].rawTables 里 group 含「资源节点」的那几张表。
   返回如「平均 26（低 8 / 高 44）」；查不到返回空串（由调用方写「无记录」）。 */
function lbHvNodeYieldOf(name){
  var d = (typeof HARVEST !== 'undefined' && HARVEST) ? HARVEST[CUR] : null;
  var tabs = (d && d.rawTables) || [];
  if (!tabs.length) return '';
  var want = '', raw = String(name || '').trim();
  if (!raw) return '';
  try { want = lbWikiZhName(raw) || raw; } catch (e0) { want = raw; }
  for (var i = 0; i < tabs.length; i++){
    var tb = tabs[i];
    if (!tb || Array.isArray(tb) || !tb.rows || !tb.rows.length) continue;
    if (String(tb.group || '').indexOf('\u8d44\u6e90\u8282\u70b9') < 0) continue;
    var tt = String(tb.title || ''), t2 = tt;
    try { t2 = lbWikiZhName(tt) || tt; } catch (e1) { t2 = tt; }
    if (t2 !== want) continue;
    var rows = tb.rows, head = rows[0] || [];
    var iL = head.indexOf('\u4f4e'), iA = head.indexOf('\u5e73\u5747'), iH = head.indexOf('\u9ad8');
    if (iL < 0) iL = 1; if (iA < 0) iA = 2; if (iH < 0) iH = 3;
    var cur = null, peak = null;
    for (var j = 1; j < rows.length; j++){
      var r = rows[j];
      if (!r || !r.length) continue;
      if (String(r[0] || '').indexOf('\u5cf0') >= 0) peak = r; else cur = cur || r;
    }
    var use = cur || peak;
    if (!use) return '';
    // v5797（用户口径「有数据的 节点产量 要让玩家能看得懂」）：
    //   旧文案「平均 26（低 8 / 高 44）· 峰值 8/26/44」玩家读不懂；
    //   改成「采 1 个资源点 ≈ N 个（最少 ~ 最多）」，峰值不同才追加一句。
    var s = '\u91c7 1 \u4e2a\u8d44\u6e90\u70b9 \u2248 ' + use[iA] + ' \u4e2a\uff08' + use[iL] + ' ~ ' + use[iH] + '\uff09';
    // v5799：比较时必须**跳过首列标签**（「当前」/「峰值」本身不同），
    //   否则两行数值一样也会被判为「不同」⇒ 多余的「拉满近战」。
    if (peak && cur && peak.slice(1).join('|') !== cur.slice(1).join('|'))
      s += ' \u00b7 \u62c9\u6ee1\u8fd1\u6218 \u2248 ' + peak[iA] + ' \u4e2a\uff08' + peak[iL] + ' ~ ' + peak[iH] + '\uff09';
    return s;
  }
  return '';
}

function renderGather(){
  var d = GATHER[CUR];
  // v109：该物种 HOME 可能没有 caps/nodes/nodeRes → 原来直接 .length 会抛
  //   「Cannot read properties of undefined (reading 'length')」把整个 tab 变报错页
  if (d) { d.caps = d.caps || []; d.nodes = d.nodes || []; d.nodeRes = d.nodeRes || []; }
  var _N = 0;
  var _H = function(t, em){ return tcHStr(_N++, t, em); };
  var h = '<div class="tc">';
  if(!d){
    h += '<div class="tc-sec"><div class="tc-hintb">该物种未收录采集数据。</div></div></div>';
    document.getElementById('lbWikiBody').innerHTML = h;
    return;
  }
  // \u63cf\u8ff0\u524d\u7f6e\uff08\u5173\u4e8e\u91c7\u96c6\uff09
  // v95：后端实际给的是 GATHER[CUR].intro（数组），原来只认 d.about → 文案全丢
  // v5780（用户口径「置顶正文都应该 AI 整理」）：AI 结果优先。
  //   gatherIntro 此前**从未纳入 AI 整理链路**（前端 lbWtCollect 没收、后端 _WT_BLOCKS 没列），
  //   v5780 起双向补齐；在整理出内容之前回退原文（回退分支不带 .tc-ai ⇒ 不参与标记）
  var _gatherAi = lbWtPick('gatherIntro', null);
  if (_gatherAi && _gatherAi.length) h += wikiIntroHtml(_gatherAi);
  else if(d.about) h += '<div class="tc-intro"><p>' + d.about + '</p></div>';
  else h += wikiIntroHtml(wikiTabIntro('gatherIntro', d.intro));
  // \u5fbd\u7ae0\uff08\u63cf\u8ff0\u4e4b\u540e\uff0c\u4e0e\u4f0f\u6b96/\u9a6f\u670d\u4e00\u81f4\uff09
  var amt = (d.params && d.params.amtMult) ? d.params.amtMult : '1';
  h += '<div class="tc-top"><span class="tc-badge">' + (d.caps.length ? ('\u53ef\u91c7 ' + d.caps.length + ' \u79cd') : '\u65e0\u91c7\u96c6\u52a0\u6210') + '</span>'
     + '<span class="tc-badge2">\u91c7\u96c6\u91cf ' + amt + '\u00d7</span>'
     + (d.nodes.length ? '<span class="tc-badge2">\u8d44\u6e90\u8282\u70b9 ' + d.nodes.length + ' \u79cd</span>' : '')
     + '</div>';
  // \u2460 \u91c7\u96c6\u52a0\u6210
  var s1;
  if(d.caps.length){
    // v5788（用户口径「① 采集加成 的 物资卡片 独占一行」）：竖排、横向撑满，每张卡一行
    s1 = '<div style="display:flex;flex-direction:column;align-items:stretch;gap:6px">'
       + d.caps.map(function(c){
                      /* v5796：采集加成卡片标注该资源的资源点产量（数据源 = 收割页「资源节点产量」组）。
              v5797（用户口径）：① 查不到就**整行不显示**；
                                 ② 文案改「采 1 个资源点 ≈ N 个（最少 ~ 最多）」；
                                 ③ 放进卡片内、第二行、靠右（第 6 参 right）。 */
           var _nd = '';
           try { _nd = lbHvNodeYieldOf(c.zh); } catch (eND) { _nd = ''; }
           return tcGhChip(c.zh, '', c.mult ? (c.mult + '\u00d7') : '', false, 24,
                           _nd ? ('<span class="tc-cap-nd">' + _nd + '</span>') : '');
         }).join('')
       + '</div>';
  }else{
    s1 = '<div class="tc-hintb">该物种没有额外的资源采集加成。</div>';
  }
  h += '<div class="tc-sec"><div class="tc-grp">\u91c7\u96c6\u52a0\u6210<em>\u9a91\u4e58\u91c7\u96c6\u65f6\u7684\u989d\u5916\u500d\u7387</em></div>' + s1 + '</div>';   // v5797：去 2460
  /* v5796（用户口径「采集里的 ② 资源节点产量 也隐藏」）：整段删除。
     原实现里 d.nodes 恒为空（后端从没产出过 nodes/nodeRes，采集块 _wiki_parse_gather 已废弃），
     于是恒定走 d.noNode 分支，输出「该物种不采集岩石、树木、金属等资源节点」——
     把「数据缺失」当成了事实断言，与收割页的真实节点数据自相矛盾（根因见进度 54.51）。
     节点产量改为标注在「① 采集加成」每张卡片下方（见 lbHvNodeYieldOf）。 */
  // \u2462 \u6bcf\u4e2a\u8282\u70b9\u8d44\u6e90
  if(d.nodeRes.length){
    // v51\uff1a\u8868\u5934\u300c\u4f4e/\u5e73\u5747/\u9ad8\u300d\u8d34\u5de6\u3001\u300c\u5f53\u524d\u300d\u300c\u5cf0\u503c\u300d\u8d34\u53f3\n    //   \u26a0 th \u4e0d\u80fd\u76f4\u63a5\u7528 flex\uff08\u4f1a\u8ba9 table \u5217\u5bbd\u5854\u7f29\uff09\uff0c\u5fc5\u987b\u5185\u5c42 div \u505a\u5bf9\u9f50
    var _thc = 'display:flex;align-items:center;justify-content:space-between;gap:8px';
    var tb = '<thead><tr><th>\u8d44\u6e90</th><th>\u6bcf\u6b21\u63b7\u9ab0</th>'
      + '<th><div style="' + _thc + '"><span>\u4f4e/\u5e73\u5747/\u9ad8</span><span>\u5f53\u524d</span></div></th>'
      + '<th><div style="' + _thc + '"><span>\u4f4e/\u5e73\u5747/\u9ad8</span><span>\u5cf0\u503c</span></div></th>'
      + '</tr></thead><tbody>'
      + d.nodeRes.map(function(x){
          return '<tr><th>' + tcGhIco(lbWikiResIcon(x.zh), 16) + lbWikiZhName(x.zh) + '</th><td>' + x.roll + '%</td>'
            + '<td>' + x.cur[0] + ' / <b style="color:#e0e0e0">' + x.cur[1] + '</b> / ' + x.cur[2] + '</td>'
            + '<td>' + x.peak[0] + ' / <b style="color:#4ade80">' + x.peak[1] + '</b> / ' + x.peak[2] + '</td></tr>';
        }).join('') + '</tbody>';
    h += '<div class="tc-sec">' + _H('\u6bcf\u4e2a\u8282\u70b9\u8d44\u6e90')
       + '<table class="tc-tb">' + tb + '</table></div>';
  }
  // \u2463 \u91c7\u96c6\u53c2\u6570
  if(d.params && d.params.hp){
    var p = d.params;
    h += '<div class="tc-sec">' + _H('\u91c7\u96c6\u53c2\u6570', '\u8282\u70b9\u57fa\u7840\u503c') + '<div class="tc-tiles">'
      + tcGhTile('\u8282\u70b9\u751f\u547d\u503c', tcNum(p.hp), '\u57fa\u7840\u8010\u4e45')
      + tcGhTile('\u91c7\u96c6\u95f4\u9694', p.interval + 's', '\u6bcf\u6b21\u547d\u4e2d\u8017\u65f6')
      + tcGhTile('\u4f24\u5bb3\u500d\u7387', p.dmgMult + '\u00d7', '\u6b66\u5668\u4f24\u5bb3\u7cfb\u6570')
      + tcGhTile('\u91c7\u96c6\u91cf\u500d\u7387', p.amtMult + '\u00d7', '\u670d\u52a1\u5668\u91c7\u96c6\u500d\u7387')
      + tcGhTile('\u57fa\u7840\u4f24\u5bb3', p.baseDmg, '\u8be5\u8282\u70b9\u7c7b\u578b')
      + tcGhTile('\u57fa\u7840\u8fd1\u6218', p.baseMelee + '%', '\u91ce\u751f\u57fa\u51c6')
      + '</div></div>';
  }
  // v5788（用户口径「附件无需显示」）：底部「近战基准 100%…」附注整条删除
  h += '</div>';
  document.getElementById('lbWikiBody').innerHTML = h;
  tcMountIntro();
}

/* ===== v5795（用户口径「重新设计 收割 TAB 里面尽量改成卡片式」）=====
   后端给的是 {title, group, rows}（旧缓存为 [[rows],…]）。这里把「表」翻译成「卡片」：
     · 四列产量表（产量|低|平均|高 × 当前/峰值）→ 平均大数字 + 低·高 + 峰值行
     · 两列键值表（项目|数值）           → 平均大数字 + 键值小行（掷骰% / 近战区间 / 峰值）
   解析不了返回 null，由调用方回退成老表格渲染（绝不丢数据）。 */
function lbHvTableCard(tb, ti, titles){
  var old = Array.isArray(tb);
  var rows = old ? tb : ((tb && tb.rows) || []);
  if (!rows.length) return null;
  var o = {
    title: old ? ((titles || [])[ti + 2] || ('表 ' + (ti + 1)))
                : (String((tb && tb.title) || '') || ('表 ' + (ti + 1))),
    group: (!old && tb && tb.group) ? String(tb.group) : '',
    icon: '', big: '', bigLabel: '', mid: '', kvs: []
  };
  try { o.icon = lbWikiResIcon(o.title) || ''; } catch (eIC) { o.icon = ''; }
  var head = rows[0] || [], body = rows.slice(1);
  if (!body.length) return null;
  if (head.length >= 4){
    var iL = head.indexOf('低'), iA = head.indexOf('平均'), iH = head.indexOf('高');
    if (iL < 0) iL = 1; if (iA < 0) iA = 2; if (iH < 0) iH = 3;
    var cur = null, peak = null;
    body.forEach(function(r){
      if (!r || !r.length) return;
      if (String(r[0] || '').indexOf('峰') >= 0) peak = r; else cur = cur || r;
    });
    var use = cur || peak;
    if (!use) return null;
    o.big = (use[iA] != null && use[iA] !== '') ? String(use[iA]) : '—';
    o.bigLabel = '平均';
    o.mid = '低 ' + ((use[iL] != null && use[iL] !== '') ? use[iL] : '—')
          + ' · 高 ' + ((use[iH] != null && use[iH] !== '') ? use[iH] : '—');
    if (peak){
      var same = !!cur && String(peak.join('\u0001')) === String(cur.join('\u0001'));
      o.kvs.push(['峰值', same ? '同当前'
                            : (peak[iL] + ' / ' + peak[iA] + ' / ' + peak[iH])]);
    }
    return o;
  }
  body.forEach(function(r){
    if (!r || r.length < 2) return;
    var k = String(r[0] || ''), v = String(r[1] || '');
    if (!k) return;
    if (k === '平均'){ o.big = v; o.bigLabel = '平均'; return; }
    o.kvs.push([k, v]);
  });
  if (o.big === '' && !o.kvs.length) return null;
  return o;
}

/* ===== renderHarvest ===== */
function renderHarvest(){
  var d = HARVEST[CUR];
  // v109：同上，perRes/tools 可能不存在
  if (d) {
    d.perRes = d.perRes || []; d.tools = d.tools || {}; d.corpse = d.corpse || {};
    d.drops = d.drops || []; d.bound = d.bound || []; d.rawTables = d.rawTables || [];
    d.rawTitles = d.rawTitles || [];
  }
  var _N = 0;
  var _H = function(t, em){ return tcHStr(_N++, t, em); };
  var h = '<div class="tc">';
  if(!d){
    h += '<div class="tc-sec"><div class="tc-hintb">该物种未收录收割数据。</div></div></div>';
    document.getElementById('lbWikiBody').innerHTML = h;
    return;
  }
  // v95：前置文案（wiki 「掉落与采集资源」段）
  // v5781（用户口径「置顶正文都应该 AI 整理」）：AI 结果优先
  h += wikiIntroHtml(lbWtPick('harvestIntro', wikiTabIntro('harvestIntro')));
  // v72p：后端直出的原文表格 -> v5795 卡片视图
  if (d.rawTables && d.rawTables.length) {
    /* v5795（用户口径「重新设计 收割 TAB 里面尽量改成卡片式」）：23 张表平铺改成
       按 group 分组 + 每资源一张卡片；卡片解析失败则回退成老表格（不丢数据）。
       注意：卡片标题用 .tc-hv-nm，**不要**用 .tc-h —— lbWikiLayoutFix()（v5756）
       会把无序号 .tc-h 全部 display:none（v5794 就是踩了这个坑）。 */
    var _gOrder = [], _gMap = {};
    d.rawTables.forEach(function(tb, ti){
      var o = null;
      try { o = lbHvTableCard(tb, ti, d.rawTitles); } catch (eHC) { o = null; }
      if (!o) return;
      var gk = o.group || '';
      if (!_gMap[gk]){ _gMap[gk] = { name: gk, items: [] }; _gOrder.push(gk); }
      _gMap[gk].items.push(o);
    });
    if (_gOrder.length){
      var rh = '<div class="tc">';
      var _nRes = 0;
      _gOrder.forEach(function(gk){ _nRes += _gMap[gk].items.length; });
      rh += '<div class="tc-top"><span class="tc-badge">' + _nRes + ' 种资源</span>'
          + '<span class="tc-badge2">共 ' + d.rawTables.length + ' 组数据</span></div>';
      _gOrder.forEach(function(gk){
        var g = _gMap[gk];
        rh += '<div class="tc-grp">' + (g.name || '数据表') + '<em>近战 100% 基准</em></div>';
        rh += '<div class="tc-hv-grid">';
        g.items.forEach(function(o){
          var _nm = lbWikiZhName(o.title) || o.title;
          rh += '<div class="tc-hv"><div class="tc-hv-h">'
              + (o.icon ? tcGhIco(o.icon, 22) : '')
              + '<span class="tc-hv-nm">' + _nm + '</span></div>';
          if (o.big !== '') rh += '<div class="tc-hv-big">' + o.big + '<em>' + o.bigLabel + '</em></div>';
          if (o.mid) rh += '<div class="tc-hv-mid">' + o.mid + '</div>';
          if (o.kvs.length){
            rh += '<div class="tc-hv-kv">' + o.kvs.map(function(kv){
              return '<span><i>' + kv[0] + '</i><b>' + kv[1] + '</b></span>';
            }).join('') + '</div>';
          }
          rh += '</div>';
        });
        rh += '</div>';
      });
      rh += '</div>';
      document.getElementById('lbWikiBody').innerHTML = rh;
      return;
    }
    // 回退：卡片解析全失败 —— 保持 v5794 的表格渲染
    var rt = '<div class="tc">';
    rt += '<div class="tc-top"><span class="tc-badge">' + d.rawTables.length + ' 张数据表</span></div>';
    var _lastGrp = null;
    d.rawTables.forEach(function(tb, ti){
      var _old = Array.isArray(tb);
      var _rows = _old ? tb : ((tb && tb.rows) || []);
      if (!_rows.length) return;
      var _grp = (!_old && tb && tb.group) ? String(tb.group) : '';
      var _ttl = _old
        ? ((d.rawTitles || [])[ti + 2] || ('表 ' + (ti + 1)))
        : (String((tb && tb.title) || '') || ('表 ' + (ti + 1)));
      var rows = _rows.map(function(row, ri){
        var tag = ri === 0 ? 'th' : 'td';
        return '<tr>' + row.map(function(cell){
          return '<' + tag + (ri === 0 ? '' : ' class="num"') + '>' + cell + '</' + tag + '>';
        }).join('') + '</tr>';
      }).join('');
      if (_grp && _grp !== _lastGrp){
        _lastGrp = _grp;
        rt += '<div class="tc-grp">' + _grp + '<em>近战 100% 基准</em></div>';
      }
      rt += '<div class="tc-sec"><div class="tc-rh">' + _ttl + '</div>'
          + '<table class="tc-tb">' + rows + '</table></div>';
    });
    rt += '</div>';
    document.getElementById('lbWikiBody').innerHTML = rt;
    return;
  }
  var c = d.corpse || {};
  // \u5fbd\u7ae0
  h += '<div class="tc-top">'
     + '<span class="tc-badge">' + (c.hp ? ('\u5c38\u4f53 ' + tcNum(c.hp) + ' HP') : '\u65e0\u5c38\u4f53\u8bb0\u5f55') + '</span>'
     + (c.interval ? '<span class="tc-badge2">\u91c7\u96c6\u95f4\u9694 ' + c.interval + 's</span>' : '')
     + (c.rolls ? '<span class="tc-badge2">' + c.rolls + ' \u6b21\u63b7\u9ab0</span>' : '')
     + (c.hits ? '<span class="tc-badge2">' + c.hits + ' \u6b21\u547d\u4e2d</span>' : '')
     + '</div>';
  // \u2460 \u6bcf\u5177\u5c38\u4f53\u8d44\u6e90
  var s1;
  if(d.perRes.length){
    s1 = '<div class="tc-own">' + d.perRes.map(function(r){
      return '<div class="tc-own-r">'
        + '<span class="tc-own-n">' + tcGhIco(lbWikiResIcon(r.zh), 18) + lbWikiZhName(r.zh) + '</span>'
        + '<span class="tc-own-q">\u6bcf\u6b21\u63b7\u9ab0 ' + r.roll + '% \u00b7 \u8fd1\u6218 ' + r.range[0] + '-' + r.range[1]
        + ' \u00b7 \u5cf0\u503c ' + r.peakRange[0] + '-' + r.peakRange[1] + '</span>'
        + '<span class="tc-ok">\u5e73\u5747 ' + r.avg + '</span></div>';
    }).join('') + '</div>'
    + (c.peak ? '<div class="tc-adv" style="margin-top:8px">\u8fd1\u6218\u5cf0\u503c\uff1a' + c.peak + '</div>' : '');
  }else if(d.noRecord){
    s1 = '<div class="tc-hintb">暂无该物种的尸体采集记录（wiki 未收录）。下方工具对比仍按已记录数据给出。</div>';
  }else{
    s1 = '<div class="tc-hintb">无每具尸体资源数据。</div>';
  }
  h += '<div class="tc-sec">' + _H('\u6bcf\u5177\u5c38\u4f53\u8d44\u6e90', '\u8fd1\u6218 100% \u57fa\u51c6') + s1 + '</div>';
  // \u2461 \u5de5\u5177\u5bf9\u6bd4
  var tw = d.tools || {};
  if((tw.rows || []).length){
    var cols = tw.cols || ['\u9550', '\u65a7\u5934'];
    var t2 = '<thead><tr><th>\u8d44\u6e90</th>';
    cols.forEach(function(nm){ t2 += '<th>' + tcGhIco(lbWikiIcCls(lbItemClsByZh(nm)), 16) + lbWikiZhName(nm) + '</th>'; });
    t2 += '</tr></thead><tbody>';
    tw.rows.forEach(function(r){
      t2 += '<tr><th>' + tcGhIco(lbWikiResIcon(r.zh), 16) + lbWikiZhName(r.zh) + '</th>';
      r.cells.forEach(function(cc){
        t2 += '<td><b style="color:#e0e0e0">' + cc.avg + '</b> '
            + '<span style="color:#8b93a7;font-size:11px">' + cc.pct + '%</span> '
            + '<span style="color:#64748b;font-size:10px">\u7ea6' + cc.hits + '\u6b21</span></td>';
      });
      t2 += '</tr>';
    });
    t2 += '</tbody>';
    h += '<div class="tc-sec">' + _H('\u5de5\u5177\u5bf9\u6bd4', '\u5c38\u4f53\u91c7\u96c6 \u00b7 \u8fd1\u6218 100%')
       + '<table class="tc-tb">' + t2 + '</table></div>';
  }
  // \u2462 \u6389\u843d\u7269 / \u2463 \u88ab\u675f\u7f1a
  if(d.drops.length){
    h += '<div class="tc-sec">' + _H('\u6389\u843d\u7269', '\u51fb\u6740\u540e\u53ef\u91c7\u96c6')
       + '<div style="display:flex;flex-wrap:wrap;gap:6px">'
       + d.drops.map(function(x){ return tcGhChip(x.zh, '', ''); }).join('') + '</div></div>';
  }
  if(d.bound.length){
    h += '<div class="tc-sec">' + _H('\u88ab\u4ee5\u4e0b\u65b9\u5f0f\u675f\u7f1a', '\u56f0\u4f4f\u7528')
       + '<div style="display:flex;flex-wrap:wrap;gap:6px">'
       + d.bound.map(function(x){ return tcGhChip(x.zh, '', ''); }).join('') + '</div></div>';
  }
  // \u2464 \u5c38\u4f53\u53c2\u6570
  if(c.baseDmg){
    h += '<div class="tc-sec">' + _H('\u91c7\u96c6\u53c2\u6570', '\u5c38\u4f53\u57fa\u7840\u503c') + '<div class="tc-tiles">'
      + tcGhTile('\u57fa\u7840\u4f24\u5bb3', c.baseDmg, '\u8be5\u7269\u79cd\u5c38\u4f53')
      + tcGhTile('\u4f24\u5bb3\u500d\u7387', c.dmgMult + '\u00d7', '\u6b66\u5668\u7cfb\u6570')
      + tcGhTile('\u91c7\u96c6\u91cf\u500d\u7387', c.amtMult + '\u00d7', '\u670d\u52a1\u5668\u91c7\u96c6\u500d\u7387')
      + tcGhTile('\u653b\u51fb\u95f4\u9694', c.atk + 's', '\u6bcf\u6b21\u547d\u4e2d\u8017\u65f6')
      + '</div></div>';
  }
  // v5788（用户口径「附件无需显示」）：底部「每次采集独立计算资源…」附注整条删除
  h += '</div>';
  document.getElementById('lbWikiBody').innerHTML = h;
}

/* ===== breedRows ===== */
function breedRows(){
  var b = BREED[CUR]; if(!b) return null;
  var M = BREED_MULT;
  if (!(M.hatch > 0)) return null;          // v130：倍率未取到 → 不算（绝不用 1 兜底凑数）
  var inc = b.inc / M.hatch;
  var mat = b.mat / (M.mature || 1);
  var cudIv = BREED_BASE.cuddleH * 3600 * (M.cuddle || 1);
  // v39：满留痕所需次数 = 成熟期内留痕点数 ÷ 每次留痕量倍率（BabyImprintAmountMultiplier）
  var impSlots = cudIv > 0 ? Math.ceil(mat / cudIv) : 0;
  var imprints = impSlots > 0 ? Math.ceil(impSlots / (M.imprint || 1)) : 0;
  var matingMin = BREED_BASE.matingMinH * 3600 * (M.mating || 1);
  var matingMax = BREED_BASE.matingMaxH * 3600 * (M.mating || 1);
  return { b:b, inc:inc, mat:mat, total:inc + mat, cudIv:cudIv, imprints:imprints,
           matingMin:matingMin, matingMax:matingMax };
}

/* ===== renderBreed ===== */
function renderBreed(){
  var r = breedRows();
  var M = BREED_MULT;
  var h = '<div class="tc">';
  if(!r){
    var _bHave = !!BREED[CUR];
    if (_bHave) {
      h += '<div class="tc-sec"><div class="tc-adv" style="color:#f59e0b">'
        + '正在读取孤岛服繁殖倍率…取到后自动重算。</div></div></div>';
      document.getElementById('lbWikiBody').innerHTML = h;
      lbBreedMultEnsure(function(){ try { renderBreed(); } catch(e) {} });
    } else {
      h += '<div class="tc-sec"><div class="tc-hintb">该物种未收录繁殖参数。</div></div></div>';
      document.getElementById('lbWikiBody').innerHTML = h;
    }
    return;
  }
  // v39：顺序 = 描述 → 徽章 → 区块（徽章在描述之下）
  var _bdArr = lbWtPick('breedDesc', BREED_DESC[CUR] || []);
  var _bdAI = LB_WT_LAST_AI; LB_WT_LAST_AI = 0;   // v5766：同上，本块独立渲染，需自行打 .tc-ai
  if(_bdArr.length){
    var ds = '<div class="tc-intro' + (_bdAI ? ' tc-ai' : '') + '">' + _bdArr.map(function(s){ return '<p>' + bdText(s) + '</p>'; }).join('') + '</div>';
    h += tcSentences(ds);
  }
  h += '<div class="tc-top"><span class="tc-badge">孵化 ' + M.hatch + '×</span>'
    + '<span class="tc-badge">成长 ' + M.mature + '×</span>'
    + '<span class="tc-badge2">交配间隔 ' + M.mating + '×</span>'
    + '<span class="tc-badge2">留痕间隔 ' + M.cuddle + '×</span>'
    + '<span class="tc-badge2">留痕量 ' + M.imprint + '×</span></div>';
  var b = r.b;
  var tile = tcTile;
  // ① 关键时长
  var t1 = tile('蛋孵化', tcDur(r.inc), '基础 ' + tcDur(b.inc) + ' ÷ ' + M.hatch + '×', true)
         + tile('幼崽成熟', tcDur(r.mat), '基础 ' + tcDur(b.mat) + ' ÷ ' + M.mature + '×', true)
         + tile('交配冷却', tcDur(r.matingMin) + ' ~ ' + tcDur(r.matingMax), '18h~48h × ' + M.mating + '×')
         + tile('蛋→成体', tcDur(r.total), '孵化 + 成长');
  // ② 孵化条件
  var t2 = tile('孵化温度', b.tMin + ' ~ ' + b.tMax + ' °C', '需恒温区间')
         + tile('出生食物', b.food.toFixed(2) + '/min', '幼崽期持续消耗');
  // ③ 留痕
  var t3 = tile('留痕间隔', tcDur(r.cudIv), '8h × ' + M.cuddle + '×')
         + tile('留痕次数', r.imprints + ' 次', '每次给 ' + M.imprint + '× 量 · 满留痕即可')
         + tile('满留痕加成', '+100%', '属性加成（满留痕）');
  // ④ 时间轴（v5735 用户口径「设计正式点」→ 横排时间轴：节点 + 按占比着色进度条 + 阶段明细 + 汇总）
  //   段宽按实际耗时占比，但给 22% 下限（孵化通常只占 5%，纯按比例会挤成一条线，失去可读性）
  var _t1 = Math.max(1, Number(r.inc) || 0), _t2 = Math.max(1, Number(r.mat) || 0);
  var _p1 = Math.max(22, Math.round(_t1 / (_t1 + _t2) * 100)), _p2 = 100 - _p1;
  var _nd = function(nm){ return '<div class="tc-tl-nd"><i></i><span>' + nm + '</span></div>'; };
  var _sg = function(p, lab, val, base){
    return '<div class="tc-tl-sg" style="flex:' + p + ' 1 0">'
      + '<div class="tc-tl-bar"></div>'
      + '<div class="tc-tl-cap"><b>' + lab + ' <span style="color:#c4b5fd">' + val + '</span></b>'
      + (base ? ('<em>' + base + '</em>') : '') + '</div></div>';
  };
  var axis = '<div class="tc-tl">'
    + '<div class="tc-tl-row">'
    + _nd('下蛋')
    + _sg(_p1, '孵化', tcDur(r.inc), '基础 ' + tcDur(b.inc) + ' ÷ ' + M.hatch + '×')
    + _nd('幼崽')
    + _sg(_p2, '成长', tcDur(r.mat), '基础 ' + tcDur(b.mat) + ' ÷ ' + M.mature + '×')
    + _nd('成体')
    + '</div>'
    + '<div class="tc-tl-foot">'
    + '<span><span class="tc-tl-fk">总计</span><b>' + tcDur(r.total) + '</b></span>'
    + '<span><span class="tc-tl-fk">留痕</span><b>' + r.imprints + '</b> 次 · 每 <b>' + tcDur(r.cudIv) + '</b> 一次</span>'
    + '</div></div>';
  h += '<div class="tc-sec"><div class="tc-h">① 关键时长<em>基础 ÷ 服务器倍率</em></div><div class="tc-tiles">' + t1 + '</div></div>'
    + '<div class="tc-sec"><div class="tc-h">② 孵化条件</div><div class="tc-tiles">' + t2 + '</div></div>'
    + '<div class="tc-sec"><div class="tc-h">③ 留痕</div><div class="tc-tiles">' + t3 + '</div></div>'
    + '<div class="tc-sec"><div class="tc-h">④ 时间轴</div>' + axis + '</div>'
    // v5738（用户口径）：删除「倍率取自 …」提示条 —— 顶部倍率 chip（孵化/成长/交配/留痕）已完整展示，重复。
    + '</div>';
  document.getElementById('lbWikiBody').innerHTML = h;
  tcMountIntro();
}

/* ===== P2 第三批：经验 + 生成指令 ===== */

/* ===== EXP_KIND ===== */
var EXP_KIND = 'wild';

/* ===== EXP_BUFF ===== */
var EXP_BUFF = { toilet: false, broth: false, ex2: false, ex4: false };

/* ===== EXP_Q ===== */
var EXP_Q = 0;

/* ===== EXP_KINDS ===== */
var EXP_KINDS = [ ['wild', '野生 1.25', 1.25], ['alpha', 'Alpha 1.33', 1.33],
                  ['boss', '首领 5×', 5], ['cave', '洞穴内 1.33', 1.33] ];

/* ===== EXP_BUFFS ===== */
var EXP_BUFFS = [ ['toilet', '马桶 +33%', 1.33], ['broth', '启蒙肉汤 1.5×', 1.5],
                  ['ex2', '笔记 2×', 2], ['ex4', '笔记 4×', 4] ];

/* ===== expLvSet ===== */
function expLvSet(v){ EXP_LV = Math.max(1, Math.min(150, parseInt(v, 10) || 1)); document.getElementById('expLvV').textContent = EXP_LV; expCalc(); }

/* ===== expKillsSet ===== */
function expKillsSet(v){ EXP_KILLS = Math.max(1, Math.min(9999, parseInt(v, 10) || 1)); expCalc(); }

/* ===== expKindSet ===== */
function expKindSet(k){
  EXP_KIND = k;
  Array.prototype.forEach.call(document.querySelectorAll('#lbWikiBody .tc-kind .tc-pre'), function(b){
    b.classList.toggle('on', b.getAttribute('data-kind') === k);
  });
  var bd = document.querySelector('#lbWikiBody .tc-badge2');
  if (bd) bd.textContent = expKindName() + ' ' + expKindRate() + '×';
  expCalc();
}

/* ===== expBuffSet ===== */
function expBuffSet(k){
  EXP_BUFF[k] = !EXP_BUFF[k];
  Array.prototype.forEach.call(document.querySelectorAll('#lbWikiBody .tc-buff .tc-pre'), function(b){
    b.classList.toggle('on', !!EXP_BUFF[b.getAttribute('data-buff')]);
  });
  expCalc();
}

/* ===== expQSet ===== */
function expQSet(v){
  EXP_Q = Math.max(0, Math.min(5, parseInt(v, 10) || 0));
  expCalc();
}

/* ===== expKindRate ===== */
function expKindRate(){
  for (var i = 0; i < EXP_KINDS.length; i++) if (EXP_KINDS[i][0] === EXP_KIND) return EXP_KINDS[i][2];
  return 1.25;
}

/* ===== expKindName ===== */
function expKindName(){
  for (var i = 0; i < EXP_KINDS.length; i++) if (EXP_KINDS[i][0] === EXP_KIND) return EXP_KINDS[i][1].split(' ')[0];
  return '野生';
}

/* ===== expBuffMul ===== */
function expBuffMul(){
  var r = 1;
  EXP_BUFFS.forEach(function(b){ if (EXP_BUFF[b[0]]) r *= b[2]; });
  return r;
}

/* ===== expBuffTxt ===== */
function expBuffTxt(){
  var a = [];
  EXP_BUFFS.forEach(function(b){ if (EXP_BUFF[b[0]]) a.push(b[2] + ' ' + b[1].split(' ')[0]); });
  return a.length ? ' × ' + a.join(' × ') : '';
}

/* ===== expPerKill ===== */
function expPerKill(e){
  var lvBase = 1 + (EXP_LV - 1) * 0.1;
  return e.base * lvBase * 4 * expKindRate() * (EXP_XP * expBuffMul());   // v5811：经验倍率走 EXP_XP
}

/* ===== expCalc ===== */
function expCalc(){
  var e = EXP[CUR]; if(!e) return;
  var lvBase = 1 + (EXP_LV - 1) * 0.1;
  var srv = EXP_XP;                 // v5811（根因修复）：经验倍率 = GUS XPMultiplier（不再借用 TC_SP 驯服倍率）
  var okSrv = (srv > 0);            // 未取到 ⇒ 指标一律「—」（用户口径：不估算）
  var per = okSrv ? expPerKill(e) : 0;
  var tile = tcTile;
  var h = tile('等级系数', lvBase.toFixed(1), '1 + (等级-1) × 0.1')
        + tile('单次击杀经验', okSrv ? tcNum(per) : '—',
               okSrv ? (e.base + ' 基础 × ' + lvBase.toFixed(1) + ' × 4 × ' + expKindRate() + ' ' + expKindName() + ' × ' + srv + ' 服务器' + expBuffTxt())
                     : '未读取到服务器经验倍率（GUS XPMultiplier）')
        // v5809：非有限值禁止直接输出；v5811：倍率缺失时同样显示「—」
        + ((okSrv && per > 0 && isFinite(per))
            ? tile('升到 100 级需', tcNum(Math.ceil(1000000 / per)) + ' 次', '按约 100 万经验估算')
            : tile('升到 100 级需', '—', '未读取到服务器经验倍率'))
        + tile('基础经验', String(e.base), '每次击杀（wiki 原值）')
        + tile('累计击杀经验', okSrv ? tcNum(per * EXP_KILLS) : '—',
               okSrv ? (EXP_KILLS + ' 只 × 单只 ' + tcNum(per)) : '未读取到服务器经验倍率');
  document.getElementById('expTiles').innerHTML = h;

  var qm = EXP_QUALITY[EXP_Q][1], qn = EXP_QUALITY[EXP_Q][0];
  var sd = '';
  (e.saddle || []).forEach(function(s){
    var xp = okSrv ? (s.base * qm * 4 * srv) : 0;    // 源码：基础 × 品质 × 4 × 服务器
    sd += '<div class="tc-own-r"><span class="tc-own-n">' + s.zh
        + (s.lv ? '（' + s.lv + ' 级）' : '') + '</span>'
        + '<span class="tc-own-q">基础 ' + s.base + ' × ' + qm + '× ' + qn + ' × 4 × ' + (okSrv ? (srv + '× 服务器') : '服务器倍率未知') + '</span>'
        + '<span class="tc-ok">' + (okSrv ? (tcNum(xp) + ' 经验') : '—') + '</span></div>';
  });
  // v5807（用户口径「要低可视化」）：占位提示不用 .tc-adv（紫底大框），改 .tc-hintb（灰小字）
  document.getElementById('expSaddle').innerHTML = sd || '<div class="tc-hintb">该物种无鞍制作经验数据</div>';
}

/* ===== renderExp ===== */
function renderExp(){
  var e = EXP[CUR];
  var h = '<div class="tc">'
    + '<div class="tc-top"><span class="tc-badge">' + (EXP_XP > 0 ? ('服务器 ' + EXP_XP + '×') : '服务器倍率 读取中') + '</span>'
    + '<span class="tc-badge2">' + expKindName() + ' ' + expKindRate() + '×</span></div>'
    + wikiIntroHtml(lbWtPick('expIntro', wikiTabIntro('expIntro')));   // v95 原文 / v5781 AI 结果优先
  if(!e){
    h += '<div class="tc-sec"><div class="tc-hintb">该物种未收录经验数据。</div></div></div>';
    document.getElementById('lbWikiBody').innerHTML = h;
    return;
  }
  var kinds = EXP_KINDS.map(function(k){
    return '<button class="tc-pre' + (EXP_KIND === k[0] ? ' on' : '') + '" data-kind="' + k[0] + '">' + k[1] + '</button>';
  }).join('');
  var buffs = EXP_BUFFS.map(function(b){
    return '<button class="tc-pre' + (EXP_BUFF[b[0]] ? ' on' : '') + '" data-buff="' + b[0] + '">' + b[1] + '</button>';
  }).join('');
  var qopts = EXP_QUALITY.map(function(q, i){
    return '<option value="' + i + '"' + (EXP_Q === i ? ' selected' : '') + '>' + q[0] + ' ×' + q[1] + '</option>';
  }).join('');
  h += '<div class="tc-ctrl"><label>目标等级</label>'
    + '<input type="range" min="1" max="150" value="' + EXP_LV + '" oninput="expLvSet(this.value)">'
    + '<span class="tc-lv" id="expLvV">' + EXP_LV + '</span>'
    + '<span class="tc-div"></span><label>击杀数</label>'
    + '<input class="tc-num" type="number" min="1" max="9999" value="' + EXP_KILLS + '" oninput="expKillsSet(this.value)">'
    + '</div>'
    // v5812：小标题组 / 选项组 分块（放不下时选项整块换行）
    + '<div class="tc-fx tc-kind"><span class="tc-fx-hd"><label>目标类型</label><span class="tc-hint">单选</span>'
    + '<span class="tc-tip" data-tip="原站按击杀目标类型取一个倍率：野生 1.25 / Alpha 1.33 / 首领 5 / 洞穴内 1.33，互斥"><svg viewBox="0 0 24 24"><path d="' + ((typeof LB_MDI_SVG !== 'undefined' && LB_MDI_SVG['mdi-information']) || '') + '"/></svg></span></span>'
    + '<span class="tc-fx-opts">' + kinds + '</span></div>'
    + '<div class="tc-fx tc-buff"><span class="tc-fx-hd"><label>额外加成</label><span class="tc-hint">可多选叠加</span>'
    + '<span class="tc-tip" data-tip="马桶 ×1.33、启蒙肉汤 ×1.5、探险家笔记 ×2 / ×4（读笔记获得的限时经验加成），均与上方类型倍率连乘"><svg viewBox="0 0 24 24"><path d="' + ((typeof LB_MDI_SVG !== 'undefined' && LB_MDI_SVG['mdi-information']) || '') + '"/></svg></span></span>'
    + '<span class="tc-fx-opts">' + buffs + '</span></div>'
    + '<div class="tc-fx"><span class="tc-fx-hd"><label>鞍品质</label>'
    + '<span class="tc-tip" data-tip="品质倍率：原始 1 / 普通 2 / 优秀 3 / 精良 4 / 史诗 5 / 传说 6"><svg viewBox="0 0 24 24"><path d="' + ((typeof LB_MDI_SVG !== 'undefined' && LB_MDI_SVG['mdi-information']) || '') + '"/></svg></span></span>'
    + '<span class="tc-fx-opts"><select class="tc-num" style="width:auto" onchange="expQSet(this.value)">' + qopts + '</select>'   // v5807（用户口径）：按内容自适应，去掉两侧空白
    + '<span class="tc-hint">影响「② 鞍制作经验」</span></span></div>'
    + '<div class="tc-sec"><div class="tc-h">① 击杀经验<em>基础 × 等级系数 × 4 × 类型 × 服务器 × 加成</em></div><div class="tc-tiles" id="expTiles"></div></div>'
    + '<div class="tc-sec"><div class="tc-h">② 鞍制作经验<em>基础 × 品质 × 4 × 服务器</em></div><div class="tc-own" id="expSaddle"></div></div>'
    // v5807（用户口径「经验倍率参考的内容应该放到下面的黄框内」）：③ 整段并入黄框（黄框已改为标题栏问号 tips）
    + '<div class="tc-note">倍率参考：固定项 公式内 <b>×4</b> · 服务器 <code>XPMultiplier = ' + (EXP_XP > 0 ? EXP_XP : '读取中') + '</code>；'
    + '目标类型与额外加成见上方开关；鞍品质 6 档倍率 1~6。击杀经验：<code>base × (1+0.1×(等级-1)) × 4 × kindRate × (server × toilet × broth × explorer)</code>，kindRate 取目标类型（野生 1.25 / Alpha 1.33 / 首领 5 / 洞穴内 1.33）。示例：30 × 15.9 × 4 × 1.25 × 1 = <b>2,385</b>。鞍经验 <code>基础 × 品质 × 4 × 服务器</code>，品质倍率 1~6（原始 1× 下 86 × 4 × 1 = 344）。</div>'
    + '</div>';
  document.getElementById('lbWikiBody').innerHTML = h;
  Array.prototype.forEach.call(document.querySelectorAll('#lbWikiBody .tc-kind .tc-pre'), function(b){
    b.onclick = function(){ expKindSet(b.getAttribute('data-kind')); };
  });
  Array.prototype.forEach.call(document.querySelectorAll('#lbWikiBody .tc-buff .tc-pre'), function(b){
    b.onclick = function(){ expBuffSet(b.getAttribute('data-buff')); };
  });
  expCalc();
  // v5811：经验倍率（GUS XPMultiplier）按需拉取；取到后刷徽章/黄框并重算
  lbXpMulEnsure(function(){
    try{
      var b = document.querySelector('#lbWikiBody .tc-top .tc-badge');
      if (b) b.textContent = '服务器 ' + EXP_XP + '×';
      var nt = document.querySelector('#lbWikiBody .tc-note code');
      if (nt) nt.textContent = 'XPMultiplier = ' + EXP_XP;
      expCalc();
    }catch(e){}
  });
}

/* ===== spawnCmdLv ===== */
function spawnCmdLv(cmd, lv){
  var s = String(cmd || '');
  if (!/GMSummon|SpawnDino/i.test(s)) return s;
  var m = /^(.*\s)(\d+)(\s*\|.*)$/.exec(s);      // 「... 150 | 后续命令」：替换 | 前的末尾数字
  if (m) return m[1] + lv + m[3];
  var m2 = /^(.*\s)(\d+)(\s*)$/.exec(s);          // 「... 0 0 150」：替换整串末尾数字
  if (m2) return m2[1] + lv;
  return s;
}

/* ===== spawnLvSet ===== */
function spawnLvSet(v){
  SPAWN_LV = Math.max(1, Math.min(150, parseInt(v, 10) || 150));
  var e0 = document.getElementById('spawnLvV'); if (e0) e0.textContent = SPAWN_LV;
  var d = SPAWN[CUR]; if (!d) return;
  var e1 = document.getElementById('tcCode_main');
  if (e1) e1.textContent = spawnCmdLv(d.main, SPAWN_LV);
  var _c = spawnCmds(CUR);
  for (var i = 0; i < _c.length; i++){
    var el = document.getElementById('tcCode_c' + i);
    if (el) el.textContent = spawnCmdLv(_c[i].c, SPAWN_LV);
  }
}

/* ===== tcCmdBox ===== */
function tcCmdBox(cmd, cid){
  return '<div class="tc-codeline">'
    + '<code class="tc-code" id="tcCode_' + cid + '">' + tcEsc(cmd) + '</code>'
    + '<button class="tc-cpbtn" onclick="tcCopy(this)" data-src="tcCode_' + cid + '">复制</button>'
    + '</div>';
}

/* ===== spawnCmds ===== */
function spawnCmds(sp){
  var d = SPAWN[sp] || {}, tpl = WIKI_DEX.SPAWN_TPL || {};
  var zh = (TAME[sp] || {}).zh || (DATA[sp] || {}).zh || '';
  var fill = function(x){
    return String(x == null ? '' : x)
      .replace(/\{bpPath\}/g, d.bpPath || '')
      .replace(/\{bp\}/g, d.bp || '')
      .replace(/\{zh\}/g, zh)
      .replace(/\{lv\}/g, String(tpl.lv == null ? 150 : tpl.lv));
  };
  var out = [];
  /* v5787（用户口径「生成里面只显示包含当前生物的」+「保留鞍命令」）：
     · 只保留「当前生物专属」的模板命令 —— 判定 = 原始模板含 {bp}/{bpPath} 占位符，
       或填充后文本含当前 d.bp / d.bpPath（双保险，防某条写死类名）
     · 鞍（slot:'saddles'）例外保留 —— 那是这只龙的坐骑装备，属当前生物相关
     · 通用 GM 命令（ForceTame/DoTame/AddExperience/GiveExpToTarget/Kill/TakeAllDino）
       命令串里没有任何生物标识、对每个物种都一字不差 ⇒ 一律不显示 */
  (tpl.cmds || []).forEach(function(c){
    if (c.slot === 'saddles'){
      (d.saddles || []).forEach(function(x){ out.push({ t: fill(x.t), c: fill(x.c) }); });
      return;
    }
    var _rawC = String(c.c == null ? '' : c.c), _rawT = String(c.t == null ? '' : c.t);
    var _keep = (/\{bp\}|\{bpPath\}/.test(_rawC) || /\{bp\}|\{bpPath\}/.test(_rawT));
    if (!_keep){
      var _f = fill(_rawC);
      _keep = !!((d.bp && _f.indexOf(d.bp) >= 0) || (d.bpPath && _f.indexOf(d.bpPath) >= 0));
    }
    if (!_keep) return;
    out.push({ t: fill(c.t), c: fill(c.c) });
  });
  return out;
}

// v5690（用户口径「物种的生成命令为啥没有参数说明？参数说明应该放在命令的卡片内，无需独立卡片」）：
//   命令卡片内补「参数」行；原「三种生成方式」独立卡片的内容并入对应命令卡片后删除
var LB_SPAWN_PARAM_ZH = {
  'Amount': '数量',
  'From Tribe': '是否计入部落（0/1）',
  'Prevent Sharing With Tribe': '是否不与部落分享（0/1）'
};
function lbSpawnParamHint(cmd){
  var s = String(cmd || ''), tips = [];
  var re = /<([A-Za-z][A-Za-z ]{0,40})>/g, m;
  while ((m = re.exec(s)) !== null) {
    var k = String(m[1]).trim();
    if (!k) continue;
    var zh = LB_SPAWN_PARAM_ZH[k] || '';
    var one = '<code>&lt;' + k + '&gt;</code>' + (zh ? (' ' + zh) : '');
    if (tips.indexOf(one) < 0) tips.push(one);
  }
  if (/^\s*admincheat\s+summon\b/i.test(s)) {
    tips.push('随机等级，生成在准心位置，最简单');
  } else if (/SpawnDino/i.test(s)) {
    tips.push('精确坐标 + 指定等级，需填蓝图路径');
    tips.push('末 5 个参数 = <code>蓝图路径 X Y Z 等级</code>');
  } else if (/GMSummon/i.test(s)) {
    tips.push('指定等级并强制驯服，想要能直接骑的个体就用它');
  }
  if (!tips.length) return '';
  return '<div style="font-size:11.5px;color:#8b93a7;margin-top:5px;line-height:1.65">参数：' + tips.join(' · ') + '</div>';
}

/* ===== renderSpawn ===== */
function renderSpawn(){
  var d = SPAWN[CUR];
  var _N = 0;
  var _H = function(t, em){ return tcHStr(_N++, t, em); };
  var h = '<div class="tc">';
  if(!d){
    h += '<div class="tc-sec"><div class="tc-hintb">该物种未收录生成指令数据。</div></div></div>';
    document.getElementById('lbWikiBody').innerHTML = h;
    return;
  }
  // v61b：过滤 wikily 主命令卡标题（「生成N级已驯服个体」）混入 intro 的噪音段
  var _intro = lbWtPick('spawnIntro', d.intro || [])
                 .filter(function(t){ return !/^生成\d+级已驯服个体$/.test(String(t).trim()); });
  if(_intro.length){
    // v5780：改走 wikiIntroHtml —— lbWtPick 已设置 LB_WT_LAST_AI，原来手拼 div 没读它 ⇒
    //   AI 整理结果拿不到 .tc-ai（既不标名词也不正名）。filter 不改变 LAST_AI，可直接传。
    h += wikiIntroHtml(_intro);
  }
  var _cmds = spawnCmds(CUR);
  h += '<div class="tc-top">'
     + '<span class="tc-badge">' + _cmds.length + ' 条指令</span>'
     + (d.bp ? '<span class="tc-badge2">类名 ' + d.bp + '</span>' : '')
     + '</div>';
  h += '<div class="tc-sec">' + _H('快速生成', '按等级即时生成已驯服个体')
     + '<div class="tc-ctrl"><label>等级</label>'
     + '<input type="range" min="1" max="150" value="' + SPAWN_LV + '" oninput="spawnLvSet(this.value)">'
     + '<span class="tc-lv" id="spawnLvV">' + SPAWN_LV + '</span></div>'
     + tcCmdBox(spawnCmdLv(d.main, SPAWN_LV), 'main') + lbSpawnParamHint(d.main) + '</div>';
  // v5787：过滤后若一条不剩（极端情况）就不渲染该块，避免空壳
  if (_cmds.length){
    h += '<div class="tc-sec">' + _H('全部指令', '原文命令逐字保留 · 点右侧复制')
       + '<div class="tc-cmds">' + _cmds.map(function(c, i){
           return '<div class="tc-cmd"><div class="tc-cmd-desc">' + tcEsc(c.t) + '</div>'
             + tcCmdBox(spawnCmdLv(c.c, SPAWN_LV), 'c' + i) + lbSpawnParamHint(c.c) + '</div>';
         }).join('') + '</div></div>';
  }
  // v5690（用户口径）：原「三种生成方式」独立卡片已删除 —— 其说明按命令家族并入各命令卡片的「参数」行（见 lbSpawnParamHint）
  // v5805（用户口径「太啰嗦了 / 无需『仅列xxx』的说法」）：删掉首句
  // v5806（用户口径「等级滑块只影响xxx 也无需显示」）：再删滑块那句，只留控制台操作说明
  h += '<div class="tc-note">'
     // v5689（用户口径「操作不对吧？我记得是按~」）：控制台键 = Tilde（与键位表 keyboard_tilde 一致，原写死 Tab 有误）
     + 'PC 上按 <code>~</code>（Tilde）打开管理员控制台，主机从暂停菜单进入；需管理员权限。</div>'
     + '</div>';
  document.getElementById('lbWikiBody').innerHTML = h;
  tcMountIntro();
}

/* ===== 技巧 TAB（v5740 实装）=====
   数据源：dododex.com 玩家投稿心得（后端 /api/dino/tips 抓取 + 30 天缓存）
   过滤：分类白名单(taming-ko/utility/encountering) + 赞数≥100 + 正文≥60 字 + Top15
   翻译：复用「大肥鱼」AI 模块自带的 token 配置（lbAiCfgGet / lbOpenConfigModal），
        一次 5 条批量翻，翻完 POST 回写后端共享缓存 —— 一个人翻过，所有人秒开
   三态：idle(未抓取) / loading / ready / err，全部复用 .lb-hf-ai* 外框，**不渲染提示词输入框** */
/* v5750：权威心得 prompt 版本戳 —— prompt/数据源升级时递增，后端据此覆盖旧 auth（其余情况仍"只写一次"） */
var LB_TIPS_PV = 5;
var LB_TIPS = { slug: '', cls: '', st: 'idle', items: [], summary: '', zh: {}, merged: null, err: null, busy: false, msg: '', needTok: false };
/* v6030：技巧共享缓存探测 —— 与 LB_WT_AI_PROBE 同构。
   入口虚线 bug 根因：wikily 索引（/api/wiki/index）没收录 ≠ 没资料，
   「技巧」TAB 的 AI 整理结果走独立链路 /api/dino/tips/zh（dodo_<slug>_zh.json 的 merged.secs/auth）。 */
var LB_TIPS_PROBE = {};     // slug(小写) -> 1 ：已确认有技巧整理结果
var LB_TIPS_PROBE_TRY = {}; // slug(小写) -> 1 ：已发起过探测（防重入 / 防轮询）

function lbTipsApi(){
  var b = (typeof LB_API === 'string' && LB_API) ? LB_API : 'https://data.whiterober.ccwu.cc';
  return String(b).replace(/\/+$/, '') + '/api/dino/tips';
}
function lbTipsEsc(s){ return (typeof tcEsc === 'function') ? tcEsc(s) : String(s == null ? '' : s); }

/* v5744（用户口径「AI 模块 的 除了输入框，其他元素一个都不能少，包括大肥鱼背景」）：
   统一生成**标准 AI 模块外壳** —— 严格对齐 lbBbNotesAiHtml 的结构：
     .lb-hf-aibox
       .lb-hf-aiinput-wrap + img.lb-hf-aiinput-water（大肥鱼水印）
       .lb-hf-airow  → 状态 + 弹性空白 + 模型/token + ⚙配置 + 主按钮
       .lb-hf-aicand（结果/候选区）
   **唯一去掉的是 textarea.lb-hf-aiinput**（技巧场景不需要用户输入提示词）。
   · 去掉 textarea 后 input-wrap 会塌陷 ⇒ 单独 min-height:56px 撑起水印
   · `.lb-hf-aimode`（追加/覆盖/优化）属「写笔记」语义，用户明确不要，此处不渲染 */
function lbTipsAiBoxHtml(opt){
  opt = opt || {};
  var cfg = {};
  try { cfg = lbAiCfgGet() || {}; } catch (e) {}
  var metaTxt = (opt.meta != null) ? opt.meta
    : ('模型 ' + (typeof lbAiModelShort === 'function' ? lbAiModelShort(cfg.model) : '') +
       ' · token ' + (typeof lbAiMask === 'function' ? lbAiMask(cfg.token || '') : ''));
  var h = '<div class="lb-hf-aibox" id="tcTipsBox"'
    + (opt.style ? (' style="' + opt.style + '"') : '') + '>'
    // v5746（用户口径「附件输入框隐藏掉，大肥鱼背景改到外框左下角」）：
    //   不再渲染 .lb-hf-aiinput-wrap 容器，水印直接挂在外框内并绝对定位到左下角
    + '<img class="lb-hf-aiinput-water lb-tips-water" src="thumbs/webp96/bdb8c3b809e6_w96.webp" alt="">'
    + '<div class="lb-hf-airow" style="position:relative;z-index:1">';
  if (opt.state){
    h += '<span class="lb-hf-ai-meta" style="text-align:left;white-space:normal">' + opt.state + '</span>';
  }
  h += '<span class="lb-hf-ai-fill"></span>'
    + '<span class="lb-hf-ai-meta">' + lbTipsEsc(metaTxt) + '</span>'
    + '<span class="lb-hf-ai-cfg" onclick="lbOpenConfigModal()">⚙ 配置</span>';
  if (opt.btn){
    h += '<button class="lb-hf-aibtn primary"'
      + (opt.disabled ? ' disabled' : '')
      + ' onclick="' + opt.btn.fn + '">' + opt.btn.txt + '</button>';
  }
  h += '</div>';
  h += opt.cand
    ? ('<div class="lb-hf-aicand" id="tcTipsCand">' + opt.cand + '</div>')
    : '<div class="lb-hf-aicand" id="tcTipsCand" style="display:none"></div>';
  h += '</div>';
  return h;
}

/* ===== v5745：wikily 原文 AI 整理（按物种，一次跑完全服共享）=====
   用户口径（2026-10-31）：
     · 「原文案 通过 AI整理归纳后，再重新分配到 各个TAB里」
     · 「原样搬，但是只包括 wikily 取的」⇒ 素材仅限后端从 wikily 抓来的 6 类描述，
        项目自己写的 UI 提示（部落塔状态 / 暂无数据 / PC 按 ~ 等）**不参与**
     · 「原文案 和 技巧 完全独立处理，互不干涉」⇒ 与 dodo_* 缓存各存各的
     · 「空着就不显（允许 AI 掽走）」⇒ 某位置没内容就不渲染该块
   6 类：OVERVIEW.intro / OVERVIEW.tips / HOME.tameIntro / BREED_DESC / ABIL.skills[].desc / SPAWN.intro */
var LB_WT = { slug: '', data: null, busy: false, msg: '', ready: false };

/* ===== v5759：方舟术语对照表（中英 → 中文，模糊匹配）=====
   用户口径（2026-10-31）：「wiki AI翻译时，要严格界定方舟词汇走网页的中英文翻译对照表内取，支持模糊匹配」
   数据源（全部取页面已加载的官方汉化表，不另维护副本）：
     · ZH_MAP          ← icon_zh_map.json（生物/图标词条，值形如「电鳗(Electrophorus)」）
     · LB_ITEM_ZH      ← item_zh.json（物品/资源，{en, zh}）
     · LB_FACILITY_ZH  ← facility_zh.json（设施/建筑，{en, zh}）
     · LB_WT_TERMS     ← 上述表未覆盖的机制/伤害类型兜底词条（页面唯一权威补充）
   模糊匹配：键统一 lower + 去空格/连字符/下划线/撇号后比对
     ⇒ SpikeWall / Spike Wall / spike_wall 视为同一个词 */
var LB_WT_TERMS = {
  'Spike Wall': '尖刺墙', 'SpikeWall': '尖刺墙',
  'Projectile': '投射物',
  'Explosion Demolition': '爆炸伤害', 'Explosion': '爆炸',
  'MiningDrill Harvest': '采矿钻采集', 'MiningDrill': '采矿钻',
  'Harvest': '采集', 'Drag Weight': '拖拽重量', 'Torpor': '眩晕值',
  'Narcotic': '麻醉药', 'Tranq Arrow': '麻醉箭', 'Tranq Dart': '麻醉镖',
  'Kibble': '饲料', 'Prime Meat': '优质生肉', 'Raw Meat': '生肉',
  'Imprint': '留痕', 'Trap': '困龙房', 'Bear Trap': '捕兽夹',
  'Tek': '泰克', 'Alpha': '精英', 'Carrion': '腐肉',
  'Juvenile': '幼年期', 'Adolescent': '青年期', 'Baby': '幼崽', 'Mature': '成年',
  'Boss': '首领', 'Saddle': '鞍', 'Armor': '护甲',
  'Melee Damage': '近战伤害', 'Movement Speed': '移动速度', 'Health': '生命值',
  'Stamina': '体力', 'Oxygen': '氧气', 'Food': '食物', 'Weight': '负重',
  'Damage': '伤害', 'Resistance': '抗性', 'Weakness': '脆弱', 'Immune': '免疫',
  'Knockback': '击退', 'Stun': '眩晕', 'Poison': '中毒', 'Radiation': '辐射',
  'Bleed': '流血', 'Loot': '战利品', 'Recipe': '配方', 'Resource': '资源',
  'Biome': '生物群系', 'Cave': '洞穴'
};
/* 允许保留英文的社区通用缩写（norm 形式） */
var LB_WT_KEEP = { asa: 1, pvp: 1, pve: 1, dps: 1, xp: 1, ui: 1, hp: 1, ko: 1, pvx: 1 };

function lbWtNormEn(s){
  return String(s == null ? '' : s).toLowerCase().replace(/[\s\-_'’.·]/g, '');
}
function lbWtGlossMap(){
  var m = {};
  function put(en, zh){
    var k = lbWtNormEn(en);
    zh = String(zh == null ? '' : zh).trim();
    if (k && k.length >= 3 && zh && !LB_WT_KEEP[k] && !m[k]) m[k] = zh;
  }
  try {
    var Z = (typeof ZH_MAP === 'object' && ZH_MAP) || {};
    Object.keys(Z).forEach(function(en){
      var s0 = String(Z[en] == null ? '' : Z[en]).trim();
      var m0 = s0.match(/^(.+?)\s*[\(（\[]([^\)）\]]*)[\)）\]]\s*$/);
      // v5772（用户口径「Kaprosuchus 怎么还有这种」）：**参数顺序写反的根因 BUG**
      //   本函数签名是 put(en, zh)，但原实现写成 put(m0[1], m0[2]) = put(中文, 英文)
      //   ⇒ 词表里 1278/1632 条键是中文，英文文本永远匹配不到 ⇒ EN→ZH 兜底整体失效，
      //     连带 lbWtGlossHits 喂给 AI 的「必须使用的中文译名」块也是空的。
      if (m0){ put(m0[2].trim(), m0[1].trim()); return; }   // put(en=m0[2], zh=m0[1])
      // v5768：无括号条目**不再整批丢弃** —— 只过滤真正的图标内部名（含下划线/icon 后缀/纯小写拼接）
      if (/_/.test(en) || /(icon|_bc|ic)$/i.test(en) || !/[a-z]/i.test(en)) return;
      put(en, s0);                                          // v5772：put(en=键, zh=值)（原为 put(s0, en)）
    });
  } catch (eI) {}
  try {
    var F = (typeof LB_FACILITY_ZH === 'object' && LB_FACILITY_ZH) || {};
    Object.keys(F).forEach(function(k){ var o = F[k] || {}; put(o.en || k, o.zh); });
  } catch (eF) {}
  Object.keys(LB_WT_TERMS).forEach(function(en){ put(en, LB_WT_TERMS[en]); });
  return m;
}
var LB_WT_GLOSS_CACHE = null, LB_WT_GLOSS_N = -1;
function lbWtGlossCached(){
  var n = 0;
  try { n += (typeof ZH_MAP === 'object' && ZH_MAP) ? Object.keys(ZH_MAP).length : 0; } catch (e1) {}
  try { n += (typeof LB_ITEM_ZH === 'object' && LB_ITEM_ZH) ? Object.keys(LB_ITEM_ZH).length : 0; } catch (e2) {}
  try { n += (typeof LB_FACILITY_ZH === 'object' && LB_FACILITY_ZH) ? Object.keys(LB_FACILITY_ZH).length : 0; } catch (e3) {}
  if (!LB_WT_GLOSS_CACHE || n !== LB_WT_GLOSS_N){
    LB_WT_GLOSS_CACHE = lbWtGlossMap();
    LB_WT_GLOSS_N = n;
  }
  return LB_WT_GLOSS_CACHE;
}
/* 从原文抓「已收录的英文术语」→ { 原文写法: 中文 }（最长匹配优先） */
function lbWtGlossHits(raw){
  var map = lbWtGlossCached(), out = {}, seen = {};
  var texts = [];
  Object.keys(raw || {}).forEach(function(k){
    var arr = raw[k] || [];
    for (var i = 0; i < arr.length; i++){
      var v = arr[i];
      if (typeof v === 'string') texts.push(v);
      else if (v && typeof v === 'object'){ texts.push(String(v.zh || '')); texts.push(String(v.desc || '')); }
    }
  });
  texts.join('\n').replace(/[A-Za-z][A-Za-z'’\-]*(?:[ \t]+[A-Za-z][A-Za-z'’\-]*){0,3}/g, function(ph){
    var words = ph.split(/[ \t]+/);
    for (var n = words.length; n >= 1; n--){
      for (var i = 0; i + n <= words.length; i++){
        var sub = words.slice(i, i + n).join(' ');
        var kk = lbWtNormEn(sub);
        if (map[kk] && !seen[kk]){ seen[kk] = 1; out[sub] = map[kk]; return ph; }
      }
    }
    return ph;
  });
  var ks = Object.keys(out);
  if (ks.length > 140){
    var o2 = {};
    ks.slice(0, 140).forEach(function(k){ o2[k] = out[k]; });
    return o2;
  }
  return out;
}
/* 渲染兜底：把一段纯文本里已收录的英文术语就地换成中文 */
function lbWtGlossText(t, map){
  if (!t || !/[A-Za-z]/.test(t)) return t;
  map = map || lbWtGlossCached();
  return String(t).replace(/[A-Za-z][A-Za-z'’\-]*(?:[ \t]+[A-Za-z][A-Za-z'’\-]*){0,3}/g, function(ph){
    var whole = map[lbWtNormEn(ph)];
    if (whole) return whole;
    return ph.replace(/[A-Za-z][A-Za-z'’\-]*/g, function(wd){
      var z = map[lbWtNormEn(wd)];
      return z || wd;
    });
  });
}
/* 渲染兜底（DOM 收口）：遍历 #lbWikiBody 文本节点做术语替换
   跳过 CODE/PRE/命令块/徽章区，以及含类名下划线标识的节点（如蓝图 Rex_Character_BP_C） */
function lbWtGlossDom(root){
  if (!root) return 0;
  var map = lbWtGlossCached();
  if (!map || !Object.keys(map).length) return 0;
  var nodes = [], n = 0;
  try {
    var wk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    while (wk.nextNode()){
      var nd = wk.currentNode, p = nd.parentNode;
      if (!p) continue;
      var tag = (p.nodeName || '').toUpperCase();
      if (tag === 'CODE' || tag === 'PRE' || tag === 'SCRIPT' || tag === 'STYLE' || tag === 'TEXTAREA') continue;
      if (p.closest && p.closest('.tc-code, .tc-codeline, .tc-top, .tc-badge, .tc-badge2, .tc-en, pre')) continue;   // v5763：.tc-en 内的英文小字不许再被翻成中文
      var tx = nd.nodeValue || '';
      if (!/[A-Za-z]/.test(tx)) continue;
      if (/[A-Za-z]{3,}_[A-Za-z]/.test(tx)) continue;
      nodes.push(nd);
    }
  } catch (eTW) { return 0; }
  for (var i = 0; i < nodes.length; i++){
    var t0 = nodes[i].nodeValue, t1 = lbWtGlossText(t0, map);
    if (t1 !== t0){ nodes[i].nodeValue = t1; n++; }
  }
  return n;
}

/* ===== v5779（用户口径「非 AI 块里的错名要改」）：**中文俗称 → 表内正名**（ZH→ZH 渲染期修正）
   场景：非 AI 整理块（renderTame 的 tabHtml、renderGather 的 d.about、renderSpawn 的 d.intro…）
         内容来自后端原始数据，里面会写「阿根廷巨鹰」「木材」「石制恐龙门」这类俗称，
         而权威表定的是「阿根廷鹫」「木头」「加固恐龙门」。
   · 数据源：LB_AI_DINO_ALIAS（物种俗称）+ LB_ZH_ALIAS（物品/建筑/资源别称）——**零硬编码**
   · 算法：与 lbEnMarkText 同构的「最长匹配 + 逐字推进」，但**正名优先保护**：
     当前位置若命中某个正名 ⇒ 原样输出、不做替换。
     否则「南方巨兽龙」会被别名「南方巨」切成「南方巨兽龙 + 兽龙」。
   · 跳过：CODE/PRE/命令块/徽章/输入框 —— 命令与参数里的中文不能改动 */
var LB_ZH_FIX = null, LB_ZH_FIX_MX = 0, LB_ZH_FIX_SIG = -1;
function lbZhFixMaps(){
  var sig = 0;
  try { sig += (typeof LB_AI_DINO_ALIAS === 'object' && LB_AI_DINO_ALIAS) ? Object.keys(LB_AI_DINO_ALIAS).length : 0; } catch (e0) {}
  try { sig += (typeof LB_ZH_ALIAS === 'object' && LB_ZH_ALIAS) ? Object.keys(LB_ZH_ALIAS).length : 0; } catch (e0) {}
  if (LB_ZH_FIX && sig === LB_ZH_FIX_SIG) return LB_ZH_FIX;
  var A = {}, C = {}, aliasKeys = {}, mx = 0;
  var TABS = [
    (typeof LB_AI_DINO_ALIAS === 'object' && LB_AI_DINO_ALIAS) || null,
    (typeof LB_ZH_ALIAS === 'object' && LB_ZH_ALIAS) || null
  ];
  for (var ti = 0; ti < TABS.length; ti++){
    var TB = TABS[ti];
    if (!TB) continue;
    Object.keys(TB).forEach(function(k){
      var v = String(TB[k] == null ? '' : TB[k]).trim();
      if (!k || k.length < 2 || !v || v === k) return;      // 单字别名 / 自映射：跳过
      aliasKeys[k] = 1;                                       // v5783：所有别称 key 先登记
      if (/[A-Za-z]/.test(v)) return;                        // 值为英文（如 'Sand'）⇒ 不是中文正名
      A[k] = v;
      if (!C[v]) C[v] = 1;
      if (k.length > mx) mx = k.length;
      if (v.length > mx) mx = v.length;
    });
  }
  /* v5783（用户口径「黑*「含硅珍珠」*Silica Pearls 这明显错了 … **黑珍珠 和 珍珠 要分别对应权威物品**」）：
     **整词优先** —— 别称表表达的是「A 这个词 ≡ B 这个词」（整词等价），
     但 v5779 的扫描实现成了「文本里出现 A 就换成 B」（子串替换）⇒
     别称「珍珠」把「黑珍珠」内部的子串吃掉，变成「黑含硅珍珠」。
     根治：把**全部已知正式中文名**并入保护集，扫描时先做整词匹配、命中即原样前进。
     正式名集合 = lbEnRevMap() 的全部中文键 **减去** 别名 key：
       · 「黑珍珠」「含硅珍珠」「南方巨兽龙」⇒ 在 rev 且不是别名 ⇒ 保护，原样保留
       · 「阿根廷巨鹰」「珍珠」「木材」⇒ 是别名 key ⇒ 不保护，仍按别称替换 */
  try {
    var _rev = (typeof lbEnRevMap === 'function') ? lbEnRevMap() : null;
    if (_rev) Object.keys(_rev).forEach(function(k){
      if (!aliasKeys[k] && k.length >= 2) C[k] = 1;
    });
    if (typeof LB_ENM_MAX === 'number' && LB_ENM_MAX > mx) mx = LB_ENM_MAX;   // 匹配长度上限并入反查表最大键长
  } catch (eRev) {}
  LB_ZH_FIX = { A: A, C: C };
  LB_ZH_FIX_MX = Math.min(mx, 24);
  LB_ZH_FIX_SIG = sig;
  return LB_ZH_FIX;
}
function lbZhFixText(t){
  if (!t || !/[\u4e00-\u9fa5]/.test(t)) return t;
  var M = lbZhFixMaps(), A = M.A, C = M.C, mx = LB_ZH_FIX_MX;
  if (!A || !Object.keys(A).length) return t;
  var out = '', i = 0, n = t.length, hit = 0, L, sub, done;
  while (i < n){
    // ① 正名保护（最长优先）：已在正名内不替换
    done = 0;
    for (L = Math.min(mx, n - i); L >= 2; L--){
      sub = t.substr(i, L);
      if (C[sub]){ out += sub; i += L; done = 1; break; }
    }
    if (done) continue;
    // ② 俗称 → 正名（最长优先）
    for (L = Math.min(mx, n - i); L >= 2; L--){
      sub = t.substr(i, L);
      if (A[sub]){ out += A[sub]; i += L; hit = 1; done = 1; break; }
    }
    if (done) continue;
    out += t.charAt(i); i++;
  }
  return hit ? out : t;
}
/* DOM 收口：遍历正文文本节点做中文正名替换 */
function lbZhFixDom(root){
  if (!root) return 0;
  var M = lbZhFixMaps();
  if (!M || !Object.keys(M.A).length) return 0;
  var nodes = [], n = 0;
  try {
    var wk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    while (wk.nextNode()){
      var nd = wk.currentNode, p = nd.parentNode;
      if (!p) continue;
      var tag = (p.nodeName || '').toUpperCase();
      if (tag === 'CODE' || tag === 'PRE' || tag === 'SCRIPT' || tag === 'STYLE' || tag === 'TEXTAREA') continue;
      // v5780：与 lbEnMark 同一套准入 —— 只认 AI 整理容器
      // v5784：+ `.abil-desc`（技能描述例外：不做 AI 整理，但要走正名修正）
      if (!p.closest || !p.closest('.tc-ai, .tc-auth-i, .tc-tipd-p, .tc-tipd-t, .abil-desc')) continue;
      // 命令块 / 徽章 / 已标记的英文小字 / 输入框：一律不动
      if (p.closest('.tc-code, .tc-codeline, .tc-top, .tc-badge, .tc-badge2, .tc-en, pre, .lb-hf-aiinput, .lw-tab, .lb-picker-overlay')) continue;
      var tx = nd.nodeValue || '';
      if (!tx || !/[\u4e00-\u9fa5]/.test(tx)) continue;
      nodes.push(nd);
    }
  } catch (eTW) { return 0; }
  for (var i = 0; i < nodes.length; i++){
    var t0 = nodes[i].nodeValue, t1 = lbZhFixText(t0);
    if (t1 !== t0){ nodes[i].nodeValue = t1; n++; }
  }
  return n;
}

/* ===== v5761：物种名权威化提示块（wiki 原文整理 / 技巧整理 **共用同一实现**）=====
   用户口径（2026-10-31）：「技巧里面的还是巨鹰」—— 证明只修 wiki 链不够：技巧是另一条独立 AI 链路。
   设计原则（与 v5759/v5760 一致）：**不硬编码任何具体词对**
     · 正式名   ← lbSpName(slug).zh 现场读取（物种表权威）
     · 俗名映射 ← 项目已有 LB_AI_DINO_ALIAS，且**只挑 texts 里真的出现的**（len>=2、非自映射）
   返回可直接拼进 user 消息的字符串；无内容时返回 ''（不影响原流程）。 */
function lbWtNameBlocks(slug, texts){
  var out = '', ofName = '';
  try {
    var spO = (typeof lbSpName === 'function') ? lbSpName(slug) : null;
    if (spO && typeof spO === 'object' && spO.zh) ofName = String(spO.zh).trim();
    else if (typeof spO === 'string') ofName = String(spO).trim();
  } catch (eOf) { ofName = ''; }
  if (ofName) out += '【物种表 · 正式中文名】' + ofName + '\n\n';
  try {
    var allTxt = (texts || []).join('\n');
    // ① 物种俗称：表大，只挑原文里真的出现的（避免灌爆 token）
    var AL = (typeof LB_AI_DINO_ALIAS === 'object' && LB_AI_DINO_ALIAS) || null;
    var hit = [];
    if (AL){
      Object.keys(AL).forEach(function(k){
        if (!k || k.length < 2) return;                 // 单字俗称易误伤
        if (!AL[k] || AL[k] === k) return;              // 自映射无意义
        if (allTxt.indexOf(k) >= 0) hit.push(k + ' → ' + AL[k]);
      });
    }
    if (hit.length){
      out += '【俗名 → 正式中文名】（文中出现的俗称，输出必须改写成右侧正式名）\n· '
        + hit.slice(0, 60).join('\n· ') + '\n\n';
    }
    // ② v5773：物品/建筑别称 —— 表很小（个位数），**整表喂**（不按原文命中筛选：
    //   原文是英文，中文通行叫法根本不会出现；但 AI 翻译时会自己生成「石制恐龙门」这类说法）
    var ZA = (typeof LB_ZH_ALIAS === 'object' && LB_ZH_ALIAS) || null;
    if (ZA){
      var zh2 = [];
      Object.keys(ZA).forEach(function(k){
        if (!k || k.length < 2 || !ZA[k] || ZA[k] === k) return;
        zh2.push(k + ' → ' + ZA[k]);
      });
      if (zh2.length){
        out += '【物品通行叫法 → 表内正名】（输出一律用右侧正名，禁止使用左侧叫法）\n· '
          + zh2.slice(0, 80).join('\n· ') + '\n\n';
      }
    }
  } catch (eAl) {}
  /* v5772（用户口径「Kaprosuchus 怎么还有这种」）：**原文出现的英文物种名 → 正式中文名**
     不硬编码任何词对：遍历 ASB 物种表，只挑 texts 里真的出现的（英文名按词边界匹配）。
     这样 AI 拿到的就是「Kupr... → 猪鳄」这类具体映射，从源头禁止它输出英文原名。 */
  try {
    var _t2 = (texts || []).join('\n');
    var _db2 = (typeof ASB_DB !== 'undefined' && ASB_DB && ASB_DB._byBp) ? ASB_DB._byBp : null;
    if (_db2 && _t2 && /[A-Za-z]/.test(_t2)){
      var _low = _t2.toLowerCase(), _seen = {}, _pn = [];
      Object.keys(_db2).forEach(function(bp){
        var sp = _db2[bp] || {};
        var en = String(sp.name || '').trim();
        if (!en || en.length < 4) return;
        var lk = en.toLowerCase();
        if (_seen[lk]) return;
        if (_low.indexOf(lk) < 0) return;                       // 先做低成本包含检查
        var re = new RegExp('(^|[^A-Za-z])' + en.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '([^A-Za-z]|$)');
        if (!re.test(_t2)) return;                              // 再确认词边界
        _seen[lk] = 1;
        var zh = '';
        try { zh = String(lbZhDeep(en) || '').trim(); } catch (eZ1) {}
        if (!zh){
          try {
            var leaf = String(sp.blueprintPath || bp).split('.').pop().replace(/_C$/, '');
            var o1 = lbSpName(leaf + '_C');
            zh = (o1 && o1.zh) ? String(o1.zh).trim() : '';
          } catch (eZ2) {}
        }
        if (zh && zh !== en) _pn.push(en + ' → ' + zh);
      });
      if (_pn.length){
        out += '【英文物种名 → 正式中文名】（原文出现的英文名，输出一律写右侧中文，禁止保留英文）\n· '
          + _pn.slice(0, 80).join('\n· ') + '\n\n';
      }
    }
  } catch (ePN) {}
  return out;
}

/* ===== v5762：方舟名词「中文 + 下方英文小字」标记引擎 =====
   用户口径（2026-10-31）：「匹配到的方舟词汇用「」，对应的英文小字在下方不影响布局」
   设计：**纯渲染期实现，不动任何 AI 提示词**（方案 C 混合）
     · 反查表 ← 页面已有中英对照表（中文→英文），AI 只管译对，样式这里补
     · 只标专有名词：生物名 / 物品名（排除 resource 通用材料）/ 设施名 / 机制术语
     · 跳过 CODE / PRE / 命令块 / 徽章 / 含类名下划线的节点（保护蓝图 Rex_Character_BP_C）
   幂等：已包过的 span 打 data-enm="1"，observer 二次触发不再改 → 自然收敛。 */
var LB_ENM_REV = null, LB_ENM_MAX = 2, LB_ENM_BUSY = 0, LB_ENM_SIG = -1;
var LB_ENM_MO = {}, LB_ENM_T = {};
/* 通用资源词（不是专名，标了会满屏小字）—— 按英文排除，不写中文词对 */
/* v5773（用户口径「金属、黑曜石 为啥都没匹配」）：**整表取消（清空）**。
   ⚠ 这张表是 v5762 我自己判定「通用资源词不是专名，标了会满屏小字」而加的**限制**，
     用户从未要求过 —— 「金属 / 黑曜石 / 水晶 / 燧石 / 木材 / 石头」同样是方舟专名，理应配英文小字。
   保留结构（默认空对象）+ put() 里的检查逻辑：日后若某几个词确实过密，往本表回填即可，无需改代码。 */
var LB_ENM_STOP = {};

/* v5763：加「表键总数」指纹 —— 对照表是异步加载的，早先建的空表/残表不能永久锁死 */
function lbEnRevMap(){
  var sig = 0;
  try { sig += (typeof ZH_MAP === 'object' && ZH_MAP) ? Object.keys(ZH_MAP).length : 0; } catch (e0) {}
  try { sig += (typeof LB_ITEM_ZH === 'object' && LB_ITEM_ZH) ? Object.keys(LB_ITEM_ZH).length : 0; } catch (e0) {}
  try { sig += (typeof LB_FACILITY_ZH === 'object' && LB_FACILITY_ZH) ? Object.keys(LB_FACILITY_ZH).length : 0; } catch (e0) {}
  if (LB_ENM_REV && sig === LB_ENM_SIG) return LB_ENM_REV;
  var m = {};
  function put(zh, en, allowShort){
    zh = String(zh == null ? '' : zh).trim();
    en = String(en == null ? '' : en).trim();
    // v5770（A）：生物名放宽到 2 字（禽龙/跳鼠/中猴/企鹅…）；物品/设施等其它来源仍要求 3 字
    var _min = allowShort ? 2 : 3;
    if (!zh || !en || zh.length < _min) return;
    if (!/[\u4e00-\u9fa5]/.test(zh)) return;
    if (zh === en) return;
    if (LB_ENM_STOP[en.toLowerCase().replace(/[\s\-_]/g, '')]) return;
    if (!m[zh]) m[zh] = en;
  }
  function splitZh(v, fallbackEn){
    var s = String(v == null ? '' : v).trim();
    var mm = s.match(/^(.+?)\s*[\(（\[]([^\)）\]]*)[\)）\]]\s*$/);
    if (mm) return { zh: mm[1].trim(), en: mm[2].trim() || fallbackEn };
    return { zh: s, en: fallbackEn };
  }
  try {
    var Z = (typeof ZH_MAP === 'object' && ZH_MAP) || {};
    Object.keys(Z).forEach(function(en){
      var s0 = String(Z[en] == null ? '' : Z[en]).trim();
      var m0 = s0.match(/^(.+?)\s*[\(（\[]([^\)）\]]*)[\)）\]]\s*$/);
      // v5764：**只有带括号的条目**才可用 —— 括号里才是真正的英文名；
      // 无括号条目的 key 是图标内部名（baseseeds_icon / condition_gainingexp_icon），当英文会出丑
      if (!m0) return;
      put(m0[1].trim(), m0[2].trim());
    });
  } catch (e1) {}
  try {
    var I = (typeof LB_ITEM_ZH === 'object' && LB_ITEM_ZH) || {};
    Object.keys(I).forEach(function(k){
      var o = I[k] || {};
      var _kd = String(o.kind || '');
      // v5774（用户口径「金属、黑曜石 为啥都没匹配」/ STOP 方案 A「完全取消」）：
      //   **第二道资源词限制，移除** —— v5762 除了 LB_ENM_STOP 之外还在这里按 kind==='resource' 挡，
      //   上一版（v5773）只清了 STOP 漏了这行 ⇒ 金属/水晶/燧石/木材/石头 仍进不了表。
      //   资源名词同样是方舟专名（金属·石头·木材·纤维·燧石·黑曜石·黏土·火药·聚合物…），应配英文小字。
      // v5771：排「特性」类 —— 武器/护甲 trait 的中文是「治疗/护盾/专注/刺客/工匠/背刺…」，
      //   是形容词/动词短语而非物品名，正文出现频率极高（「治疗效果」「护盾值」）⇒ 标了就是满屏错字
      if (_kd === 'trait') return;
      put(o.zh, o.en || k, true);       // v5771（用户口径）：物品放行 2 字（鱼竿/机床/篝火/冰箱…）
    });
  } catch (e2) {}
  try {
    var F = (typeof LB_FACILITY_ZH === 'object' && LB_FACILITY_ZH) || {};
    Object.keys(F).forEach(function(k){ var o = F[k] || {}; put(o.zh, o.en || k, true); });   // v5771：设施放行 2 字
  } catch (e3) {}
  /* v5768（用户口径「我的词汇匹配是否复用了 选物种/物品 的完整匹配逻辑」）：补齐权威来源
     ⚠ 全部与「选物种 / 选物品」浮窗同源，不另造表 */
  // ④ 物种全量：走 ASB 物种表推理链（含 Alpha / Ghost / 地图变体），与选物种器同一底座
  try {
    if (typeof lbSpKeysSorted === 'function' && typeof lbSpName === 'function'){
      var _allC = (lbSpKeysSorted() || {}).allCls || null;
      if (_allC){
        Object.keys(_allC).forEach(function(cls){
          var o = null;
          try { o = lbSpName(cls); } catch (eS) {}
          if (o && typeof o === 'object' && o.zh && o.eng) put(o.zh, o.eng, true);   // v5770：物种名允许 2 字
        });
      }
    }
  } catch (e5) {}
  // ⑤ 配置项（cfg_zh：{en: zh}）
  try {
    var CZ = (typeof LB_CFG_ZH === 'object' && LB_CFG_ZH) || null;
    if (CZ) Object.keys(CZ).forEach(function(k){ put(CZ[k], k); });
  } catch (e6) {}
  // ⑥ 基因特性（gene_traits_zh）
  try {
    var GZ = (typeof LB_GENE_ZH === 'object' && LB_GENE_ZH) || null;
    if (GZ) Object.keys(GZ).forEach(function(k){ var v = GZ[k]; put(typeof v === 'string' ? v : (v && v.zh), k); });
  } catch (e7) {}
  // ⑦ v5770（B）/ v5773：**别称 → 正名 → 英文**（统一通道，遍历所有别称表）
  //   物种俗称 LB_AI_DINO_ALIAS + 物品/建筑别称 LB_ZH_ALIAS ⇒ 由数据表驱动，本函数零词对
  //   v5773 起不再为每张表写一份循环：新增别称表只需往 _ALS 里加一项
  try {
    var _ALS = [
      (typeof LB_AI_DINO_ALIAS === 'object' && LB_AI_DINO_ALIAS) || null,
      (typeof LB_ZH_ALIAS === 'object' && LB_ZH_ALIAS) || null
    ];
    for (var _ti = 0; _ti < _ALS.length; _ti++){
      var _TB = _ALS[_ti];
      if (!_TB) continue;
      Object.keys(_TB).forEach(function(alias){
        var canon = String(_TB[alias] || '').trim();
        if (!alias || alias.length < 2 || !canon || canon === alias) return;
        // v5776：值含 ASCII 字母 ⇒ **直接当英文用**（正名只有 1 个字时，如「沙」「油」，
        //   该正名因引擎最短 2 字限制从未进过 m ⇒ 查 m[canon] 必然取空，只能直接给英文）
        var en = /[A-Za-z]/.test(canon) ? canon : m[canon];
        if (en && !m[alias]) m[alias] = en;
      });
    }
  } catch (e8) {}
  try {
    Object.keys(LB_WT_TERMS).forEach(function(en){ put(LB_WT_TERMS[en], en); });
  } catch (e4) {}
  var mx = 2;   // v5770：允许 2 字专名（仅物种来源会产出 2 字键）
  Object.keys(m).forEach(function(z){ if (z.length > mx) mx = z.length; });
  LB_ENM_MAX = Math.min(mx, 24);
  LB_ENM_REV = m;
  LB_ENM_SIG = sig;
  return m;
}
/* 单段文本 → HTML 片段（无命中返回 null） */
function lbEnMarkText(txt){
  var rev = lbEnRevMap();
  if (!rev || !txt) return null;
  var mx = LB_ENM_MAX, out = '', buf = '', i = 0, n = txt.length, hit = 0;
  while (i < n){
    var found = null, fl = 0;
    for (var L = Math.min(mx, n - i); L >= 2; L--){   // v5770：最短 2 字
      var sub = txt.substr(i, L);
      if (rev[sub]){ found = rev[sub]; fl = L; break; }
    }
    if (found){
      out += tcEsc(buf) + '<span class="tc-en" data-enm="1"><i>\u300c' + tcEsc(txt.substr(i, fl)) + '\u300d</i><sub>' + tcEsc(found) + '</sub></span>';
      buf = '';
      i += fl;
      hit++;
    } else {
      buf += txt.charAt(i);
      i++;
    }
  }
  if (!hit) return null;
  return out + tcEsc(buf);
}
/* 遍历 root 内文本节点做标记 */
function lbEnMark(root){
  if (!root || LB_ENM_BUSY) return 0;
  var rev = lbEnRevMap();
  if (!rev || !Object.keys(rev).length) return 0;
  LB_ENM_BUSY = 1;
  var nodes = [], n = 0;
  try {
    var wk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    while (wk.nextNode()){
      var nd = wk.currentNode, p = nd.parentNode;
      if (!p) continue;
      var tag = (p.nodeName || '').toUpperCase();
      if (tag === 'CODE' || tag === 'PRE' || tag === 'SCRIPT' || tag === 'STYLE' || tag === 'TEXTAREA') continue;
      // v5780（用户口径「我发现了 根源是你漏了置顶正文都应该 AI 整理，标记只标注 AI 整理块」）：
      //   **范围收回** —— v5778 把准入扩到 .tc-intro/.tc-sec/.tc-note/... 属于超范围（用户明确否掉）。
      //   正确做法不是「放宽标记范围去覆盖没 AI 的块」，而是**让那些块真正走 AI 整理**（见 renderTame/
      //   renderGather/renderSpawn 的 v5780 改动）。标记本身只认 AI 整理容器。
      // v5784（用户口径「附件不走 AI 整理，但是要走标注」）：`.abil-desc`（技能演示下方描述）
      //   作为**明确例外**纳入 —— 它保持 wikily 原文不做 AI 整理，但仍然要中英小字 + 正名。
      if (!p.closest || !p.closest('.tc-ai, .tc-auth-i, .tc-tipd-p, .tc-tipd-t, .abil-desc')) continue;
      if (p.closest('.tc-code, .tc-codeline, .tc-top, .tc-badge, .tc-badge2, .tc-en, pre, .lb-hf-aiinput, .lw-tab, .lb-picker-overlay')) continue;
      var tx = nd.nodeValue || '';
      if (!tx || !/[\u4e00-\u9fa5]/.test(tx)) continue;
      if (/[A-Za-z]{3,}_[A-Za-z]/.test(tx)) continue;      // 蓝图/类名保护
      nodes.push(nd);
    }
  } catch (eTW) { LB_ENM_BUSY = 0; return 0; }
  for (var i = 0; i < nodes.length; i++){
    var nd2 = nodes[i], html = null;
    try { html = lbEnMarkText(nd2.nodeValue || ''); } catch (e1) { html = null; }
    if (!html) continue;
    try {
      var holder = document.createElement('span');
      holder.innerHTML = html;
      var frag = document.createDocumentFragment();
      while (holder.firstChild) frag.appendChild(holder.firstChild);
      nd2.parentNode.replaceChild(frag, nd2);
      n++;
    } catch (e2) {}
  }
  LB_ENM_BUSY = 0;
  return n;
}
/* 给容器挂 observer（元素存在返回 true） */
function lbEnMarkWatch(id){
  var el = document.getElementById(id);
  if (!el || LB_ENM_MO[id]) return !!el;
  try {
    LB_ENM_MO[id] = new MutationObserver(function(){
      if (LB_ENM_BUSY) return;
      if (LB_ENM_T[id]) clearTimeout(LB_ENM_T[id]);
      LB_ENM_T[id] = setTimeout(function(){
        if (LB_ENM_BUSY) return;
        try { lbEnMark(document.getElementById(id)); } catch (e) {}
      }, 90);
    });
    LB_ENM_MO[id].observe(el, { childList: true, subtree: true });
    setTimeout(function(){ if (!LB_ENM_BUSY) { try { lbEnMark(el); } catch (e) {} } }, 120);
  } catch (eMO) { delete LB_ENM_MO[id]; }
  return true;
}
(function(){
  var tries = 0;
  function boot(){
    var a = lbEnMarkWatch('lbWikiBody'), b = lbEnMarkWatch('lbWikiItemBody');
    if ((!a || !b) && tries < 8){ tries++; setTimeout(boot, 500); }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();

/* v5782（用户实测「一键整理两次都无效」的真因）：**AI 整理输出的字段清单唯一来源**。
   ⚠ 历史教训：这份清单原本在 3 处各自硬编码 ——
     ① lbWtCollect() 收集什么素材
     ② SYS prompt 的 JSON 结构（让 AI 返回什么）
     ③ lbWtDigest() 里提取 AI 结果的 blocks 白名单
   v5780/v5781 只改了 ①② 就以为通了，③ 还停在 5 个旧 key ⇒ AI 即使返回 abilIntro /
   gatherIntro / harvestIntro / expIntro 也会在这一步被**静默丢弃**，写不到后端。
   现在 ③ 改成遍历本清单；新增字段时**只需改这里 + 加一行收集 + 改 prompt 文本**。 */
var LB_WT_OUT_KEYS = ['ovIntro', 'ovTips', 'tameIntro', 'gatherIntro', 'abilIntro', 'expIntro', 'breedDesc', 'spawnIntro', 'gearTips'];   // v5826：补 gearTips（装备要点）   // v5800：收割 Tab 已隐藏 ⇒ 去掉 harvestIntro

function lbWtApi(){
  var b = (typeof LB_API === 'string' && LB_API) ? LB_API : 'https://data.whiterober.ccwu.cc';
  return String(b).replace(/\/+$/, '') + '/api/dino/wikitext';
}
function lbWtSlug(){ try { return String((LB_WIKI || {}).cur || ''); } catch (e) { return ''; } }

/* 取整理结果；没有则回落 wikily 原文 */
var LB_WT_LAST_AI = 0;   // v5765：记录上一次 lbWtPick 命中的是否 AI 整理结果
function lbWtPick(key, fallback){
  var d = LB_WT.data;
  if (d && d[key] && d[key].length){ LB_WT_LAST_AI = 1; return d[key]; }
  LB_WT_LAST_AI = 0;
  return fallback || [];
}
/* 技能描述按技能名对位取整理结果 */
function lbWtAbilDesc(zh, orig){
  var d = LB_WT.data;
  var nm = String(zh || '').trim();
  if (d && (d.abil || []).length && nm){
    for (var i = 0; i < d.abil.length; i++){
      if (String((d.abil[i] || {}).zh || '').trim() === nm){
        LB_WT_LAST_AI = 1;   // v5768：技能描述命中 AI 整理 ⇒ 下游容器打 .tc-ai
        return String(d.abil[i].desc || orig || '');
      }
    }
  }
  LB_WT_LAST_AI = 0;
  return orig || '';
}
/* v6031（用户实测「菊石 甚至都不能骑，怎么你还在抓到了操作键？」）：
   根因 —— 后端 88 个物种源缓存里**只有泰克悬浮艇 1 个**有 wiki.gg Controls 原文（HOME.abilKeys），
   其余全无素材；而整理提示词里既写了「操作键必须逐条写成『按键 + 中文动作』短句」，
   又给了**带具体键位的可抄示例**⇒ AI 没素材就照抄示例 + 补一套通用键位。
   菊石实测输出 6 条全是通用模板，还把源缓存里**真实的**两条战斗说明（受伤倍率）整段丢了。
   判定（不依赖「是否可骑」——没鞍不一定没操作）：AI 的 abilIntro **全部**都是键位行（0 条文字总述），
   而源缓存里**有**真实文字内容 ⇒ 判定 AI 丢了原文换键位，回落源缓存原文。 */
function lbWtAbilIntroDropped(fbArr){
  var fb = (fbArr || []).filter(function (x) { return !!String(x == null ? '' : x).trim(); });
  if (!fb.length) return false;
  var ai = [];
  try { ai = (LB_WT.data && LB_WT.data.abilIntro) || []; } catch (e) { return false; }
  if (!ai.length) return false;
  var txt = 0;
  ai.forEach(function (s) {
    var t = String(s == null ? '' : s).trim();
    if (!t) return;
    var r = null;
    try { r = lbAbilParseKeys([t]); } catch (e) { r = null; }
    if (!(r && r.length)) txt++;
  });
  return txt === 0;
}

/* 读某个物种的整理结果（切物种时调用） */
/* v6029（用户实测「附件浮窗不断闪烁」/「90 次重渲染既吃性能也没必要」）：**防重复拉取** ——
   原逻辑「ready||data 才复用，否则重置 LB_WT 再 fetch」：当该物种**没有 AI 整理结果**时
   （后端返 ok=false 或 ready=false ⇒ data 恒为 null、ready 恒为 false），每次调用都会重新拉；
   而 lbWikiRender 的 err 分支在回调里又调 lbWikiRender ⇒ fetch→render→fetch 死循环，
   实测 4 次/秒重建整个 #lbWikiBody 并打后端接口 ⇒ 浮窗闪烁 + 白耗流量。
   修法：按 slug 记一次性标记，试过且无数据就直接异步回调（不再 fetch）。切物种时由 lbWikiOpen 清空。 */
var LB_WT_TRIED = {};
function lbWtLoad(cb){
  var slug = lbWtSlug();
  if (!slug){ if (cb) cb(); return; }
  if (LB_WT.slug === slug && (LB_WT.ready || LB_WT.data)){ if (cb) cb(); return; }
  if (LB_WT_TRIED[slug]){ if (cb) setTimeout(cb, 0); return; }   /* v6029：已试过且无数据 ⇒ 不再重复拉取（异步回调，防同步递归） */
  LB_WT_TRIED[slug] = 1;
  LB_WT = { slug: slug, data: null, busy: false, msg: '', ready: false };
  fetch(lbWtApi() + '?slug=' + encodeURIComponent(slug), { cache: 'no-store' })
    .then(function(r){ return r.json(); })
    .then(function(j){
      if (LB_WT.slug !== slug) return;
      if (j && j.ok){
        LB_WT.ready = !!j.ready;
        LB_WT.data = j.blocks || null;
      }
      if (cb) cb();
    })
    .catch(function(){ if (cb) cb(); });
}

/* 收集当前物种的 6 类 wikily 原文 */
function lbWtCollect(){
  // ⚠ 新增字段时必须同步三处：本函数 + LB_WT_OUT_KEYS（在 lbWtApi 上方）+ SYS prompt 的 JSON 结构
  var out = {};
  var ov = {};
  try {
    var _wk = lbWikiKey(LB_WIKI.cur);
    ov = (LB_WIKI.data.OVERVIEW || {})[_wk] || {};
  } catch (e) { ov = {}; }
  if ((ov.intro || []).length) out.ovIntro = ov.intro.slice();
  // v5746：OVERVIEW.tips 已归「技巧」线（喂进技巧整合），不再作为原文案素材
  var ti = []; try { ti = wikiTabIntro('tameIntro') || []; } catch (e) {}
  if (ti.length) out.tameIntro = ti.slice();
  var bd = []; try { bd = BREED_DESC[CUR] || []; } catch (e) {}
  if (bd.length) out.breedDesc = bd.slice();
  var ab = [];
  try {
    ab = (((ABIL[CUR] || {}).skills) || []).filter(function(x){ return x && x.zh && x.desc; })
      .map(function(x){ return { zh: x.zh, desc: x.desc }; });
  } catch (e) { ab = []; }
  if (ab.length) out.abil = ab;
  var sp = []; try { sp = (SPAWN[CUR] || {}).intro || []; } catch (e) {}
  if (sp.length) out.spawnIntro = sp.slice();
  // v5780（用户口径「置顶正文都应该 AI 整理」）：采集 Tab 置顶正文此前从未进整理链路
  var ga = [];
  try {
    var _gd = GATHER[CUR] || {};
    if (_gd.about) ga.push(String(_gd.about));
    if ((_gd.intro || []).length) ga = ga.concat(_gd.intro.filter(function(x){ return !!x; }));
    /* v5788（用户口径「采集加成数据当素材」）：wikily「采集能力」页对多数物种抓不到正文
       （intro / about 全空），此时 prompt 里连【采集页原文】分组都没有 —— AI 缺归属锚点，
       会把采集内容留在概览/技能里、就是不搬进 gatherIntro。这里用结构化数据补一段素材。 */
    var _capTxt = (_gd.caps || []).map(function(c){
      var _z = String((c && c.zh) || '').trim();
      if (!_z) return '';
      // v5789：素材里的物品名必须走项目正式中文名（wiki 原文「几丁质」→ 表内「甲壳素」），
      //   否则 AI 会把错名写进 gatherIntro，与页面其它位置的显示不一致
      var _zn = _z; try { _zn = lbWikiZhName(_z) || _z; } catch (e2) {}
      return _zn + ((c && c.mult && String(c.mult) !== '1') ? (' ' + c.mult + '倍') : '');
    }).filter(function(x){ return x; });
    var _amv = _gd.params && _gd.params.amtMult;
    var _amTxt = (_amv != null && String(_amv) !== '' && String(_amv) !== '1') ? ('采集量倍率 ' + _amv + '倍。') : '';
    if (_capTxt.length) ga.push('采集加成数据：' + _capTxt.join('、') + '。' + _amTxt);
    else if (_amTxt) ga.push(_amTxt);
  } catch (e) { ga = []; }
  if (ga.length) out.gatherIntro = ga.slice();
  // v5781：收割 / 技能 / 经验 三个 Tab 的置顶正文——此前**从未进整理链路**（前端不收 + 后端白名单不列）
  /* v5800（用户口径「既然收割 TAB 消失了，同步调整 AI 提示词」）：
     收割 Tab 已隐藏 ⇒ harvestIntro 不再是输出位；但收割页原文（尸体可采资源、击杀产物、
     工具对产量影响）仍有价值 ⇒ 并入 gatherIntro 素材，由 AI 写进「采集」页，信息不丢。 */
  var hv = []; try { hv = wikiTabIntro('harvestIntro') || []; } catch (e) {}
  if (hv.length){
    ga = ga.concat(hv.filter(function(x){ return !!x; }));
    if (ga.length) out.gatherIntro = ga.slice();
  }
  var ai2 = []; try { ai2 = (lbAbilIntroPick().list) || []; } catch (e) {}
  if (ai2.length) out.abilIntro = ai2.slice();
  /* v5857（用户口径「后端英文数据 也不能丢啊 应该喂给AI」）：
     v5856 改成只从中文字面解析按键后，后端 wiki.gg Controls 段的结构化英文数据
     （HOME.abilKeys = [{k,a}]）就完全没人用了 —— 那是权威原文，必须在整理阶段喂给 AI，
     由 AI 结合中文文案一起产出带按键的中文短句。这里单独作为素材位，不与 abilIntro 重复。 */
  try {
    var _akRaw = [];
    try { _akRaw = wikiTabIntro('abilKeys') || []; } catch (eAK0) { _akRaw = []; }
    var _akT = [];
    (_akRaw || []).forEach(function (x) {
      var _kk = String((x && x.k) || '').trim();
      var _aa = String((x && x.a) || '').trim();
      if (!_kk && !_aa) return;
      _akT.push(_kk ? (_kk + ' -> ' + _aa) : _aa);
    });
    if (_akT.length) out.abilKeys = _akT.slice(0, 40);
  } catch (eAK) {}
  var ex = []; try { ex = wikiTabIntro('expIntro') || []; } catch (e) {}
  if (ex.length) out.expIntro = ex.slice();
  // v5826（用户口径「AI 生成技巧或整理原文时，也要考虑到装备」）：把该物种的鞍/附件清单作为素材喂进去
  try {
    var _gl = lbSeriesGears(lbCurSpKey());
    if (_gl.length){
      out.gearList = _gl.map(function (g) {
        return g.zh + (g.en ? ('（' + g.en + '）') : '') + ' · ' + ((g.kind === 'saddle') ? '鞍' : '附件');
      });
    }
  } catch (eGL) {}
  return out;
}

/* 调 AI 整理当前物种的 wikily 原文，成功后回写后端共享缓存 */
function lbWtDigest(force){
  if (LB_WT.busy) return;
  var slug = lbWtSlug();
  if (!slug) return;
  if (LB_WT.ready && !force){
    try { if (typeof lbToast === 'function') lbToast('该物种的原文已整理过'); } catch (e0) {}
    return;
  }
  var cfg = null; try { cfg = lbAiCfgGet(); } catch (e1) {}
  if (!cfg || !cfg.token){
    try { if (typeof lbToast === 'function') lbToast('请先在「⚙ 配置」里填大肥鱼 token'); } catch (e2) {}
    try { lbOpenConfigModal(); } catch (e3) {}
    return;
  }
  var raw = lbWtCollect();
  var total = 0;
  Object.keys(raw).forEach(function(k){ total += raw[k].length; });
  if (!total){ LB_WT.msg = '该物种没有可整理的原文'; lbWtRepaint(); return; }

  LB_WT.busy = true; LB_WT.msg = '整理中…'; lbWtRepaint();

  var SYS = '你是《方舟：生存飞升》的资料编辑。下面是一个物种从 wiki 抓来的全部原文段落，已按来源分好组。\n'
    + '任务：把这些原文**整理归纳后重新分配到 8 个展示位置**。\n\n'
    + '硬性要求：\n'
    + '1) **去重**：同一个知识点只保留一处；两个来源讲同一件事时合并成一段更完整的表述。\n'
    + '2) **按内容重新分配**（可以搬走，不必留在原位置）：\n'
    + '   · ovIntro（概览·概述）= 物种定位、体型、生态、驯服难度、与原版差异等「是什么」\n'
    + '   · ovTips（概览·技巧）= 通用实战心得、冷知识、注意事项（不含具体驯服/繁殖步骤）\n'
    + '   · tameIntro（驯服）= 击晕手法、武器弹药、饲料与喂食节奏、麻醉与眩晕维持、驯服后等级\n'
    + '   · breedDesc（繁殖）= 交配、孵化、成长、留痕、变异\n'
    + '   · gatherIntro（采集）= 采集能力、可采资源、采集加成、采集工具；以及击杀/尸体可采资源、收割产物与工具对产量的影响（原「收割」页内容一律归这里，不再有独立「收割」位）\n'
    + '   · abilIntro（技能）= 战斗方式与技能总述（**逐个技能的作用放 abil，不要写这里**）；**仅当用户消息里真的出现【操作键原文（wiki.gg Controls）】分组时**，才把该分组的按键逐条写成「按键 + 中文动作」短句追加在后面（一条一句）。分组不存在 ⇒ 这里只写文字总述，不写任何按键（见第 10、11 条）\n'
    + '   · expIntro（经验）= 经验获取方式与倍率相关说明\n'
    + '   · spawnIntro（生成）= 控制台/管理员命令相关说明\n'
    + '   · abil（技能）= 逐个技能的作用说明，**必须与给定技能名一一对应，不要新增、改名或合并**\n'
    + '   · gearTips（装备要点）= 针对【可装备物品】清单逐条说明该装备的用途、搭配与注意事项（鞍、附件同样算装备）；'
    + '**只写你说得清的**，资料未提及的数值与机制一律不得编造（沿用「不得编造」条）；清单为空就返回 []\n'
    + '3) **措辞**：简体中文、玩家习惯译法；每段 1~3 句；不要 markdown 符号（不要 #、*、-）；\n'
    + '   不要出现「原文」「来源」「wiki」之类字样。\n'
    + '4) **宁缺勿滥**：某位置没有合适内容就返回空数组，绝不硬凑。\n'
    + '5) **细节不丢**：具体数字（时间、倍率、数量、等级、伤害）必须保留。\n'
    + '6) **术语强制中文化（硬性）**：方舟专有名词 —— 生物名、物品名、设施/建筑名、地图与生物群系名、天气名、伤害类型、状态与 buff 名、生长阶段、数值单位 —— **必须使用用户消息【必须使用的中文译名】里给出的中文**，逐字照抄、不得改写或另取译名；清单未覆盖的英文词，按 ARK 中文社区通行译法译成中文。除 ASA / PvE / PvP / DPS 这类通用缩写外，**输出正文不得残留任何英文单词或词组**；确实无通行译法的写成「中文（原词）」且全文只出现一次。宁可意译，也绝不保留英文原词。\n'
    + '7) **禁止照搬原文英文**：原文本身是机翻时，把英文术语原样抄进输出等同未完成；遇到「XX 伤害」「XX 抗性」「XX 攻击」这类结构，XX 必须换成中文术语。\n'
    + '8) **物种名一律用正式名（硬性）**：正文凡指代本物种，必须使用用户消息【物种表 · 正式中文名】给出的名字；原文中出现的一切其它叫法（第三方译名、俗称、旧译、简称）**全部改写为正式名**，既不保留也不并列写出。正文提到的其它物种，同样要能对上项目物种表的正式名。\n\n'
    + '9) **采集内容必须归入 gatherIntro（硬性，优先于第 4 条「宁缺勿滥」）**：凡涉及「这个物种能采什么资源、采集/采伐倍率、采集工具、采集范围、骑乘采集加成」的描述，**一律写入 gatherIntro**，不得只留在 ovIntro 或 abilIntro 里；写进 gatherIntro 之后，**原位置不得再保留同一句**（同义重复同样禁止）。若用户消息里给了【采集加成数据】，必须据此写出一条采集概述。\n\n'
    + '10) **操作键只认素材（硬性）**：**仅当用户消息里出现【操作键原文（wiki.gg Controls）】分组时，本条才生效**。\n'
    + '    该分组**存在**时：其中给出的**每一条**都要写进 abilIntro，改写为中文「按键 + 中文动作」短句；'
    + 'Hold/Tap/Press/Held 译成「按住/轻按/按下」；WS/AD 这类连写键拆成「W/S」「A/D」；Cursor 译成「鼠标」；键盘键用大写单字母或 Ctrl/Shift/Alt/空格/Tab 的通行中文写法。'
    + '**不得把按键改写成纯文字描述，不得漏条目，不得保留英文长句。**'
    + '每一条都必须明确写出按键（如「按住 鼠标左键 填充目标进度条」）；'
    + '原文某条只写了手势没写按键时，按同一段 Controls 里该分组的按键补全；实在无法确定才省略该条。\n'
    + '    该分组**不存在**时：abilIntro **一条操作键都不许出现**，只写战斗方式与技能总述的文字。\n'
    + '    **严禁凭游戏常识、凭本提示词里的示例、凭其它物种的按键去编造键位**——W/A/S/D、Shift、空格、Ctrl、鼠标左键/右键这类「通用键位」尤其禁止：不同物种（尤其不可骑乘的野生生物）操作方式差异极大，编出来的按键就是错误信息。\n\n'
    + '11) **不可骑乘物种不得有操作键（硬性）**：若该物种不能被玩家骑乘 / 驾驶 / 操控（例如只能被大型生物叼走或携带的菊石、三叶虫、水母、腔棘鱼这类野生小型生物），abilIntro 只能写战斗方式与技能总述的文字，**绝对不许出现任何「按键 + 动作」短句**。\n\n'
    + '输出严格 JSON（不要代码块）：\n'
    + '{"ovIntro":[],"ovTips":[],"tameIntro":[],"gatherIntro":[],"abilIntro":[],"expIntro":[],"breedDesc":[],"abil":[{"zh":"技能名","desc":"说明"}],"spawnIntro":[],"gearTips":[]}';

  var parts = [];
  if (raw.ovIntro) parts.push('【概览·概述原文】\n' + raw.ovIntro.map(function(s, i){ return (i + 1) + '. ' + s; }).join('\n'));
  if (raw.ovTips) parts.push('【概览·技巧原文】\n' + raw.ovTips.map(function(s, i){ return (i + 1) + '. ' + s; }).join('\n'));
  if (raw.tameIntro) parts.push('【驯服页原文】\n' + raw.tameIntro.map(function(s, i){ return (i + 1) + '. ' + s; }).join('\n'));
  if (raw.breedDesc) parts.push('【繁殖页原文】\n' + raw.breedDesc.map(function(s, i){ return (i + 1) + '. ' + s; }).join('\n'));
  if (raw.abil) parts.push('【技能列表原文】\n' + raw.abil.map(function(x){ return '· ' + x.zh + '：' + x.desc; }).join('\n'));
  if (raw.gatherIntro) parts.push('【采集/收割页原文】\n' + raw.gatherIntro.map(function(s, i){ return (i + 1) + '. ' + s; }).join('\n'));
  if (raw.abilIntro) parts.push('【技能总述原文】\n' + raw.abilIntro.map(function(s, i){ return (i + 1) + '. ' + s; }).join('\n'));
  // v5857：后端 wiki.gg Controls 结构化原文（按键 -> 动作）必须一起喂给 AI
  if (raw.abilKeys) parts.push('【操作键原文（wiki.gg Controls）】\n' + raw.abilKeys.map(function(s, i){ return (i + 1) + '. ' + s; }).join('\n'));
  if (raw.expIntro) parts.push('【经验页原文】\n' + raw.expIntro.map(function(s, i){ return (i + 1) + '. ' + s; }).join('\n'));
  if (raw.spawnIntro) parts.push('【生成命令页原文】\n' + raw.spawnIntro.map(function(s, i){ return (i + 1) + '. ' + s; }).join('\n'));
  // v5826：可装备物品清单（AI 必须据此写 gearTips，并在 ovTips 里结合装备说明打法）
  if (raw.gearList) parts.push('【可装备物品】\n' + raw.gearList.map(function(s, i){ return (i + 1) + '. ' + s; }).join('\n'));
  // v5759：注入「必须使用的中文译名」—— 由页面中英对照表模糊匹配得出，AI 必须逐字采用
  var _gl = {}, _glKeys = [], _glBlock = '';
  try {
    _gl = lbWtGlossHits(raw);
    _glKeys = Object.keys(_gl);
    if (_glKeys.length){
      _glBlock = '【必须使用的中文译名】（原文出现的方舟术语，输出必须用右侧中文，不得保留左侧英文）\n'
        + _glKeys.map(function(en){ return '· ' + en + ' → ' + _gl[en]; }).join('\n') + '\n\n';
    }
  } catch (eGL) { _glBlock = ''; }
  // v5761：改走公共函数（与技巧链路**同一实现**，避免再次只修一边）
  var _nameBlock = lbWtNameBlocks(slug, parts.concat(_glKeys));
  var usr = '物种：' + slug + '\n\n' + _nameBlock + _glBlock + parts.join('\n\n');

  fetch(String(cfg.base || LB_AI_BASE).replace(/\/+$/, '') + '/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + cfg.token },
    body: JSON.stringify({
      model: lbAiNormModel(cfg.model),
      messages: [{ role: 'system', content: SYS }, { role: 'user', content: usr }],
      temperature: 0.25, max_tokens: 8000,
      thinking: { type: 'disabled' },
      response_format: { type: 'json_object' }
    })
  }).then(function(r){ return r.text().then(function(tx){ return { s: r.status, t: tx }; }); })
    .then(function(x){
      LB_WT.busy = false;
      if (x.s !== 200){ LB_WT.msg = '接口错误 ' + x.s + '：' + String(lbAiErrText(x.s) || ''); lbWtRepaint(); return; }
      var j = null; try { j = JSON.parse(x.t); } catch (eJ) {}
      var ch0 = (j && j.choices && j.choices[0]) ? j.choices[0] : null;
      var m0 = (ch0 && ch0.message) ? ch0.message : null;
      var content = (m0 && m0.content) ? String(m0.content) : '';
      var d = null;
      try { d = lbAiParseJson(content); } catch (eP) {}
      if (!d && m0 && m0.reasoning_content){ try { d = lbAiParseJson(String(m0.reasoning_content)); } catch (eR) {} }
      if (!d || typeof d !== 'object'){ LB_WT.msg = '整理结果无法解析'; lbWtRepaint(); return; }

      var blocks = {};
      /* v5838（用户反馈装备要点里出现「[object Object]」）：
         AI 偶尔把数组元素写成对象（如 {装备:"…", 说明:"…"}），旧代码 String(s) 直接拍平成
         "[object Object]"，还被 POST 进缓存 ⇒ 永久脏数据。这里统一抽可读文本。 */
      var _wtFlat = function (s) {
        if (s === null || s === undefined) return '';
        var tp = typeof s;
        if (tp === 'string') return s.trim();
        if (tp === 'number' || tp === 'boolean') return String(s);
        if (tp !== 'object') return '';
        var _ks = ['t', 'text', 'point', 'zh', 'desc', 'title', 'name', 'note', 'n', 'd', 'v', 'k', 'a', 'p'];
        var _vals = [];
        for (var _i = 0; _i < _ks.length; _i++){
          var _x = s[_ks[_i]];
          if (typeof _x === 'string' && _x.trim()) { _vals.push(_x.trim()); break; }
        }
        if (!_vals.length){
          for (var _k in s){
            if (!Object.prototype.hasOwnProperty.call(s, _k)) continue;
            var _y = s[_k];
            if (typeof _y === 'string' && _y.trim()) _vals.push(_y.trim());
            else if (typeof _y === 'number' || typeof _y === 'boolean') _vals.push(String(_y));
          }
        }
        return _vals.join('：');
      };
      var _wtClean = function (v) {
        var out = [];
        (v || []).forEach(function (s) {
          var tx = _wtFlat(s);
          if (!tx) return;
          if (tx === '[object Object]') return;
          if (out.indexOf(tx) < 0) out.push(tx);
        });
        return out;
      };
      // v5782：遍历**唯一清单**（原来是硬编码 5 个旧 key ⇒ 新字段全被丢弃）
      LB_WT_OUT_KEYS.forEach(function(k){
        var v = d[k];
        if (Array.isArray(v)){
          var arr = _wtClean(v);
          if (arr.length) blocks[k] = arr;
        }
      });
      if (Array.isArray(d.abil)){
        var ab = [];
        d.abil.forEach(function(it){
          if (!it || typeof it !== 'object') return;
          var zh = String(it.zh || '').trim(), ds = String(it.desc || '').trim();
          if (zh && ds) ab.push({ zh: zh, desc: ds });
        });
        if (ab.length) blocks.abil = ab;
      }
      LB_WT.data = blocks; LB_WT.ready = true; LB_WT.msg = '整理完成';
      lbWtRepaint();
      fetch(lbWtApi(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slug: slug, blocks: blocks, force: !!force })   // v5768：重新整理必须能覆盖旧缓存
      }).catch(function(){});
    })
    .catch(function(e){
      LB_WT.busy = false;
      LB_WT.msg = '网络错误：' + String((e && e.message) || e);
      lbWtRepaint();
    });
}

/* 重新渲染当前 tab（整理完成后让各 TAB 立刻用上新文案） */
function lbWtRepaint(){
  try {
    var i = lbWikiTabIdx();
    if (i === 0) renderOverview();
    else if (i === 1) renderTame();
    else if (i === 2) renderBreed();
    else if (i === 5) renderAbilTab();
    else if (i === 8) renderSpawn();
    else lbWikiRender();
  } catch (e) {}
}

/* 概览底部的整理入口（标准 AI 模块外壳，仅手动触发） */
function lbWtEntryHtml(){
  var st;
  if (LB_WT.busy) st = lbWtEsc(LB_WT.msg || '整理中…');
  else if (LB_WT.ready) st = '该物种原文已整理';
  else if (LB_WT.msg) st = lbWtEsc(LB_WT.msg);
  else st = '原文尚未整理 —— 整理后各 TAB 的说明会重新分配';
  return lbTipsAiBoxHtml({
    state: st,
    style: 'margin-top:14px',
    disabled: !!LB_WT.busy,
    btn: { txt: (LB_WT.ready ? '重新整理' : 'AI 整理原文'), fn: 'lbWtDigest(true)' }
  });
}
function lbWtEsc(s){ return lbTipsEsc(s); }

/* 入口：renderTame 等同级 renderer 调用它填充 #lbWikiBody */
/* v5832（用户口径「技巧只从 wiki 分解即可」）：
   当前物种的 wiki 原文要点素材。ark 回退物种没有玩家心得，但仍可只凭原文让 AI 分解成要点。 */
function lbTipsOvSrc(){
  var out = null;
  try {
    var _k = lbWikiKey(LB_WIKI.cur);
    out = (((LB_WIKI.data || {}).OVERVIEW || {})[_k] || {}).tips || null;
    if ((!out || !out.length) && (LB_WIKI.data || {}).OVERVIEW) out = LB_WIKI.data.OVERVIEW.tips || null;
  } catch (e) { out = null; }
  out = (out && out.length) ? out.slice() : [];
  /* v5852（用户口径「AI 还是显示 没有可整合的心得，找根因」）：
     载具 / 器械在 wikily 页**没有「技巧」段**，而 dododex 也无载具心得 ⇒
     lbTipsDigest 三个素材源全空，直接提示「没有可整合的心得」。
     这里在无「技巧」时，改用其它置顶文案（概述 / 驯服 / 技能 / 采集）当原文素材。 */
  if (!out.length){
    try {
      var _ovx = (((LB_WIKI.data || {}).OVERVIEW || {})[lbWikiKey(LB_WIKI.cur)] || {}) || {};
      var _addT = function (arr) {
        (arr || []).forEach(function (x) {
          var s = String(x == null ? '' : x).trim();
          if (s && out.indexOf(s) < 0) out.push(s);
        });
      };
      _addT(_ovx.intro);
      ['tameIntro', 'abilIntro', 'harvestIntro', 'expIntro'].forEach(function (f) {
        try { _addT(wikiTabIntro(f)); } catch (eA) {}
      });
      if (out.length > 24) out = out.slice(0, 24);
    } catch (e2) {}
  }
  return out;
}

/* v5848（用户口径「回退物品页 只用物品页的数据」 + C2）：
   物种在 wikily 无页面时（载具 / 器械），dododex 也无心得 ⇒ AI 整理无素材。
   这里把「对应物品页」的 PARSED（描述 / 标签 / 印痕 / 工作台 / 配方 / 属性 / 官方要点）
   展成文本行，作为「游戏资料原文」市场供给 AI。 */
function lbTipsFbSrc(){
  try {
    var st = LB_WIKI.itemFB || null;
    var p = (st && st.data && st.data.PARSED) || null;
    if (!p) return [];
    var out = [];
    if (p.zh) out.push('物品：' + String(p.zh));
    if (p.tags && p.tags.length) out.push('标签：' + p.tags.join(' / '));
    if (p.desc) out.push('描述：' + String(p.desc));
    if (p.kick) out.push('印痕：' + String(p.kick));
    if (p.station && p.station.length) out.push('工作台：' + p.station.join(' / '));
    (p.mats || []).slice(0, 24).forEach(function (m) {
      if (!m || !m[0]) return;
      out.push('材料：' + String(m[0]) + ' × ' + (m[1] == null ? '?' : String(m[1])));
    });
    (p.attrs || []).slice(0, 24).forEach(function (kv) {
      if (!kv || !kv[0]) return;
      out.push('属性：' + String(kv[0]) + ' = ' + (kv[1] == null ? '' : String(kv[1])));
    });
    var ak = p.ark || {};
    (ak.keys || []).forEach(function (x) { if (x && x.a) out.push('按键：' + String(x.a) + ' → ' + String(x.k || '')); });
    (ak.points || []).slice(0, 12).forEach(function (s) { if (s) out.push('要点：' + String(s)); });
    return out;
  } catch (e) { return []; }
}

/* v5834：把「按当前物种初始化 LB_TIPS」抽出来 —— 概览底部的 AI 模块也要用它 */
function lbTipsEnsure(){
  var slug = '';
  try { slug = String((LB_WIKI || {}).cur || ''); } catch (e0) {}
  var cls = '';
  try { cls = String((LB && LB.curClass) || ''); } catch (e1) {}
  if (LB_TIPS.slug !== slug){
    LB_TIPS = { slug: slug, cls: cls, st: 'idle', items: [], summary: '', zh: {}, merged: null, err: null, busy: false, msg: '', needTok: false };
    if (slug) setTimeout(function(){ if (LB_TIPS.slug === slug && LB_TIPS.st === 'idle') lbTipsLoad(false); }, 30);
    return true;
  }
  return false;
}

/* v5834（用户口径「技巧 TAB 根据有没有整理出技巧来决定展示」）：是否已有 AI 整理结果 */
function lbTipsHasResult(){
  try {
    var m = LB_TIPS && LB_TIPS.merged;
    return !!(m && (((m.secs || []).length) || ((m.auth || []).length)));
  } catch (e) { return false; }
}

/* AI 外壳的状态行文案（原 lbTipsListHtml 底部的 _foot，v5834 抽出共用） */
function lbTipsFootText(){
  var m = (LB_TIPS && LB_TIPS.merged) || {};
  var secs = m.secs || [], auth = m.auth || [];
  if (LB_TIPS.busy) return '更新中… ' + lbTipsEsc(LB_TIPS.msg || '');
  if (LB_TIPS.needTok) return '未配置模型 token，无法整理';
  if (LB_TIPS.msg) return '<span style="color:#f87171">' + lbTipsEsc(LB_TIPS.msg) + '</span>';
  if (secs.length || auth.length){
    return '已整理为 ' + secs.length + ' 节' + (auth.length ? (' · 权威心得 ' + auth.length + ' 条') : '');
  }
  if (LB_TIPS.st === 'err'){
    /* v5853（用户口径「AI 本来就是 技巧+原文整理啊？难道你没做原文整理？」）：
       原写法只要 dododex 抓不到心得就显示「该物种暂无玩家心得」，
       看起来像「不能整理」。实际原文整理（LB_WT）是独立链路，
       只要有原文素材就能整理出 auth ⇒ 按素材有无分别描述。 */
    var _ovN = 0;
    try { _ovN = (typeof lbTipsOvSrc === 'function') ? lbTipsOvSrc().length : 0; } catch (eOV) { _ovN = 0; }
    if (_ovN) return '无玩家心得 · 将按官方原文整理';
    return '该物种确实没有可整理的资料';
  }
  if (LB_TIPS.st === 'loading') return '正在收集玩家心得…';
  return '尚无 AI 整理结果';
}

/* AI 外壳本体（概览底部 / 物品概览共用同一形态） */
function lbTipsAiBoxInner(){
  var _has = lbTipsHasResult();
  return lbTipsAiBoxHtml({
    state: lbTipsFootText(),
    disabled: !!LB_TIPS.busy,
    btn: { txt: LB_TIPS.busy ? '整理中…' : (_has ? '重新整理' : '一键整理'), fn: 'lbTipsDigest(true)' }
  });
}
/* v5836（用户口径「技巧整理 改叫 AI整理；灰字：技巧补充梳理」）
   v5837（用户口径「AI整理小标题 以及右侧灰字 直接删掉吧」）：标题整行不再渲染 */
var LB_TIPS_AI_H = '';
function lbTipsAiWrapHtml(){
  return '<div class="tc-sec" id="lbOverviewAiWrap">'
    + LB_TIPS_AI_H
    + lbTipsAiBoxInner()
    + '</div>';
}
/* 只替换外壳容器，不整页重绘（避免滚动跳回顶部） */
function lbTipsRefreshAiWrap(){
  var w = document.getElementById('lbOverviewAiWrap');
  if (!w){ return; }
  w.innerHTML = LB_TIPS_AI_H + lbTipsAiBoxInner();
}

function renderTips(){
  lbTipsEnsure();
  lbTipsPaint();
}

function lbTipsPaint(){
  /* v5834（用户口径「物种 wiki 里的技巧 AI 模块全部移到概览最下面」）：
     技巧 TAB 只渲染整理结果；不在技巧页时只刷新概览底部的 AI 外壳（不整页重绘）。
     v5836（用户口径「AI整理后要全量考虑回填，而不是仅当前显示的 TAB」）：
     整理结果的有无会改变「技巧」TAB 显隐 ⇒ 状态一变就整页重绘，TAB 条与内容一起回填。 */
  var _hasNow = false;
  try { _hasNow = lbTipsHasResult(); } catch (eH) { _hasNow = false; }
  if (_hasNow !== LB_TIPS._shownHas){
    LB_TIPS._shownHas = _hasNow;
    try { lbWikiRender(); } catch (eR) {}
    return;
  }
  var _T = 7;
  try { _T = lbWikiTabIdx(); } catch (e0) { _T = 7; }
  if (_T !== 7){ lbTipsRefreshAiWrap(); return; }
  var body = document.getElementById('lbWikiBody');
  if (!body) return;
  var _nm = '';
  try { _nm = ((DATA || {})[CUR] || {}).zh || ''; } catch (e) {}
  if (!_nm) _nm = String(CUR || '该物种');

  var h = '<div class="tc-sec"><div class="tc-h">技巧<em>AI 整理</em></div>';
  if (lbTipsHasResult()){
    h += lbTipsListHtml(false);       // v5834：AI 外壳已移到概览，这里只要结果
  } else {
    h += '<div class="tc-hintb">尚无整理结果 · 请在「概览」页底部点「一键整理」</div>';
  }
  h += '</div>';
  body.innerHTML = h;
  body.scrollTop = 0;
}

/* v5747（用户口径「技巧里 大段的文字 可读性还是很差」）：
   之前整节只输出一个 .tc-tipd-t，段间用 <br> 硬换行 —— 行高虽有 1.95，但**段间零间距**，
   长文挤成一坨。改为按换行拆成独立段落 .tc-tipd-p，每段带左侧主题色竖线引导 + 8px 段间距，
   字号 12.5 -> 13.5px，行高 1.95 -> 1.8（实际行距 24.3px 与原来一致，但段与段拉开）。 */
function lbTipsParasHtml(txt){
  var arr = String(txt || '').split(/\n+/).map(function(x){ return x.trim(); }).filter(function(x){ return x; });
  if (!arr.length) return '';
  return '<div class="tc-tipd-t">' + arr.map(function(p){
    return '<div class="tc-tipd-p">' + lbTipsEsc(p) + '</div>';
  }).join('') + '</div>';
}

function lbTipsListHtml(withBox){
  // v5742（用户口径「不要按照帖子来展示，直接和用户共识合并」）：
  //   不再逐条列帖子，改为把「综合结论 + 全部玩家心得」交给 AI 整合成**一篇攻略长文**，
  //   按主题分节（每节带主题色序号 + 分隔线），细节一条不丢、不怕长。
  // v5834：withBox === false 时不输出底部 AI 外壳（外壳已移到概览）
  var d = LB_TIPS.merged;
  var h = '';
  var _secs0 = (d && d.secs) || [];
  var _auth0 = (d && d.auth) || [];
  if (!_secs0.length && !_auth0.length){
    if (withBox === false) return '';
    // v5755（用户口径「没人点整理就绝不重跑」）：占位态改为**等用户主动点击**，不再自动跑 AI
    h += lbTipsAiBoxHtml({
      state: LB_TIPS.busy
        ? ('正在整理成攻略… ' + lbTipsEsc(LB_TIPS.msg || ''))
        : (LB_TIPS.needTok ? '未配置模型 token，无法整理'
                           : '尚无整理结果 · 点右侧「一键整理」生成'),
      disabled: !!LB_TIPS.busy,
      btn: { txt: (LB_TIPS.busy ? '整理中…' : '一键整理'), fn: 'lbTipsDigest(true)' }
    });
    return h;
  }
  // v5748：原文权威要点**置顶**（琥珀金块，与下方紫色玩家心得区分）
  if (_auth0.length){
    h += '<div class="tc-auth">'
      + '<div class="tc-auth-h">'
      + '<span class="tc-auth-bdg">📜 权威心得</span>'
      + '</div>'
      + _auth0.map(function(s){ return '<div class="tc-auth-i">' + lbTipsEsc(s) + '</div>'; }).join('')
      + '</div>';
  }
  var secs = _secs0;
  h += '<div class="tc-tipd">';
  secs.forEach(function(s, i){
    // v5749（用户口径「技巧里的 tc-tipd-hr 无需显示」）：不再输出横向分隔线，改由节间距分隔
    h += '<div class="tc-tipd-sec">'
      + '<div class="tc-tipd-h"><span class="tc-tipd-n">' + (i + 1) + '</span>' + lbTipsEsc(s.h || '') + '</div>'
      + lbTipsParasHtml(s.t)
      + '</div>';
  });
  h += '</div>';
  // v5744（用户口径「附件这条可以不显示」）：底部那条说明文字整条删除；
  //   操作区改用**标准 AI 模块外壳**（大肥鱼水印 + 模型/token + ⚙配置 + 主按钮），
  //   ⚙配置 由外壳统一提供，状态行不再重复放配置链接。
  // v5834（用户口径「AI 模块全部移到概览最下面」）：底部 AI 外壳改为可选
  if (withBox !== false){
    h += lbTipsAiBoxHtml({
      state: lbTipsFootText(),
      style: 'margin-top:12px',
      disabled: !!LB_TIPS.busy,
      btn: { txt: (LB_TIPS.busy ? '整理中…' : '一键整理'), fn: 'lbTipsDigest(true)' }
    });
  }
  return h;
}

/* 抓取（force=1 绕过 30 天缓存）*/
function lbTipsLoad(force){
  if (!LB_TIPS.slug) return;
  var slug = LB_TIPS.slug;
  LB_TIPS.st = 'loading'; LB_TIPS.err = null; lbTipsPaint();
  var u = lbTipsApi() + '?slug=' + encodeURIComponent(slug) + (force ? '&force=1' : '');
  fetch(u, { cache: 'no-store' })
    .then(function(r){ return r.json(); })
    .then(function(j){
      if (LB_TIPS.slug !== slug) return;
      if (!j || !j.ok){
        LB_TIPS.st = 'err';
        LB_TIPS.err = (j && (j.note || j.err)) || '抓取失败';
        if (LB_TIPS.err === 'fetch') LB_TIPS.err = '玩家心得抓取失败（网络或数据源改版），稍后重试';
        /* v5867（用户口径「战车 · Wiki 明明已经AI整理过了 并有了技巧TAB 但是再次打开 就没有了」）：
           **玩家心得抓不到 ≠ 没有整理结果** —— 后端共享缓存（dodo_<slug>_zh.json）里可能已有 AI 整理
           （尤其「无玩家心得、只有官方原文整理 auth」的载具/器械）。原来这里直接 return，
           连共享缓存都不拉 ⇒ LB_TIPS.merged 永远为空 ⇒ 技巧 TAB 消失（刚整理完那次之所以有，
           是 lbTipsDigest 把结果写在内存里，一刷新就断）。这里补拉一次（**只读缓存，绝不触发 AI**）。 */
        try {
          lbTipsLoadZh(function () {
            try {
              var _ov = document.getElementById('lbWikiOverlay');
              if (_ov && _ov.classList && _ov.classList.contains('show')) lbWikiRender();   // 重绘 TAB 条，技巧 TAB 才会出现
            } catch (eR1) {}
          });
        } catch (eZ1) {}
        lbTipsPaint();
        return;
      }
      LB_TIPS.items = j.items || [];
      LB_TIPS.summary = j.summary || '';
      LB_TIPS.st = 'ready';
      lbTipsPaint();
      // v5741/v5742：抓取 → 拉共享长文缓存 → 没有就自动整理（一步到位，无需二次点击）
      lbTipsLoadZh(function(){
        if (LB_TIPS.slug !== slug) return;
        // v5755（用户口径「没人点整理就绝不重跑」，2026-10-31 强调"这很重要"）：
        //   **彻底取消自动重跑**。原实现在「缓存缺失 / pv 落后」时会自动调 AI，
        //   等于任何人随手打开技巧 TAB 都会消耗**他自己的 token**。
        //   现改为：只读缓存并渲染；没有结果就显示占位 + 「一键整理」按钮，由用户主动触发。
        //   （整理结果全服共享一份，只需一人跑一次，见后端 _dodo_zh_merge）
        lbTipsPaint();
        /* v5867：拿到共享整理结果后要重绘 TAB 条 —— 否则「技巧」TAB 要等下次重新打开才出现（再打开因 slug 未变又不重拉） */
        try {
          var _ov2 = document.getElementById('lbWikiOverlay');
          if (_ov2 && _ov2.classList && _ov2.classList.contains('show')) lbWikiRender();
        } catch (eR2) {}
      });
    })
    .catch(function(e){
      if (LB_TIPS.slug !== slug) return;
      LB_TIPS.st = 'err';
      LB_TIPS.err = '网络错误：' + String((e && e.message) || e);
      lbTipsPaint();
    });
}
function lbTipsReload(){ LB_TIPS.msg = ''; LB_TIPS.needTok = false; lbTipsLoad(true); }

/* 拉共享整合结果（长文 + 旧版逐条译文都放同一个 map 文件） */
function lbTipsLoadZh(cb){
  var slug = LB_TIPS.slug;
  return fetch(lbTipsApi() + '/zh?slug=' + encodeURIComponent(slug), { cache: 'no-store' })
    .then(function(r){ return r.json(); })
    .then(function(j){
      if (LB_TIPS.slug !== slug) return;
      if (j && j.ok){
        if (j.map) LB_TIPS.zh = j.map || {};
        /* v5866（用户口径「战车 · Wiki 明明已经 AI 整理过了 并有了技巧 TAB，但是再次打开 就没有了」）：
           这里读共享缓存时**只认 secs**（玩家心得节），而「无玩家心得、只有官方原文整理(auth)」的物种（载具/器械）
           secs 恒空 ⇒ 重新打开时 LB_TIPS.merged 根本不被赋值 ⇒ lbTipsHasResult() 为 false ⇒ 技巧 TAB 消失
           （刚整理完那次之所以有，是因为 lbTipsDigest 成功后直接赋值在内存里）。
           判据必须与 lbTipsHasResult() / lbTipsFootText() 同口径：secs 或 auth 任一非空即算有整理结果。 */
        if (j.merged && ((j.merged.secs || []).length || (j.merged.auth || []).length)) LB_TIPS.merged = j.merged;
      }
      lbTipsPaint();
      if (typeof cb === 'function') cb();
    })
    .catch(function(){ if (typeof cb === 'function') cb(); });
}

/* v5742：把「综合结论 + 全部心得」交给 AI 整合成一篇攻略长文
   · 复用大肥鱼模块自带 token 配置（lbAiCfgGet / lbOpenConfigModal）
   · ASE 判定：ASA 于 2023-10-25 上线，早于此日期的心得按「旧版经验」处理，
     提示词明确要求剔除只在 ASE / Mobile / 旧版数值下成立的内容
   · 展示层不出现任何来源站点名，也不显示赞数/日期（用户口径） */
function lbTipsDigest(force){
  if (LB_TIPS.busy) return;
  var items = LB_TIPS.items || [];
  /* v5832（用户口径「技巧只从 wiki 分解即可」）：没有玩家心得但有 wiki 原文时，仍允许只按原文整理 */
  var _ovT = lbTipsOvSrc();
  /* v5848：物种无 wiki 页且 dododex 无心得时，用对应物品页的资料当素材 */
  var _fbT = (typeof lbTipsFbSrc === 'function') ? lbTipsFbSrc() : [];
  if (!items.length && !_ovT.length && !_fbT.length){ LB_TIPS.msg = '没有可整合的心得'; lbTipsPaint(); return; }
  var cfg = null; try { cfg = lbAiCfgGet(); } catch (e0) {}
  if (!cfg || !cfg.token){
    LB_TIPS.needTok = true; LB_TIPS.msg = '';
    if (force){
      try { if (typeof lbToast === 'function') lbToast('请先在「⚙ 配置」里填大肥鱼 token'); } catch (e1) {}
      try { lbOpenConfigModal(); } catch (e2) {}
    }
    lbTipsPaint();
    return;
  }
  LB_TIPS.needTok = false;
  LB_TIPS.busy = true;
  LB_TIPS.msg = '整理中…';
  lbTipsPaint();

  var SYS = '你是《方舟：生存飞升》(ARK: Survival Ascended，下称 ASA) 的资深中文玩家兼攻略编辑。\n'
    + '任务：把西方玩家论坛里零散的心得，**整合成一篇结构清晰、可直接照做的中文攻略长文**。\n\n'
    + '硬性要求：\n'
    + '1) **合并而非罗列**：把多条心得按主题归并（例如：击晕准备 / 困龙与地形 / 麻醉与眩晕维持 / '
    + '饲料与喂食节奏 / 驯服后用途与注意事项）。同一主题下不同说法的信息要融成完整表述，'
    + '**不要出现「有人说」「某位玩家」「原文」这类帖子口吻**，也不要编造来源。\n'
    + '2) **细节一条不丢**：具体数字（数量、时长、倍率、等级、距离、掉血风险）、前置条件、'
    + '失败教训、替代方案、反直觉的坑全部保留。**宁可长，绝不许省略**。\n'
    + '3) **剔除过时版本内容**：目标版本是 ASA（2023-10-25 上线）。每条心得带发帖日期，'
    + '**早于 2023-10-25 的按旧版 (ASE / Survival Evolved / Mobile) 经验对待** —— '
    + '若其中提到只在旧版或手机版才成立的做法（已改版的数值、已移除的机制、移动端专属操作、'
    + '已失效的驯服方式），一律剔除；仍然适用于 ASA 的通用打法可以保留。'
    + '若某条心得日期较早但内容明显通用，保留其要点。\n'
    + '4) **可读性优先**：每节一个主题，小标题 ≤10 字；正文用短句分点陈述，'
    + '不要 markdown 符号（不要 #、*、-），换行用真实换行。\n'
    + '5) 术语用中文玩家习惯译法：Narcotic=麻醉药 / Tranq Dart=麻醉镖 / Tranq Arrow=麻醉箭 / '
    + 'Kibble=饲料 / Torpor=眩晕值 / Imprint=留痕 / Trap=困龙房 / Prime Meat=优质生肉 / '
    + 'Bear Trap=捕兽夹 / Spike Wall=尖刺墙 / juvenile=幼年期 / adolescent=青年期 / '
    + 'baby=幼崽 / mature=成年 / boss=首领 / Tek=泰克 / Alpha=精英 / Carrion=腐肉 / '
    + 'Regen=再生 / Carrion Regen=腐肉再生 / Drag Weight=拖拽重量。\n'
    + '5b) **中文优先，禁止夹生英文（硬性）**：除 ASA / PvP / PvE / DPS 这类玩家社区通用缩写外，'
    + '正文**不得残留任何英文单词或词组** —— 物品名、状态/buff 名、生物名、技能名、地点名、'
    + '数值单位、生长阶段、建筑名一律译成中文；原文出现上表以外的英文，按 ARK 中文社区通行译法翻译，'
    + '确实无通行译法的写成「中文（原词）」且全文只出现一次。宁可意译，也不要留着英文不管。\n'
    + '6) 不添加原材料没有的信息，不写「综合了 N 条」「参考来源」之类的话。\n'
    + '7) **原文权威要点单独输出（auth）**：用户消息里的【游戏资料原文 · 技巧要点】来自游戏资料原文，'
    + '**权威性高于玩家心得**。把它整理成 auth 列表：每条一句话，保留全部数字/条件/前提/替代方案，'
    + '去掉口水话与重复项，**不得引入心得的说法，也不得补充原文没有的内容**。'
    + '原文没有这个板块时 auth 输出空数组 []。\n'
    + '7b) **发现原文明显语义错误必须纠正**：若某条原文存在主宾颠倒（把「A 使 B 昏迷」写成「B 使 A 昏迷」）、'
    + '因果倒置、术语误译（例如把 Drag Weight 拖拽重量译成负重上限 Weight）、数值单位错乱，'
    + '按 ASA 实际游戏机制改写正确后再输出；仍然一句话，不要加解释，不要写「原文有误」之类说明。\n'
    + '8) **secs 只写玩家心得**：secs 只基于【玩家整体共识】+【玩家心得】，'
    + '**不得重复 auth 已经写过的内容** —— 只补充原文没提到的实操细节、失败教训、替代方案、'
    + '反直觉的坑、具体数值经验。若心得与原文冲突，以原文为准，不必再写进 secs。\n'
    + '9) **物种名一律用正式名（硬性）**：正文凡指代本物种，必须使用用户消息【物种表 · 正式中文名】给出的名字；玩家心得与原文里出现的俗称、旧译、第三方译名，**全部改写为正式名**，既不保留也不并列写出。正文提到的其它物种，同样要能对上项目物种表的正式名。\n'
    + '10) **无玩家心得时只输出 auth（硬性）**：若用户消息里没有【玩家心得】板块，secs 必须输出空数组 []，只把【游戏资料原文 · 技巧要点】整理进 auth；不得用常识、其它物种经验或臆测补充任何内容。\n\n'
    + '输出严格 JSON（不要代码块）：\n'
    + '{"auth":["要点1","要点2"],"secs":[{"h":"小标题","t":"该节正文"}]}\n'
    + 'auth 取 0~12 条（原文无技巧板块则为 []），secs 取 3~7 节，必须覆盖全部有价值的玩家心得。';

  var arr = items.map(function(x, i){
    return '[' + (i + 1) + '] ' + (x.date || '日期未知') + ' | ' + (x.catZh || x.cat || '') + '\n' + String(x.text || '');
  }).join('\n\n');
  // v5746（用户口径「除了 dododex 心得还要喂进去原文案的技巧」）：
  //   把 wiki 原文里的「技巧」板块也作为素材一起交给 AI 整合
  // v5832：统一走函数开头算好的 _ovT（避免两处口径不一致）
  var _ovTips = _ovT.length ? _ovT : _fbT;   // v5848：无 wiki 原文时用物品页资料充当原文要点
  var _ovBlock = _ovTips.length
    ? ('【游戏资料原文 · 技巧要点】\n' + _ovTips.map(function(s, i){ return (i + 1) + '. ' + s; }).join('\n') + '\n\n')
    : '';
  // v5761：注入【物种表 · 正式中文名】+【俗名 → 正式中文名】（与 wiki 整理同一公共函数）
  var _nameBlk = '';
  try {
    var _nameSlug = '';
    try { _nameSlug = (typeof lbWtSlug === 'function' ? lbWtSlug() : '') || (LB_WIKI && LB_WIKI.cur) || ''; } catch (eNs) { _nameSlug = ''; }
    _nameBlk = lbWtNameBlocks(_nameSlug, [arr || '', _ovBlock || ''].concat(_ovTips || []));
  } catch (eNB) { _nameBlk = ''; }
  var usr = _nameBlk + _ovBlock
    + (LB_TIPS.summary ? ('【玩家整体共识】\n' + LB_TIPS.summary + '\n\n') : '')
    + (items.length ? ('【玩家心得（共 ' + items.length + ' 条，方括号内为发帖日期）】\n' + arr) : '');

  fetch(String(cfg.base || LB_AI_BASE).replace(/\/+$/, '') + '/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + cfg.token },
    body: JSON.stringify({
      model: lbAiNormModel(cfg.model),
      messages: [{ role: 'system', content: SYS }, { role: 'user', content: usr }],
      temperature: 0.3, max_tokens: 8000,
      thinking: { type: 'disabled' },
      response_format: { type: 'json_object' }
    })
  }).then(function(r){ return r.text().then(function(tx){ return { s: r.status, t: tx }; }); })
    .then(function(x){
      LB_TIPS.busy = false;
      if (x.s !== 200){
        LB_TIPS.msg = '接口错误 ' + x.s + '：' + String(lbAiErrText(x.s) || '');
        lbTipsPaint();
        return;
      }
      var j = null; try { j = JSON.parse(x.t); } catch (eJ) {}
      var ch0 = (j && j.choices && j.choices[0]) ? j.choices[0] : null;
      var m0 = (ch0 && ch0.message) ? ch0.message : null;
      var content = (m0 && m0.content) ? String(m0.content) : '';
      var d = null;
      try { d = lbAiParseJson(content); } catch (eP) {}
      if (!d && m0 && m0.reasoning_content){ try { d = lbAiParseJson(String(m0.reasoning_content)); } catch (eR) {} }
      var secs = (d && d.secs && d.secs.length) ? d.secs : null;
      var auth = [];
      if (d && Array.isArray(d.auth)){
        d.auth.forEach(function(x){
          var tx = (typeof x === 'string') ? x : String((x && (x.t || x.p || x.text)) || '');
          tx = tx.trim();
          if (tx) auth.push(tx);
        });
      }
      if (!secs && !auth.length){
        LB_TIPS.msg = '整理结果无法解析' + (content ? ('：' + String(content).replace(/\s+/g, ' ').slice(0, 60)) : '');
        lbTipsPaint();
        return;
      }
      var clean = [];
      (secs || []).forEach(function(s){
        var hh = String((s && s.h) || '').trim();
        var tt = String((s && s.t) || '').trim();
        if (tt) clean.push({ h: hh || ('要点 ' + (clean.length + 1)), t: tt });
      });
      LB_TIPS.merged = { secs: clean, auth: auth };
      LB_TIPS.msg = '';
      LB_TIPS.needTok = false;
      LB_TIPS.st = 'ready';   // v5833：成功后必须切 ready，否则 lbTipsPaint 会一直停在 err/按钮态
      lbTipsPaint();
      lbTipsPostZh(null, function(){}, LB_TIPS.merged, force);   // 回写共享缓存（v5769：带 force）
      // v5746（用户口径「在技巧点按钮统一把原文整理也做了」）：
      //   长文整合成功后**串行**接着整理该物种的 wikily 原文（手动点则强制重跑）
      try {
        if (typeof lbWtDigest === 'function'){
          if (force) lbWtDigest(true);
          else if (!LB_WT.ready) lbWtDigest(false);
        }
      } catch (eW2) {}
    })
    .catch(function(e){
      LB_TIPS.busy = false;
      LB_TIPS.msg = '网络错误：' + String((e && e.message) || e);
      lbTipsPaint();
    });
}

/* 回写共享缓存：长文放 merged（只写一次，已有则不覆盖）；items 为旧版逐条译文（兼容保留） */
function lbTipsPostZh(pairs, done, merged, force){   // v5769：补 force 形参（v5768 只在 body 里用了 force 却没声明 ⇒ force is not defined）
  var body = { slug: LB_TIPS.slug, cls: LB_TIPS.cls, force: !!force };
  if (pairs && pairs.length) body.items = pairs;
  if (merged && (((merged.secs || []).length) || ((merged.auth || []).length))){
    // v5750：带上 pv，后端在 pv 升级时允许覆盖旧 auth
    body.merged = { secs: merged.secs || [], auth: merged.auth || [], pv: LB_TIPS_PV };
  }
  if (!body.items && !body.merged){ if (done) done(); return; }
  fetch(lbTipsApi() + '/zh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  }).then(function(r){ return r.json(); })
    .then(function(j){ if (done) done(); })
    .catch(function(){ if (done) done(); });
}

/* P2：键位图标一律复用项目 lbKeyChipHtml()（lbk 键位字体 + 内联 SVG 多色键），
   不再复制原型页的 LB_KEYSVG / tcKeySrc / tcKeyFontHas，避免 6.5 KB 重复定义 */
function tcKeyChipHtml(k, size, extraCls){
  try {
    if (typeof lbKeyChipHtml === 'function') return lbKeyChipHtml(k, size, extraCls);
  } catch (e) {}
  return '<span class="tc-km-note">' + String(k || '?') + '</span>';
}

/* ===== P2 第四批：技能 tab ===== */

/* ===== ABIL_IDX ===== */
var ABIL_IDX = 0;

/* ===== ABIL_SEL ===== */
var ABIL_SEL = {};

/* ===== abilGo（v73d：技能标签切换，v72 搬迁时遗漏）===== */
function abilGo(el){
  if(!el) return;
  var scope = el.getAttribute('data-scope') || 'main';
  var i = parseInt(el.getAttribute('data-i'), 10) || 0;
  var list = ((ABIL[CUR] || {}).videos) || [];
  var a = list[i];
  if(!a) return;
  ABIL_SEL[scope] = i;
  var box = document.getElementById('abilBox_' + scope);
  if(box){
    Array.prototype.forEach.call(box.querySelectorAll('.abil-t'), function(n, k){
      n.classList.toggle('on', k === i);
    });
  }
  var v = document.getElementById('abVideo_' + scope);
  if(v){
    if(a.poster) v.setAttribute('poster', a.poster); else v.removeAttribute('poster');
    var src = v.querySelector('source');
    if(src) src.src = a.video;
    try { v.pause(); } catch(e) {}
    v.load();
  }
  var desc = document.getElementById('abilDesc_' + scope);
  var _abAI = 0; var _abTxt = ''; try { _abTxt = lbWtAbilDesc(a.zh, a.desc) || ''; _abAI = LB_WT_LAST_AI; LB_WT_LAST_AI = 0; } catch (eAB) {}
  if(desc){ desc.innerHTML = _abTxt; if (_abAI) desc.classList.add('tc-ai'); }   // v5768：技能描述也是 AI 出口
}

/* ===== ABIL_COND_ZH ===== */
var ABIL_COND_ZH = {
  'activate': '激活',
  'fire': '开火',
  'underwater': '水下',
  'enable fish hunting': '启用捕鱼'
};

/* ===== ABIL_KM ===== */
var ABIL_KM = {
  'LMB':       { act:'attack',   zh:'开火',              kbm:'mouse_left',     pad:'xbox_rt',            hold:0 },
  'RMB':       { act:'aim',      zh:'瞄准 / 备用攻击',    kbm:'mouse_right',    pad:'xbox_lt',            hold:0 },
  'Left Ctrl': { act:'melee',    zh:'近战',              kbm:'keyboard_ctrl_left', pad:'xbox_rb',            hold:0 },
  'Space':     { act:'jump',     zh:'跳跃',              kbm:'keyboard_space', pad:'xbox_button_a',      hold:0 },
  'C':         { act:'crouch',   zh:'下蹲',              kbm:'keyboard_c',     pad:'xbox_stick_r_press', hold:0 },
  'Hold E':    { act:'interact', zh:'使用',              kbm:'keyboard_e',     pad:'xbox_button_y',      hold:1 },
  'E':         { act:'interact', zh:'使用',              kbm:'keyboard_e',     pad:'xbox_button_y',      hold:0 },
  'WhistleAttack This Target': { act:'wh_atk_this', zh:'吹哨·攻击这个目标', kbm:'keyboard_period', pad:null, hold:0 },
  'Whistle: Attack This Target': { act:'wh_atk_this', zh:'吹哨·攻击这个目标', kbm:'keyboard_period', pad:null, hold:0 }
};

/* ===== tcCondZh ===== */
function tcCondZh(c){ c = String(c || '').trim(); return ABIL_COND_ZH[c] || c; }

/* ===== tcKeyParse ===== */
function tcKeyParse(raw){
  if(!raw) return [];
  var s = String(raw).trim();
  if(ABIL_KM[s]) return [{ km:ABIL_KM[s], cond:'' }];
  var out = [];
  s.split(';').forEach(function(seg){
    seg = seg.trim(); if(!seg) return;
    var p = seg.split(':'), k = p[0].trim(), cond = p.slice(1).join(':').trim();
    if(ABIL_KM[k]) out.push({ km:ABIL_KM[k], cond:cond });
    else out.push({ km:{ act:'', zh:'', kbm:'', pad:null, hold:0, raw:k }, cond:cond });
  });
  return out;
}

/* ===== tcKeyChips ===== */
function tcKeyChips(raw, small){
  var arr = tcKeyParse(raw);
  if(!arr.length) return '\u2014';
  /* v5784（用户口径「食腐再生、铁匠台鞍 这种无操作键的不要硬显示操作键」）：
     被动技能（Passive / Inventory）的原始串里既没有键鼠键位也没有手柄键位，
     原实现仍会拼出「Passive / 不适用 consume a corpse」「Inventory / 不适用 鞍 equipped」。
     判定：整串**没有任何一个真实按键**（kbm / pad 全空）⇒ 直接给「—」，不再硬凑。
     只要有任意一段有真实按键，就照常渲染（保留「不适用」用于「只有键鼠没有手柄」这类真实缺项）。 */
  var _hasRealKey = arr.some(function(o){ return !!(o.km && (o.km.kbm || o.km.pad)); });
  if (!_hasRealKey) return '\u2014';
  var cls = 'tc-km' + (small ? ' small' : '');
  var _sz = small ? 15 : 23;
  /* v5790（用户口径「长按不是应该对齐键位配置里的显示逻辑么」+「哪侧实际需要长按就显示在哪侧」）：
     原实现手写纯文字 <span class="tc-km-note">长按</span>，而键位配置用的是字体图标
     touch_tap_hold（LB_KEYMAP_MODES 里 {id:'long', n:'长按', ic:'touch_tap_hold'}，走 lbKeyChipHtml 渲染）。
     这里统一成同一字形；并改为**按侧判定**：kbmHold / padHold 显式指定优先，
     未指定时回落到旧的 hold 字段（= 两侧都需要长按，用于「Hold E」这类整条 hold 的动作）。 */
  // v5791（用户口径「键位配置里操作都是在主键之前的吧？你是不是没完全对齐」）：站队 lbKmChips 的 v5379 口径 ——
  //   · 位置：操作标识一律在被作用键**左侧**（原来我放在右侧，方向反了）
  //   · 包裹：外包 .lb-km-mod（title=操作名），与键位配置同构
  //   · 尺寸：键格 × 0.8（键位配置 22→18，此处 23→18 / 15→12）
  var _hIc = Math.round(_sz * 0.8);
  var _holdIco = function(on){
    if (!on) return '';
    return '<span class="lb-km-mod" title="长按">' + tcKeyChipHtml('touch_tap_hold', _hIc) + '</span>';
  };
  var parts = arr.map(function(o){
    var km = o.km, seg = '';
    var tipK = '键鼠·' + (km.act || '') + (km.zh ? ('（' + km.zh + '）') : '');
    var tipP = 'Xbox·' + (km.act || '') + (km.zh ? ('（' + km.zh + '）') : '');
    var _hKbm = (km.kbmHold != null) ? !!km.kbmHold : !!km.hold;
    var _hPad = (km.padHold != null) ? !!km.padHold : !!km.hold;
    if (km.kbm){
      seg += '<span class="tc-km-g" title="' + tipK + '">'
          +  _holdIco(_hKbm)
          +  tcKeyChipHtml(km.kbm, _sz)
          +  '</span>';
    } else {
      seg += '<span class="tc-km-g"><span class="tc-km-note">' + (km.raw || '?') + '</span></span>';
    }
    seg += '<span class="tc-km-vs">/</span>';
    if (km.pad){
      seg += '<span class="tc-km-g" title="' + tipP + '">'
          +  _holdIco(_hPad)
          +  tcKeyChipHtml(km.pad, _sz)
          +  '</span>';
    } else {
      seg += '<span class="tc-km-g" title="' + tipP + '"><span class="tc-km-note">不适用</span></span>';
    }
    if(o.cond) seg += '<span class="tc-km-cond">' + tcCondZh(o.cond) + '</span>';
    return '<span class="tc-km-g" style="gap:5px">' + seg + '</span>';
  });
  return '<span class="' + cls + '">' + parts.join('<span class="tc-km-sep">+</span>') + '</span>';
}

/* ===== renderAbil ===== */
function renderAbil(list, scope){
  scope = scope || 'main';
  list = list || [];   // v67：DATA[*].abils 已瘦身移除（技能演示统一走 tabHtml 的 abils）
  if(!list.length) return '';
  var idx = ABIL_SEL[scope] || 0;
  if(idx >= list.length) idx = 0;
  var cur = list[idx];
  var h = '<div class="abil" id="abilBox_' + scope + '"><div class="abil-h">🎬 技能演示（' + list.length + ' 个）</div><div class="abil-tabs">';
  list.forEach(function(a, i){
    // v60（用户口径「技能演示的小TAB里无需显示快捷键」）：小 TAB 只留技能名，键位由「技能一览」表与下方描述承担
    h += '<span class="abil-t' + (i === idx ? ' on' : '') + '" data-scope="' + scope + '" data-i="' + i + '"'
       + ' onclick="abilGo(this)">' + (a.title || ('技能' + (i + 1))) + '</span>';
  });
  h += '</div>';
  h += '<video id="abVideo_' + scope + '" controls preload="none" playsinline'
     + (cur.poster ? (' poster="' + cur.poster + '"') : '') + '>'
     + '<source src="' + cur.video + '" type="video/mp4">'
     + '</video>';
  // v5745：技能描述优先用 AI 整理版（按技能名对位）
  var _abT2 = ''; var _abA2 = 0; try { _abT2 = lbWtAbilDesc(cur.zh, cur.desc) || ''; _abA2 = LB_WT_LAST_AI; LB_WT_LAST_AI = 0; } catch (eAB2) {}
  h += '<div class="abil-desc' + (_abA2 ? ' tc-ai' : '') + '" id="abilDesc_' + scope + '">' + _abT2 + '</div></div>';   // v5768
  return h;
}

// v5691（用户口径「可破坏茅草木材石头金属泰克 这个也解析成表格」）：
//   wiki 的「可破坏」徽章被后端拍平成纯文本（多个材质名粘连）⇒ 按已知材质词贪婪切回列表
var LB_ABIL_MAT_WORDS = ['茅草','木材','石头','金属','泰克','特克','水晶','玻璃','黏土','甲壳','纤维','皮革','肉'];
// v5692（用户口径「加材质名归一」）：wiki 徽章写「木材」而技能 tiers 写「木头」⇒ 精确比对会漏匹配
var LB_MAT_ALIAS = { '木头': '木材', '木材': '木材', '特克': '泰克', '泰克': '泰克', '草': '茅草' };
function lbMatNorm(s){
  var t = String(s == null ? '' : s).trim();
  return LB_MAT_ALIAS[t] || t;
}
/* v5785（用户口径「要有实物图标」）：**材质名 → 实物图标 URL**。
   数据源：LB_ITEM_ZH 里 zh 与材质名相同（经 lbMatNorm 归一）的条目 ⇒ 取它的 icon ⇒ lbItemIconUrl 生成地址。
   **不硬编码任何类名**（茅草/木材/石头/金属/水晶/黏土/甲壳素/纤维/兽皮/生肉… 全部自动对上）。
   带键数指纹：LB_ITEM_ZH 与 LB_ITEM_ICON_URL 都是异步加载的，早先建的空表不能永久锁死。 */
var LB_MAT_ICON = null, LB_MAT_ICON_SIG = -1;
function lbMatIconMap(){
  var sig = 0;
  try { sig += (typeof LB_ITEM_ZH === 'object' && LB_ITEM_ZH) ? Object.keys(LB_ITEM_ZH).length : 0; } catch (e0) {}
  try { sig += (typeof LB_ITEM_ICON_URL === 'object' && LB_ITEM_ICON_URL) ? Object.keys(LB_ITEM_ICON_URL).length : 0; } catch (e1) {}
  if (LB_MAT_ICON && sig === LB_MAT_ICON_SIG) return LB_MAT_ICON;
  var m = {}, I = (typeof LB_ITEM_ZH === 'object' && LB_ITEM_ZH) || {};
  Object.keys(I).forEach(function(k){
    var o = I[k] || {};
    var zh = String(o.zh || '').trim();
    if (!zh || zh.length > 5 || !o.icon) return;          // 材质名都很短，长名不可能命中
    var nm = lbMatNorm(zh);
    if (m[nm]) return;
    var u = '';
    try { u = lbItemIconUrl(k) || ''; } catch (e2) { u = ''; }
    if (u) m[nm] = u;
  });
  LB_MAT_ICON = m; LB_MAT_ICON_SIG = sig;
  return m;
}
function lbMatIconUrl(name){
  try { return lbMatIconMap()[lbMatNorm(name)] || ''; } catch (e) { return ''; }
}

function lbAbilMatList(line, fallback){
  var out = [], t = String(line || '').replace(/^可破坏/, '').trim();
  var i = 0;
  while (i < t.length){
    var hit = '';
    for (var j = 0; j < LB_ABIL_MAT_WORDS.length; j++){
      var w = LB_ABIL_MAT_WORDS[j];
      if (t.substr(i, w.length) === w){ hit = w; break; }
    }
    if (hit){ if (out.indexOf(hit) < 0) out.push(hit); i += hit.length; }
    else i++;
  }
  if (!out.length && fallback && fallback.length){
    fallback.forEach(function (m){ if (m && m.zh && out.indexOf(m.zh) < 0) out.push(m.zh); });
  }
  return out;
}

/* ===== v5781：技能 Tab 置顶正文取数（renderAbilTab 与 lbWtCollect **共用同一实现**）=====
   后端 HOME.abilIntro 三句里 ①「可破坏茅草木材…」是徽章被拍平 ⇒ 抽出来给「可破坏材质」表格用；
   ②「1 级、100% 驯服效率、无烙印时的基础伤害。打开伤害计算器 ›」是模板套话 + 失效链接 ⇒ 丢弃；
   ③ 真实战斗说明 ⇒ 保留。
   抽成公共函数的原因：收集端（喂 AI）和渲染端必须**用同一份过滤**，否则 AI 整理出来的素材
   与实际展示的内容对不上（历史上就是各自复制一份过滤逻辑）。 */
function lbAbilIntroPick(){
  var d = (typeof ABIL === 'object' && ABIL) ? (ABIL[CUR] || null) : null;
  var arr = [];
  try { arr = ((d && d.notes && d.notes.length) ? d.notes : wikiTabIntro('abilIntro')).slice(); } catch (e) { arr = []; }
  var matLine = '', keep = [];
  arr.forEach(function(t){
    var x = String(t == null ? '' : t).trim();
    if (!x) return;
    if (/^可破坏/.test(x)) { matLine = x; return; }
    if (/打开伤害计算器/.test(x) || /无烙印时的基础伤害/.test(x) || /100%\s*驯服效率/.test(x)) return;
    keep.push(x);
  });
  return { list: keep, matLine: matLine };
}

/* v5855（用户口径「泰克悬浮艇的技能里为啥没取到操作键」）：
   载具的操作按键在 wiki.gg Controls 段，后端已解析成 HOME.abilKeys = [{k,a}]。
   这里渲染成「操作键」表（左动作 / 右键帽），与物品 wiki 的操作键表同构。 */
/* v5856（用户口径「你自己看看附件这合理么？而且置顶文案中有按键，为啥没渲染？」）：
   v5855 直接拿后端 wiki.gg 英文 abilKeys，键名是 Hold/Press/Tap/WS/AD 这类
   **无效 key id** ⇒ lbKeyChipHtml 走 CDN PNG 分支全部 404 隐藏（按键列全空），动作还是英文长句。
   现改为：**从 AI 整理后的中文置顶文案**里解析「动作 → 按键」，映射成项目真实键 ID。 */
var LB_ABIL_KEYMAP = [
  ['鼠标左键', 'mouse_left'], ['鼠标右键', 'mouse_right'], ['鼠标滚轮', 'mouse_scroll'],
  ['鼠标滑轮', 'mouse_scroll'], ['左键', 'mouse_left'], ['右键', 'mouse_right'],
  ['鼠标', 'mouse_move'],   // v5861：项目 LB_KEYFONT 里有 mouse_move 真图标，不再用文本键帽
  ['Ctrl', 'keyboard_ctrl_left'], ['Shift', 'keyboard_shift_left'], ['Alt', 'keyboard_alt_left'],
  ['空格', 'keyboard_space'], ['Space', 'keyboard_space'], ['Tab', 'keyboard_tab'],
  ['W', 'keyboard_w'], ['S', 'keyboard_s'], ['A', 'keyboard_a'], ['D', 'keyboard_d'],
  ['C', 'keyboard_c'], ['N', 'keyboard_n'], ['X', 'keyboard_x'], ['E', 'keyboard_e'],
  ['R', 'keyboard_r'], ['F', 'keyboard_f'], ['G', 'keyboard_g'], ['Q', 'keyboard_q'],
  ['Z', 'keyboard_z'], ['V', 'keyboard_v'], ['T', 'keyboard_t']
];
/* v5859：手势前缀（按住/轻按/按下…）转成图标，与物品侧 .lb-km-mod 同构 */
var LB_ABIL_MOD_ALIAS = {
  '按住': '长按', '长按住': '长按', '长押': '长按',
  '轻按': '轻按', '轻触': '轻按',
  '双击': '双击', '连按两次': '双击',
  '按下': '开始按压', '松手': '释放按压'
};
var LB_ABIL_MOD_FALLBACK = {
  '长按': 'touch_tap_hold', '轻按': 'generic_button_finger', '双击': 'touch_tap_double',
  '开始按压': 'generic_button_finger', '释放按压': 'generic_button_finger'
};
function lbAbilEscRe(s){ return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
/* v5859：单段文字 -> [{keys,a,mods}]。相对 v5857 改两处：
   ① 手势前缀（按住/长按/轻按/双击/按下）**不再丢弃**，转成 mods 供渲染成图标（与物品侧同构）；
   ② sig 加入 mods，避免「按住 X」与「轻按 X」被误去重。 */
function lbAbilParseKeys(lines){
  var out = [], seen = {};
  (lines || []).forEach(function (line) {
    var s = String(line == null ? '' : line).replace(/[（(][^）)]*[）)]/g, ' ');
    s.split(/[，,、；;。]/).forEach(function (seg) {
      var t = String(seg || '').trim().replace(/^[^：:]{0,10}[：:]/, '').trim();   // 去掉「操控按键：」这类前缀
      /* v5857③：「按住 / 长按 / 轻按 / 双击 / 按下」是动作修饰前缀，
         不剥离的话「按住空格上升」里的「空格」前边界是中文字符，键 token 永远匹配不到。 */
      var mods = [];
      var _mm = /^(按住|长按|按下|长按住|长押|轻按|轻触|双击|连按两次)\s*/.exec(t);
      if (_mm){
        var _mn = LB_ABIL_MOD_ALIAS[_mm[1]] || _mm[1];
        if (_mn && mods.indexOf(_mn) < 0) mods.push(_mn);
        t = t.replace(/^(按住|长按|按下|长按住|长押|轻按|轻触|双击|连按两次)\s*/, '').trim();
      }
      if (t.length < 3) return;
      var keys = [], rest = ' ' + t + ' ';
      /* v5857④：段首「/ 动作」= 斜杠键（项目键位表无斜杠图标 ⇒ 用文本键帽）。
         先摘出，避免与「W/S 前进后退」里作为分隔的 / 混淆。 */
      /* v5861：斜杠键的项目正规 ID 是 keyboard_slash_forward（LB_KEYMAP_ACTIONS 里就是这个），LB_KEYFONT 有字形 ⇒ 用真图标 */
      if (/^\/\s+/.test(t)) { keys.push('keyboard_slash_forward'); rest = ' ' + t.replace(/^\/\s+/, '') + ' '; }
      LB_ABIL_KEYMAP.forEach(function (kv) {
        var tok = kv[0], id = kv[1];
        /* v5857②：中文 token（空格 / 鼠标…）后面直接接动作，不能要求后边界；拉丁 token 必须要求。 */
        var _cjk = /[\u4e00-\u9fff]/.test(tok);
        var _pat = '(^|[\\s/])' + lbAbilEscRe(tok) + (_cjk ? '' : '(?=$|[\\s/,])');
        if (new RegExp(_pat).test(rest)) {
          if (keys.indexOf(id) < 0) keys.push(id);
          rest = rest.replace(new RegExp(_pat, 'g'), '$1');
        }
      });
      var act = rest.replace(/^[\s/]+/, '').replace(/[\s/]+$/, '').trim();
      /* v5861（用户口径「内容完全不知道在说什么」）：
         wiki.gg 牵引模式段的原文只写了 Hold / Press / Tap（后端 abilKeys 实测 k='Hold'/'Press'/'Tap'），
         **没写按键** ⇒ AI 照译成「按住 填充目标进度条」，缺宾语、读不懂。
         游戏内该段（抓取 / 松开 / 拉近 / 放低目标）全部是**鼠标左键**，这里在「有手势但无键」时补 mouse_left，
         手势由 mods 图标表达。仅限动作里出现「目标 / 牵引」的条目，避免误伤其它物种的「长按 蓄力」类行。 */
      if (!keys.length) {
        if (!mods.length) return;
        if (!/(目标|牵引)/.test(act)) return;
        keys = ['mouse_left'];
      }
      if (act.length < 2 || act.length > 40) return;
      /* v5857：动作里含 3 个以上连续拉丁字母 = 未中文化的原文长句，不进中文键表（交给英文兜底） */
      if (/[A-Za-z]{3,}/.test(act)) return;
      var sig = keys.join('|') + '|' + mods.join('|') + '|' + act;
      if (seen[sig]) return;
      seen[sig] = 1;
      out.push({ keys: keys, a: act, mods: mods });
    });
  });
  return out;
}
/* v5857·B（用户口径「后端英文数据 也不能丢啊」）：
   中文解析为 0 条时，退回后端 wiki.gg Controls 英文结构化数据（HOME.abilKeys），
   把脏键名（WS/AD/Cursor/Space/LMB…）归一成项目真实键 ID，动作保留英文原文并在表头标注「原文」。
   —— 只在中文解析为 0 条时启用，绝不与 AI 整理结果混排，避免英文长句污染表格。 */
var LB_ABIL_EN_WORD = {
  CURSOR: 'mouse_move', MOUSE: 'mouse_move', MOUSELOOK: 'mouse_move',
  LMB: 'mouse_left', LEFTCLICK: 'mouse_left', LEFTMOUSE: 'mouse_left',
  RMB: 'mouse_right', RIGHTCLICK: 'mouse_right',
  MMB: 'mouse_scroll', SCROLL: 'mouse_scroll', WHEEL: 'mouse_scroll',
  CTRL: 'keyboard_ctrl_left', SHIFT: 'keyboard_shift_left', ALT: 'keyboard_alt_left',
  SPACE: 'keyboard_space', SPACEBAR: 'keyboard_space', TAB: 'keyboard_tab',
  ENTER: 'keyboard_enter', ESC: 'keyboard_esc', ESCAPE: 'keyboard_esc',
  UP: '~↑', DOWN: '~↓', LEFT: '~←', RIGHT: '~→',
  PGUP: '~PgUp', PGDN: '~PgDn', LB: '~LB', RB: '~RB', LT: '~LT', RT: '~RT',
  LMB1: 'mouse_left', RMB1: 'mouse_right'
};
function lbAbilEnKeyIds(k){
  var ids = [], s = String(k == null ? '' : k).toUpperCase().replace(/[_\-.\u00b7]/g, ' ').trim();
  if (!s) return ids;
  var push = function (v) { if (v && ids.indexOf(v) < 0) ids.push(v); };
  /* v5858：纯斜杠键（wiki.gg Controls 里的 "/ toggle Tractor Turret"）走文本键帽，
     不能被下面的 split 当分隔符吃掉。 */
  if (/^\/+$/.test(String(k == null ? '' : k).trim())) { ids.push('keyboard_slash_forward'); return ids; }
  s.split(/[\s\/+,&]+/).forEach(function (p) {
    if (!p) return;
    if (LB_ABIL_EN_WORD[p]) { push(LB_ABIL_EN_WORD[p]); return; }
    if (/^[A-Z]$/.test(p)) { push('keyboard_' + p.toLowerCase()); return; }
    if (/^[A-Z]{2}$/.test(p)) { p.split('').forEach(function (ch) { push('keyboard_' + ch.toLowerCase()); }); return; }
    push('~' + p);
  });
  return ids;
}
/* v5859：手势 -> 项目手势图标（与物品侧 .lb-km-mod 同构；图标取自 LB_KEYMAP_MODES 权威表） */
function lbAbilModIcon(nm){
  var n = String(nm || '');
  if (!n) return '';
  var ic = '';
  try {
    var M = (typeof LB_KEYMAP_MODES !== 'undefined' && LB_KEYMAP_MODES) ? LB_KEYMAP_MODES : [];
    for (var i = 0; i < M.length; i++) { if (M[i] && M[i].n === n && M[i].ic) { ic = M[i].ic; break; } }
  } catch (e1) {}
  if (!ic) ic = LB_ABIL_MOD_FALLBACK[n] || '';
  if (!ic) return '<span class="tc-km-note">' + tcEsc(n) + '</span>';
  try { return '<span class="lb-km-mod" title="' + tcEsc(n) + '">' + lbKeyChipHtml(ic, 18) + '</span>'; }
  catch (e2) { return '<span class="tc-km-note">' + tcEsc(n) + '</span>'; }
}
/* v5859（用户口径「操作键列表 要和 其他物种的操作键列表同构，键鼠/xbox 都要有」）：
   键鼠键 -> Xbox 键**不猜**：
     ① 先拿项目权威键位表 LB_KEYMAP_ACTIONS 按 kbm 反查同动作的 pad（与物品侧 _findAct 同口径）
     ② 表里没有才落 LB_WIT_XBOX（物品侧的静态映射）
     ③ 都没有 -> 返回 ''（渲染成「不适用」） */
function lbAbilKeyPad(kbm){
  var kb = String(kbm || '');
  if (!kb || kb.charAt(0) === '~') return '';
  /* v5861：鼠标移动（视角）= 手柄右摇杆。
     ARK 手柄的视角控制就是右摇杆；项目 LB_KEYMAP_ACTIONS 里没有「转动视角」这个 kbm 动作，反查不到，
     所以这里显式给出（不是从表里推出来的，而是游戏内确定的映射）。 */
  if (kb === 'mouse_move') return 'xbox_stick_r';
  try {
    var A = (typeof LB_KEYMAP_ACTIONS !== 'undefined' && LB_KEYMAP_ACTIONS) ? LB_KEYMAP_ACTIONS : [];
    for (var i = 0; i < A.length; i++) {
      var a = A[i];
      if (!a) continue;
      /* v5861：项目表里 kbm 可能是字符串也可能是 {k:[…],hold:1} 对象，两种都要认。 */
      var _k = a.kbm;
      var k0 = (typeof _k === 'string') ? _k : ((_k && _k.k && _k.k.length) ? String(_k.k[0] || '') : '');
      if (k0 !== kb) continue;
      var p = a.pad;
      if (typeof p === 'string' && p) return p;
      if (p && p.k && p.k.length) return String(p.k[0] || '');
    }
  } catch (e1) {}
  try { if (LB_WIT_XBOX[kb]) return LB_WIT_XBOX[kb]; } catch (e2) {}
  return '';
}
function lbAbilEnRows(){
  var arr = [];
  try { arr = wikiTabIntro('abilKeys') || []; } catch (e0) { arr = []; }
  var out = [], seen = {};
  (arr || []).forEach(function (x) {
    var keys = lbAbilEnKeyIds((x && x.k) || '');
    var a = String((x && x.a) || '').trim();
    if (!keys.length || a.length < 2) return;
    var sig = keys.join('|') + '|' + a;
    if (seen[sig]) return;
    seen[sig] = 1;
    out.push({ keys: keys, a: a });
  });
  return out;
}
/* v5857⑤：无图标的键（鼠标 / 斜杠）用文本键帽，不走 CDN PNG（那条路必然 404 隐藏）。 */
function lbAbilKeyChip(kd, size){
  var s = String(kd || '');
  if (s.charAt(0) === '~'){
    return '<span class="lbk-txt" style="display:inline-block;min-width:20px;padding:0 6px;border:1px solid currentColor;'
      + 'border-radius:4px;font-size:12px;line-height:16px;text-align:center;opacity:.85">' + tcEsc(s.slice(1)) + '</span>';
  }
  try { return (typeof tcKeyChipHtml === 'function') ? tcKeyChipHtml(s, size || 23) : s; } catch (eC) { return s; }
}
/* v5859（用户口径「明明都渲染了操作键列表，为啥置顶文案中还在重复介绍」）：
   置顶文案剔除**已经被操作键表覆盖**的整行（能解析出按键的行）。
   ⚠ 只在操作键表真的渲染出来时才过滤（见 renderAbilTab），否则信息全丢。 */
function lbAbilIntroRest(list){
  var out = [];
  (list || []).forEach(function (line) {
    var s = String(line == null ? '' : line).trim();
    if (!s) return;
    var r = null;
    try { r = lbAbilParseKeys([s]); } catch (e) { r = null; }
    if (r && r.length) return;   // 已由操作键表呈现
    out.push(s);
  });
  return out;
}
function lbAbilKeysHtml(){
  /* v5857：只读 AI 整理结果（LB_WT.data.abilIntro）做主干，
     不再用 lbWtPick 回落 wiki 英文原文（回落来的是英文长句，会污染表格）。 */
  /* v6031：AI 丢了原文换键位（见 lbWtAbilIntroDropped）⇒ 这些键位是编造的，整表不渲染 */
  try {
    var _fbK = (lbAbilIntroPick().list) || [];
    if (lbWtAbilIntroDropped(_fbK)) return '';
  } catch (eG0) {}
  var arr = [];
  try { arr = (LB_WT.data && LB_WT.data.abilIntro) || []; } catch (eK0) { arr = []; }
  var rows = [], _en = 0;
  try { rows = lbAbilParseKeys(arr); } catch (eK1) { rows = []; }
  if (!rows.length){
    try { rows = lbAbilEnRows(); } catch (eK2) { rows = []; }
    if (rows.length) _en = 1;
  }
  if (!rows.length) return '';
  /* v5859：与物品侧 / 技能一览完全同构：
     tc-km > tc-km-g(键鼠) + tc-km-vs(/) + tc-km-g(Xbox)，表头「操作 / 操作键」（不限宽） */
  var _side = function (keys) {
    var kk = (keys || []).filter(function (x) { return !!x; });
    if (!kk.length) return '<span class="tc-km-note">不适用</span>';
    return kk.map(function (k) { return lbAbilKeyChip(k, 23); }).join('<span class="tc-km-sep">+</span>');
  };
  var h = '<div class="tc-sec"><div class="tc-h" data-keep="1">操作键<em>' + rows.length + ' 项' + (_en ? ' · 原文' : '') + '</em></div>'
    + '<table class="tc-tb"><thead><tr><th>操作</th><th>操作键</th></tr></thead><tbody>';
  rows.forEach(function (r) {
    var mp = '';
    (r.mods || []).forEach(function (m) { mp += lbAbilModIcon(m); });
    /* v5860：W/S 都反查到 xbox_stick_l_vertical、A/D 都反查到 xbox_stick_l_horizontal
       ⇒ 不去重会渲染成两个一模一样的图标。按顺序去重。 */
    var padKeys = [];
    (r.keys || []).forEach(function (k) {
      var p = lbAbilKeyPad(k);
      if (p && padKeys.indexOf(p) < 0) padKeys.push(p);
    });
    h += '<tr><th>' + tcEsc(r.a) + '</th><td><span class="tc-km">'
      + '<span class="tc-km-g">' + mp + _side(r.keys) + '</span>'
      + '<span class="tc-km-vs">/</span>'
      + '<span class="tc-km-g">' + mp + _side(padKeys) + '</span>'
      + '</span></td></tr>';
  });
  return h + '</tbody></table>'
    + '<div class="tc-note">按键取自 wiki 官方操控说明；'
    + '牵引模式的按键原文未标注，按游戏内实际键位补齐；游戏内改过按键时以游戏设置为准。</div>'
    + '</div>';
}

/* ===== renderAbilTab ===== */
function renderAbilTab(){
  var d = ABIL[CUR];
  var _N = 0;
  var _H = function(t, em){ return tcHStr(_N++, t, em); };
  var h = '<div class="tc">';
  if(!d){
    /* v5850：结构化技能块缺失（载具 / ark 回退）时，只要还有置顶文案（战斗说明等）就照常渲染，不再直接早退。 */
    var _ap0 = { list: [], matLine: '' };
    try { _ap0 = lbAbilIntroPick(); } catch (eA0) { _ap0 = { list: [], matLine: '' }; }
    var _hk0 = '';
    try { _hk0 = lbAbilKeysHtml(); } catch (eK1) { _hk0 = ''; }
    if ((_ap0.list || []).length || _ap0.matLine || _hk0){
      /* v5859：有操作键表时，置顶文案剔除已覆盖行（防重复） */
      var _ai0 = null;
      try { _ai0 = lbWtAbilIntroDropped(_ap0.list || []) ? (LB_WT_LAST_AI = 0, (_ap0.list || [])) : lbWtPick('abilIntro', _ap0.list || []); } catch (eGD0) { _ai0 = lbWtPick('abilIntro', _ap0.list || []); }
      if (_hk0) { try { _ai0 = lbAbilIntroRest(_ai0); } catch (eR0) {} }
      var _h0 = '<div class="tc">' + wikiIntroHtml(_ai0) + _hk0 + '</div>';
      document.getElementById('lbWikiBody').innerHTML = _h0;
      return;
    }
    h += '<div class="tc-sec"><div class="tc-hintb">该物种未收录技能数据。</div></div></div>';
    document.getElementById('lbWikiBody').innerHTML = h;
    return;
  }
  // 描述前置：战斗说明（一句一行，>5 行折叠）
  // v5691（用户口径「这种说明是无效的」）：后端 HOME.abilIntro 三句里
  //   ①「可破坏茅草木材石头金属泰克」= 徽章被拍平 ⇒ 抽出做表格（见下）
  //   ②「1 级、100% 驯服效率、无烙印时的基础伤害。打开伤害计算器 ›」= 模板套话 + 失效链接 ⇒ 丢弃
  //   ③ 真实战斗说明 ⇒ 保留
  var _ap = lbAbilIntroPick();
  var _matLine = _ap.matLine;
  var _introArr = _ap.list;
  // v5781（用户口径「置顶正文都应该 AI 整理」）：技能 Tab 置顶正文此前从未走 AI ⇒ 永远没有 .tc-ai
  /* v5859：先算操作键表，有表时置顶文案剔除已覆盖行（避免同一按键被介绍两遍）。
     lbAbilKeysHtml / lbAbilIntroRest 都不调 lbWtPick ⇒ 不会污染 LB_WT_LAST_AI（.tc-ai 标记）。 */
  var _hkB = '';
  try { _hkB = lbAbilKeysHtml(); } catch (eK2) { _hkB = ''; }
  var _aiB = null;
  try { _aiB = lbWtAbilIntroDropped(_introArr) ? (LB_WT_LAST_AI = 0, _introArr) : lbWtPick('abilIntro', _introArr); } catch (eGD) { _aiB = lbWtPick('abilIntro', _introArr); }
  if (_hkB) { try { _aiB = lbAbilIntroRest(_aiB); } catch (eR2) {} }
  h += wikiIntroHtml(_aiB);
  h += _hkB;

  // v5691：可破坏材质 → 表格（材质 / 采集破坏值；值从技能表反查，同材质取各技能最大值）
  var _matList = lbAbilMatList(_matLine, d.mats);
  if (_matList.length){
    var _matValOf = function (name) {
      var mx = null;
      (d.skills || []).forEach(function (k) {
        (k.mats || []).forEach(function (m) {
          if (lbMatNorm(m.zh) !== lbMatNorm(name)) return;
          var n = parseFloat(String(m.v || '').replace(/[^0-9.\-]/g, ''));
          if (!isFinite(n)) return;
          if (mx === null || n > mx) mx = n;
        });
      });
      return (mx === null) ? '—' : String(mx);
    };
    // v5694（用户口径「— 就是指不能破坏，可以直接不显示那一行」）：无破坏值的材质行不渲染
    var _matKeep = _matList.filter(function (n) { return _matValOf(n) !== '\u2014'; });
    if (_matKeep.length){
      // v5785：表格 → 卡片（每材质一张，含实物图标）
      var _mCards = '<div class="tc-tiles">' + _matKeep.map(function (n) {
        var _u = lbMatIconUrl(n);
        return '<div class="tc-tile tc-tile-ic">'
          + (_u ? '<img src="' + _u + '" alt="" loading="lazy">' : '')
          + '<div class="tc-tile-tx">'
          +   '<div class="tc-tile-k">' + n + '</div>'
          +   '<div class="tc-tile-v">' + _matValOf(n) + '</div>'
          + '</div></div>';
      }).join('') + '</div>';
      h += '<div class="tc-sec">' + _H('可破坏材质', '采集时对各材质的破坏值') + _mCards + '</div>';
    }
  }

  // v5695（用户口径「4 个技能 这个无需显示」）：徽章与下方「🎬 技能演示（N 个）」重复，整块删除

  // ① 技能一览（技能 / 操作键 / 基础伤害 / 特殊倍率）
  if(d.skills && d.skills.length){
    var t1 = '<thead><tr><th>\u6280\u80fd</th><th>\u64cd\u4f5c\u952e</th><th class="num">\u57fa\u7840\u4f24\u5bb3</th><th class="num">\u7279\u6b8a\u500d\u7387</th></tr></thead><tbody>'
      + d.skills.map(function(k){
          return '<tr><th>' + k.zh + '</th>'
            + '<td>' + tcKeyChips(k.key) + '</td>'
            + '<td class="num">' + (k.dmg || '\u2014') + '</td>'
            + '<td class="num">' + (k.mult || '\u2014') + '</td></tr>';
        }).join('') + '</tbody>';
    // v5691（用户口径「这种说明是无效的」）：删掉副标题「1 级 · 100% 驯服效率 · 无烙印」模板
    h += '<div class="tc-sec">' + _H('\u6280\u80fd\u4e00\u89c8')
       + '<table class="tc-tb">' + t1 + '</table></div>';
  }

  // ② 采集伤害（技能 × 材质）
  var withMats = (d.skills || []).filter(function(k){ return k.mats && k.mats.length; });
  if(withMats.length){
    // v5785：表格 → 卡片（每技能一张，卡内逐材质列「图标 + 材质 + 值」）
    var _sCards = '<div class="tc-tiles">' + withMats.map(function(k){
      var _rows = k.mats.filter(function(m){ return m.v && String(m.v).trim() && String(m.v).trim() !== '\u2014'; })
        .map(function(m){
          var _u = lbMatIconUrl(m.zh);
          return '<span class="tc-mi">' + (_u ? '<img src="' + _u + '" alt="" loading="lazy">' : '')
               + m.zh + ' <b>' + m.v + '</b></span>';
        }).join('');
      if (!_rows) return '';
      return '<div class="tc-tile">'
        + '<div class="tc-tile-k">' + k.zh + '</div>'
        + '<div class="tc-mi-rows">' + _rows + '</div></div>';
    }).join('') + '</div>';
    if (_sCards !== '<div class="tc-tiles"></div>'){
      h += '<div class="tc-sec">' + _H('\u91c7\u96c6\u4f24\u5bb3', '\u5bf9\u5404\u6750\u8d28\u7684\u7834\u574f\u503c') + _sCards + '</div>';
    }
  }

  // ③ 伤害抗性（分类 / 项目 / 效果）
  if(d.resist && d.resist.length){
    var rows = [];
    d.resist.forEach(function(c){
      c.items.forEach(function(it, i){
        var v = it.v || '';
        var col = '#8b93a7';
        if (v.indexOf('+') === 0) col = '#f87171';
        else if (v.indexOf('-') === 0) col = '#4ade80';
        else if (v.indexOf('\u514d\u75ab') >= 0) col = '#38bdf8';
        rows.push('<tr><th>' + (i === 0 ? c.cat : '') + '</th><td>' + it.zh + '</td>'
          + '<td class="num" style="color:' + col + '">' + v + '</td></tr>');
      });
    });
    h += '<div class="tc-sec">' + _H('\u4f24\u5bb3\u6297\u6027', '\u6b63\u503c=\u53d7\u4f24\u52a0\u6210 \u00b7 \u8d1f\u503c=\u51cf\u4f24')
       + '<table class="tc-tb"><thead><tr><th>\u5206\u7c7b</th><th>\u9879\u76ee</th><th class="num">\u6548\u679c</th></tr></thead><tbody>'
       + rows.join('') + '</tbody></table></div>';
  }

  // ④ 技能演示（视频，源仍为 wikily CDN）
  if(d.videos && d.videos.length){
    h += '<div class="tc-sec">' + _H('\u6280\u80fd\u6f14\u793a', '\u70b9\u51fb\u5207\u6362')
       + renderAbil(d.videos, 'tab') + '</div>';
  }

  h += '</div>';
  document.getElementById('lbWikiBody').innerHTML = h;
  tcMountIntro();
}

/* ===== v161：物品 Wiki 速查（与物种面板同构；入口按钮共用 lbWikiBtnPaint） ===== */
var LB_WIKI_ITEM_API = String(LB_WIKI_API || '').replace(/\/api\/wiki\/?$/, '/api/wiki_item/');
/* v288：武器专属动作表（键位由后端从 ARK Wiki Usage 段抽出：{k,kbm,pad}）
   结构对齐 LB_KEYMAP_ACTIONS；只登记「该武器上含义与通用不同」的动作名。
   未登记的键自动回落 LB_KEYMAP_ACTIONS 同 kbm 条目的中文名 —— 键位不重复翻译。 */
var LB_WI_WEAPON_ACT = {
  'Goo_Gun': [
    { id:'goo_harvest', zh:'采集尸体（装填黏液）', kbm:'keyboard_ctrl_left', pad:'xbox_rb',       note:'对准尸体按 Ctrl，把尸体转成黏液弹药' },
    { id:'goo_burst',   zh:'快速喷射',             kbm:'mouse_left',          pad:'xbox_rt',       note:'点按只射一个小黏液球' },
    { id:'goo_charge',  zh:'蓄力球（按住）',       kbm:'mouse_right',         pad:'xbox_lt',       note:'约 2.5 秒充满，再按左键射出' },
    { id:'goo_switch',  zh:'切换黏液类型',         kbm:'keyboard_r',          pad:'xbox_button_x', note:'腐蚀性 / 弹性 两种' }
  ]
};

/* ===== v5641（用户口径）：本服 Game.ini 的 ConfigOverrideSupplyCrateItems 接入「战利品来源」=====
   · 数据源：后端 /api/cfg_rules?server=X&file=GAME（全部服务器并行，任一有覆盖即纳入，未来新增服自动跟进）
   · 解析：复用项目既有 UE 括号解析器 lbUeFields/lbUeList/lbUeStrs/lbUeNums（v5515 同一套）
   · 概率：按「每箱至少出 1 个」逆推 —— 单 set 固定件数用超几何公式；结构复杂则不算（保留 wiki 值并标注） */
var LB_INI_OVR = null;      // { crateClass: { servers:[], sets:[], computable:bool } }
var LB_INI_OVR_P = null;    // 加载 Promise（幂等）

function lbIniNormCls(s){
  return String(s || '').replace(/^PrimalItem_?/i, '').replace(/_C$/i, '').replace(/[^a-z0-9]/gi, '').toLowerCase();
}
function lbIniParseCrateOvr(val){
  var f = null;
  try { f = lbUeFields(val); } catch (e0) { return null; }
  if (!f) return null;
  var crate = (lbUeStrs(f.SupplyCrateClassString)[0] || '').trim();
  if (!crate) return null;
  var sets = [];
  lbUeList(f.ItemSets || '').forEach(function (s) {
    var sf = null;
    try { sf = lbUeFields(s); } catch (e1) { return; }
    if (!sf) return;
    var entries = [];
    lbUeList(sf.ItemEntries || '').forEach(function (e) {
      var ef = null;
      try { ef = lbUeFields(e); } catch (e2) { return; }
      if (!ef) return;
      var w = lbUeNum(ef.EntryWeight, 1);
      // v5669：补出行的「能显示的信息」——ini 里本就有数量范围与品质倍率，此前全被丢弃
      var _qMin = lbUeNum(ef.MinQuality, 0), _qMax = lbUeNum(ef.MaxQuality, 0);
      var _nMin = lbUeNum(ef.MinQuantity, 1), _nMax = lbUeNum(ef.MaxQuantity, 1);
      lbUeStrs(ef.ItemClassStrings || '').forEach(function (c) {
        if (c) entries.push({ cls: c, w: w, qMin: _qMin, qMax: _qMax, nMin: _nMin, nMax: _nMax });
      });
    });
    sets.push({
      w: lbUeNum(sf.SetWeight, 1),
      n: lbUeNum(sf.MinNumItems, 1),
      nMax: lbUeNum(sf.MaxNumItems, 1),
      entries: entries
    });
  });
  // 可算条件：每个 set 抽取件数固定（minN==maxN）且有条目
  var computable = sets.length > 0 && sets.every(function (s) { return s.n === s.nMax && s.entries.length > 0; });
  return { crate: crate, sets: sets, computable: computable };
}
// 超几何：T 总权重、不放回抽 n 次、目标权重 W ⇒ 至少命中 1 次
function lbIniHyper(W, T, n){
  if (!(T > 0) || !(W > 0) || n <= 0) return 0;
  if (W >= T) return 1;
  var p = 1, N = Math.max(0, Math.floor(n));
  for (var i = 0; i < N; i++) {
    var den = T - i;
    if (den <= 0) { p = 0; break; }
    var num = T - W - i;
    if (num <= 0) { p = 0; break; }
    p *= num / den;
  }
  return 1 - p;
}
// 某物品在某箱子里的「每箱至少出 1 个」百分比；算不出返回 null
function lbIniCrateChance(rec, itemKeys){
  if (!rec || !rec.computable || !itemKeys || !itemKeys.length) return null;
  var totSetW = 0, acc = 0, any = false;
  rec.sets.forEach(function (s) { totSetW += s.w; });
  if (!(totSetW > 0)) return null;
  rec.sets.forEach(function (s) {
    var T = 0, W = 0;
    s.entries.forEach(function (e) {
      T += e.w;
      if ((typeof lbIniKeyHit === 'function' ? lbIniKeyHit(lbIniNormCls(e.cls), itemKeys) : (itemKeys.indexOf(lbIniNormCls(e.cls)) >= 0))) W += e.w;   // v5663：同步后缀匹配
    });
    if (!(T > 0)) return;
    any = true;
    acc += (s.w / totSetW) * ((W > 0) ? lbIniHyper(W, T, s.n) : 0);
  });
  return any ? (acc * 100) : null;
}
// v5652（用户口径「wikily 没写到、本服 ini 有写的也要补出来」）：
//   判断某箱子是否**包含**该物品 —— lbIniCrateChance 的 null 无法区分「不含该物品」与「结构不可算」，故单独判定
// v5663（用户口径「没看到补出的标识」根治）：修「键格式不对齐」导致的 0 命中
//   现象：页面 LB_WI.cur 是**短名**（GooGun），ini 里是**全类名**（PrimalItem_WeaponGooGun_C）
//        lbIniNormCls 剥掉 PrimalItem_/ _C 后得到 googun vs weapongoogun ⇒ 永远不等
//   修法：除全等外，再做**双向后缀匹配**（短名 ≥6 字符才启用，避免误吞）
function lbIniKeyHit(k, itemKeys){
  if (itemKeys.indexOf(k) >= 0) return true;
  for (var i = 0; i < itemKeys.length; i++){
    var t = itemKeys[i];
    if (!t || t.length < 6) continue;
    if (k.length > t.length && k.slice(-t.length) === t) return true;   // 全类名以短名结尾
    if (t.length > k.length && t.slice(-k.length) === k) return true;   // 反向
  }
  return false;
}
function lbIniCrateHas(rec, itemKeys){
  if (!rec || !itemKeys || !itemKeys.length) return false;
  var sets = rec.sets || [];
  for (var i = 0; i < sets.length; i++){
    var es = sets[i].entries || [];
    for (var j = 0; j < es.length; j++){
      if (lbIniKeyHit(lbIniNormCls(es[j].cls), itemKeys)) return true;
    }
  }
  return false;
}
// v5669：补出行展示用统计 —— 该物品在「命中权重占比最高」的 set 里的权重/数量/品质倍率
function lbIniCrateStat(rec, itemKeys){
  if (!rec || !itemKeys || !itemKeys.length) return null;
  var best = null;
  var _has = (typeof lbIniKeyHit === 'function');
  (rec.sets || []).forEach(function (s) {
    var T = 0, W = 0, qMin = null, qMax = null, nMin = null, nMax = null;
    (s.entries || []).forEach(function (e) {
      T += e.w;
      var _hit = _has ? lbIniKeyHit(lbIniNormCls(e.cls), itemKeys) : (itemKeys.indexOf(lbIniNormCls(e.cls)) >= 0);
      if (!_hit) return;
      W += e.w;
      if (e.qMin != null && (qMin === null || e.qMin < qMin)) qMin = e.qMin;
      if (e.qMax != null && (qMax === null || e.qMax > qMax)) qMax = e.qMax;
      if (e.nMin != null && (nMin === null || e.nMin < nMin)) nMin = e.nMin;
      if (e.nMax != null && (nMax === null || e.nMax > nMax)) nMax = e.nMax;
    });
    if (!(W > 0) || !(T > 0)) return;
    var ratio = W / T;
    if (!best || ratio > best.ratio) {
      best = { w: W, T: T, ratio: ratio, qMin: qMin, qMax: qMax, nMin: nMin, nMax: nMax, setW: s.w };
    }
  });
  return best;
}
function lbIniLoadOvr(){
  if (LB_INI_OVR_P) return LB_INI_OVR_P;
  LB_INI_OVR_P = new Promise(function (resolve) {
    var srv = [], base = '';
    try { srv = (LB.SERVERS || []).map(function (s) { return s.abbr; }); } catch (e0) {}
    try { base = LB_API || ''; } catch (e1) {}
    if (!srv.length) { LB_INI_OVR = {}; resolve({}); return; }
    var tasks = srv.map(function (ab) {
      return fetch(base + '/api/cfg_rules?server=' + encodeURIComponent(ab) + '&file=GAME', { method: 'GET' })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (j) { return { ab: ab, j: j }; })
        .catch(function () { return { ab: ab, j: null }; });
    });
    Promise.all(tasks).then(function (arr) {
      var map = {};
      var cost = {};
      var stack = {};   // v5917（用户口径）：堆叠上限——只取孤岛 Game.ini 的 ConfigOverrideItemMaxQuantity，当全服通用   // v5913（用户口径）：ini 自定义配方索引 —— { normCls: { cls, servers:[], bySrv:{ab:costs} } }
      arr.forEach(function (o) {
        var j = o.j; if (!j) return;
        var items = j.items || j.entries || [];
        for (var i = 0; i < items.length; i++) {
          var e = items[i];
          var k = String((e && (e.k || e.key)) || '').toLowerCase();
          if (k === 'configoverrideitemcraftingcosts') {   // v5913：ConfigOverrideItemCraftingCosts → 服务器自定义配方
            var _pc = null;
            try { _pc = lbCfgParseCraftCost(String(e.v || e.value || '')); } catch (_ePC) { _pc = null; }
            if (_pc && _pc.costs && _pc.costs.length) {
              var _nk = lbIniNormCls(_pc.item);
              if (_nk) {
                var _rc = cost[_nk];
                if (!_rc) _rc = cost[_nk] = { cls: _pc.item, servers: [], bySrv: {} };
                if (_rc.servers.indexOf(o.ab) < 0) _rc.servers.push(o.ab);
                _rc.bySrv[o.ab] = _pc.costs;
              }
            }
            continue;
          }
          if (k === 'configoverrideitemmaxquantity') {   // v5917：堆叠上限覆盖（仅孤岛，全服通用）
            if (String(o.ab) === 'Isl') {
              var _pm = null;
              try { _pm = lbCfgParseMaxQty(String(e.v || e.value || '')); } catch (_ePM) { _pm = null; }
              if (_pm && Number(_pm.max) > 0 && _pm.item) {
                var _nkS = lbIniNormCls(_pm.item);
                if (_nkS) stack[_nkS] = Number(_pm.max);
              }
            }
            continue;
          }
          if (k !== 'configoverridesupplycrateitems') continue;
          var rec = lbIniParseCrateOvr(String(e.v || e.value || ''));
          if (!rec) continue;
          var cur = map[rec.crate];
          if (!cur) {
            cur = map[rec.crate] = { crate: rec.crate, servers: [], sets: rec.sets, computable: rec.computable };
          }
          if (cur.servers.indexOf(o.ab) < 0) cur.servers.push(o.ab);
        }
      });
      LB_INI_OVR = map;
      LB_INI_COST = cost;
      LB_INI_STACK = stack;   // v5917   // v5913：ini 自定义配方索引（空表也算已加载）
      resolve(map);
    });
  });
  return LB_INI_OVR_P;
}

/* ===== v5913（用户口径）：服务器 ini 自定义配方**优先**（ConfigOverrideItemCraftingCosts 整体覆盖官方原配方）=====
   · 索引：LB_INI_COST{ normCls: { cls, servers:[], bySrv:{ab:[{item,count,exact}]} } }
   · 取用：先按当前服找，当前服没写覆盖则取任一写了覆盖的服（同名覆盖口径一致）
   · 语义：命中即**整体替换**官方配方，绝不与原配方合并 */
var LB_INI_COST = null;
function lbIniCostOf(cls, sv){
  try{
    if(!LB_INI_COST) return null;
    var nk = lbIniNormCls(cls);
    if(!nk) return null;
    var rec = LB_INI_COST[nk] || null;
    if(!rec){
      var keys = Object.keys(LB_INI_COST);
      for(var i = 0; i < keys.length; i++){ if(lbIniKeyHit(keys[i], [nk])){ rec = LB_INI_COST[keys[i]]; break; } }
    }
    if(!rec || !rec.bySrv) return null;
    var ab = String(sv || '');
    if(ab && rec.bySrv[ab]) return { costs: rec.bySrv[ab], src: 'ini', server: ab, servers: rec.servers || [] };
    var f = (rec.servers || [])[0];
    if(f && rec.bySrv[f]) return { costs: rec.bySrv[f], src: 'ini', server: f, servers: rec.servers || [] };
    return null;
  }catch(e){ return null; }
}
function lbIniCostEnsure(cb){
  if(LB_INI_COST){ if(cb) cb(); return; }
  if(typeof lbIniLoadOvr !== 'function'){ if(cb) cb(); return; }
  try{ lbIniLoadOvr().then(function(){ if(cb) cb(); }).catch(function(){ if(cb) cb(); }); }
  catch(e){ if(cb) cb(); }
}

/* ===== v5917（用户口径）：材料堆叠上限（用于待制作汇总的「N组」）优先级：
   ① 孤岛 Game.ini 的 ConfigOverrideItemMaxQuantity（覆盖优先；视为全服通用，不展示服名）
   ② 物品 wiki 缓存 quick 的「堆栈大小 / Stack Size」（未缓存则主动拉取 + 轮询直到就绪）
   ③ 都没有 ⇒ 返回 0（就不显示组数） */
var LB_INI_STACK = null;                 // { normCls: max }
var LB_STACK_LSKEY = 'lb_item_stack_v2'; // { normCls: { v:max|0, ts } }   // v5919：v1→v2（作废上一版写入的「未命中」记录，否则 1h 内不重试）
LB._stackMem = null;
LB._stackPend = {};
LB._stackQ = [];
LB._stackBusy = false;
function lbStackNorm(s){ try{ return lbIniNormCls(s); }catch(e){ return String(s||'').toLowerCase().replace(/[^a-z0-9]/g,''); } }
// v5919（事故修复）：wiki 接口只认「不含实例后缀」的类名——配方给的是 `PrimalItemResource_MetalIngot_C`，
//   直传会拿不到 ready（实测：去 `_C` 后 status=ready 且 quick 含「堆栈大小 300」）⇒ 查询前统一剥后缀。
function lbStackQueryCls(cls){
  var s = String(cls == null ? '' : cls).trim();
  s = s.replace(/_C_\d+$/i, '').replace(/_C$/i, '');
  return s || String(cls == null ? '' : cls).trim();
}
function lbIniStackOf(cls){
  try{
    if(!LB_INI_STACK) return 0;
    var nk = lbStackNorm(cls); if(!nk) return 0;
    var v = LB_INI_STACK[nk];
    if(!v){
      var ks = Object.keys(LB_INI_STACK);
      for(var i = 0; i < ks.length; i++){ if(lbIniKeyHit(ks[i], [nk])){ v = LB_INI_STACK[ks[i]]; break; } }
    }
    return Number(v) || 0;
  }catch(e){ return 0; }
}
function lbStackCacheAll(){
  if(!LB._stackMem){
    try{ LB._stackMem = JSON.parse(localStorage.getItem(LB_STACK_LSKEY) || '{}') || {}; }catch(e){ LB._stackMem = {}; }
  }
  return LB._stackMem;
}
function lbStackCacheRec(cls){
  var m = lbStackCacheAll(), r = m[lbStackNorm(cls)];
  if(!r) return null;
  var ttl = (Number(r.v) > 0) ? (30 * 86400000) : (60000);   // v5920：命中长缓存；未命中仅 1 分钟（下次打开即重试）
  if(Date.now() - (Number(r.ts) || 0) > ttl) return null;
  return r;
}
function lbStackKnown(cls){ try{ if(lbIniStackOf(cls) > 0) return true; }catch(e){} return !!lbStackCacheRec(cls); }
function lbStackGet(cls){
  try{ var iv = lbIniStackOf(cls); if(iv > 0) return iv; }catch(e0){}
  var r = lbStackCacheRec(cls);
  return (r && Number(r.v) > 0) ? Number(r.v) : 0;
}
function lbStackPut(cls, v){
  var m = lbStackCacheAll();
  m[lbStackNorm(cls)] = { v: Number(v) || 0, ts: Date.now() };
  try{ localStorage.setItem(LB_STACK_LSKEY, JSON.stringify(m)); }catch(e){}
}
function lbStackFromQuick(q){
  var arr = (Object.prototype.toString.call(q) === '[object Array]') ? q : [];
  for(var i = 0; i < arr.length; i++){
    var kv = arr[i] || {};
    var k = String(kv[0] == null ? '' : kv[0]);
    if(!/\u5806\u6808\u5927\u5c0f|\u5806\u53e0\u5927\u5c0f|Stack\s*Size/i.test(k)) continue;
    var n = parseFloat(String(kv[1] == null ? '' : kv[1]).replace(/[^0-9.]/g, ''));
    if(isFinite(n) && n > 0) return Math.round(n);
  }
  return 0;
}
function lbStackEnsure(cls, cb){
  // v5918（事故修复）：**任何分支都不同步回调**——原实现在「已命中/已挂起」分支里同步 cb，
  //   cb 又调 lbTodoRender，而 lbTodoRender 再调 lbStackEnsure ⇒ 同步无限递归 ⇒ 主线程卡死（就是「运行几分钟后卡住」）。
  if(!cls) return;
  if(lbStackKnown(cls)) return;
  var nk = lbStackNorm(cls);
  if(LB._stackPend[nk]) return;
  if(!LB._stackQ) LB._stackQ = [];
  if(LB._stackQ.length >= 24) return;   // v5918：队列上限
  LB._stackPend[nk] = 1;
  LB._stackQ.push({ cls: cls, nk: nk, cb: (typeof cb === 'function' ? cb : null) });
  if(LB._stackBusy) return;
  LB._stackBusy = true;
  (function next(){
    var job = LB._stackQ.shift();
    if(!job){ LB._stackBusy = false; return; }
    var settled = false;
    var finished = function(){
      if(settled) return;
      settled = true;
      delete LB._stackPend[job.nk];
      if(job.cb){ try{ setTimeout(job.cb, 0); }catch(e0){} }   // v5918：异步回调，杜绝重入递归
      setTimeout(next, 400);
    };
    var base = (typeof LB_WIKI_ITEM_API === 'string' && LB_WIKI_ITEM_API) ? LB_WIKI_ITEM_API : 'https://data.whiterober.ccwu.cc/api/wiki_item/';
    /* v5921（用户口径）：**复用项目现有解析** —— 物品 Wiki 面板就是用 `lbItemMeta(cls).base`（词典基名）作引擎键，
       堆叠查询同样只用这一个键（不另造候选名），与面板共享同一份缓存；base 为空才退回去 _C 全类名。 */
    var _mmq = null; try{ _mmq = lbItemMeta(job.cls); }catch(_e0){ _mmq = null; }
    var _qkey = String((_mmq && _mmq.base) || '').trim();
    if(!_qkey) _qkey = lbStackQueryCls(job.cls);
    /* v5920（用户口径）：**每次打开待制作浮窗只查一次**，不做连续轮询；
       fetching/idle 不写缓存（下次打开重试），避免高频打后端。 */
    fetch(base + encodeURIComponent(_qkey), { cache: 'no-store' })
      .then(function(r){ return r.json(); })
      .then(function(j){
        var d = (j && j.data) || {};
        var v = lbStackFromQuick(((d.PARSED || {}).quick) || []);
        if(v > 0){ lbStackPut(job.cls, v); finished(); return; }
        var st = String((j && j.status) || '');
        if(st === 'error' || d._fail){ lbStackPut(job.cls, 0); finished(); return; }
        finished();   // 仍在抓取：不记缓存，下次打开再查
      })
      .catch(function(){ finished(); });
  })();
}

/* v303：wikily 地图英文名 -> 项目地图中文名（官方口径）
   Astraeos=星耀（L6922 PO 官译）/ Genesis=创世（v5623 起服务器昵称与地图口径一致） */
var LB_WI_MAP_ZH = {
  'The Island': '孤岛', 'Scorched Earth': '焦土', 'The Center': '核心岛',
  'Aberration': '畸变', 'Extinction': '灭绝', 'Ragnarok': '仙境',
  'Valguero': '瓦尔盖罗', 'Astraeos': '星耀', 'Lost Colony': '失落地',
  // v5634（用户口径 + 取证）：创世是**一张地图**，含陆地/海洋两个相对独立区域；
  //   wikily 分列两个 chip（各 17），但 maps/genesis-ocean 会 302 重定向到 maps/genesis、
  //   canonical/title/h1/正文指纹全同 ⇒ 不是独立地图。此处标注成「创世 · 陆地 / 创世 · 海洋」。
  'Genesis': '创世 · 陆地', 'Genesis Ocean': '创世 · 海洋', 'Genesis 2': '创世2',
  'Crystal Isles': '水晶岛', 'Fjordur': '峡湾',
  'Mod maps': '模组地图', 'Mod Maps': '模组地图', 'Mod map': '模组地图', 'Club ARK': '俱乐部'
};
function lbWiMapZh(s){
  var t = String(s || '').trim();
  if (!t) return t;
  if (LB_WI_MAP_ZH[t]) return LB_WI_MAP_ZH[t];
  var m = /^(.+?)\s*(\+\s*\d+\s*地图)?$/.exec(t);
  if (m){
    var base = m[1].trim();
    if (LB_WI_MAP_ZH[base]) return LB_WI_MAP_ZH[base] + (m[2] ? (' ' + m[2].trim()) : '');
  }
  return t;
}

/* v303：物品品质档位 —— 项目权威定稿（L13153：0 原始 / 1 普通 / 2 优秀 / 3 精良 / 4 史诗 / 5 传说，对齐 ShooterGame 官中）
   注意：这是**物品品质**，与 LB_EGG_LV（饲料/蛋品质：基础/简易/普通/上等/卓越/非凡）不是同一套。
   wikily 页面给的是 ARK 官方档位译名（原始/粗糙/学徒/工匠/精工/卓越），需先归档再取项目名。
   色值唯一源：lbBpStageCol() —— 不在此处定义颜色 */
var LB_WI_QUAL_ZH = ['原始', '普通', '优秀', '精良', '史诗', '传说'];
var LB_WI_QUAL_IDX = {
  '原始': 0, 'Primitive': 0,
  '普通': 1, '粗糙': 1, 'Ramshackle': 1,
  '优秀': 2, '学徒': 2, 'Apprentice': 2,
  '精良': 3, '工匠': 3, 'Journeyman': 3,
  '史诗': 4, '精工': 4, 'Mastercraft': 4,
  '传说': 5, '卓越': 5, 'Ascendant': 5
};
function lbWiQualIdx(v){
  var t = String(v || '').trim();
  if (!t) return -1;
  return Object.prototype.hasOwnProperty.call(LB_WI_QUAL_IDX, t) ? LB_WI_QUAL_IDX[t] : -1;
}
function lbWiQualHtml(v){
  var t = String(v || '').trim();
  if (!t) return '';
  var i = lbWiQualIdx(t);
  if (i < 0) return t;
  var col = '';
  try { col = (typeof lbBpStageCol === 'function') ? lbBpStageCol(i) : ''; } catch (e) { col = ''; }
  return '<span style="color:' + col + ';font-weight:600">' + (LB_WI_QUAL_ZH[i] || t) + '</span>';
}

// v5687（用户口径「把属性的内容直接拼接到概览里」）：删「属性」tab，属性数值/使用效果并入概览
var LB_WI_TABS = ['概览', '制作', '获取', '指南', '生成'];   // v5829（用户口径「物品里都不应该有模块TAB，全部统一叫装备」）：移除「模块」   // v301：删「同类」；v5687：删「属性」；v5739：「生成指令」→「生成」（物品侧不加「技巧」——dododex 无物品 tips）
var LB_WI = { cur: '', tab: 0, err: null, data: null, p: null, pIdx: null, pollN: 0 };   // 索引：0概览/1制作/2获取/3指南/4生成（v5739 修正过时注释——原写「tab5=指南、tab6=生成指令」，而那套编号在 v301/v5687 删 tab 后早已不存在）
// 属性字段中文（ARK 官方口径；项目无数值字段词典，悬停可见英文原名）
var LB_WI_STAT_ZH = {
  'Equip Time': '装备时间', 'Harvest Tool': '采集工具', 'Melee Damage': '近战伤害',
  'Ammo Per Clip': '弹匣容量', 'Ammo Per Shot': '每发耗弹', 'Infinite Ammo': '无限弹药',
  'Reload Duration': '装填时间', 'Time Between Shots': '射击间隔',
  'Durability Per Shot': '每发耗耐久', 'Durability Per Melee Hit': '近战每次耗耐久',
  'Harvest Resource Multiplier': '资源采集倍率', 'Hit Damage': '单发伤害',
  'Armor': '护甲', 'Durability': '耐久度', 'Hypothermal Insulation': '抗寒',
  'Hyperthermal Insulation': '抗热', 'Water Capacity': '水容量', 'Food': '食物',
  'Health': '生命', 'Stamina': '耐力', 'Oxygen': '氧气', 'Torpidity': '昏迷',
  'Night Vision': '夜视', 'FOV': '视野', 'Size': '尺寸', 'Weight': '重量',
  'Decay Time': '腐烂时间', 'Socket Count': '插槽数', 'Craft XP': '制作经验',
  'Craft Time': '制作时间', 'Stack Size': '堆叠大小',
  // v5689（用户口径「Spoil time 为啥没翻译？全面排查还有哪里没翻译」）：
  //   后 4 项对应后端 _WK_ITEM_QUICK / _WK_ITEM_STAT 白名单里此前未覆盖的键
  'Spoil time': '腐烂时间', 'Stack size': '堆叠大小', 'Engram': '记忆印痕',
  'Impulse': '冲击力', 'Disable On Electric Storm': '雷暴时失效'
};
var LB_WI_VAL_ZH = { 'Pick': '镐', 'Hatchet': '斧', 'yes': '是', 'no': '否', 'Yes': '是', 'No': '否' };

function lbWiEl(id){ return document.getElementById(id); }
function lbWiZh(k){ return LB_WI_STAT_ZH[k] || k; }
function lbWiVal(v){ return LB_WI_VAL_ZH[v] || v; }

function lbWikiItemHas(cls){
  if (!cls) return false;
  try {
    var m = (LB_WI.idx && LB_WI.idx.items) || null;
    return !!(m && String(m[cls] || '').length);
  } catch (e) { return false; }
}

function lbWikiItemIndexLoad(){
  if (LB_WI.pIdx) return LB_WI.pIdx;
  var u = LB_WIKI_ITEM_API.replace(/\/api\/wiki_item\/?$/, '/api/wiki_item/index');
  LB_WI.pIdx = fetch(u, { cache: 'no-store' })
    .then(function (r) { return r.json(); })
    .then(function (j) { LB_WI.idx = j || {}; return j; })
    .catch(function (e) { LB_WI.pIdx = null; throw e; });
  return LB_WI.pIdx;
}

/* ===== v5924：通用浮窗层 lbSheet*（物种 Wiki / 物品 Wiki / 资讯浮窗 共用 .lw-* 结构）
   规范见 计划\计划_资讯广场迁入搞事系统_v1_20261102.md §4.1
   · 不新增 .lw-* 样式；显隐与定位靠 `#<id>` 的 id 规则
   · 现有两个 Wiki 浮窗的静态 HTML 保持不变，仅共享布局修正逻辑 */
function lbSheetBuild(id, opts){
  opts = opts || {};
  var ov = document.getElementById(id);
  if (!ov){
    ov = document.createElement('div');
    ov.id = id;
    ov.innerHTML =
      '<div class="lw-panel">'
      + '<div class="lw-head">'
      +   '<span class="lw-title" id="' + id + 'Title"></span>'
      +   '<span class="lw-help" id="' + id + 'Help" hidden aria-label="本页说明"><i class="mdi mdi-help-circle-outline"></i></span>'
      +   (opts.extraHeadHtml || '')
      +   '<button class="lw-x" onclick="' + (opts.onClose || ('lbSheetClose(\'' + id + '\')')) + '" title="关闭" aria-label="关闭"><i class="mdi mdi-close"></i></button>'
      + '</div>'
      + '<div class="lw-tabs" id="' + id + 'Tabs"></div>'
      + '<div class="lw-meta" id="' + id + 'Meta"></div>'
      + '<div class="lw-body" id="' + id + 'Body"></div>'
      + '<div class="lw-foot" id="' + id + 'Foot" hidden></div>'
      + '</div>';
    document.body.appendChild(ov);
  }
  /* v6403（根治）：所有 lbSheet 浮窗统一带 .lb-sheet 类 —— 默认显隐/遮罩由 app.css 的
     .lb-sheet / .lb-sheet.show 提供，**新增浮窗不必再往 id 白名单里加名字**。
     （历史踩坑：v5966 / v6032 / v6208 / v6402 各因漏加白名单导致「浮窗关不掉」） */
  try { if (ov.classList && !ov.classList.contains('lb-sheet')) ov.classList.add('lb-sheet'); } catch (eC) {}
  /* v6211（用户口径「在线玩家行的 tips 呢」）：**所有 lbSheet 浮窗在此统一挂 tips 引擎** ——
     tips 引擎靠 .lb-tipb 标记类（closest('.lb-tipb')），原来只有 lbSrvCtl / lbNews 两份复制品
     各自写死容器，新建浮窗默认没有 ⇒ 气泡全丢（#lbUpd 就这么中招的）。
     这里建窗即挂，以后新增浮窗无需再记。lbTipsWatch 定义在 app_core.js（先加载），
     延迟加载场景用 typeof 兜底。 */
  try { if (typeof lbTipsWatch === 'function') lbTipsWatch(id, 60); } catch (eT) {}
  return {
    ov: ov,
    title: document.getElementById(id + 'Title'),
    help:  document.getElementById(id + 'Help'),
    tabs:  document.getElementById(id + 'Tabs'),
    meta:  document.getElementById(id + 'Meta'),
    body:  document.getElementById(id + 'Body'),
    foot:  document.getElementById(id + 'Foot')   /* v6050：底部固定栏（无内容时 hidden） */
  };
}
/* v6405（用户口径「拉取指定版本 浮窗层级不对 被覆盖了」）：打开时把 z-index 抬到最上层。
   根因：所有浮窗的 z-index 都是 9998（.lb-sheet / id 白名单同值）⇒ 谁在 DOM 后面谁在上；
   「先建过 A、后建 B，再打开 A」时 A 会被 B 盖住（lbUpdVer 被 lbUpd 盖住即此）。
   递增 z-index 不改 DOM 结构、不影响滚动位置与 iframe，最安全。 */
var _LB_SHEET_Z = 9998;
function lbSheetOpen(id){
  var o = document.getElementById(id);
  if (!o) return;
  try { _LB_SHEET_Z += 1; o.style.zIndex = String(_LB_SHEET_Z); } catch (e) {}
  o.classList.add('show');
}
function lbSheetClose(id){ var o = document.getElementById(id); if (o) o.classList.remove('show'); }
/* 布局修正（原 lbWikiItemLayoutFix 主体参数化）：隐藏「紧邻 .tc-intro 的无序号小标题」 */
function lbSheetLayoutFix(body){
  if (!body) return;
  var hs = body.querySelectorAll('.tc-h');
  for (var i = 0; i < hs.length; i++){
    var el = hs[i];
    var nx = el.nextElementSibling;
    var beforeIntro = !!(nx && nx.classList && nx.classList.contains('tc-intro'));
    var hasNum = /[\u2460-\u2473]/.test(String(el.textContent || ''));
    if (el.getAttribute('data-keep') === '1') continue;   // v5925：显式保留（资讯每条消息的标题）
    if (beforeIntro && !hasNum){
      if (el.getAttribute('data-lf-hide') !== '1'){ el.style.display = 'none'; el.setAttribute('data-lf-hide', '1'); }
    } else if (el.getAttribute('data-lf-hide') === '1'){
      el.style.display = ''; el.removeAttribute('data-lf-hide');
    }
  }
}
function lbSheetLayoutWatch(body){
  if (!body || body.__lbSheetLF) return;
  try {
    var t = null;
    var mo = new MutationObserver(function(){
      /* v6106：同 lbWikiLayoutWatch —— 先同步修正（微任务阶段，浏览器绘制之前），
         再保留 60ms 校正。lbSheetLayoutFix 只改 style/属性、不改 childList ⇒ 不会自触发。 */
      try { lbSheetLayoutFix(body); } catch (e0) {}
      if (t) clearTimeout(t);
      t = setTimeout(function(){ try { lbSheetLayoutFix(body); } catch (e) {} }, 60);
    });
    mo.observe(body, { childList: true, subtree: true });
    body.__lbSheetLF = mo;
  } catch (e) {}
}

/* ===== v5924：资讯广场（阶段 1：骨架 + 假数据；阶段 2 接后端 /api/news/*）
   · 入口在「生存者」浮窗 header（联盟成员位置左侧）
   · 正文走 wiki 的 .tc-* 结构；中英标注复用 lbEnMark（容器带 .tc-ai）
   · 无刷新按钮：打开/切 Tab 时按需拉取（后端 1 分钟冷却 + 增量） */
/* v5952（用户口径「[discord](https://mdi.bessarabov.com/icon/discord) 这个图标能用么」）：
   MDI 官方库里**确实有** discord 图标，但项目内置的 MDI 字体版本缺这个字形
   （实测 `content:none`、宽度 0）。升级全站字体风险大，改为**内联 SVG**（path 取自
   cdn.jsdelivr.net/npm/@mdi/svg/svg/discord.svg），不依赖字体版本。 */
var LB_SVG_DISCORD = 'M22,24L16.75,19L17.38,21H4.5A2.5,2.5 0 0,1 2,18.5V3.5A2.5,2.5 0 0,1 4.5,1H19.5A2.5,2.5 0 0,1 22,3.5V24M12,6.8C9.32,6.8 7.44,7.95 7.44,7.95C8.47,7.03 10.27,6.5 10.27,6.5L10.1,6.33C8.41,6.36 6.88,7.53 6.88,7.53C5.16,11.12 5.27,14.22 5.27,14.22C6.67,16.03 8.75,15.9 8.75,15.9L9.46,15C8.21,14.73 7.42,13.62 7.42,13.62C7.42,13.62 9.3,14.9 12,14.9C14.7,14.9 16.58,13.62 16.58,13.62C16.58,13.62 15.79,14.73 14.54,15L15.25,15.9C15.25,15.9 17.33,16.03 18.73,14.22C18.73,14.22 18.84,11.12 17.12,7.53C17.12,7.53 15.59,6.36 13.9,6.33L13.73,6.5C13.73,6.5 15.53,7.03 16.56,7.95C16.56,7.95 14.68,6.8 12,6.8M9.93,10.59C10.58,10.59 11.11,11.16 11.1,11.86C11.1,12.55 10.58,13.13 9.93,13.13C9.29,13.13 8.77,12.55 8.77,11.86C8.77,11.16 9.28,10.59 9.93,10.59M14.1,10.59C14.75,10.59 15.27,11.16 15.27,11.86C15.27,12.55 14.75,13.13 14.1,13.13C13.46,13.13 12.94,12.55 12.94,11.86C12.94,11.16 13.45,10.59 14.1,10.59Z';
var LB_NEWS = {
  tab: 0, data: null, err: null, loading: false,
  /* v5931：译文缓存 {mid: 中文}（来自后端 /api/news/zh，全服共享）+ 补翻忙碌标记 */
  zh: {}, zhBusy: false,
  /* v5934：每 Tab 折叠状态 {tabId: 1=已展开}（会话内保持，打开浮窗重置） */
  expand: {},
  /* v5933（用户口径「就算有缓存，为啥切换TAB时还是要正在拉取资讯…挺久的」）：
     会话级内存缓存 {tabId: {data, zh}}。切 Tab 命中即秒开、零请求；
     只在「打开浮窗」时清空一次（等于每次打开拉一次最新），关闭再打开会重新拉。 */
  cache: {},
  mock: /(\?|&)newsmock=1/.test(String(location.search || '')),   // v5927：默认走真实后端，?newsmock=1 看演示数据
  /* v5948（用户口径）：一级 Tab 合并为分组结构——
     「ADM版本 + ADM预告」合为一个一级 ADM；「API版本 + API缓存」合为一个一级 API。
     组内用二级切换条（样式弱化，不抢一级 tab）；子项 id 必须与后端 NEWS_TABS 一致。 */
  /* v5950（用户口径「HA 的资讯广场 每个 TAB 似乎都有底部的链接吧？」）：
     对齐旧 HA `ark_patch` 视图的「底部链接图标」。旧页用的是 HA 内部签名图片
     （/api/image/serve/xxx?authSig=...，**会过期**），此处改用项目已有的 MDI 字体图标，不会失效。 */
  tabs: [
    { id: 'patch_pc', name: 'ASA PC版本', short: 'PC版本', links: [
        { href: 'https://survivetheark.com/index.php?/forums/', icon: 'mdi-forum-outline', text: '论坛', label: 'survivetheark 论坛' },
        { href: 'https://discord.com/channels/729837326120910915/735188487615283232', icon: 'mdi-chat-outline', svg: LB_SVG_DISCORD, text: 'Discord', label: 'Discord 频道' }
      ] },
    { id: 'news',     name: '方舟新闻',   short: '新闻', links: [
        { href: 'https://survivetheark.com/', icon: 'mdi-forum-outline', text: '官网', label: 'survivetheark 官网' },
        { href: 'https://discord.com/channels/729837326120910915/735188458972381194', icon: 'mdi-chat-outline', svg: LB_SVG_DISCORD, text: 'Discord', label: 'Discord 频道' }
      ] },
    { id: 'grp_adm',  name: 'ADM', short: 'ADM', children: [
        /* v5956（用户口径）：二级 Tab 文字 ADM版本 ⇒ 版本（一级已标暂 ADM） */
        { id: 'patch_channel', name: 'ADM版本', short: '版本', links: [
            { href: 'https://asadedicatedmanager.eu/', icon: 'mdi-shield-crown-outline', text: 'ADM', label: 'ASADedicatedManager' },
            { href: 'https://discord.com/channels/1219676794840547388/1239938054328684657', icon: 'mdi-chat-outline', svg: LB_SVG_DISCORD, text: 'Discord', label: 'Discord 频道' }
          ] },
        { id: 'adm',           name: 'ADM预告', short: '预告', links: [
            { href: 'https://discord.com/channels/1219676794840547388/1219684258298200224', icon: 'mdi-chat-outline', svg: LB_SVG_DISCORD, text: 'Discord', label: 'Discord 频道' }
          ] }
      ] },
    /* v5954（用户口径「汉化TAB底下 替换成一个」）：原贴吧 + 123 网盘 ⇒ 飞书文档 */
    { id: 'tieba',    name: '汉化版本',   short: '汉化', links: [
        { href: 'https://my.feishu.cn/wiki/ZipZwbSwZipThMkiFrHcibeCn6e', icon: 'mdi-file-document-outline', text: '飞书', label: '汉化文档（飞书）' }
      ] },
    { id: 'grp_api',  name: 'API', short: 'API', children: [
        /* v5953（用户口径）：API 组两个子 Tab 底部加「Ark Survival Ascended | Ark Server Api」入口 */
        /* v5956（用户口径）：二级 Tab 文字 API版本 ⇒ 版本（一级已标暂 API） */
        { id: 'api_ver',   name: 'API版本', short: '版本', links: [
            { href: 'https://ark-server-api.com/resources/categories/ark-survival-ascended.2/', icon: 'mdi-api', text: 'ASA API', label: 'Ark Survival Ascended | Ark Server Api' },
            { href: 'https://discord.com/channels/1219408563122999356/1219419717694001313', icon: 'mdi-chat-outline', svg: LB_SVG_DISCORD, text: 'Discord', label: 'Discord 频道' }
          ] },
        /* v5956（用户口径）：二级 Tab 文字 API缓存 ⇒ 缓存 */
        { id: 'api_cache', name: 'API缓存', short: '缓存', links: [
            { href: 'https://ark-server-api.com/resources/categories/ark-survival-ascended.2/', icon: 'mdi-api', text: 'ASA API', label: 'Ark Survival Ascended | Ark Server Api' },
            { href: 'https://discord.com/channels/1219408563122999356/1243622513779675186', icon: 'mdi-chat-outline', svg: LB_SVG_DISCORD, text: 'Discord', label: 'Discord 频道' }
          ] }
      ] }
  ]
};
function lbNewsEntry(){
  var po = document.querySelector('.lb-picker-overlay');
  if (po) po.remove();
  lbNewsOpen();
}
function lbNewsOpen(){
  LB_NEWS.tab = 0; LB_NEWS.data = null; LB_NEWS.err = null; LB_NEWS.zh = {};
  LB_NEWS.sub = {}; LB_NEWS.__leafId = '';   /* v5948：重置二级选择 */
  LB_NEWS.cache = {};          // v5933：每次打开浮窗清空 ⇒ 「打开浮窗时刷一次最新」
  LB_NEWS.expand = {};         // v5934：每次打开恢复折叠（只展开最新 5 条）
  lbSheetBuild('lbNews', { onClose: 'lbNewsClose()' });
  lbSheetOpen('lbNews');
  try { lbNewsTipsWatch(); lbNewsTips(); } catch (eT) {}   // v5955：首屏浮窗建好后立即补齐
  lbNewsFetch();
}
function lbNewsClose(){ lbSheetClose('lbNews'); }
/* v5948：取当前真正要拉数据的「叶子 tab」（分组时取组内当前子项，否则就是自身） */
function lbNewsLeaf(){
  var g = LB_NEWS.tabs[LB_NEWS.tab] || null;
  if (!g) return null;
  if (!g.children || !g.children.length) return g;
  var want = (LB_NEWS.sub && LB_NEWS.sub[g.id]) || g.children[0].id;
  for (var i = 0; i < g.children.length; i++){
    if (g.children[i].id === want) return g.children[i];
  }
  return g.children[0];
}
/* v5948：组内二级切换（不改一级选中项） */
function lbNewsSub(gi, id){
  try {
    var g = LB_NEWS.tabs[gi];
    if (!g || !g.children || !g.children.length) return;
    LB_NEWS.sub = LB_NEWS.sub || {};
    if (LB_NEWS.sub[g.id] === id) return;
    LB_NEWS.sub[g.id] = id;
    lbNewsTab(gi);
  } catch (e) {}
}
function lbNewsTab(i){
  var g = LB_NEWS.tabs[i] || null;
  if (!g) return;
  LB_NEWS.tab = i;
  var t = lbNewsLeaf();
  if (!t) return;
  /* v5948：同一个叶子就不重复拉（分组后可能重复点同一一级） */
  if (LB_NEWS.__leafId === t.id && LB_NEWS.data) return;
  LB_NEWS.__leafId = t.id;
  /* v5933：命中会话缓存 ⇒ 立即渲染（0 请求、无「正在拉取」闪烁）；
     未命中才走 loading + 拉取。缓存只在 lbNewsOpen 时清空，故会话内切回永远秒开。 */
  var c = (t && LB_NEWS.cache) ? LB_NEWS.cache[t.id] : null;
  if (c && c.data){
    LB_NEWS.data = c.data;
    LB_NEWS.zh = c.zh || {};
    LB_NEWS.err = null; LB_NEWS.loading = false;
    lbNewsRender();
    return;
  }
  LB_NEWS.data = null; LB_NEWS.zh = {};
  LB_NEWS.loading = true;      // v5933：直接进 loading，避免先闪一下「暂无内容」
  lbNewsRender();
  lbNewsFetch();
}
/* HTML 白名单清洗：剥脚本/事件属性，块级标签转段落（防 XSS） */
function lbNewsHtmlToText(html){
  var s = String(html || '');
  s = s.replace(/<(script|style)[\s\S]*?<\/\1>/gi, '');
  s = s.replace(/\son[a-z]+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, '');
  s = s.replace(/<a\b[^>]*>([\s\S]*?)<\/a>/gi, '$1');
  s = s.replace(/<\/?(div|p|br|h[1-6]|li|ul|ol|tr|table|tbody|thead)[^>]*>/gi, '\n');
  s = s.replace(/<[^>]+>/g, '');
  var lines = s.split('\n').map(function(x){ return x.replace(/[ \t]+/g, ' ').trim(); })
                 .filter(function(x){ return x; });
  if (!lines.length) return '';
  /* v5929：本函数只做 lbMdEsc 转义、不走 lbMdRender ⇒ 行内 **加粗** 会原样显示星号
     （实测 patch_pc 有 2 个 <p> 形如 **v94.19 - Minor version ...**）。这里补渲染成 <b>，
     与 lbMdRender 的颜色口径一致（#f1f5f9）；残余不成对星号直接剥掉。 */
  return lines.map(function(x){
    var hh = lbMdEsc(x).replace(/\*\*([^*]+)\*\*/g, '<b style="color:#f1f5f9">$1</b>').replace(/\*\*/g, '');
    return '<p style="margin:0 0 6px">' + hh + '</p>';
  }).join('');
}
/* v5937（用户口径「所有经过 AI 翻译处理过的，完全可以重构结构，生成那种复杂结构啊？」）：
   AI 译文允许带结构化标签（h3/p/ul/ol/li/table/thead/tbody/tr/th/td/b/strong/em/br）。
   旧的 lbNewsHtmlToText 会把除 <p> 外全部剥掉 ⇒ 表格被打回纯文本，所以另开一个**白名单**渲染器：
     · 危险块（script/style/iframe/object/embed/link/meta）整段删除
     · 所有 on* 事件属性、javascript: 协议一律去掉
     · 其余非白名单标签只剥标签、保留文字
     · <table> 自动补 class="tc-tb"（复用 wiki 同款表格样式），th.num 保留数字右对齐
     · h1/h2/h4~h6 统一降级为 h3（只保留一种标题层级） */
function lbNewsRichHtml(html){
  var s = String(html || '');
  s = s.replace(/<(script|style|iframe|object|embed|link|meta)\b[^>]*>[\s\S]*?<\/\1>/gi, '');
  s = s.replace(/<(script|style|iframe|object|embed|link|meta)\b[^>]*\/?>/gi, '');
  s = s.replace(/\son[a-z]+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, '');
  s = s.replace(/javascript\s*:/gi, '');
  var ALLOW = /^(h1|h2|h3|h4|h5|h6|p|ul|ol|li|table|thead|tbody|tfoot|tr|th|td|b|strong|em|i|br)$/i;
  s = s.replace(/<(\/?)([a-z][a-z0-9]*)([^>]*)>/gi, function(mo, close, tag, attrs){
    var t = String(tag).toLowerCase();
    if (!ALLOW.test(t)) return '';
    if (/^h[1-6]$/.test(t)) t = 'h3';
    if (close) return '</' + t + '>';
    var keep = '';
    if ((t === 'td' || t === 'th') && /class\s*=\s*"\s*num\s*"/i.test(attrs || '')) keep = ' class="num"';
    return '<' + t + keep + '>';
  });
  s = s.replace(/<table\s*>/gi, '<table class="tc-tb">');
  s = s.replace(/<thead\s*>/gi, '<thead>').replace(/<tbody\s*>/gi, '<tbody>');
  return s.trim();
}
/* v5941：点击封面才注入真播放器（避免重建时 iframe 被 ERR_ABORTED） */
function lbNewsVideoPlay(el){
  try {
    var box = el && el.parentNode;
    if (!box) return;
    var src = box.getAttribute('data-embed') || '';
    var raw = box.getAttribute('data-raw') || src;
    if (!src) return;
    /* v5944（用户口径「视频点了后是黑的，找根因」）：实测发现本机浏览器会
       **静默阻止 YouTube 的 iframe 导航**（google.com 会报 X-Frame-Options 错误，
       而 youtube.com/embed 和 youtube-nocookie.com/embed 都停在 about:blank 且零报错）⇒ 永远是空白黑块。
       这里先真嵌入，2.5s 后若 iframe 仍未导航（contentDocument=null 表示跨域已加载成功）
       则自动降级为「在 YouTube 打开」按钮，不再留黑块。 */
    var f = document.createElement('iframe');
    f.className = 'tc-frame';
    f.setAttribute('allowfullscreen', '');
    f.setAttribute('frameborder', '0');
    f.setAttribute('allow', 'accelerometer;autoplay;clipboard-write;encrypted-media;gyroscope;picture-in-picture');
    f.setAttribute('src', src);
    box.innerHTML = '';
    box.appendChild(f);
    /* v5945：实测（等满 8s 仍 about:blank、onload 0 次）确认浏览器**禁止网页内嵌 YouTube**，
       但**顶层导航** youtube.com/watch 能正常打开 ⇒ 内嵌无解，只能降级为可点跳转卡。
       判定延时 2.5s → 6s（YouTube 首次加载偏慢时不误判）。 */
    setTimeout(function(){
      var blocked = false;
      try { blocked = !!f.contentDocument && f.contentDocument.URL === 'about:blank'; }
      catch (eD) { blocked = false; }
      if (!blocked) return;
      /* v5946：降级为纯文字提示，不再提供任何跳转链接 */
      box.innerHTML = '<div class="tc-video-fail">'
        + '<div class="tc-video-fail-t">当前浏览器不允许内嵌播放该视频</div>'
        + '</div>';
    }, 6000);
  } catch (e) {}
}
/* YouTube watch → embed（否则拒绘） */
function lbNewsFrameUrl(u){
  var s = String(u || '');
  var m = s.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([A-Za-z0-9_-]{6,})/);
  return m ? ('https://www.youtube.com/embed/' + m[1]) : s;
}
/* cards → .tc-* 段落（含 HTML 的剥标签，纯 md 才走 lbMdRender） */
function lbNewsCardsToTc(cards, tabId, zhMap){
  /* v5934（用户口径三项）：① 每个 Tab 只展开最新 5 条，其余折叠；
     ② 标题带序号（复用 tcHStr 的 TC_CN 序号表）；③ 每条独立卡片（样式见 #lbNews .lw-body .tc-sec）。
     分组口径 = Discord 消息（mid）：一条消息可能产出 文字+图+视频 多个卡片，必须算「一条」。 */
  var FOLD = 5;
  var groups = [], gmap = {};
  (cards || []).forEach(function(c){
    c = c || {};
    var key = String(c.mid || ('_x' + groups.length));
    if (!gmap[key]){ gmap[key] = { mid: String(c.mid || ''), items: [] }; groups.push(gmap[key]); }
    gmap[key].items.push(c);
  });
  /* v5944（用户口径「排序都错了，应该最新的在最上面」）：
     后端 `_news_refresh` 已 `reversed(msgs)`（Discord 返回最新在前 → 反转成最旧在前），
     这里在前端统一倒序回来（最新在上，且 FOLD=5 取到的就是最新 5 条）。*/
  groups.reverse();
  var exp = !!(LB_NEWS.expand && tabId && LB_NEWS.expand[tabId]);
  var out = [];
  /* v5935：序号必须按「有标题的卡片」自增，不能用消息组索引 ——
     首条消息常是纯图片/纯视频（无 <h3>），用组索引会让第一个标题从 ② 开始（实测）。 */
  var _n = 0;
  groups.forEach(function(g, gi){
    var parts = [];
    g.items.forEach(function(c){
      if (c.type === 'markdown'){
        var raw = String(c.content || '');
        /* v5931：译文按 mid 整段替换（译文保留 <h3> / `- ` 结构，下游渲染零改动） */
        var _zh = (zhMap && c.mid) ? String(zhMap[c.mid] || '') : '';
        if (_zh) raw = _zh;
        var m = raw.match(/^\s*<h3[^>]*>([\s\S]*?)<\/h3>/i);
        /* v5927/v5928：标题剥 markdown 标记（**加粗** / #### 井号 / 反引号） */
        var title = m ? m[1].replace(/<[^>]+>/g, '')
          .replace(/\*\*/g, '')
          .replace(/^#{1,6}\s+/, '')
          .replace(/`/g, '')
          .trim() : '';
        var rest = m ? raw.slice(m[0].length) : raw;
        /* v5937：含标签的（AI 译文 / 原始 HTML）走白名单富文本，保留表格与列表结构；
           纯 markdown 仍交给 lbMdRender。 */
        var body = /<[a-z][^>]*>/i.test(rest) ? lbNewsRichHtml(rest) : lbMdRender(rest);
        if (title) _n++;
        /* v5940（用户口径「每个小标题 无需 ⑤ 这种」）：卡片标题不再带 ①②③ 圈号，只留标题文字 */
        var hd = title
          ? ('<div class="tc-h" data-keep="1">' + lbMdEsc(title) + '</div>')
          : '';
        parts.push(hd + (body ? '<div class="tc-intro">' + body + '</div>' : ''));
      } else if (c.type === 'picture'){
        parts.push('<div class="tc-pic">'
          + '<img src="' + lbMdEsc(c.image || '') + '"'
          + ' data-mid="' + lbMdEsc(c.mid || '') + '" data-tab="' + lbMdEsc(tabId || '') + '"'
          + ' onerror="lbNewsImgErr(this)"'
          + ((c.tap_action && c.tap_action.url_path) ? (' onclick="window.open(\'' + lbMdEsc(c.tap_action.url_path) + '\',\'_blank\')"') : '')
          + ' loading="lazy" alt="" style="max-width:100%;border-radius:8px">'
          + '</div>');
      } else if (c.type === 'iframe'){
        /* v5941：封面 + 点击播放（避免 iframe 被重建中止后留黑块） */
        var _fu = lbNewsFrameUrl(c.url);
        var _raw = String(c.url || _fu);
        var _ym = _raw.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([A-Za-z0-9_-]{6,})/);
        var _pos = _ym ? ('https://i.ytimg.com/vi/' + _ym[1] + '/hqdefault.jpg') : '';
        parts.push('<div class="tc-video" data-embed="' + lbMdEsc(_fu) + '" data-raw="' + lbMdEsc(_raw) + '">'
          + '<div class="tc-video-ph" onclick="lbNewsVideoPlay(this)">'
          + (_pos ? ('<img src="' + lbMdEsc(_pos) + '" alt="" loading="lazy" onerror="this.setAttribute(\'data-broken\',\'1\')">') : '')
          + '<span class="tc-video-play"><i class="mdi mdi-play"></i></span>'
          + '</div>'
          /* v5946（用户口径「不需要 在新窗口打开 功能」）：已删除底部「▶ 在新窗口打开视频」链接 */
          + '</div>');
      }
    });
    var hid = (!exp && gi >= FOLD) ? ' lb-news-hide' : '';
    out.push('<div class="tc-sec lb-news-item' + hid + '" data-mid="' + lbMdEsc(g.mid) + '">'
      + parts.join('') + '</div>');
  });
  if (!exp && groups.length > FOLD){
    out.push('<button class="lb-news-more" onclick="lbNewsExpandMore()">展开全部（还有 '
      + (groups.length - FOLD) + ' 条）</button>');
  }
  return out.join('');
}
/* v5934：展开当前 Tab 的全部条目（状态记在 LB_NEWS.expand，会话内保持） */
function lbNewsExpandMore(){
  try {
    var t = lbNewsLeaf();
    if (!t) return;
    LB_NEWS.expand = LB_NEWS.expand || {};
    LB_NEWS.expand[t.id] = 1;
    lbNewsRender();
    var ov = document.getElementById('lbNews');
    var body = ov ? ov.querySelector('[id="lbNewsBody"]') : null;
    if (body) body.scrollTop = 0;
  } catch (e) {}
}
/* 阶段 1 假数据（三种卡片都覆盖，便于验证渲染与标注） */
function lbNewsMock(tabId){
  return [
    { type: 'markdown', content: '<h3>' + tabId + ' · 本次活动概览</h3>\n本次更新加入全新生物，并调整多张地图的资源分布。维护期间服务器将重启，请提前做好存档准备。' },
    { type: 'markdown', content: '<h3>改动要点</h3>\n金属锭 采集倍率提升至 2x\n聚合物 制作配方异常修复\n神器 掉落展示新增' },
    { type: 'picture', image: 'thumbs/webp96/757968e4bd91_w96.webp', tap_action: { action: 'url', url_path: 'https://survivetheark.com' } },
    { type: 'iframe', url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' }
  ];
}
/* v5927：图片过期自愈 —— Discord CDN 签名会过期，onerror 时只修这一条消息 */
function lbNewsApiBase(){
  return ((typeof LB_API === 'string' && LB_API) ? LB_API : 'https://data.whiterober.ccwu.cc').replace(/\/+$/, '');
}
function lbNewsImgErr(img){
  try {
    if (!img || img.__fixBusy) return;
    var mid = img.getAttribute('data-mid') || '';
    var tab = img.getAttribute('data-tab') || '';
    if (!mid || !tab) return;
    img.__fixBusy = 1;
    fetch(lbNewsApiBase() + '/api/news/imgfix?tab=' + encodeURIComponent(tab) + '&mid=' + encodeURIComponent(mid),
          { method: 'POST', cache: 'no-store' })
      .then(function(r){ return r.json(); })
      .then(function(j){
        img.__fixBusy = 0;
        if (j && j.ok && j.images && j.images.length){
          var u = j.images[0];
          if (u && u !== img.getAttribute('src')){ img.removeAttribute('data-broken'); img.src = u; }
        } else {
          /* v5940：修不回来的图直接隐藏（避免留下空框） */
          try { img.setAttribute('data-broken', '1'); } catch (eB) {}
        }
      })
      .catch(function(){ img.__fixBusy = 0; try { img.setAttribute('data-broken', '1'); } catch (eC) {} });
  } catch (e) {}
}
/* ===== v5955（用户口径「资讯广场 浮窗里的tips 全部要用自定义浮窗」）=====
   现状：关闭按钮(.lw-x) / 一级TAB(.lw-tab) / 底部来源链接(a) 只挂了 title
        ⇒ 浏览器原生白框提示（不受控、长文本被截）。
   做法：渲染后给 #lbNews 内所有带 title 的元素补 .lb-tipb，交给项目 tips 引擎 #lbTipBox。
   作用域仅 #lbNews（不动 lbSheet 共享模板，wiki 等其它浮窗不受影响）。
   注：.lb-tipb 在本项目无任何 CSS 定义（纯标记类）⇒ 补 class 不会改变外观。 */
/* v6211（用户口径「复用非复制」）：本函数原是 lbSrvCtlTips 的**复制品（第 2 份）**，
   现统一改调 app_core.js 的通用挂载器 lbTipsMark / lbTipsWatch（唯一实现），此处只留薄包装。
   60ms 防抖沿用原行为（资讯内容是异步插入/展开重建的，合并高频重渲染）。 */
function lbNewsTips(){
  if (typeof lbTipsMark === 'function') return lbTipsMark('lbNews');
  return 0;   /* app_core 未加载时兜底：不补类，保持原生 title */
}
function lbNewsTipsWatch(){
  if (typeof lbTipsWatch === 'function'){ lbTipsWatch('lbNews', 60); return; }
}
/* v5959（用户口径「资讯广场要有 AI 模块（复用非复制 wiki 的 ai 模块，整理按钮改叫翻译）」）：
   复用 lbTipsAiBoxHtml（wiki 用的同一个盒子，零复制），只换 state 文案与按钮名。
   行为＝增量补翻：只翻 LB_NEWS.zh 里还没 mid 的卡片（与自动补翻同一条链路 lbNewsTranslate）。 */
function lbNewsAiStat(){
  var d = LB_NEWS.data || {};
  var cards = d.cards || [];
  var total = 0, done = 0;
  for (var i = 0; i < cards.length; i++){
    var c = cards[i];
    if (!c || c.type !== 'markdown') continue;
    var mid = String(c.mid || '');
    if (!mid) continue;
    total++;
    if (LB_NEWS.zh && LB_NEWS.zh[mid]) done++;
  }
  return { total: total, done: done, todo: total - done };
}
function lbNewsAiBoxHtml(){
  var s = lbNewsAiStat();
  var st;
  if (LB_NEWS.zhBusy) st = 'AI 翻译中…';
  else if (!s.total) st = '当前 TAB 暂无可翻译内容';
  else if (!s.todo) st = '本 TAB 共 ' + s.total + ' 条，已全部译好';
  else st = '本 TAB 共 ' + s.total + ' 条 · 已译 ' + s.done + ' 条 · 待译 ' + s.todo + ' 条';
  return lbTipsAiBoxHtml({
    state: lbMdEsc(st),
    style: 'margin-top:12px',
    disabled: (!s.todo) || !!LB_NEWS.zhBusy,
    btn: { txt: '翻译', fn: 'lbNewsAiTranslate()' }
  });
}
function lbNewsAiTranslate(){
  if (LB_NEWS.zhBusy) return;
  var d = LB_NEWS.data || {};
  var s = lbNewsAiStat();
  if (!s.total){ try { lbToast('当前 TAB 暂无可翻译内容'); } catch (e0) {} return; }
  if (!s.todo){ try { lbToast('本 TAB 已全部译好'); } catch (e1) {} return; }
  LB_NEWS._noTok = 0;        /* 用户主动点 ⇒ 允许再次提示未配置 token */
  try { lbToast('AI 翻译已开始（待译 ' + s.todo + ' 条）…'); } catch (e2) {}
  lbNewsTranslate(d.tab, d.cards);
}
function lbNewsRender(){
  var S = lbSheetBuild('lbNews', { onClose: 'lbNewsClose()' });
  if (!S || !S.ov) return;
  S.title.innerHTML = '<i class="mdi mdi-newspaper-variant-outline"></i> 资讯广场';
  S.body.classList.add('tc-ai');
  S.tabs.innerHTML = LB_NEWS.tabs.map(function(t, i){
    return '<button class="lw-tab' + (i === LB_NEWS.tab ? ' on' : '') + '" onclick="lbNewsTab(' + i + ')" title="' + lbMdEsc(t.name) + '">'
         + lbMdEsc(t.short || t.name) + '</button>';
  }).join('');
  /* v5948：二级切换条（紧跟在一级 tab 栏下方，样式弱化）——只有当前一级有 children 才出现 */
  try {
    var pn = S.tabs.parentNode;
    var oldBar = pn ? pn.querySelector('.lb-news-sub') : null;
    if (oldBar && oldBar.parentNode) oldBar.parentNode.removeChild(oldBar);
    var g = LB_NEWS.tabs[LB_NEWS.tab];
    if (pn && g && g.children && g.children.length){
      var curLeaf = lbNewsLeaf() || {};
      var bar = document.createElement('div');
      bar.className = 'lb-news-sub';
      bar.innerHTML = g.children.map(function(c2){
        return '<button class="' + (c2.id === curLeaf.id ? 'on' : '') + '" onclick="lbNewsSub(' + LB_NEWS.tab + ',\'' + c2.id + '\')">'
             + lbMdEsc(c2.short || c2.name) + '</button>';
      }).join('');
      pn.insertBefore(bar, S.tabs.nextSibling);
    }
  } catch (eSub) {}
  var d = LB_NEWS.data || {};
  if (LB_NEWS.err){
    S.body.innerHTML = '<div class="tc-hintb">加载失败：' + lbMdEsc(String(LB_NEWS.err)) + '</div>';
  } else if (LB_NEWS.loading){
    S.body.innerHTML = '<div class="tc-hintb">正在拉取资讯…</div>';
  } else if (!d.cards || !d.cards.length){
    S.body.innerHTML = '<div class="tc-hintb">暂无内容</div>';
  } else {
    S.body.innerHTML = lbNewsCardsToTc(d.cards, d.tab || (lbNewsLeaf() || {}).id, LB_NEWS.zh);
  }
  /* v5959：AI 模块（复用 wiki 的 AI 盒子，按钮=翻译，增量补翻）——位于底部来源链接上方 */
  try {
    if (d.cards && d.cards.length){
      var _aiW = document.createElement('div');
      _aiW.innerHTML = lbNewsAiBoxHtml();
      if (_aiW.firstChild) S.body.appendChild(_aiW.firstChild);
    }
  } catch (eAi) {}
  /* v5950：底部来源链接（对齐旧 HA 资讯广场的「底部链接图标」）——不管有无内容都显示 */
  try {
    var _lf = lbNewsLeaf() || {};
    var _lks = _lf.links || [];
    if (_lks.length){
      var _ld = document.createElement('div');
      _ld.className = 'lb-news-links';
      _ld.innerHTML = _lks.map(function(l){
        return '<a href="' + lbMdEsc(l.href) + '" target="_blank" rel="noopener" title="' + lbMdEsc(l.label || '') + '">'
          + (l.svg
              ? ('<svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor" aria-hidden="true"><path d="' + l.svg + '"/></svg>')
              : ('<i class="mdi ' + lbMdEsc(l.icon || 'mdi-open-in-new') + '"></i>'))
          + (l.text ? ('<span>' + lbMdEsc(l.text) + '</span>') : '')
          + '</a>';
      }).join('');
      S.body.appendChild(_ld);
    }
  } catch (eLk) {}
  S.meta.innerHTML = d.updated ? ('更新于 ' + lbMdEsc(d.updated)) : '';
  try { lbNewsEnhance(S.body); } catch (e0) {}   // v5938：主题 + 列表/表格 重组为分区子卡片
  try { lbEnMarkWatch('lbNewsBody'); } catch (e1) { try { lbEnMark(S.body); } catch (e2) {} }
  try { tcSyncNotes('lbNewsBody', 'lbNewsHelp'); } catch (e3) {}
  try { lbSheetLayoutFix(S.body); } catch (e4) {}
  try { lbNewsTipsWatch(); lbNewsTips(); } catch (e5) {}   // v5955：浮窗内 tips 全走自定义浮窗（关闭/TAB/底部链接）
}
function lbNewsFetch(){
  var t = lbNewsLeaf();
  if (!t) return;
  if (LB_NEWS.mock){
    LB_NEWS.loading = false; LB_NEWS.err = null;
    LB_NEWS.data = { ok: true, tab: t.id, name: t.name, updated: '演示数据（?newsmock=1）', cards: lbNewsMock(t.name) };
    lbNewsRender();
    return;
  }
  LB_NEWS.err = null; LB_NEWS.loading = true;
  lbNewsRender();
  /* v5931：取数据 + 取译文**并行**，一次打开内完成（用户口径「翻译要和取数据完全合在一起」）。
     译文接口失败不影响正文；译文由后端全服共享，命中即零成本。 */
  var _base = lbNewsApiBase();
  var _pCards = fetch(_base + '/api/news/' + encodeURIComponent(t.id) + '?t=' + Date.now(), { cache: 'no-store' })
    .then(function(r){ if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); });
  var _pZh = fetch(_base + '/api/news/zh?tab=' + encodeURIComponent(t.id) + '&t=' + Date.now(), { cache: 'no-store' })
    .then(function(r){ return r.ok ? r.json() : null; })
    .catch(function(){ return null; });
  Promise.all([_pCards, _pZh])
    .then(function(arr){
      var j = arr[0], zj = arr[1];
      if (!j || j.ok === false) throw new Error((j && j.error) || '加载失败');
      var cur = lbNewsLeaf() || {};
      if (cur.id !== t.id) return;                       // 期间已切到别的 Tab，丢弃本次结果
      LB_NEWS.data = j; LB_NEWS.loading = false;
      /* v5932：历史脏数据（v5931 误写的 id/object/model 等元数据键）在入口处过滤掉 */
      var _zm = (zj && zj.map) ? zj.map : {};
      Object.keys(_zm).forEach(function(k3){ if (!/^[0-9]{15,25}$/.test(k3)) delete _zm[k3]; });
      LB_NEWS.zh = _zm;
      try { LB_NEWS.cache[t.id] = { data: j, zh: _zm }; } catch (eC) {}   // v5933：写会话缓存（zh 与 LB_NEWS.zh 同一引用，补翻后自动可见）
      lbNewsRender();
      lbNewsTranslate(t.id, j.cards || []);               // 只补翻缺译文的消息（增量）
    })
    .catch(function(e){
      LB_NEWS.err = String((e && e.message) || e); LB_NEWS.loading = false;
      lbNewsRender();
    });
}

/* v5931：资讯增量补翻（后端已有 GET/POST /api/news/zh，全服共享一份译文）
   · 只翻「zh map 里没有 mid」的 markdown 卡片 ⇒ 与取数据的增量口径完全一致，不重复烧 token
   · 分批（每批 4 条）串行请求，避免单次 token 超限；任一批失败只跳过该批，不阻断后续
   · 译文严格保留 <h3> 标签与 `- ` 列表前缀 ⇒ 下游 lbMdRender 渲染逻辑零改动
   · 全部批次结束后统一重渲染一次（避免多次重建浮窗导致滚动位置丢失） */
var LB_NEWS_ZH_SYS = '你是《方舟：生存飞升》(ARK: Survival Ascended) 官方公告的**译者兼排版编辑**。\n'
  + '用户给你若干条 Discord 公告原文（每条带 id），请逐条处理后返回。\n\n'
  + '【语言】\n'
  + '1) 一律输出**简体中文**：繁体中文必须转成简体；原本就是简体则保留其表达；英文全部翻译。\n'
  + '2) **不译**：版本号（v93.25 / 93.36 / v94.11）、日期、纯数字、@Steam/@Xbox/@Playstation/@Windows\n'
  + '   等平台标记、URL、代码/枚举类英文词。\n'
  + '3) **术语**：方舟专有名词用玩家通行译法（Metal Ingot 金属锭 / Polymer 聚合物 / '
  + 'Artifact 神器 / Bounty 赏金 / Boss 首领 等）；确无通行译法可保留英文。\n\n'
  + '【排版：允许重构结构】（不必逐行照搬，可按语义重新组织得更清晰）\n'
  + '4) **只能使用以下标签**：\n'
  + '   `<h3>标题</h3>`  `<p>段落</p>`  `<ul><li>条目</li></ul>`  `<ol><li>条目</li></ol>`\n'
  + '   `<table><thead><tr><th>表头</th></tr></thead><tbody><tr><td>单元</td></tr></tbody></table>`\n'
  + '   `<b>强调</b>`  `<br>`\n'
  + '   禁止使用 `<script>` `<style>` `<iframe>` `<a>` `<div>` `<span>`，'
  + '禁止任何 on* 事件属性、class、id、style。\n'
  + '5) **主动使用结构化排版**（本项目的 wiki 样式已全部开放）：\n'
  + '   - 「名称 → 说明」「项目 → 数量」「属性 → 数值」这类**有对照关系**的，一律用 `<table>` 两列表格；\n'
  + '   - 并列的同类条目（一条条修复项）用 `<ul><li>`；有先后顺序的步骤用 `<ol><li>`；\n'
  + '   - 内容分成多个主题时，**每个主题用 `<p><b>主题名</b></p>` 单独起头**（≤15 字），'
  + '     紧跟该主题的列表或表格，便于前端渲染成卡片区块。\n'
  + '6) 每条**必须以 `<h3>` 标题开头**（用原文标题精炼，不超过 40 字）。\n'
  + '7) 不要输出 Markdown 符号（** # - ` 等），不要加任何解释，不要出现「原文」「翻译」字样。\n\n'
  + '输出严格 JSON（不要代码块），键为 id，值为处理后的 HTML 串：\n'
  + '{"<id>": "<h3>标题</h3><p>...</p>", ...}';
function lbNewsTranslate(tabId, cards){
  try {
    var cfg = null; try { cfg = lbAiCfgGet(); } catch (e0) { cfg = null; }
    if (!cfg || !cfg.token){
      if (!LB_NEWS._noTok){ LB_NEWS._noTok = 1; try { lbToast('未配置大肥鱼 token，资讯显示英文原文'); } catch (e1) {} }
      return;
    }
    if (LB_NEWS.zhBusy) return;
    var todo = [], seen = {};
    (cards || []).forEach(function(c){
      if (!c || c.type !== 'markdown') return;
      var mid = String(c.mid || '');
      var raw = String(c.content || '');
      if (!mid || seen[mid]) return;
      if (LB_NEWS.zh && LB_NEWS.zh[mid]) return;          // 已有译文（含别处已翻好的）⇒ 跳过
      /* v5937（用户口径「还繁体监测啥？直接翻译不行么」）：取消「含英文才翻」的准入 ——
         汉化 Tab 的内容本身就是繁体中文，旧规则会把它们全部跳过。现在一律送 AI，
         由提示词负责「繁体转简体 / 已是简体原样保留」。已有译文的（含别的玩家翻好的）仍然直接命中缓存。 */
      if (raw.length < 8) return;
      seen[mid] = 1;
      todo.push({ id: mid, text: raw.slice(0, 1800) });
    });
    if (!todo.length) return;
    LB_NEWS.zhBusy = true;
    var BATCH = 4, batches = [], bi;
    for (bi = 0; bi < todo.length; bi += BATCH) batches.push(todo.slice(bi, bi + BATCH));
    var _ep = String(cfg.base || LB_AI_BASE).replace(/\/+$/, '') + '/chat/completions';
    var _done = 0, _all = batches.length, _got = 0;
    function step(k){
      if (k >= _all){
        LB_NEWS.zhBusy = false;
        if (_got) { try { lbNewsRender(); } catch (eR) {} }
        return;
      }
      var chunk = batches[k];
      var usr = chunk.map(function(x, n){ return '[' + (n + 1) + '] id=' + x.id + '\n' + x.text; }).join('\n\n');
      fetch(_ep, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + cfg.token },
        body: JSON.stringify({
          model: lbAiNormModel(cfg.model),
          messages: [{ role: 'system', content: LB_NEWS_ZH_SYS }, { role: 'user', content: usr }],
          temperature: 0.2, max_tokens: 8000,
          thinking: { type: 'disabled' },
          response_format: { type: 'json_object' }
        })
      })
        .then(function(r){ return r.text(); })
        .then(function(tx){
          /* v5932（实测事故修复）：v5931 直接把**整个 DeepSeek 响应体**当译文 map 解析 ⇒
             key 变成 id / object / model / system_fingerprint（全是响应元数据），
             4 条垃圾写进共享缓存、真译文一条没拿到。
             这里与 lbMapWikiDigest 逐字同款：先取 choices[0].message.content，再解析其中的 JSON。 */
          var _raw = null; try { _raw = JSON.parse(tx); } catch (eR0) { _raw = null; }
          var _ch0 = (_raw && _raw.choices && _raw.choices[0]) ? _raw.choices[0] : null;
          var _m0 = (_ch0 && _ch0.message) ? _ch0.message : null;
          var _ct = (_m0 && _m0.content) ? String(_m0.content) : '';
          var d = null;
          try { d = lbAiParseJson(_ct); } catch (eP) { d = null; }
          if (!d && _m0 && _m0.reasoning_content){ try { d = lbAiParseJson(String(_m0.reasoning_content)); } catch (eR1) { d = null; } }
          /* v5932：白名单校验 —— 只接受本批真实 id，杜绝 AI 自造键污染共享缓存 */
          var _valid = {};
          chunk.forEach(function(x){ _valid[String(x.id)] = 1; });
          var _pairs = [];
          if (Array.isArray(d)){
            d.forEach(function(e){
              if (!e || typeof e !== 'object') return;
              var pid = String(e.id || e.mid || '').trim();
              var ptx = String(e.zh || e.text || e.translation || e.content || '').trim();
              if (pid && ptx) _pairs.push([pid, ptx]);
            });
          } else if (d && typeof d === 'object'){
            Object.keys(d).forEach(function(k2){
              var v2 = d[k2];
              if (typeof v2 !== 'string' || !v2.trim()) return;
              _pairs.push([String(k2).replace(/^id=/, '').trim(), v2.trim()]);
            });
          }
          var items = [];
          _pairs.forEach(function(pr){
            var kk = pr[0], vv = pr[1];
            if (!_valid[kk]) return;                                   // 非本批 id ⇒ 丢弃
            if (vv.length > 20 && !/[\u4e00-\u9fa5]/.test(vv)) return;  // 明显没翻成中文 ⇒ 丢弃
            LB_NEWS.zh[kk] = vv.slice(0, 2000);
            items.push({ id: kk, text: vv.slice(0, 2000) });
          });
          if (items.length){
            _got += items.length;
            try {
              fetch(lbNewsApiBase() + '/api/news/zh', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tab: tabId, items: items })
              }).catch(function(){});
            } catch (eS) {}
          }
          step(k + 1);
        })
        .catch(function(){ step(k + 1); });
    }
    step(0);
  } catch (e) { LB_NEWS.zhBusy = false; }
}

function lbWikiItemOpen(){
  try { LB_WI.showAll = false; } catch (eSA) {}   // v5674：每次打开重置折叠状态
  var cls = '';
  try { if (LB.pickItem && LB.pickItem.base) cls = String(LB.pickItem.base); } catch (e) {}
  if (!cls) return;
  LB_WI.cur = cls; LB_WI.tab = 0; LB_WI.err = null; LB_WI.data = null; LB_WI.pollN = 0;
  LB_WI._iniTried = 0; LB_WI._craftHas = false;   // v5913：每次打开重置 ini 配方探测与「制作关注」按钮态
  var ov = lbWiEl('lbWikiItemOverlay'); if (ov) ov.classList.add('show');
  lbWikiItemLayoutWatch();   // v5915：隐藏紧邻文案块的无序号小标题
  lbWikiItemRender();
  lbWikiItemFetch();
}

function lbWikiItemClose(){
  var ov = lbWiEl('lbWikiItemOverlay'); if (ov) ov.classList.remove('show');
}

/* ===== v5913（用户口径）：wiki 浮窗「制作关注」——普通印痕（非品质蓝图）按「类」加入待制作
   · 只做表层叠加：沿用既有 lb_bp_follow 存储与 lbTodoRender 渲染，**不改待制作结构**
   · inst 前缀 `wk|` 标记「类级（无实例）」条目，与品质蓝图实例条目互不干扰 */
// v5913：关注条目归属服——当前 tab 是服务器就用它；「玩家携带」（player）时按物品所在服回推
function lbCraftWatchSrv(){
  var ab = ''; try{ ab = String(LB.tab || ''); }catch(e0){ ab = ''; }
  var ok = false;
  try{ ok = (LB.SERVERS || []).some(function(s){ return String(s.abbr) === ab; }); }catch(e1){ ok = false; }
  if(ok) return ab;
  try{
    var cls = String(LB_WI.cur || '').replace(/_C_\d+$/, '');
    var ibs = (LB._cache && LB._cache.data && LB._cache.data.itemsByServer) || {};
    var ks = Object.keys(ibs);
    for(var i = 0; i < ks.length; i++){
      var byCid = (ibs[ks[i]] && ibs[ks[i]].byCid) || {};
      var cids = Object.keys(byCid);
      for(var j = 0; j < cids.length; j++){
        var arr = byCid[cids[j]] || [];
        for(var k = 0; k < arr.length; k++){
          var cc = String((arr[k] && arr[k]['class']) || '').replace(/_C_\d+$/, '');
          if(cc === cls) return ks[i];
        }
      }
    }
  }catch(e2){}
  try{ return String(((LB.SERVERS || [])[0] || {}).abbr || ''); }catch(e3){}
  return '';
}
var LB_WK_WATCH_PREFIX = 'wk|';
function lbCraftWatchInst(cls){ return LB_WK_WATCH_PREFIX + String(cls || ''); }
function lbCraftWatchFind(cls, sv){
  var k = '';
  try{ k = lbBpKey(sv, String(cls || ''), lbCraftWatchInst(cls)); }catch(e){ return -1; }
  var l = [];
  try{ l = lbBpFollowLoad() || []; }catch(e2){ return -1; }
  for(var i = 0; i < l.length; i++){
    try{ if(lbBpKey(l[i].sv, l[i].base, l[i].inst) === k) return i; }catch(e3){}
  }
  return -1;
}
function lbCraftWatchOn(cls, sv){ return lbCraftWatchFind(cls, sv) >= 0; }
function lbCraftWatchToggle(){
  var cls = ''; try{ cls = String(LB_WI.cur || ''); }catch(e){ cls = ''; }
  if(!cls) return false;
  var sv = lbCraftWatchSrv();
  var zh = ''; try{ zh = lbItemZh(cls) || ''; }catch(e3){ zh = ''; }
  if(!zh) zh = cls;
  var i = lbCraftWatchFind(cls, sv);
  if(i >= 0){
    try{ (lbBpFollowLoad() || []).splice(i, 1); }catch(e4){}
    try{ lbToast('已取消关注'); }catch(e5){}
  } else {
    var kind = '';
    try{ kind = String((lbItemMeta(cls) || {}).kind || ''); }catch(e6){ kind = ''; }
    try{
      (lbBpFollowLoad() || []).push({ sv:sv, base:cls, inst:lbCraftWatchInst(cls), cls:cls, zh:zh,
        snap:{ 'class':cls, key:'', qidx:0, rating:0, stats:[], kind:kind, customName:'', craftingSkill:null },
        wk:1, ts:Date.now() });
    }catch(e7){}
    try{ lbToast('已加入待制作（制作关注）'); }catch(e8){}
  }
  try{ lbBpFollowSave(); }catch(e9){}
  try{ lbBpCnt(); }catch(e10){}
  if(LB._todoOpen) try{ lbTodoRender(); }catch(e11){}
  lbCraftWatchPaint();
  return false;
}
function lbCraftWatchPaint(){
  var b = null; try{ b = document.getElementById('lbWikiItemWatch'); }catch(e){ b = null; }
  if(!b) return;
  if(!LB_WI._craftHas){ b.style.display = 'none'; return; }
  var cls = ''; try{ cls = String(LB_WI.cur || ''); }catch(e2){ cls = ''; }
  var sv = lbCraftWatchSrv();
  var on = lbCraftWatchOn(cls, sv);
  b.style.display = '';
  b.innerHTML = ((typeof lbMdiSvg === 'function') ? lbMdiSvg(on ? 'mdi-eye-off-outline' : 'mdi-eye', 13) : '')
    + '<span style="margin-left:5px">' + (on ? '已关注' : '制作关注') + '</span>';
  b.setAttribute('title', on ? '取消关注（移出待制作）' : '制作关注（加入待制作）');
  b.style.color = on ? '#f59e0b' : '#c4b5fd';
  b.style.borderColor = on ? '#f59e0b88' : '#7c3aed66';
  b.style.background = on ? 'rgba(245,158,11,.14)' : '#7c3aed1f';
}

function lbWikiItemTab(i){
  // v5687：tab 可条件隐藏（制作/指南）⇒ 位置索引需映射回 LB_WI_TABS 原始索引
  var m = (LB_WI && LB_WI.tabMap) || null;
  LB_WI.tab = (m && m[i] != null) ? m[i] : i;
  LB_WI.showAll = false;
  lbWikiItemRender();
}
// v5687（用户口径「哪些物品不应该显示 制作 TAB / 指南」）：
//   · 制作：无材料且无工作台 ⇒ 无配方 ⇒ 不显示该 tab（原来会渲染一句「该物品无制作配方数据。」）
//   · 指南：无专属按键 且 只剩「用途：它是制作材料…」那一条废话 ⇒ 不显示
//     （资源类无配方时该文案还自相矛盾：写着「切到制作页可看配方」，而制作页本身是空的）
// v5817（用户口径「物品中 为啥只有 黏液枪 有指南」根治）：
//   根因：指南 Tab 判据只有 ark.keys（后端从 ARK Wiki Usage 段正则抽的键位），
//         而 45 个缓存物品里只有 5 个抽到 keys，其中 4 个还是 alt 误命中
//         （石头 / 黏土 / 硫磺 / 制式弩）⇒ 真武器没指南、材料反而长假指南。
//   修法：① 纯修饰键（ctrl/shift/alt）单独出现不算键位（必须有主键）；
//         ② 判据扩为「有效键位 或 ark.points（ARK Wiki Usage/Notes 使用要点）」。
var LB_ARK_MODS = { ctrl: 1, shift: 1, alt: 1 };
function lbArkKeysMain(keys){
  var arr = (Object.prototype.toString.call(keys) === '[object Array]') ? keys : [];
  var out = [];
  for (var i = 0; i < arr.length; i++){
    var k = String((arr[i] || {}).k || '').toLowerCase();
    if (!k || LB_ARK_MODS[k]) continue;
    out.push(arr[i]);
  }
  return out;
}
function lbWikiGuideHasContent(d){
  d = d || {};
  var ark = d.ark || {};
  if (lbArkKeysMain(ark.keys || []).length) return true;
  return !!((ark.points || []).length);
}

function lbWikiItemFetch(){
  var cls = LB_WI.cur;
  if (!cls) return;
  var u = LB_WIKI_ITEM_API + encodeURIComponent(cls);
  fetch(u, { cache: 'no-store' })
    .then(function (r) { return r.json(); })
    .then(function (j) {
      if (LB_WI.cur !== cls) return;
      LB_WI.p = j;
      if (j && j.status === 'ready') { LB_WI.data = j.data; LB_WI.err = null; }
      else if (j && j.status === 'error') { LB_WI.err = new Error((j && j.err) || '暂无详细资料'); }
      /* v5846（用户口径「未组装的泰克悬浮艇 一直卡初始化，找根因」）：
         后端对无资料物品返回 status='fetching' + done=0/total=1 ，
         但 data 里已明确 _fail=1 + err='该物品暂无资料' 。
         旧逻辑只认 status 的 ready/error ⇒ 无限轮询后永远停在「正在初始化」。这里直接把 _fail 当失败。 */
      else if (j && j.data && j.data._fail) { LB_WI.err = new Error((j.data && j.data.err) || '暂无详细资料'); }
      var _more = !!(j && (j.status === 'fetching' || j.status === 'idle') && !LB_WI.err && !LB_WI.data);
      /* v5846：轮询用尽仍未就绪 -> 超时错误态（可点重试），不再永久「正在初始化」 */
      if (_more && LB_WI.pollN >= 40) { LB_WI.err = new Error('抓取超时，请点重试'); _more = false; }
      lbWikiItemRender();
      if (_more) {
        LB_WI.pollN++;
        setTimeout(function () { if (LB_WI.cur === cls) lbWikiItemFetch(); }, 1500);
      }
    })
    .catch(function (e) {
      if (LB_WI.cur === cls) { LB_WI.err = e; lbWikiItemRender(); }
    });
}

function lbWikiItemRetry(){
  LB_WI.err = null; LB_WI.data = null; LB_WI.pollN = 0;
  lbWikiItemRender();
  lbWikiItemFetch();
}

/* v264：物品使用指南 —— 按已取到的类型标签 / 属性 / 效果推导，不做猜测 */
function lbWikiItemGuide(d, nm){
  d = d || {};
  var ty = (d.tags && d.tags[0]) ? String(d.tags[0]) : '';
  var at = {};
  (d.attrs || []).forEach(function(kv){ at[String(kv[0])] = kv[1]; });
  var has = function(k){ return Object.prototype.hasOwnProperty.call(at, k); };
  var num = function(v){ var n = parseFloat(String(v || '').replace(/[^0-9.\-]/g, '')); return isNaN(n) ? 0 : n; };

  var h = '', _gN = 0;
  var G = function (title) {
    _gN++;
    return (_gN > 1 ? '</div>' : '') + '<div class="tc-sec">'
      + (title ? ('<div class="tc-h">' + title + '</div>') : '');
  };
  var steps = [];

  if (/武器|工具|护甲|结构物/.test(ty)){
    steps.push(['取出', '在背包里拖到下方快捷栏（1-0），按对应数字键拿在手上；护甲可直接拖到装备栏穿戴。']);
  } else if (/消耗品/.test(ty)){
    steps.push(['食用', '拖到快捷栏后按对应数字键选中，再按 <b>E</b> 使用；部分消耗品可直接右键食用。']);
  } else if (/资源|材料/.test(ty)){
    steps.push(['用途', '它是制作材料，不需要装备使用。切到「制作」页可看它参与哪些配方。']);
  }

  if (has('Harvest Tool')){
    steps.push(['采集', '对准石头 / 树木 / 尸体等资源节点按<b>左键</b>采集，采集类型：<b>' + lbWiVal(at['Harvest Tool']) + '</b>。']);
  }
  if (has('Harvest Resource Multiplier') && num(at['Harvest Resource Multiplier']) > 1){
    steps.push(['采集加成', '资源采集倍率 <b>' + at['Harvest Resource Multiplier'] + 'x</b>，同样一次敲击能拿到更多资源。']);
  }
  if (has('Melee Damage') && num(at['Melee Damage']) > 0){
    steps.push(['近战', '按<b>左键</b>挥击，基础伤害 <b>' + at['Melee Damage'] + '</b>。']);
  }
  if (has('Hit Damage') && num(at['Hit Damage']) > 0){
    steps.push(['射击', '按<b>左键</b>开火，单发伤害 <b>' + at['Hit Damage'] + '</b>。']);
  }
  if (has('Ammo Per Clip') && num(at['Ammo Per Clip']) > 0){
    steps.push(['瞄准', '按<b>右键</b>进入瞄准（远程武器通用）。']);
    steps.push(['换弹', '弹匣容量 <b>' + at['Ammo Per Clip'] + '</b> 发，打空后按 <b>R</b> 装填'
      + (has('Reload Duration') ? ('，装填耗时 <b>' + at['Reload Duration'] + '</b> 秒') : '') + '。']);
    steps.push(['补给', '每发消耗 <b>' + (at['Ammo Per Shot'] || '1') + '</b> 发弹药，需在背包里备好对应子弹。']);
  }
  if (has('Infinite Ammo') && /是|Yes|yes/.test(String(at['Infinite Ammo']))){
    steps.push(['弹药', '<b>无限弹药</b>，无需准备子弹。']);
  }
  if (has('Equip Time') && num(at['Equip Time']) > 0){
    steps.push(['装备耗时', '拿出或切换需要 <b>' + at['Equip Time'] + '</b> 秒。']);
  }
  if (has('Durability') && num(at['Durability']) > 0){
    steps.push(['耐久', '耐久上限 <b>' + at['Durability'] + '</b>，用尽后需修理（修理台 / 修理工具）。']);
  }
  if (has('Armor') && num(at['Armor']) > 0){
    steps.push(['防护', '提供 <b>' + at['Armor'] + '</b> 点护甲，穿戴在对应装备槽生效。']);
  }
  if (has('Socket Count') && num(at['Socket Count']) > 0){
    steps.push(['插槽', '可镶嵌 <b>' + at['Socket Count'] + '</b> 个插槽道具。']);
  }
  if (/结构物/.test(ty)){
    steps.push(['放置', '拿到手上后对准地面按<b>左键</b>放置；建造模式下可旋转与吸附拼接。']);
  }
  if ((d.effects || []).length){
    steps.push(['效果', '使用后生效：' + d.effects.map(function(kv){ return kv[0] + ' <b>' + kv[1] + '</b>'; }).join('、') + '。']);
  }

  // v289（用户口径「通用的都不需要」）：指南页只保留该物品的**专属按键**。
  //   ① 通用键位表整体移除（原 6 条硬编码 / 「通用键位」标题 / 通用键位说明都不再输出）
  //   ② 「怎么用」是按 attrs 反推的通用模板，且会与专属按键**互相矛盾**
  //      （例：黏液枪 R 是「切换黏液类型」，模板却写「按 R 装填」）
  //      ⇒ 有专属按键时不再显示，只在该物品没有任何专属按键时兜底，避免整页空白
    // v283：与物种「技能一览」完全同构 —— 每个操作并排「键鼠 / Xbox」两侧键帽
    //   结构：tc-km > tc-km-g(键鼠) + tc-km-vs(/) + tc-km-g(Xbox)
    //   键帽统一走 tcKeyChipHtml() -> lbKeyChipHtml()（lbk 字体 + 内联多色 SVG）
    var _kc = function (k) {
      try {
        return (typeof tcKeyChipHtml === 'function')
          ? tcKeyChipHtml(k, 23)
          : '<span class="tc-km-note">' + k + '</span>';
      } catch (e) { return '<span class="tc-km-note">' + k + '</span>'; }
    };
    // v5640（用户口径「根治 —— 以后出现都要自动适配」）：操作名里的手势标记自动转图标。
    //   权威源 = `LB_KEYMAP_MODES`（与键位配置同一张表）⇒ 以后新增/改名操作方式，此处自动跟随，无需再改代码。
    //   支持写法：XX（按住）/（长按）/（双击）/（轻按）/（开始按压）/（释放按压）/（组合键）…；
    //   非手势括号（如「（装填黏液）」）原样保留，不会被误删。图标位置/尺寸/class 全部对齐键位配置 v5379（左侧 · 18px · .lb-km-mod）。
    var _modMap = (function () {
      var o = {};
      try {
        (typeof LB_KEYMAP_MODES !== 'undefined' && LB_KEYMAP_MODES ? LB_KEYMAP_MODES : []).forEach(function (m) {
          if (m && m.ic && m.n) o[m.n] = m;
        });
      } catch (e1) {}
      // 口语别名 → 表内中文名（复用项目 AI 参数归一表的叫法）
      var al = { '按住': '长按', '长按住': '长按', '持续按住': '长按', '连按两次': '双击',
                 '点按': '普通按压', '轻触': '轻按', '松手': '释放按压', '按下': '开始按压' };
      Object.keys(al).forEach(function (k) { if (o[al[k]] && !o[k]) o[k] = o[al[k]]; });
      if (!Object.keys(o).length) {   // 兜底（表未就绪时）
        o['长按'] = { n: '长按', ic: 'touch_tap_hold' };
        o['双击'] = { n: '双击', ic: 'touch_tap_double' };
        o['轻按'] = { n: '轻按', ic: 'generic_button_finger' };
      }
      return o;
    })();
    var _stripMod = function (s) {
      var t = String(s || ''), mods = [];
      t = t.replace(/[（(]\s*([^（）()]{1,8}?)\s*[)）]/g, function (all, inner) {
        var m = _modMap[inner];
        if (m) { mods.push(m); return ''; }   // 手势标记 ⇒ 抽出来做图标
        return all;                           // 普通括号内容 ⇒ 原样保留
      });
      return { name: t.replace(/\s+/g, ' ').trim(), mods: mods };
    };
    var _modIc = function (m) {
      try {
        if (m && m.ic && typeof lbKeyChipHtml === 'function') {
          return '<span class="lb-km-mod" title="' + m.n + '">' + lbKeyChipHtml(m.ic, 18) + '</span>';
        }
      } catch (e2) {}
      return (m && m.n) ? ('<span class="tc-km-note">' + m.n + '</span>') : '';
    };
    var _kchip = function (side, mods) {
      var arr = (Object.prototype.toString.call(side) === '[object Array]') ? side : (side ? [side] : []);
      if (!arr.length) return '<span class="tc-km-note">不适用</span>';
      var s = arr.map(_kc).join('<span class="tc-km-sep">+</span>');
      var pre = '';
      (mods || []).forEach(function (m) { pre += _modIc(m); });   // 左侧（对齐键位配置 v5379）
      return pre + s;
    };
    var _chip = function (kbm, pad, mods) {
      return '<span class="tc-km">'
        + '<span class="tc-km-g">' + _kchip(kbm, mods) + '</span>'
        + '<span class="tc-km-vs">/</span>'
        + '<span class="tc-km-g">' + _kchip(pad, mods) + '</span>'
        + '</span>';
    };
    // v288：专属按键 —— 键位由后端从 ARK Wiki Usage 段抽出（d.ark.keys）
    //   中文名：先查 LB_WI_WEAPON_ACT（该武器特有叫法）→ 回落 LB_KEYMAP_ACTIONS 同 kbm 条目
    var _ark = d.ark || {};
    // v5817：纯修饰键（alt 等）无效 —— 石头/黏土/硫磺/制式弩的 keys=[alt] 是误命中，不再当键位
    var _akKeys = (typeof lbArkKeysMain === 'function') ? lbArkKeysMain(_ark.keys || []) : (_ark.keys || []);
    // v5817：ARK Wiki Usage / Notes 段的使用要点（后端 ark.points，每条约 12-220 字符）
    var _akPts = (_ark.points && _ark.points.length) ? _ark.points.slice(0, 10) : [];
    var _actMap = (typeof LB_WI_WEAPON_ACT !== 'undefined' && LB_WI_WEAPON_ACT)
      ? (LB_WI_WEAPON_ACT[_ark.slug || ''] || null) : null;
    var _usedKbm = {};
    var _findAct = function (kbm) {
      var i;
      if (_actMap) {
        for (i = 0; i < _actMap.length; i++) { if (_actMap[i].kbm === kbm) return _actMap[i]; }
      }
      if (typeof LB_KEYMAP_ACTIONS !== 'undefined' && LB_KEYMAP_ACTIONS) {
        for (i = 0; i < LB_KEYMAP_ACTIONS.length; i++) {
          if (LB_KEYMAP_ACTIONS[i].kbm === kbm) return LB_KEYMAP_ACTIONS[i];
        }
      }
      return null;
    };
    if (_akKeys.length) {
      h += G();   // v5639（用户口径「专属按钮这4个字无需显示」）：不再输出「专属按键」标题
      h += '<table class="tc-tb"><thead><tr><th>操作</th><th>操作键</th></tr></thead><tbody>';
      _akKeys.forEach(function (kk) {
        var kb = kk.kbm || '';
        _usedKbm[kb] = 1;
        var lb = _findAct(kb);
        var nm2 = (lb && (lb.zh || lb.id)) ? (lb.zh || lb.id) : kk.k;
        // v5640：自动剥离「（按住）」等手势标记 → 图标；同时兼容数据层 hold:1
        var _pm = _stripMod(nm2);
        var _mods = _pm.mods.slice();
        if (!_mods.length && lb && lb.hold && _modMap['长按']) _mods.push(_modMap['长按']);
        if (_pm.name) nm2 = _pm.name;
        var pd2 = kk.pad || ((lb && typeof lb.pad === 'string') ? lb.pad : '');
        h += '<tr><th>' + nm2 + '</th><td>' + _chip(kb, pd2, _mods) + '</td></tr>';
      });
      h += '</tbody></table>';
      // v5816（用户口径「不是应该显示在右上角的问号里么」）：说明性文案改 .tc-note
      //   （CSS 隐藏 + tcSyncNotes 汇总到标题栏问号 tips，与 v5807 黄框同一机制）
      h += '<div class="tc-note">以上按键取自该物品的官方使用说明；游戏内改过按键时以游戏设置为准。</div>';
    }
    // v5820（用户口径「怎么用给的是无效信息，应该只显示键位或整理后的要点」）：
    //   删除 steps 推导出的通用操作表（取出 / 近战 / 弹药 之类与具体物品无关的废话），
    //   指南页只保留「官方键位表」+「AI 整理要点」。
    // v5821（用户口径「原先的英文的使用要点就不用显示了（多余）只用于整理时喂给AI即可」）：
    //   指南页不再渲染 ark.points 的**英文原文**（AI 整理素材仍由 lbWitDigest 直接取 ark.points，
    //   与此处渲染无关）；页面只显示官方键位表 + AI 整理出的中文要点。
    // v5819：指南常驻后不再输出「暂无专属按键说明」红字（改为由下方 AI 整理模块提示）
  if (_gN) h += '</div>';

  return h;
}

// v5815（用户口径「附件怎么没翻译。找根因 根治，而不是打补丁」）
//   根因：wiki_item 的 station 是 wiki 英文显示名；后端 _STMAP 只硬编码 4 条
//        （Player Inventory / Smithy / Tek Replicator / Campfire），其余原样英文；
//        前端两处输出（概览「可在…制作」/ 制作标签）直接拼 d.station，从不查汉化表
//        ⇒ 每新增一个工作台就要再补一条硬编码，永远补不完。
//   根治：工作台名一律走「权威表规范化反查」——facility_zh（人工主表）→ item_zh（结构物/别名补表）。
//        规范化 = 小写 + 去非字母数字 ⇒ "Mortar And Pestle" / "Mortar and Pestle" / 键 "MortarAndPestle" 三者归一。
//        表内无 ⇒ 保留原文（补表即生效，无需改代码/发版）；已是中文（后端已映射）⇒ 原样放行。
var LB_ST_ZH_IDX = { ref: null, n: 0, map: null };
function lbStationZhIndex(){
  try{
    var f = (typeof LB_FACILITY_ZH !== 'undefined' && LB_FACILITY_ZH) ? LB_FACILITY_ZH : null;
    var it = (typeof LB_ITEM_ZH !== 'undefined' && LB_ITEM_ZH) ? LB_ITEM_ZH : null;
    var n = (f ? Object.keys(f).length : 0) + (it ? Object.keys(it).length : 0);
    if (LB_ST_ZH_IDX.map && LB_ST_ZH_IDX.ref === f && LB_ST_ZH_IDX.n === n) return LB_ST_ZH_IDX.map;
    var m = {}, nz = function(s){ return String(s == null ? '' : s).toLowerCase().replace(/[^a-z0-9]/g, ''); };
    var put = function(k, v){ var x = nz(k); if (x && v && !m[x]) m[x] = String(v); };
    var k1, v1, k2, v2;
    if (f) for (k1 in f){ v1 = f[k1] || {}; put(k1, v1.zh); put(v1.en, v1.zh); }
    if (it) for (k2 in it){ v2 = it[k2] || {}; put(k2, v2.zh); put(v2.en, v2.zh); put(v2.alias, v2.zh); }
    LB_ST_ZH_IDX.map = m; LB_ST_ZH_IDX.ref = f; LB_ST_ZH_IDX.n = n;
    return m;
  }catch(e){ return {}; }
}
function lbStationZh(name){
  var s = String(name == null ? '' : name).trim();
  if (!s) return '';
  var k = s.toLowerCase().replace(/[^a-z0-9]/g, '');
  if (!k) return s;   // 无 ASCII 字母数字 ⇒ 已是中文（后端已翻译）→ 原样
  try{ var m = lbStationZhIndex(); if (m[k]) return m[k]; }catch(e){}
  return s;
}
// 表未就绪 ⇒ 加载完成后重渲一次（限次，避免失败时空转递归）
function lbWikiItemStationEnsure(){
  try{
    var needF = !(typeof LB_FACILITY_ZH !== 'undefined' && LB_FACILITY_ZH && Object.keys(LB_FACILITY_ZH).length);
    var needI = !(typeof LB_ITEM_ZH !== 'undefined' && LB_ITEM_ZH && Object.keys(LB_ITEM_ZH).length);
    if (!needF && !needI) return;
    if (LB_WI._stEnsuring) return;
    LB_WI._stTries = (LB_WI._stTries || 0) + 1;
    if (LB_WI._stTries > 2) return;
    LB_WI._stEnsuring = true;
    var ps = [];
    if (needF && typeof lbFacilityZhLoad === 'function') ps.push(lbFacilityZhLoad());
    if (needI && typeof lbItemZhLoad === 'function') ps.push(lbItemZhLoad());
    if (!ps.length){ LB_WI._stEnsuring = false; return; }
    Promise.all(ps).then(function(){
      LB_WI._stEnsuring = false;
      var ov = document.getElementById('lbWikiItemOverlay');
      if (ov && ov.classList.contains('show')) { try{ lbWikiItemRender(); }catch(e1){} }
    }).catch(function(){ LB_WI._stEnsuring = false; });
  }catch(e){}
}

// ===== v5819（用户口径「指南 TAB 常驻物品 TAB，里面直接复用 物种的技巧AI模块，逻辑照抄；
//        用于翻译以及标识 要点」）=====
//   · 外壳：复用 lbTipsAiBoxHtml（大肥鱼水印 / 状态 / 模型·token / ⚙配置 / 主按钮 / 结果区）
//   · 数据：物品 ark.points（ARK Wiki 英文要点）+ desc + attrs + 官方按键
//   · AI 只输出**中文**；方舟专名的英文小字标识由项目既有 lbEnMark 自动完成
//     （它只认 .tc-ai / .tc-auth-i / .tc-tipd-* 等 AI 容器 ⇒ 本模块结果必须放在 .tc-ai 里）
//   · 缓存：全服共享（后端 /api/item/tips），照抄技巧链路「一人跑过所有人秒开」
//   · 不自动跑（v5755 口径）：没有缓存只显示占位 + 按钮，由用户主动点
var LB_WIT_PV = 3;   // v5843：键位动作名必须具体（禁自指空话），旧结果视为旧版
var LB_WIT = { cls: '', st: 'idle', merged: null, busy: false, msg: '', needTok: false };
// v5822（用户口径「器械类 但ammo不用」）：只有这三类、且**官方没抓到键位**时，才让 AI 从资料里提取键位
/* v5841（用户口径「附件这种 不是应该渲染成键位列表么？」）：鞍/附件同样需要「动作 → 键」，
   原先只放 armor/attachment/weapon ⇒ saddle 被判 needKeys=false，prompt 不给 keys 结构，
   键位只能写成普通要点。 */
var LB_WIT_KEY_KINDS = { armor: 1, attachment: 1, weapon: 1, saddle: 1 };
function lbWitNeedKeys(cls){
  try {
    var m = (typeof lbItemMeta === 'function') ? (lbItemMeta(cls) || {}) : {};
    if (!LB_WIT_KEY_KINDS[String(m.kind || '')]) return false;
  } catch (e) { return false; }
  try {
    var d = (LB_WI.data && LB_WI.data.PARSED) || {};
    var ks = ((d.ark || {}).keys) || [];
    if (typeof lbArkKeysMain === 'function') return !lbArkKeysMain(ks).length;
    return !ks.length;
  } catch (e2) { return false; }
}

// v5824（用户口径「你不是说不猜测么？怎么会有这种不确定的」）：
//   动作名一旦含模糊/占位词，说明资料没写明 ⇒ 整条丢弃，绝不以「（如有）」占位
var LB_WIT_VAGUE_RE = /如有|可能|也许|或许|视情况|大概|可选|待定|猜测|推测|疑似|不确定|之类|等等/;
function lbWitVague(a){
  return LB_WIT_VAGUE_RE.test(String(a || ''));
}
function lbWitApi(){
  var b = (typeof LB_API === 'string' && LB_API) ? LB_API : 'https://data.whiterober.ccwu.cc';
  return String(b).replace(/\/+$/, '') + '/api/item/tips';
}
/* v5836（用户口径「指南如果无数据时暂不显示」）：
   有 AI 整理结果（键位/要点/分节）或官方指南步骤非空，才算「指南」有数据。 */
function lbWitGuideHasData(cls){
  cls = String(cls || '');
  try {
    var mg = LB_WIT.merged || null;
    if (mg && (((mg.keys || []).length) || ((mg.points || []).length) || ((mg.secs || []).length))) return true;
  } catch (e0) {}
  try {
    var d = (LB_WI.data && LB_WI.data.PARSED) || {};
    var nm = (typeof lbItemZh === 'function') ? (lbItemZh(cls) || '') : '';
    var html = lbWikiItemGuide(d, nm || cls);
    var txt = String(html || '').replace(/<[^>]*>/g, '').replace(/\s+/g, '');
    return txt.length > 0;
  } catch (e1) { return false; }
}

function lbWitPaint(){
  /* v5834：AI 外壳已移到概览底部 ⇒ 只刷新外壳容器，避免整页重绘把滚动位置打回顶部。
     v5836（用户口径「AI整理后要全量考虑回填」）：结果有无会改变「指南」TAB 显隐 ⇒ 状态一变整页重绘。 */
  var _has = false;
  try {
    var mg = LB_WIT.merged || null;
    _has = !!(mg && (((mg.keys || []).length) || ((mg.points || []).length) || ((mg.secs || []).length)));
  } catch (e0) { _has = false; }
  if (_has !== LB_WIT._shownHas){
    LB_WIT._shownHas = _has;
    try { lbWikiItemRender(); } catch (e1) {}
    return;
  }
  if (lbWitRefreshAiWrap()) return;
  try { lbWikiItemRender(); } catch (e) {}
}
function lbWitEnsure(cls){
  cls = String(cls || '');
  if (!cls) return;
  if (LB_WIT.cls === cls && LB_WIT.st !== 'idle') return;
  LB_WIT.cls = cls; LB_WIT.st = 'loading'; LB_WIT.merged = null; LB_WIT.msg = '';
  lbWitLoadZh();
}
function lbWitLoadZh(cb){
  var cls = LB_WIT.cls;
  return fetch(lbWitApi() + '?cls=' + encodeURIComponent(cls), { cache: 'no-store' })
    .then(function (r) { return r.json(); })
    .then(function (j) {
      if (LB_WIT.cls !== cls) return;
      LB_WIT.st = 'ready';
      if (j && j.ok && j.merged) LB_WIT.merged = j.merged;
      lbWitPaint();
      if (typeof cb === 'function') cb();
    })
    .catch(function () { LB_WIT.st = 'ready'; if (typeof cb === 'function') cb(); });
}
function lbWitPost(mg, force){
  try {
    fetch(lbWitApi(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cls: LB_WIT.cls, merged: mg, force: !!force })
    }).catch(function () {});
  } catch (e) {}
}
/* v5841（用户口径「附件这种 不是应该渲染成键位列表么？」）：
   AI（尤其旧缓存）常把「按 X 键可…」写成普通要点。这里把它识别出来并解析成 {a,k,p}，
   交给键位表渲染；解析不出的句子保持原样，绝不丢信息。 */
var LB_WIT_KEYMAP = {
  'ctrl': 'keyboard_ctrl_left', 'shift': 'keyboard_shift_left', 'space': 'keyboard_space',
  '空格': 'keyboard_space', 'tab': 'keyboard_tab',
  'r': 'keyboard_r', 'e': 'keyboard_e', 'c': 'keyboard_c', 'f': 'keyboard_f', 'g': 'keyboard_g',
  'q': 'keyboard_q', 'x': 'keyboard_x', 'z': 'keyboard_z', 'v': 'keyboard_v', 't': 'keyboard_t',
  '鼠标左键': 'mouse_left', '左键': 'mouse_left', '鼠标右键': 'mouse_right', '右键': 'mouse_right',
  '鼠标中键': 'mouse_middle', '中键': 'mouse_middle'
};
var LB_WIT_XBOX = {
  mouse_left: 'xbox_rt', mouse_right: 'xbox_lt', mouse_middle: 'xbox_stick_r_press',
  keyboard_r: 'xbox_button_x', keyboard_e: 'xbox_button_y', keyboard_f: 'xbox_button_y',
  keyboard_c: 'xbox_stick_r_press', keyboard_space: 'xbox_button_a',
  keyboard_ctrl_left: 'xbox_rb', keyboard_shift_left: 'xbox_stick_l_press',
  keyboard_tab: 'xbox_button_view', keyboard_q: 'xbox_lb',
  keyboard_x: '', keyboard_z: '', keyboard_v: '', keyboard_t: '', keyboard_g: ''
};
function lbWitParseKeySentence(txt){
  var s = String(txt || '').trim();
  if (!s || s.indexOf('键') < 0) return null;
  /* v5842：允许「按鼠标左键挥击」这类**不带「键」字**的写法（句子本身仍必须含「键」字，见上面的前置判断） */
  var m = /按(?:下)?\s*(鼠标左键|鼠标右键|鼠标中键|左键|右键|中键|Ctrl|Shift|Space|空格|Tab|[A-Za-z])\s*键?/.exec(s);
  if (!m) return null;
  var raw = String(m[1] || '');
  var k = LB_WIT_KEYMAP[raw.toLowerCase()] || LB_WIT_KEYMAP[raw] || '';
  if (!k) return null;
  var a = s.replace(m[0], '')
           .replace(/^[，,、\s]+/, '')
           .replace(/^(?:可|可以|即可|能够|用于|会)/, '')
           .replace(/[。．.；;]$/, '')
           .trim();
  if (!a || a.length < 2) return null;
  return { a: a, k: k, p: LB_WIT_XBOX[k] || '' };
}

// 指南页整理结果（v5834：AI 外壳已拆到 lbWitAiBoxInner，统一挂到概览底部）
function lbWitResultHtml(d, nm){
  d = d || {};
  var mg = LB_WIT.merged || null;
  // v5824（用户口径「你不是说不猜测么」）：后端缓存里可能残留旧的不确定动作名，渲染前再兜一层
  var akKeys = ((mg && mg.keys) ? mg.keys : []).filter(function (x) {
    return !(typeof lbWitVague === 'function' && lbWitVague(x && x.a));
  });
  var pts = (mg && mg.points) ? mg.points : [];
  var secs = (mg && mg.secs) ? mg.secs : [];
  /* v5841：把 points 里的「按 X 键…」并入键位表（历史缓存也能立刻变成键位列表） */
  try {
    var _kept = [];
    (pts || []).forEach(function (t) {
      var _tx = String(t === null || t === undefined ? '' : t).trim();
      if (!_tx) return;
      if (t && typeof t === 'object') { _kept.push(t); return; }
      var _kv = lbWitParseKeySentence(_tx);
      if (_kv && _kv.a && _kv.k) { akKeys.push(_kv); return; }
      _kept.push(t);
    });
    pts = _kept;
  } catch (eKP) {}
  var h = '';
  // v5822（用户口径「器械类 但ammo不用」）：官方没抓到键位时，AI 从资料里提取的「动作 → 键」按项目按键样式渲染
  if (akKeys.length){
    h += '<div class="tc-sec"><div class="tc-h">操作键<em>AI 提取</em></div>';
    h += '<table class="tc-tb"><thead><tr><th>操作</th><th>操作键</th></tr></thead><tbody>';
    // v5823（用户口径「AI 整理的操作键要键鼠/xbox」）：与官方键位表同款「键鼠 / Xbox」两枚 chip
    var _kw = function (key) {
      var kx = String(key || '');
      if (!kx) return '<span class="tc-km-note">不适用</span>';
      try {
        return (typeof tcKeyChipHtml === 'function') ? tcKeyChipHtml(kx, 20) : escapeHtml(kx);
      } catch (eK) { return escapeHtml(kx); }
    };
    akKeys.forEach(function (x) {
      var cell = '<span class="tc-km">'
        + '<span class="tc-km-g">' + _kw(x.k) + '</span>'
        + '<span class="tc-km-vs">/</span>'
        + '<span class="tc-km-g">' + _kw(x.p) + '</span>'
        + '</span>';
      h += '<tr><th>' + escapeHtml(String(x.a || '')) + '</th><td>' + cell + '</td></tr>';
    });
    h += '</tbody></table></div>';
  }
  if (pts.length || secs.length){
    /* v5868：要点与置顶文案块同一实现（.tc-intro） */
    h += '<div class="tc-sec"><div class="tc-h">要点<em>AI 整理</em></div>';
    h += '<div class="tc-intro tc-ai">';
    // v5825（用户口径「要点的行距太小了，应该和别的列表内容一致」）：补 .tc-pts 容器（gap:7px），条目间距对齐官方列表
    /* v5838：同物种侧 —— 对象 / "[object Object]" 一律跳过 */
    pts.forEach(function (t) {
      if (t && typeof t === 'object') return;
      var _tx = String(t === null || t === undefined ? '' : t).trim();
      if (!_tx || _tx === '[object Object]') return;
      h += '<p>' + escapeHtml(_tx) + '</p>';
    });
    secs.forEach(function (x) {
      var hh = escapeHtml(String(x.h || '')), tt = escapeHtml(String(x.t || ''));
      h += '<p>' + (hh ? ('<b>' + hh + '</b>') : '') + (tt ? ((hh ? '：' : '') + tt) : '') + '</p>';
    });
    h += '</div></div>';
  }
  return h;
}

/* v5834（用户口径「物品 wiki 指南里的 AI 模块全部移到概览最下面」）：
   AI 外壳独立出来 —— 物品概览底部用它，指南页只展示整理结果。 */
function lbWitAiBoxInner(){
  var mg = LB_WIT.merged || null;
  var hasRes = !!(mg && (((mg.keys || []).length) || ((mg.points || []).length) || ((mg.secs || []).length)));
  /* v5916（用户口径）：所有状态提示（整理中 / 错误 / 无结果）一律放进 AI 模块**内左侧**状态位，
     不再在模块外挂 .tc-hintb（原实现在框上方多一行，与用户要求不符） */
  var stTxt = LB_WIT.busy ? 'AI 整理中…' : (LB_WIT.msg || '');
  if (!stTxt) stTxt = hasRes ? '物品信息已整理' : '尚无 AI 整理结果';
  var out = '';
  out += lbTipsAiBoxHtml({
    state: escapeHtml(stTxt),
    btn: { fn: 'lbWitDigest(false)', txt: hasRes ? '重新整理' : '一键整理' },
    disabled: !!LB_WIT.busy
  });
  return out;
}
/* 由调用方用 SEC() 包一层 .tc-sec（物品面板的块闭合走 SEC 机制） */
/* v5836（用户口径「指南整理 改叫 AI整理；灰字：技巧键位补充梳理」）
   v5837（用户口径「AI整理小标题 以及右侧灰字 直接删掉吧」）：标题整行不再渲染 */
var LB_WIT_AI_H = '';
function lbWitAiBlockHtml(){
  return '<div id="lbWiOverviewAiWrap">'
    + LB_WIT_AI_H
    + lbWitAiBoxInner()
    + '</div>';
}
function lbWitRefreshAiWrap(){
  var w = document.getElementById('lbWiOverviewAiWrap');
  if (!w) return false;
  w.innerHTML = LB_WIT_AI_H + lbWitAiBoxInner();
  return true;
}
function lbWitDigest(force){
  if (LB_WIT.busy) return;
  // v5820（用户实测「AI 整理停不下来」根因）：原函数体用了未定义的 `nm`（它是 lbWikiItemRender 的
  //   局部变量）⇒ 点按钮抛 ReferenceError，且抛错时 busy 已被置 true ⇒ 永久卡在「AI 整理中…」、
  //   按钮永久 disabled、请求根本没发出。这里包一层 try/catch 保底复位 busy。
  try { return lbWitDigestRun(force); }
  catch (eX) {
    LB_WIT.busy = false;
    LB_WIT.msg = '整理失败：' + String((eX && eX.message) || eX);
    lbWitPaint();
  }
}
function lbWitDigestRun(force){
  var cfg = null; try { cfg = lbAiCfgGet(); } catch (e0) {}
  if (!cfg || !cfg.token){
    LB_WIT.needTok = true; LB_WIT.msg = '请先在「⚙ 配置」里填大肥鱼 token';
    lbWitPaint();
    try { if (typeof lbOpenConfigModal === 'function') lbOpenConfigModal(); } catch (e1) {}
    return;
  }
  var d = (LB_WI.data && LB_WI.data.PARSED) || {};
  var ark = d.ark || {};
  var kk = ark.keys || [], pp = ark.points || [];
  var desc = String(d.desc || '').trim();
  var attrs = (d.attrs || []).slice(0, 20);
  var needKeys = (typeof lbWitNeedKeys === 'function') ? lbWitNeedKeys(LB_WIT.cls) : false;
  if (!pp.length && !desc && !attrs.length){
    LB_WIT.msg = '该物品暂无可整理资料'; lbWitPaint(); return;
  }
  LB_WIT.busy = true; LB_WIT.msg = ''; lbWitPaint();

  var SYS = '你是《方舟：生存飞升》(ARK: Survival Ascended，下称 ASA) 的资深中文玩家兼攻略编辑。\n'
    + '任务：把一份物品资料整理成**中文使用指南**，供玩家速查（要点式，不写长文）。\n\n'
    + '硬性要求：\n'
    + '1) **全中文**：除 ASA / PvP / PvE / DPS 这类社区通用缩写外，正文不得残留英文单词；'
    + '物品名、结构/工作台名、生物名、状态与增益名、键位名、地名、数值单位一律译成方舟中文社区通行译法。\n'
    + '2) **要点化**：每条一句话，聚焦「怎么用 / 什么条件用 / 注意什么」，'
    + '保留全部数字（键位、距离、时长、倍率、等级）；原文的键位按中文键名写（如 鼠标左键 / R 键 / 空格）。\n'
    + '3) **不得编造**：只基于用户给的资料；资料没提到的机制不要补。资料是英文时按原意翻译，不擅自扩展。\n'
    + '   · **禁止不确定/占位表述**：任何字段都不许出现「如有 / 可能 / 也许 / 或许 / 视情况 / 大概 / 可选 / 待定 / 猜测 / 推测 / 疑似 / 之类 / 等等」'
    + '这类模糊词或括号占位；资料没明确写的内容**直接不写**，不要用「（如有）」凑一条。\n'
    + '4) 输出严格 JSON（不要代码块）：'
    + (needKeys
        ? ('{"keys":[{"a":"动作中文名","k":"键鼠键名","p":"Xbox键名"}],"points":["要点1"],"secs":[{"h":"小标题","t":"正文"}]}\n'
           + '   · keys（本次必做）：只写**该物品自身**的操作，按资料提取「动作 → 键鼠 + Xbox」。\n'
           + '   · 键鼠键名只能取：mouse_left / mouse_right / mouse_middle / keyboard_r / keyboard_e / keyboard_c / keyboard_f / keyboard_g / '
           + 'keyboard_q / keyboard_x / keyboard_z / keyboard_v / keyboard_t / keyboard_space / keyboard_ctrl_left / keyboard_shift_left / keyboard_tab。\n'
           + '   · Xbox 键名只能取：xbox_rt / xbox_lt / xbox_rb / xbox_lb / xbox_button_a / xbox_button_b / xbox_button_x / xbox_button_y / '
           + 'xbox_button_view / xbox_button_menu / xbox_stick_l_press / xbox_stick_r_press / xbox_dpad_up / xbox_dpad_down / xbox_dpad_left / xbox_dpad_right。\n'
           + '   · **手柄推断（必做）**：资料只写了键鼠时，按 ASA 默认手柄映射补 p —— 鼠标左键→xbox_rt、鼠标右键→xbox_lt、'
           + 'R→xbox_button_x、E/F→xbox_button_y、空格→xbox_button_a、Ctrl→xbox_rb、Shift→xbox_stick_l_press、Tab→xbox_button_view；'
           + '实在推不出就留空字符串。\n'
           + '   · **禁止写入全局通用键**：丢弃(G)、背包(I)、交互(E)、蹲下(C)、跳跃(空格)、地图(M) 这类全局操作不属于物品自身键位，一律不要写。\n'
           + '   · **动作名必须确定**：a 只能写资料里**明确写出**的操作（如「挥击采集」「放下塞子」「切换弹药类型」），'
           + '不得出现「如有 / 可能 / 视情况 / 可选」等不确定词，也不得写「（如有）」这类占位；'
           + '资料没明确就**整条不输出**（宁可少写，不许凑数）；完全没有物品自身操作则输出 []。\n')
        : ('{"keys":[{"a":"动作中文名","k":"键鼠键名","p":"Xbox键名"}],"points":["要点1"],"secs":[{"h":"小标题","t":"该节正文"}]}\n'
           + '   · keys：只写**该物品自身**的按键操作；资料里没有明确的物品自身按键就输出 []。\n'
           + '   · 键鼠键名只能取：mouse_left / mouse_right / mouse_middle / keyboard_r / keyboard_e / keyboard_c / keyboard_f / keyboard_g / '
           + 'keyboard_q / keyboard_x / keyboard_z / keyboard_v / keyboard_t / keyboard_space / keyboard_ctrl_left / keyboard_shift_left / keyboard_tab。\n'
           + '   · Xbox 键名只能取：xbox_rt / xbox_lt / xbox_rb / xbox_lb / xbox_button_a / xbox_button_b / xbox_button_x / xbox_button_y / '
           + 'xbox_button_view / xbox_button_menu / xbox_stick_l_press / xbox_stick_r_press / xbox_dpad_up / xbox_dpad_down / xbox_dpad_left / xbox_dpad_right。\n'
           + '   · 手柄推断：鼠标左键→xbox_rt、鼠标右键→xbox_lt、R→xbox_button_x、E/F→xbox_button_y、空格→xbox_button_a、'
           + 'Ctrl→xbox_rb、Shift→xbox_stick_l_press、Tab→xbox_button_view；推不出留空字符串。\n'))
    + '   · **按键类内容一律写进 keys（硬性）**：凡资料里出现「按 X 键做 Y」「X 键可…」「按 X 触发…」这类描述，'
    + '必须拆成一条 keys 记录（a = 做 Y 的动作名，k = 对应键位，p = Xbox），**points / secs 里不得再保留同一句**。\n'
    + '   · **键位动作名必须具体（硬性·全分支适用）**：keys 的 a 必须写出**具体动作或武器 / 设施名**'
    + '（如「发射等离子炮」「开启 / 关闭护盾」「变速」「切换弹药类型」），玩家照着能直接做出来；'
    + '**严禁自指空话**——「触发近战键对应的操作」「执行相关操作」「使用对应功能」「进行攻击」「按键操作」'
    + '这类等于没说的说法一律不得出现；资料只给了模糊描述时，**必须结合该物品自身的武器 / 功能补成具体动作名**，实在无法确定则整条不输出。\n'
    + '   points 取 3~10 条（最核心的操作要点）；secs 取 0~4 节（更细的技巧分组，可为空数组）。';

  // v5820：物品名从数据层取（不再依赖 render 的局部变量 nm）
  var _nm2 = '';
  try { _nm2 = (typeof lbItemZh === 'function') ? (lbItemZh(LB_WIT.cls) || '') : ''; } catch (eNm) {}
  if (!_nm2) _nm2 = String(LB_WIT.cls || '');
  var usr = '【物品】' + _nm2 + '（类名 ' + String(LB_WIT.cls || '') + '）\n'
    + (desc ? ('【官方描述】\n' + desc + '\n\n') : '')
    + (kk.length ? ('【官方按键 / 操作】\n' + kk.map(function (k) {
        return '- ' + String(k.k || '') + (k.en ? ('：' + String(k.en).slice(0, 120)) : '');
      }).join('\n') + '\n\n') : '')
    + (pp.length ? ('【官方使用要点（英文原文）】\n' + pp.map(function (x, i) {
        return (i + 1) + '. ' + String(x);
      }).join('\n') + '\n\n') : '')
    + (attrs.length ? ('【属性数值】\n' + attrs.map(function (kv) { return kv[0] + '=' + kv[1]; }).join('；') + '\n') : '');

  fetch(String(cfg.base || LB_AI_BASE).replace(/\/+$/, '') + '/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + cfg.token },
    body: JSON.stringify({
      model: lbAiNormModel(cfg.model),
      messages: [{ role: 'system', content: SYS }, { role: 'user', content: usr }],
      temperature: 0.3, max_tokens: 4000,
      thinking: { type: 'disabled' },
      response_format: { type: 'json_object' }
    })
  }).then(function (r) { return r.text().then(function (tx) { return { s: r.status, t: tx }; }); })
    .then(function (x) {
      LB_WIT.busy = false;
      if (x.s !== 200){
        LB_WIT.msg = '接口错误 ' + x.s + '：' + String(lbAiErrText(x.s) || '');
        lbWitPaint(); return;
      }
      var j = null; try { j = JSON.parse(x.t); } catch (eJ) {}
      var ch0 = (j && j.choices && j.choices[0]) ? j.choices[0] : null;
      var m0 = (ch0 && ch0.message) ? ch0.message : null;
      var content = (m0 && m0.content) ? String(m0.content) : '';
      var o = null;
      try { o = lbAiParseJson(content); } catch (eP) {}
      if (!o && m0 && m0.reasoning_content){ try { o = lbAiParseJson(String(m0.reasoning_content)); } catch (eR) {} }
      var keys2 = [], pts2 = [], secs2 = [];
      if (o && Array.isArray(o.keys)){
        o.keys.forEach(function (x){
          var a = String((x && (x.a || x.act || x.action)) || '').trim();
          var kz = String((x && (x.k || x.key)) || '').trim().toLowerCase().replace(/[^a-z0-9_]/g, '');
          // v5823（用户口径「操作键要键鼠/xbox」）：p = Xbox 手柄键名
          var pz = String((x && (x.p || x.pad || x.gp)) || '').trim().toLowerCase().replace(/[^a-z0-9_]/g, '');
          // v5824（用户口径「你不是说不猜测么」）：动作名含模糊/占位词 ⇒ 整条丢弃
          if (lbWitVague(a)) return;
          if (a && (kz || pz)) keys2.push({ a: a.slice(0, 40), k: kz, p: pz });
        });
      }
      if (o && Array.isArray(o.points)){
        o.points.forEach(function (t){ t = String(t == null ? '' : t).trim(); if (t) pts2.push(t); });
      }
      if (o && Array.isArray(o.secs)){
        o.secs.forEach(function (s){
          var hh = String((s && s.h) || '').trim(), tt = String((s && s.t) || '').trim();
          if (tt) secs2.push({ h: hh, t: tt });
        });
      }
      if (!keys2.length && !pts2.length && !secs2.length){
        LB_WIT.msg = '整理结果无法解析' + (content ? ('：' + String(content).replace(/\s+/g, ' ').slice(0, 60)) : '');
        lbWitPaint(); return;
      }
      LB_WIT.merged = { keys: keys2.slice(0, 12), points: pts2.slice(0, 16), secs: secs2.slice(0, 12), pv: LB_WIT_PV };
      LB_WIT.msg = '';
      lbWitPaint();
      lbWitPost(LB_WIT.merged, force);
    })
    .catch(function (e) {
      LB_WIT.busy = false;
      LB_WIT.msg = '网络错误：' + String((e && e.message) || e);
      lbWitPaint();
    });
}

/* v5847（用户口径「暂无详细资料 + 重试 不是应该走 无权威信息 的同构么」）：
   物品 wiki 抓取失败时的降级页（与物种侧 err 兜底同构）：
   统一提示文案 「无权威信息，建议AI整理」 + 保留 AI 整理模块 + 重试。
   注：AI 整理的素材来自 wikily 解析结果，无素材时点整理会提示「该物品暂无可整理资料」（不说谎）。 */
function lbWikiItemErrRender(nm){
  var tabs = lbWiEl('lbWikiItemTabs'), meta = lbWiEl('lbWikiItemMeta'), body = lbWiEl('lbWikiItemBody');
  if (tabs) tabs.innerHTML = '';
  if (meta){ meta.textContent = '无权威信息，建议AI整理'; meta.style.display = ''; }
  if (!body) return;
  var h = '';
  try { h += '<div class="tc-sec">' + lbWitAiBlockHtml() + '</div>'; } catch (e1) {}
  h += '<div class="lw-err" style="margin-top:12px">「' + escapeHtml(String(nm || '')) + '」的权威资料暂未取到'
    + '<div style="margin-top:8px"><button class="lw-retry" onclick="lbWikiItemRetry()">重试</button></div></div>';
  body.innerHTML = h;
  body.scrollTop = 0;
}

function lbWikiItemRender(){
  var ttl = lbWiEl('lbWikiItemTitle'), tabs = lbWiEl('lbWikiItemTabs'),
      meta = lbWiEl('lbWikiItemMeta'), body = lbWiEl('lbWikiItemBody');
  if (!ttl || !tabs || !meta || !body) return;
  var cls = LB_WI.cur || '';
  var nm = '';
  try { nm = (typeof lbItemZh === 'function' && lbItemZh(cls)) || ''; } catch (e) {}
  if (!nm) nm = cls;
  // v5682（用户口径「wiki 浮窗标题的图标用实际物种（记得反色）或物品图标」）
  try {
    var _ticU = (typeof lbItemIconUrl === 'function') ? (lbItemIconUrl(cls) || '') : '';
    if (_ticU) {
      var _ticF = '';
      try {
        var _fs = lbIconFilterStyleByName('', _ticU) || '';
        var _mf = /filter:([^";]+)/.exec(_fs);
        if (_mf) _ticF = 'filter:' + _mf[1] + ';';
      } catch (eTF) {}
      // v5687（用户口径「生肉 · 后面应该叫 Wiki，对齐物种」）：与物种浮窗（📖 xx · Wiki）同一写法
      ttl.innerHTML = '<img src="' + _ticU + '" style="' + _ticF + 'width:20px;height:20px;object-fit:contain;vertical-align:-4px;margin-right:6px" onerror="this.style.display=\'none\'">' + nm + ' · Wiki';
    } else {
      ttl.textContent = '📖 ' + nm + ' · Wiki';
    }
  } catch (eTI) {
    ttl.textContent = '📖 ' + nm + ' · Wiki';
  }

  var _ids = { title: 'lbWikiItemTitle', tabs: 'lbWikiItemTabs', meta: 'lbWikiItemMeta', body: 'lbWikiItemBody' };
  if (!LB_WI.data && !LB_WI.err){
    lbWikiPanelLoading(_ids, null, '');
    try { lbCraftWatchPaint(); } catch (_eP0) {}
    return;
  }
  if (LB_WI.err){
    /* v5847（用户口径「不是应该走 无权威信息 的同构么」）：
       不再只给「错误 + 重试」，改与物种侧一致的降级页（提示文案 + AI 整理模块 + 重试）。 */
    try { lbWitEnsure(cls); } catch (eWE0) {}
    lbWikiItemErrRender(nm);
    try { lbCraftWatchPaint(); } catch (_eP1) {}
    return;
  }

  var d = (LB_WI.data && LB_WI.data.PARSED) || {};
  // v5913（用户口径）：服务器 ini 自定义配方优先（ConfigOverrideItemCraftingCosts 整体覆盖官方原配方）
  var _svCur = (typeof lbCraftWatchSrv === 'function') ? lbCraftWatchSrv() : '';
  var _iniCost = null; try { _iniCost = (typeof lbIniCostOf === 'function') ? lbIniCostOf(cls, _svCur) : null; } catch (_eIC0) { _iniCost = null; }
  if (!LB_INI_COST && !LB_WI._iniTried && typeof lbIniCostEnsure === 'function') {
    LB_WI._iniTried = 1;
    lbIniCostEnsure(function () { try { if (LB_WI.cur === cls) lbWikiItemRender(); } catch (_eRI0) {} });
  }
  var _wkMats = !!((d.mats && d.mats.length) || (d.station && d.station.length));
  LB_WI._craftHas = !!(_iniCost && _iniCost.costs && _iniCost.costs.length) || _wkMats;
  // v5687：条件隐藏「制作」（无配方）与「指南」（无实质内容）；v5913：ini 有自定义配方也算「有配方」
  var _noMake = !LB_WI._craftHas;
  var _noGuide = (typeof lbWikiGuideHasContent === 'function') ? !lbWikiGuideHasContent(d) : false;
  /* v5836（用户口径「指南如果无数据时暂不显示」）：AI 整理结果 + 官方指南步骤都为空 -> 隐藏该 TAB */
  var _guideHas = (typeof lbWitGuideHasData === 'function') ? lbWitGuideHasData(cls) : true;
  var _tabsShow = [], _tabMap = [];
  LB_WI_TABS.forEach(function (t, i) {
    if (i === 1 && _noMake) return;
    if (i === 3 && !_guideHas) return;   // v5836
    _tabsShow.push(t); _tabMap.push(i);
  });
  LB_WI.tabMap = _tabMap;
  var _curPos = _tabMap.indexOf(LB_WI.tab); if (_curPos < 0) _curPos = 0;
  lbWikiPanelTabs(_ids, _tabsShow, _curPos, 'lbWikiItemTab');
  var _mk = [];
  if (d.tags && d.tags[0]) _mk.push(d.tags[0]);
  if (d.kick) _mk.push(d.kick);
  meta.textContent = (d.zh || nm) + (_mk.length ? (' · ' + _mk.join(' · ')) : '');

  // v277：模块统一包进 .tc-sec（与物种面板同结构），自动闭合避免漏
  var h = '', _secN = 0;
  var SEC = function (title) {
    _secN++;
    return (_secN > 1 ? '</div>' : '') + '<div class="tc-sec">'
      + (title ? ('<div class="tc-h">' + title + '</div>') : '');
  };
  if (LB_WI.tab === 0){
    // v5834：进概览即拉共享 AI 整理缓存（只读；没有就显示按钮，不自动跑）
    if (typeof lbWitEnsure === 'function') lbWitEnsure(cls);
    // ① 官方描述
    if (d.desc) h += SEC() + '<div class="lw-quote">' + d.desc + '</div>';
    // ② 分类标签
    if (d.tags && d.tags.length){
      h += SEC() + '<div class="lw-tags">';
      d.tags.forEach(function (t, i) { h += '<span class="lw-tag' + (i === 0 ? ' k' : '') + '">' + t + '</span>'; });
      h += '</div>';
    }
    // ③ 一句话小结（用已取到的结构化字段拼，非猜测）
    var _ty = (d.tags && d.tags[0]) ? d.tags[0] : '';
    var _lv = '';
    var _m2 = String(d.kick || '').match(/([0-9]+)\s*级/);
    if (_m2) _lv = _m2[1] + ' 级';
    var _sm = [];
    _sm.push('「' + nm + '」' + (_ty ? ('是方舟中的<b>' + _ty + '</b>') : '是方舟物品'));
    if (_lv) _sm.push('<b>' + _lv + '</b>解锁');
    if (d.station && d.station.length) _sm.push('可在<b>' + d.station.map(lbStationZh).join('、') + '</b>制作');
    if (d.mats && d.mats.length) _sm.push('需要 <b>' + d.mats.length + '</b> 种材料');
    if (_sm.length > 1) h += SEC() + '<div class="tc-adv">' + _sm.join('，') + '。</div>';
    // ④ 快速信息
    if (d.quick && d.quick.length){
      h += SEC('基本信息');
      h += '<table class="tc-tb"><thead><tr><th>项目</th><th>数值</th></tr></thead><tbody>';
      // v5689：键原本直接输出原文（Spoil time 等英文键漏翻）⇒ 改走 lbWiZh，悬停显示英文原名
      d.quick.forEach(function (kv) {
        var _qz = lbWiZh(kv[0]);
        var _qt = (_qz !== kv[0]) ? (' title="' + String(kv[0]).replace(/"/g, '&quot;') + '"') : '';
        h += '<tr><th' + _qt + '>' + _qz + '</th><td>' + lbWiVal(kv[1]) + '</td></tr>';
      });
      h += '</tbody></table>';
    } else if (!d.desc){
      h += SEC() + '<div class="lw-err">该物品暂无概览数据。</div>';
    }
    // v5687（用户口径「把属性的内容直接拼接到概览里」）：属性数值 / 使用效果 并入概览，属性 tab 取消
    var _hasA = !!(d.attrs && d.attrs.length), _hasE = !!(d.effects && d.effects.length);
    if (_hasA){
      h += SEC('属性数值');
      h += '<table class="tc-tb"><thead><tr><th>字段</th><th>数值</th></tr></thead><tbody>';
      d.attrs.forEach(function (kv) {
        h += '<tr><th title="' + kv[0] + '">' + lbWiZh(kv[0]) + '</th><td>' + lbWiVal(kv[1]) + '</td></tr>';
      });
      h += '</tbody></table>';
    }
    if (_hasE){
      h += SEC('使用效果');
      h += '<table class="tc-tb"><thead><tr><th>效果</th><th>数值</th></tr></thead><tbody>';
      // v5689：同上，键走 lbWiZh，悬停显示英文原名
      d.effects.forEach(function (kv) {
        var _ez = lbWiZh(kv[0]);
        var _et = (_ez !== kv[0]) ? (' title="' + String(kv[0]).replace(/"/g, '&quot;') + '"') : '';
        h += '<tr><th' + _et + '>' + _ez + '</th><td>' + kv[1] + '</td></tr>';
      });
      h += '</tbody></table>';
    }
    // v5834（用户口径「物品 wiki 指南里的 AI 模块全部移到概览最下面」）
    h += SEC() + lbWitAiBlockHtml();
  } else if (LB_WI.tab === 1){
    if (d.station && d.station.length){
      // v5814（用户口径「附件无需显示」）：制作工作台小标题不再输出，工作台标签保留
      h += SEC();
      h += '<div class="lw-tags">';
      d.station.forEach(function (t) { h += '<span class="lw-tag">' + escapeHtml(lbStationZh(t)) + '</span>'; });
      h += '</div>';
    }
    if (_iniCost && _iniCost.costs && _iniCost.costs.length){
      // v5913（用户口径）：ini 自定义配方优先 —— 整体覆盖官方原配方（不合并）
      h += SEC('所需材料 · 服务器自定义配方');
      h += '<div class="tc-hv-grid">';
      _iniCost.costs.forEach(function (cc) {
        var c3 = String((cc && cc.item) || ''), q3 = Number(cc && cc.count) || 0, zn3 = c3, ic3 = '';
        try { var _m3 = lbItemMeta(c3); if (_m3 && _m3.zh) zn3 = _m3.zh; } catch (_eM3) {}
        try { var _u3 = lbItemIconUrl(c3); if (_u3) ic3 = '<img src="' + _u3 + '" style="width:20px;height:20px;object-fit:contain;margin-right:4px;flex-shrink:0" onerror="this.style.display=\'none\'">'; } catch (_eU3) {}
        h += '<div class="tc-hv"><div class="tc-hv-h">' + ic3 + '<span class="tc-hv-nm">' + escapeHtml(zn3) + '</span></div>'
           + '<div class="tc-hv-big">' + q3 + '<em>个</em></div></div>';
      });
      h += '</div>';
    } else if (d.mats && d.mats.length){
      h += SEC('所需材料');
      // v5813（用户口径「物品wiki 的制作 里的 所需材料 改成 卡片式的」）：表格 → 卡片网格（复用收割 Tab 的 .tc-hv 卡片）
      h += '<div class="tc-hv-grid">';
      d.mats.forEach(function (mm) {
        // v293：材料名 + 图标**一律走项目数据**（LB_ITEM_ZH + lbItemIconUrl）
        //   反查顺序：wikily slug（与项目 .en 规范化对齐，机器标识不受译名差异影响）
        //           -> wikily 中文名（旧接口无 slug 时兜底）
        //           -> 仍查不到才显示 wikily 原名（极少，说明项目表缺条目）
        var wname = mm[0], qty = mm[1], slug = mm[2] || '', c2 = '', ic = '';
        try { if (slug && typeof lbItemClsBySlug === 'function') c2 = lbItemClsBySlug(slug) || ''; } catch (e1) {}
        if (!c2) { try { if (typeof lbItemClsByZh === 'function') c2 = lbItemClsByZh(wname) || ''; } catch (e2) {} }
        var zname = wname;
        if (c2) {
          try { var _pz = lbItemZh(c2); if (_pz) zname = _pz; } catch (e3) {}
          try {
            var u = lbItemIconUrl(c2);
            if (u) ic = '<img src="' + u + '" style="width:20px;height:20px;object-fit:contain;margin-right:4px;flex-shrink:0" onerror="this.style.display=\'none\'">';
          } catch (e4) {}
        }
        // 卡片：图标 + 材料名 一行，数量大字（带「个」后缀）一行
        h += '<div class="tc-hv"><div class="tc-hv-h">' + ic + '<span class="tc-hv-nm">' + zname + '</span></div>'
           + '<div class="tc-hv-big">' + qty + '<em>个</em></div></div>';
      });
      h += '</div>';
    } else {
      h += SEC() + '<div class="lw-err">该物品无制作配方数据。</div>';
    }
    // v293（用户口径「蓝图品质材料表 不显示，没用」）：该表整块移除，不再输出
  } else if (LB_WI.tab === 2){
    // v301（用户口径）：获取 = 中文战利品来源。
    //   箱子名/图标一律走项目既有 lbCfgCrateName() / lbCfgCrateIcon()
    //   （二者优先查 facility_zh.json，补汉化即生效，代码里不再硬编译名）
    var _hasL = false;
    // v303（用户口径）：lootSum 那条提示块无用 -> 不再渲染（数据仍用于底部「共 N 条」计数）
    // v5626（用户口径「附件行没有必要」）：lootKind 标签行（任务 / 空投 / 洞穴 统计）不再渲染
    // v5641：首次进入「获取」或数据未就绪 ⇒ 异步拉全部服的 Game.ini 覆盖表，完成后重渲一次
    if (!LB_INI_OVR && typeof lbIniLoadOvr === 'function') {
      lbIniLoadOvr().then(function () {
        try { if (LB_WI && LB_WI.tab === 2) lbWikiItemRender(); } catch (e4) {}
      });
    }
    var _lr = d.lootRows || [];
    // v5649（用户口径）：Mod 地图（本服没有也不会有的图）相关来源**整行不显示**
    var _lrK = _lr.filter(function (r) { return (typeof lbWiKeepCrateRow === 'function') ? lbWiKeepCrateRow(r) : true; });
    // v5652（用户口径）：wikily **未收录**、但本服 Game.ini 的 ConfigOverrideSupplyCrateItems 里有该物品的箱子 ⇒ 也补出来
    //   · 去重口径：只要 wikily 原始行里出现过该箱子（无论其行是否被 Mod 图规则隐藏）就不再补，避免重复
    //   · 概率：能按权重逆推就用逆推值；结构复杂算不出则显示「—」
    var _iniOnly = [];
    try {
      if (LB_INI_OVR && typeof lbIniCrateHas === 'function'){
        var _ik2 = [lbIniNormCls(LB_WI.cur || '')];
        var _tz2 = (LB_ITEM_ZH || {})[LB_WI.cur || ''] || {};
        if (_tz2.en) _ik2.push(lbIniNormCls(_tz2.en));
        if (_tz2.icon) _ik2.push(lbIniNormCls(_tz2.icon));
        var _wiSeen = {};
        _lr.forEach(function (rr) { if (rr && rr.crate) _wiSeen[lbIniNormCls(rr.crate)] = 1; });
        Object.keys(LB_INI_OVR).forEach(function (cr) {
          if (_wiSeen[lbIniNormCls(cr)]) return;
          var rec = LB_INI_OVR[cr];
          if (!lbIniCrateHas(rec, _ik2)) return;
          var pv = null;
          try { pv = lbIniCrateChance(rec, _ik2); } catch (e01) {}
          // v5669：把 ini 里能拿到的信息一起带出（权重 / 数量范围 / 品质倍率原始值）
          var _st = null;
          try { _st = lbIniCrateStat(rec, _ik2); } catch (eSt) { _st = null; }
          // v5670（用户口径）：权重/数量 → 概率列；品质倍率 → 副标题（分两段存，渲染时各归其位）
          var _stChance = '', _stQual = '';
          if (_st) {
            var _sp = ['权重 ' + _st.w + '/' + _st.T];
            if (_st.nMin != null && _st.nMax != null) _sp.push('数量 ' + _st.nMin + '~' + _st.nMax);
            _stChance = _sp.join(' · ');
            if (_st.qMin != null && _st.qMax != null) _stQual = '品质倍率 ' + _st.qMin + '~' + _st.qMax;
          }
          _iniOnly.push({ crate: cr, mapSlug: '', chance: null, q: '', qr: '', tags: [], k: '', _iniOnly: 1, _pct: pv, _iniChance: _stChance, _iniQual: _stQual });
        });
      }
    } catch (e00) {}
    if (_lrK.length || _iniOnly.length){
      // v5655（用户口径「Legendary 为啥没翻译」根治）：难度/档位词补齐**英文键**，值统一改多别名数组，
      //   与 _ENV 同一去重机制 —— 箱名已含该词（如「星耀空投（传说）」）则副标题不再重复
      var _DIFF = {
        '阿尔法': ['精英'], '贝塔': ['中等'], '伽马': ['简单'],
        'Alpha': ['精英'], 'Beta': ['中等'], 'Gamma': ['简单'],
        'Easy': ['简单'], 'Medium': ['中等'], 'Hard': ['困难'], 'Legendary': ['传说'],
        // v5656：中文难度/档位同样入表（值同自身），使「星耀空投（困难）」这类箱名的难度 tag 也被去重
        '精英': ['精英'], '中等': ['中等'], '简单': ['简单'], '困难': ['困难'], '传说': ['传说'], '原始': ['原始'],
        '普通': ['普通'], '优秀': ['优秀'], '精良': ['精良'], '史诗': ['史诗']
      };
      // v5625（用户口径「BOSS 难度不要着色，太乱」）：难度词保持纯文本，不做着色
      // v5636（用户口径）：Double 只是箱子类名后缀，wikily 全站无任何说明文字、概率也未体现差异
      //   ⇒ 不再映射为「双倍掉落」（显示无意义）。环境词只保留地表类。
      // v5651（用户口径）：环境 tag 支持**多别名去重** —— 名称已含任一别名即不重复显示，否则显示中文
      //   实测 wikily tag `Scorched Earth` = 环境标签（焦土/沙漠生态），箱名已由类名拼成「星耀沙漠补给箱」
      var _ENV = { 'Aberrant Surface': ['畸变地表'], 'Scorched Earth': ['焦土', '沙漠'] };
      // v5632（用户口径）：三种精选徽章只保留「最好品质」→ 改叫「最佳品质」；最高概率 / 最低等级不再显示。
      //   兼容三种来源写法（后端 kw 中文化「最好品质」/ 已改名「最佳品质」/ wikily 原文「Best quality」）。
      var _PK_KEEP = { '最好品质': '最佳品质', '最佳品质': '最佳品质', 'Best quality': '最佳品质' };
      // v5687（用户口径「『战利品来源』这几个字无需显示」）：标题去掉，内容仍包在 .tc-sec 里保持间距
      h += SEC();
      // v5638（用户口径「恢复原 7 行逻辑」）：撤销分段排序，全部按概率降序单一排列（数据有几条显示几条）。
      // v5652：ini 独有行按逆推概率参与排序（算不出的排最后）
      var _wiP = function (r) {
        if (r && r._pct != null) return r._pct;
        var c = (r && r.chance != null) ? parseFloat(r.chance) : NaN;
        return isFinite(c) ? c : -1;
      };
      // v5669（用户口径「补出行置顶」）：本服补出的行（官方未收录）一律排最前，避免沉在列表末尾看不到
      var _lrS = _lrK.concat(_iniOnly).sort(function (a, b) {
        var _ai = a._iniOnly ? 1 : 0, _bi = b._iniOnly ? 1 : 0;
        if (_ai !== _bi) return _bi - _ai;
        return _wiP(b) - _wiP(a);
      });
      // v5630（用户口径「位置信息明显不对，没有权威数据就不显示」）：去掉「位置」列。
      //   根因：后端 `ark-ils-pick-map` 只存在于精选(pick)行，普通行无 map；且 maptxt 硬截 40 字符
      //   ⇒ 渲染出「畸变 +5 地图」这类半截文本，不可信。数据仍保留在 r.map（后端未删），仅不渲染。
      // v5673（用户口径「只显示概率前 4；品质前 4 也要；其他隐藏；不含本服改动」）：
      //   · 概率前 4 = 已按概率降序的 wikily 行前 4
      //   · 品质前 4 = 按项目权威档位 lbWiQualIdx（原始0…传说5）降序前 4
      //   · 两集合合并去重；本服改动行（_iniOnly）全保留，不受限制
      var _wiRows = _lrS.filter(function (x) { return !x._iniOnly; });
      var _keepKey = {};
      _wiRows.slice(0, 4).forEach(function (x) { _keepKey[x.crate] = 1; });
      _wiRows.slice().sort(function (a, b) {
        var _ia = (typeof lbWiQualIdx === 'function') ? lbWiQualIdx(a.q) : -1;
        var _ib = (typeof lbWiQualIdx === 'function') ? lbWiQualIdx(b.q) : -1;
        return _ib - _ia;
      }).slice(0, 4).forEach(function (x) { _keepKey[x.crate] = 1; });
      var _lrShow = _lrS.filter(function (x) { return x._iniOnly || _keepKey[x.crate]; });
      // v5674（用户口径「不是隐藏，是折叠，可以展开」）：
      //   默认只列 概率前4 ∪ 品质前4 ∪ 本服改动；其余折叠，底部「展开全部（剩 N 条）」可点开
      var _hidN = _lrS.length - _lrShow.length;
      var _lrDraw = (LB_WI.showAll && _hidN > 0) ? _lrS : _lrShow;
      h += '<table class="tc-tb"><thead><tr><th>来源</th><th>概率</th></tr></thead><tbody>';
      _lrDraw.forEach(function (r) {
        // v5647（用户口径「创世补给箱却标失落地图标」根治）：名称与图标同源，都取权威 mapSlug
        var _lb = null;
        try { if (typeof lbWiCrateLabel === 'function') _lb = lbWiCrateLabel(r); } catch (e0x) {}
        var cname = '';
        if (_lb && _lb.zh) cname = _lb.zh;
        else {
          try { if (typeof lbCfgCrateName === 'function') cname = lbCfgCrateName(r.crate) || ''; } catch (e1) {}
          if (!cname) cname = r.name || r.crate || '';
        }
        // v5631（用户口径「来源不用显示图标」）：不再渲染箱子图标（名与徽章保留）
        // v5628（用户口径「（双倍掉落）+ · 双倍掉落 重复，只保留备注」）：
        //   **根治** —— 环境词（_ENV 映射项，如「畸变地表」「双倍掉落」）若已含于箱子名，副标题就不再重复；
        //   难度词（_DIFF：简单/中等/精英）不受影响（箱子名「堡垒·简单」与难度语义不同层级，需保留）。
        var tg = (r.tags || []).map(function (t) {
          if (t === 'Double') return '';   // v5636：Double 无官方定义、概率也未体现差异，完全不显示（否则会露出英文原文）
          // v5655：难度词与环境词统一走「别名数组」——箱名已含任一别名即不重复显示
          var _al = _DIFF[t] || _ENV[t] || null;
          var v = _al ? _al[0] : t;
          if (!v) return '';
          if (_al) {
            for (var _ei = 0; _ei < _al.length; _ei++) { if (cname.indexOf(_al[_ei]) >= 0) return ''; }
          }
          return v;
        }).filter(function (t) { return t; });
        var sub = tg.slice();
        // v5677（用户口径「本服改动不用徽章样式，改成着色文字拼接到品质倍率之前」）
        var _ovrRec = null;
        try { _ovrRec = r._iniOnly ? null : ((LB_INI_OVR || {})[r.crate] || null); } catch (eO0) {}
        var _isOvr = !!(r._iniOnly || _ovrRec);
        if (_isOvr) {
          var _ovrTip = '本服改动：' + (_ovrRec ? (_ovrRec.servers || []).join(' / ') : '')
            + (r._iniOnly ? '（官方未收录，本服配置独有）' : '');
          sub.push('<span style="color:#fbbf24;font-weight:600" title="' + _ovrTip + '">本服改动</span>');
        }
        // v5669/v5670：本服补出行 —— 品质倍率留在副标题；权重/数量改到概率列（见 _chCell）
        if (r._iniOnly && r._iniQual) { try { sub.push(r._iniQual); } catch (eSub) {} }
        // v5664：提前算服务器缩写（档位色与地图图标共用）
        var _srvAbX = (_lb && _lb.srv) ? _lb.srv : ((typeof lbCrateSrvOf === 'function') ? lbCrateSrvOf(r) : '');
        // v5680（用户口径）：多地图信息不再放副标题，改到概率列第二行低可视显示（见 _chCell）
        // v5635（用户口径「1+ / 4.3-10.4x 意义不明，要让玩家看懂」）：加语义前缀。
        //   依据 wikily 原始结构：`ark-ils-lvl` = 箱子等级门槛（等级 1+ / 65+）；
        //   `ark-ils-q` 内 <small> = 物品评级范围，官方 tooltip「物品评级范围（卓越为10以上）」。
        // v5637（用户口径「箱子等级无需显示，标题已含」）：不再输出等级（如「畸变地表补给箱 Lv65」已含 65）
        // v303：品质名走项目物品品质口径并着色（色值唯一源 lbBpStageCol）
        // v5666（用户口径「金属锭这种无品质物品，为啥来源里也显示了品质」）：
        //   `r.q` 是**该箱子能开出的最高品质**（箱子属性），wikily 对每行都会给，与物品自身有无品质无关。
        //   金属锭(resource)/熟肉(consumable) 概念上无品质 ⇒ 显示「优秀」会让玩家以为能刷出优秀金属锭。
        //   判据（用户选定，只按此一条）：物品页的**品质倍率表** `PARSED.quality` rows/cols 均空 ⇒ 无品质体系。
        var _noQual = false;
        try {
          var _qq = (d.quality || {});   // v5667：d 本身即 PARSED（`var d = LB_WI.data.PARSED`），此处不能多套一层
          _noQual = !(((_qq.rows || []).length) || ((_qq.cols || []).length));
        } catch (eQ1) { _noQual = false; }
        if (r.q && !_noQual) {
          var _qrN = String(r.qr || '').replace(/x\s*$/i, '').replace(/-/g, '~').trim();
          sub.push(lbWiQualHtml(r.q) + (_qrN ? (' · 评分 ' + _qrN) : ''));
        }
        // v5664（用户口径「档位要与公共设施地图图例的对照一致」）：
        //   档位色**复用**唯一源 lbQualColor() + LB_QUAL_TBL / LB_FAC_DIFF_C（不另建表、不复制规则）
        //   · 补给箱/洞穴箱按等级 → lXX 键（各服主表不同：孤岛/焦土/畸变三套）
        //   · 空投/前哨按难度词 → easy/medium/hard/legendary
        try {
          var _gk = /Cave/i.test(r.crate) ? 'cavecrate' : ((/Horde|OSD|SupplyDrop/i.test(r.crate)) ? 'osd' : 'beacon');
          var _gkey = '';
          var _lvN = parseInt(String(r.lvl || ''), 10);
          // v5668：QualityTier 体系（洞窟补给箱 Tier1/2/3）走 t1/t2/t3 键（图例：t1蓝 / t2黄 / t3红）
          //   优先于等级数字：这类箱子的 lvl 常为 0/空，只有 Tier 有意义
          var _tm = /QualityTier0*(\d+)/i.exec(r.crate);
          if (_tm) _gkey = 't' + _tm[1];
          else if (isFinite(_lvN) && _lvN > 1) _gkey = 'l' + ((_lvN < 10) ? ('0' + _lvN) : String(_lvN));
          else if (/Legendary/i.test(r.crate)) _gkey = 'legendary';
          else if (/Hard/i.test(r.crate)) _gkey = 'hard';
          else if (/Medium/i.test(r.crate)) _gkey = 'medium';
          else if (/Easy/i.test(r.crate)) _gkey = 'easy';
          // v5665：lbQualColor 只覆盖「等级表」，难度档（easy/medium/hard/legendary）在 LB_FAC_DIFF_C
          //   ⇒ 统一走 lbFacDiffInfoS（先等级表、再难度表），与公共设施图例的取色路径完全一致
          var _gcol = '', _gHex = '';
          if (_gkey) {
            try { var _gi = lbFacDiffInfoS(_gkey, _srvAbX, _gk); if (_gi && _gi[0]) _gcol = _gi[0]; } catch (eG2) {}
          }
          // v5682（用户口径「紫/蓝/白这些不显示，改成标题的等级部分着色」）：
          //   色名不再进副标题，改为把标题里的等级片段（Lv65 / 3 阶 / 末尾难度词）直接染成该档位色
          if (_gcol) _gHex = (typeof LB_COLOR_HEX !== 'undefined' && LB_COLOR_HEX[_gcol]) ? LB_COLOR_HEX[_gcol] : '';
        } catch (eG) {}
        // v5644（用户口径）：来源标题前加对应地图的 MDI 图标（地图取自类名，用 lbMdiSvg 内联渲染）
        var _mdiNm = '', _mdiHtml = '';
        try {
          // v5645：优先用后端给出的权威 mapSlug（wikily 行 href 的 ?map=），而非类名猜测
          // v5647：Mod 地图（本服未开服）用通用 mdi-map，**不再错标成某台服务器**；藏宝等非地图不显示图标
          var _srvAb = (_lb && _lb.srv) ? _lb.srv : ((typeof lbCrateSrvOf === 'function') ? lbCrateSrvOf(r) : '');
          // v5655：多地图箱子不标单一地图图标，统一通用 mdi-map
          if (_lb && _lb.multi > 1) _mdiNm = _lb.isMap ? 'mdi-map' : 'mdi-package-variant-closed';
          else if (_srvAb && typeof LB_SERVER_MDI !== 'undefined' && LB_SERVER_MDI[_srvAb]) _mdiNm = LB_SERVER_MDI[_srvAb];
          else if (_lb && _lb.known) _mdiNm = _lb.isMap ? 'mdi-map' : 'mdi-package-variant-closed';   // v5648：藏宝非地图 ⇒ 宝箱图标
        } catch (e5) {}
        if (_mdiNm && typeof lbMdiSvg === 'function') {
          try { _mdiHtml = '<span style="display:inline-block;vertical-align:-2px;margin-right:5px;opacity:.85">' + lbMdiSvg(_mdiNm, 13) + '</span>'; } catch (e6) {}
        }
        // v5641（用户口径）：命中本服 ini 覆盖 ⇒ 概率按权重逆推（每箱至少出 1 个），并标「本服改动」
        var _ovr = null, _pct = null;
        try {
          _ovr = (LB_INI_OVR || {})[r.crate] || null;
          if (_ovr) {
            var _keys = [lbIniNormCls(LB_WI.cur || '')];
            var _t = (LB_ITEM_ZH || {})[LB_WI.cur || ''] || {};
            if (_t.en) _keys.push(lbIniNormCls(_t.en));
            if (_t.icon) _keys.push(lbIniNormCls(_t.icon));
            _pct = lbIniCrateChance(_ovr, _keys);
          }
        } catch (e3) {}
        var _chTxt = (r.chance ? (r.chance + '%') : '—');
        if (_pct != null) _chTxt = (_pct >= 0.01 ? _pct.toFixed(2) : _pct.toFixed(3)) + '%';
        var _ovrTi = '本服改动：' + (_ovr ? (_ovr.servers || []).join(' / ') : '');
        if (r._iniOnly) _ovrTi += '（官方未收录，本服配置独有）';
        _ovrTi += (_pct == null ? (r._iniOnly ? '；结构复杂未换算' : '；数值未换算，显示官方值') : '；概率按本服权重逆推');
        // v5682：标题等级片段着色（Lv65 / 3 阶 / 末尾难度词），用档位色代替原来的色名文字
        var _cnameHtml = cname;
        try {
          if (_gHex) {
            var _cl = String(cname);
            var _reLv = /(Lv\s*\d+|\d+\s*阶|(?:简单|中等|困难|传说|精英))$/;
            if (_reLv.test(_cl)) {
              _cnameHtml = _cl.replace(_reLv, '<span style="color:' + _gHex + ';font-weight:700">$1</span>');
            }
          }
        } catch (eCN) {}
        // v5683（用户口径「类名里所有的信息都要在中英文翻译中体现出来」）：英文名放悬停提示
        var _enNm = '';
        try { if (typeof lbCfgCrateEn === 'function') _enNm = lbCfgCrateEn(r.crate) || ''; } catch (eEn) {}
        var _enTitle = _enNm ? (' title="' + _enNm.replace(/"/g, '&quot;') + '"') : '';
        var head = _mdiHtml + '<b' + _enTitle + '>' + _cnameHtml + '</b>'
          + (_PK_KEEP[r.k] ? (' <span class="lw-tag" style="margin-left:6px">' + _PK_KEEP[r.k] + '</span>') : '')
          + (sub.length ? ('<div style="font-size:11px;color:#8b93a7;margin-top:3px">' + sub.join(' · ') + '</div>') : '');
        // 概率列：本服行无概率 ⇒ 徽章占据原「—」位置；有概率 ⇒ 数值 + 徽章；末行小字 = 权重/数量
        // v5677：徽章改为副标题着色文字后，概率列恢复「有值显示数值、无值留空（本服行）」；权重/数量仍在下方小字
        var _chCell = (_chTxt === '—' && _isOvr) ? '' : _chTxt;
        // v5680/v5681（用户口径「横跨 n 张地图」→ 后改为「只显示地图名，不用横跨 N 张地图」）：
        //   多图箱在概率列第二行低可视列出**具体地图中文名**（取后端权威 offMaps → LB_WI_MAPS，不猜类名）
        if (_lb && _lb.multi > 1) {
          var _mapZh = [];
          try {
            (r.offMaps || []).forEach(function (s) {
              var _mm = lbWiMapOf(s);
              if (_mm && _mm.zh && _mapZh.indexOf(_mm.zh) < 0) _mapZh.push(_mm.zh);
            });
          } catch (eMap) {}
          if (_mapZh.length) {
            _chCell += '<div style="font-size:10px;color:#6b7280;margin-top:2px;line-height:1.3">' + _mapZh.join(' / ') + '</div>';
          }
        }
        if (r._iniChance) _chCell += '<div style="font-size:10px;color:#8b93a7;margin-top:2px;line-height:1.35">' + r._iniChance + '</div>';
        h += '<tr><th>' + head + '</th><td>' + _chCell + '</td></tr>';
      });
      h += '</tbody></table>';
      // v5674/v5676（用户口径「不是隐藏，是折叠，可以展开」）：
      //   默认只列 概率前4 ∪ 品质前4 ∪ 本服改动；其余折叠，底部「展开全部（剩 N 条）」可点开
      if (_hidN > 0) {
        h += '<div class="lw-more" onclick="LB_WI.showAll=!LB_WI.showAll;lbWikiItemRender()" style="margin-top:8px;text-align:center;font-size:12px;color:#a78bfa;cursor:pointer;user-select:none;padding:4px 0">'
          + (LB_WI.showAll ? ('收起（共 ' + _lrS.length + ' 条）') : ('展开全部（剩 ' + _hidN + ' 条）'))
          + '</div>';
      }
      // v5633（用户口径「这块提示没用」）：不再渲染「共 N 个箱子来源…」提示块（lootSum 仍由后端返回，仅不渲染）
      _hasL = true;
    } else if (_lr.length){
      // v5649：原本有来源、但全部落在 Mod 地图 ⇒ 给一句说明，而不是空表
      // v5687（用户口径）：标题去掉
      h += SEC();
      h += '<div class="lw-err">该物品的来源都在本服未开放的地图上，本服无可获得途径。</div>';
      _hasL = true;
    }
    // v5684（用户口径「各地图箱子数量语义有歧义」）：整块删除。
    //   根因：该块数字来自后端 lootMap（正则抓 wiki 页面「地图条」文本，**wiki 全量口径**，
    //   含 Mod 图与被剔除的 Double 变体行），与上方战利品表的 offMaps 口径不一致
    //   （实例：生肉页仙境/瓦尔盖罗显示 12，按战利品表实算只有 9；孤岛/核心岛显示 6 实算 3），
    //   且「箱子数量」被误读为箱子实体数，实际是「可开出该物品的箱种数」且多图重复计数。
    if (!_hasL){
      var lt = String(d.loot || '').trim();
      h += SEC() + (lt ? ('<div class="tc-adv">' + lt + '</div>')
                       : '<div class="lw-err">该物品暂无获取途径数据。</div>');
    }
  } else if (LB_WI.tab === 3) {
    // v280：指南前置（原为末尾 tab 6）
    // v5834（用户口径「AI 模块移到概览最下面」）：指南只留整理结果，AI 外壳已挂到概览底部；
    //   仍在这里补一次 lbWitEnsure（只读缓存，幂等），避免用户直接进指南页时没数据。
    if (typeof lbWitEnsure === 'function') lbWitEnsure(cls);
    var _gdHtml = lbWikiItemGuide(d, nm);
    var _grHtml = lbWitResultHtml(d, nm);
    h += _gdHtml;
    h += _grHtml;
    // v5835：无整理结果时补一句入口提示（与物种技巧页口径一致），避免指南页整页空白
    if (!_grHtml){
      h += '<div class="tc-sec"><div class="tc-hintb">尚无整理结果 · 请在「概览」页底部点「一键整理」</div></div>';
    }
  } else {
    // v296（用户口径）：模块之间要有间距 —— 改用与物种同构的 .tc-cmds / .tc-cmd 卡片结构
    //   原实现两个 .tc-adv 同级且 .tc-adv 无 margin ⇒ 边框直接贴死，0 间距
    //   复用 tcCmdBox()：代码行 + 一键复制（与物种生成指令同一实现）
    if (d.gfi){
      h += SEC('生成');   // v5739：与 tab 名一致（原「生成指令」）
      h += '<div class="tc-cmds">';
      // v5813（用户口径「生成的用法说明的展示方式要对齐物种的wiki」）：
      //   物种侧 = 命令卡 + 代码框 + 一行灰字「参数：…」（lbSpawnParamHint），无紫底大框；
      //   物品侧同样处理 → 只留一张命令卡 + 参数行；控制台说明改放 .tc-note（CSS 已隐藏，
      //   由 tcSyncNotes 汇总到标题栏问号 tips，与物种 wiki 同一机制）。
      h += '<div class="tc-cmd"><div class="tc-cmd-desc">给予物品（GFI · 管理员指令）</div>'
         + (typeof tcCmdBox === 'function'
              ? tcCmdBox(d.gfi, 'itemgfi')
              : ('<div class="tc-codeline"><code class="tc-code">' + tcEsc(d.gfi) + '</code></div>'))
         + '<div style="font-size:11.5px;color:#8b93a7;margin-top:5px;line-height:1.65">参数：末尾三个 = <code>数量 品质 是否蓝图</code>（示例 <b>1 0 0</b> = 1 个 · 原始品质 · 非蓝图）</div>'
         + '</div>';
      h += '</div>';
      // v5689（用户口径）：控制台键 = Tilde（键位表 keyboard_tilde），原写死 Tab 有误
      h += '<div class="tc-note">PC 上按 <code>~</code>（Tilde）打开管理员控制台，需管理员权限。</div>';
    } else {
      h += SEC() + '<div class="lw-err">该物品暂无生成指令。</div>';
    }
  }
  if (_secN) h += '</div>';
  body.innerHTML = h;
  // v5815：工作台名汉化 —— 权威表未就绪时加载完成后自动重渲一次
  lbWikiItemStationEnsure();
  try { lbCraftWatchPaint(); } catch (_eP2) {}   // v5913：「制作关注」按钮显隐/状态
  try { lbWikiItemLayoutFix(); } catch (_eLF2) {}   // v5915：隐藏紧邻 .tc-intro 的小标题（如「要点 · AI 整理」）
}

/* ===== v163：Wiki 面板公共骨架（物种 / 物品共用，禁止各写一套） ===== */
//   loading / error / tabs 三段统一在这里；body 渲染由各自面板负责
function lbWikiPanelLoading(ids, pg, metaText){
  var tabs = document.getElementById(ids.tabs), meta = document.getElementById(ids.meta),
      body = document.getElementById(ids.body);
  if (tabs) tabs.innerHTML = '';
  if (meta) meta.textContent = metaText || '';
  if (!body) return;
  body.innerHTML = '<div class="lw-load" style="flex-direction:column;gap:10px;width:100%">'
    + '<span class="lw-spin"></span>'
    + '<span class="lw-pgw" style="max-width:320px">'
    + (pg
        ? ('<span class="lw-pgl" id="lwPgLbl">正在初始化 ' + (pg.done || 0) + '/' + (pg.total || 6) + '</span>'
           + '<span class="lw-pgb"><i id="lwPgBar" style="width:' + Math.round(((pg.done || 0) / (pg.total || 6)) * 100) + '%"></i></span>')
        : '<span class="lw-pgl">正在初始化</span><span class="lw-pgb lw-pgb-indet"><i></i></span>')
    + '</span></div>';
}

function lbWikiPanelErr(ids, name, msg, retryFn, rawErr){
  var tabs = document.getElementById(ids.tabs), meta = document.getElementById(ids.meta),
      body = document.getElementById(ids.body);
  if (tabs) tabs.innerHTML = '';
  if (meta) meta.textContent = '';
  if (!body) return;
  var detail = rawErr ? ('（' + String(rawErr) + '）') : '';
  var h = '<div class="lw-err">「' + name + '」' + (msg || '暂无详细资料') + detail;
  if (retryFn){
    h += '<div style="margin-top:8px"><button class="lw-retry" onclick="' + retryFn + '">重试</button></div>';
  }
  h += '</div>';
  body.innerHTML = h;
}

function lbWikiPanelTabs(ids, tabs, cur, fnName){
  var el = document.getElementById(ids.tabs);
  if (!el) return;
  var h = '';
  (tabs || []).forEach(function(lb, i){
    h += '<span class="lw-tab' + (i === cur ? ' on' : '') + '" onclick="' + fnName + '(' + i + ')">' + lb + '</span>';
  });
  el.innerHTML = h;
}

/* ===== v5756（用户口径 2026-10-31）=====
   ① 「附件1、2 不显示」= 各 TAB 的 .tc-h 小标题行不显示；但**保留 ①-⑳ 分步标题**
      （驯服 ①建议 / ②速览 / 经验 ①击杀经验 … 这些带序号的仍有导航价值）
   ② 「附件3 放到置顶的文案块下方」= .tc-top（服务器 6× / 野生 1.25× 倍率徽章）
      从文案块(.tc-intro)**上方**挪到**下方**
   实现方式：MutationObserver 监听 #lbWikiBody，覆盖所有 tab 的同步/异步重绘，
   不需要在每个 render 函数里重复调用（原各 render 直接 return，改末尾挂钩易漏）。 */
var LB_WIKI_LF_MO = null, LB_WIKI_LF_T = null;

function lbWikiLayoutFix(){
  var body = document.getElementById('lbWikiBody');
  if (!body) return;
  /* v6029（闪烁次因）：本函数自己会移动节点（② insertBefore）与替换文本（③④⑤ lbEnMark replaceChild），
     这些改动会被 lbWikiLayoutWatch 自己的 observer 看到 ⇒ 60ms 后再跑一次，形成自我触发；
     .tc-h 的 data-lf-hide 因此反复翻转 ⇒ 小标题 / 「鞍·附件」标题闪烁。
     修法：修改期间断开自身 observer，结束在 finally 里重连。 */
  var _lfMO = LB_WIKI_LF_MO;
  if (_lfMO) { try { _lfMO.disconnect(); } catch (eLFD) {} }
  try {
  // ① 隐藏无序号 .tc-h（保留 U+2460–U+2473 = ①…⑳）
  var hs = body.querySelectorAll('.tc-h');
  for (var i = 0; i < hs.length; i++){
    var el = hs[i];
    // v5829：带 data-keep 的分组标题强制保留（装备 TAB 的「鞍 / 附件」）
    var hasNum = /[\u2460-\u2473]/.test(String(el.textContent || '')) || (el.getAttribute('data-keep') === '1');
    /* v5869（用户口径「置顶文案块之上 无需显示 小标题行；比如附件」）：
       .tc-h 的**下一个兄弟是 .tc-intro** 时一律隐藏（即使带 data-keep="1"）——
       置顶文案块本身已说明内容，额外的「装备要点 AI 整理」「要点 AI 整理」「概述」等小标题只是噪声。
       「鞍 / 附件」这类**分组标题**下面是卡片网格、不是 .tc-intro ⇒ 不受影响。 */
    var _nx0 = el.nextElementSibling;
    var _beforeIntro = !!(_nx0 && _nx0.classList && _nx0.classList.contains('tc-intro'));
    if (hasNum && !_beforeIntro){
      if (el.getAttribute('data-lf-hide') === '1'){ el.style.display = ''; el.removeAttribute('data-lf-hide'); }
    } else if (el.getAttribute('data-lf-hide') !== '1'){
      el.style.display = 'none';
      el.setAttribute('data-lf-hide', '1');
    }
  }
  // ② .tc-top 紧跟 .tc-intro 时，交换两者顺序（徽章移到文案块下方）
  var tops = body.querySelectorAll('.tc-top');
  for (var j = 0; j < tops.length; j++){
    var tp = tops[j];
    var nx = tp.nextElementSibling;
    if (nx && nx.classList && nx.classList.contains('tc-intro')){
      tp.parentNode.insertBefore(tp, nx.nextSibling);
    }
  }
  // ③ v5759：术语中文化兜底 —— 对照表内术语一律显示中文（CODE/PRE/命令块/蓝图类名跳过）
  try { lbWtGlossDom(body); } catch (eGD) {}
  // ④ v5779（用户口径「非 AI 块里的错名要改」）：中文俗称 → 表内正名（阿根廷巨鹰→阿根廷鹫 / 木材→木头…）
  //   必须排在 enMark 之前：先把中文改对，再给正确的中文配英文小字
  try { lbZhFixDom(body); } catch (eZF) {}
  // v5762：术语中文化之后再补「英文小字」（中文→英文反查；命令块/徽章已在内层跳过）
  try { lbEnMark(body); } catch (eEM) {}
  } finally {
    if (_lfMO) { try { _lfMO.observe(body, { childList: true, subtree: true }); } catch (eLFR) {} }
  }
}

function lbWikiLayoutWatch(){
  var body = document.getElementById('lbWikiBody');
  if (!body || LB_WIKI_LF_MO) return;
  try {
    LB_WIKI_LF_MO = new MutationObserver(function(){
      /* v6106（用户口径「既然最终不显示，为啥要渲染后再隐藏」）：
         隐藏判定必须发生在**浏览器绘制之前**。MutationObserver 回调运行在微任务阶段
         （当前任务结束、下一帧绘制之前）⇒ 在这里**同步**跑一次 lbWikiLayoutFix，
         新插入的 .tc-h 在首帧就是隐藏态，不再有可见窗口。
         保留一次 60ms 后的校正，兜住图片/异步展开等「首帧后才长出来」的内容。 */
      try { lbWikiLayoutFix(); } catch (eLF0) {}
      if (LB_WIKI_LF_T) clearTimeout(LB_WIKI_LF_T);
      LB_WIKI_LF_T = setTimeout(function(){ try { lbWikiLayoutFix(); } catch (eLF) {} }, 60);
    });
    LB_WIKI_LF_MO.observe(body, { childList: true, subtree: true });
  } catch (eMO) { LB_WIKI_LF_MO = null; }
}

/* ===== v5915（用户口径）：物品 Wiki 面板同样隐藏「紧邻文案块(.tc-intro)」的无序号小标题
   · 命中例：「要点 · AI 整理」——正文块自说明内容，额外标题只是噪声（与物种面板 v5869 同口径）
   · 表格小标题（基本信息 / 属性数值 / 所需材料 等）下面不是 .tc-intro ⇒ **保留**
   · 带序号（①-⑳）小标题一律保留（同物种侧） */
var LB_WIKI_ITEM_LF_MO = null, LB_WIKI_ITEM_LF_T = null;
function lbWikiItemLayoutFix(){
  // v5924：主体抽到通用层 lbSheetLayoutFix（与资讯浮窗共用，逻辑不变）
  lbSheetLayoutFix(document.getElementById('lbWikiItemBody'));
}
function lbWikiItemLayoutWatch(){
  var body = document.getElementById('lbWikiItemBody');
  if (!body || LB_WIKI_ITEM_LF_MO) return;
  try {
    LB_WIKI_ITEM_LF_MO = new MutationObserver(function(){
      /* v6106：同 lbWikiLayoutWatch —— 先同步修正（微任务阶段，浏览器绘制之前），再保留 60ms 校正 */
      try { lbWikiItemLayoutFix(); } catch (eILF0) {}
      if (LB_WIKI_ITEM_LF_T) clearTimeout(LB_WIKI_ITEM_LF_T);
      LB_WIKI_ITEM_LF_T = setTimeout(function(){ try { lbWikiItemLayoutFix(); } catch (eILF) {} }, 60);
    });
    LB_WIKI_ITEM_LF_MO.observe(body, { childList: true, subtree: true });
  } catch (eIMO) { LB_WIKI_ITEM_LF_MO = null; }
}

/* ===== v5848（用户口径「回退物品页 只用物品页的数据」）=====
   物种在 wikily 无页面时的物品数据回退（同面板渲染，不跳转）：
     ① lbWikiFbBase() 反查本物种对应的物品（优先 Spawner_* 本体）
     ② lbWikiFbLoad() 拉该物品的物品 wiki 数据（PARSED）
     ③ lbWikiFbRender() 在物种面板内渲染描述/标签/工作台/配方/属性/官方要点 + AI 模块 */
function lbWikiFbBase(){
  try {
    var sp = (typeof lbCurSpKey === 'function') ? lbCurSpKey() : '';
    if (!sp) return '';
    var gs = lbSeriesGears(sp) || [];
    /* v5870（用户口径「寒冰飞龙 … 错误显示：本站无该物种页面 · 下列资料取自物品「双足飞龙骨架套装」」）：
       原写法「优先 Spawner，否则取第一个装备」⇒ 寒冰飞龙唯一关联物品是时装
       Wyvern_Bone_Costume（双足飞龙骧架套装），整个面板被换成一件骨架时装的资料。
       护栏：① 优先 Spawner 本体；② 其余排除 kind==='attachment'（附件/时装/皮肤）—— 这类根本不能当物种的替代资料；
       ③ 都没有就返回 ''（不回退，走「概览 + AI 模块」原兜底）。 */
    for (var i = 0; i < gs.length; i++){
      var b = String((gs[i] || {}).base || '');
      if (b && /Spawner/i.test(b)) return b;
    }
    var rest = gs.filter(function (g) {
      var bb = String((g || {}).base || '');
      if (!bb) return false;
      if ((g || {}).kind === 'attachment') return false;
      return true;
    });
    return rest.length ? String((rest[0] || {}).base || '') : '';
  } catch (e) { return ''; }
}
function lbWikiFbLoad(base){
  var st = LB_WIKI.itemFB || null;
  if (!st || st.base !== base || st.data) return;
  st.n = (st.n || 0) + 1;
  if (st.n > 6){
    st.busy = false;
    if (!st.err) st.err = new Error('抓取超时');
    try { lbWikiRender(); } catch (e0) {}
    return;
  }
  st.busy = true;
  /* v6107（卡死根因）：原 fetch 无超时 —— 请求挂死时下面 1.5s 重试永远不会触发
     ⇒ 面板永久停在「正在初始化」。加 15s AbortController，超时走 catch 落地错误。 */
  var _ac = null, _ato = null;
  try {
    _ac = new AbortController();
    _ato = setTimeout(function () { try { _ac.abort(); } catch (eA) {} }, 15000);
  } catch (eAC) { _ac = null; }
  fetch(LB_WIKI_ITEM_API + encodeURIComponent(base), { cache: 'no-store', signal: _ac ? _ac.signal : undefined })
    .then(function (r) { if (_ato) { clearTimeout(_ato); _ato = null; } return r.json(); })
    .then(function (j) {
      var s2 = LB_WIKI.itemFB;
      if (!s2 || s2.base !== base) return;
      if (j && j.status === 'ready' && j.data){ s2.data = j.data; s2.err = null; s2.busy = false; try { lbWikiRender(); } catch (e1) {} return; }
      if (j && j.data && j.data._fail){ s2.err = new Error((j.data && j.data.err) || '暂无资料'); s2.busy = false; try { lbWikiRender(); } catch (e2) {} return; }
      s2.busy = false;   // 仍在抓取 -> 稍后重试
      setTimeout(function () { if (LB_WIKI.itemFB && LB_WIKI.itemFB.base === base) { try { lbWikiFbLoad(base); } catch (e3) {} } }, 1500);
    })
    .catch(function (e) {
      if (_ato) { clearTimeout(_ato); _ato = null; }
      var s3 = LB_WIKI.itemFB;
      if (!s3 || s3.base !== base) return;
      s3.err = e; s3.busy = false;
      try { lbWikiRender(); } catch (e4) {}
    });
}
function lbWikiFbBodyHtml(p){
  var h = '';
  var esc = function (s) { return (typeof tcEsc === 'function') ? tcEsc(String(s == null ? '' : s)) : String(s == null ? '' : s); };
  var tags = (p.tags || []).filter(function (x) { return x; });
  if (tags.length) h += '<div class="tc-note">' + tags.map(esc).join(' · ') + '</div>';
  if (p.desc) h += '<div class="tc-sec"><div class="tc-h">描述</div><div class="lw-quote">' + ovPara(String(p.desc)) + '</div></div>';
  if (p.kick) h += '<div class="tc-note">' + esc(p.kick) + '</div>';
  var st = (p.station || []).filter(function (x) { return x; });
  var mats = (p.mats || []).filter(function (m) { return m && m[0]; });
  if (mats.length){
    h += '<div class="tc-sec"><div class="tc-h" data-keep="1">制作配方<em>' + mats.length + ' 项</em></div>';
    if (st.length) h += '<div class="tc-note">工作台：' + st.map(esc).join(' · ') + '</div>';
    h += '<table class="tc-tb"><thead><tr><th>材料</th><th style="text-align:right">数量</th></tr></thead><tbody>';
    mats.forEach(function (m) {
      var q = (m[1] === null || m[1] === undefined) ? '' : String(m[1]);
      h += '<tr><td class="ov-k">' + esc(m[0]) + '</td><td class="num">' + esc(q) + '</td></tr>';
    });
    h += '</tbody></table></div>';
  } else if (st.length){
    h += '<div class="tc-sec"><div class="tc-h" data-keep="1">工作台</div><div class="tc-note">' + st.map(esc).join(' · ') + '</div></div>';
  }
  var attrs = (p.attrs || []).filter(function (kv) { return kv && kv[0]; });
  if (attrs.length){
    h += '<div class="tc-sec"><div class="tc-h" data-keep="1">物品属性<em>' + attrs.length + ' 项</em></div><table class="tc-tb"><tbody>';
    attrs.forEach(function (kv) { h += '<tr><td class="ov-k">' + esc(kv[0]) + '</td><td class="num">' + esc(kv[1]) + '</td></tr>'; });
    h += '</tbody></table></div>';
  }
  var ak = p.ark || {};
  var pts = (ak.points || []).filter(function (x) { return x; });
  if (pts.length){
    /* v5868：官方要点与置顶文案块同一实现（.tc-intro） */
    h += '<div class="tc-sec"><div class="tc-h">官方要点</div>'
      + '<div class="tc-intro tc-ai">' + pts.map(function (x) { return '<p>' + esc(x) + '</p>'; }).join('') + '</div>'
      + '</div>';
  }
  try { lbTipsEnsure(); } catch (eT0) {}
  try { h += lbTipsAiWrapHtml(); } catch (eT1) {}
  return h;
}
function lbWikiFbRender(){
  var tabs = lbWikiEl('lbWikiTabs'), meta = lbWikiEl('lbWikiMeta'), body = lbWikiEl('lbWikiBody');
  var st = LB_WIKI.itemFB || {};
  var p = (st.data && st.data.PARSED) || {};
  var pz = String(p.zh || st.base || '');
  try { var _z = lbItemZh(st.base); if (_z) pz = _z; } catch (e0) {}
  var _g = false; try { _g = lbSpHasGear(); } catch (e1) { _g = false; }
  var _ok = [{ i: 0, t: '概览' }];
  if (_g) _ok.push({ i: 9, t: '装备' });
  var _cur = 0;
  for (var i = 0; i < _ok.length; i++){ if (_ok[i].i === (LB_WIKI.tab | 0)) { _cur = i; break; } }
  LB_WIKI.tab = _ok[_cur].i;
  if (tabs){
    var th = '';
    _ok.forEach(function (x, k) {
      th += '<span class="lw-tab' + (k === _cur ? ' on' : '') + '" data-i="' + x.i + '" onclick="lbWikiTab(' + x.i + ')">' + x.t + '</span>';
    });
    tabs.innerHTML = th;
  }
  if (meta){
    if (LB_WIKI.tab === 0){ meta.textContent = '本站无该物种页面 · 下列资料取自物品「' + pz + '」'; meta.style.display = ''; }
    else { meta.textContent = ''; meta.style.display = 'none'; }
  }
  if (!body) return;
  try {
    if (LB_WIKI.tab === 9){ renderGear(); return; }
    body.innerHTML = lbWikiFbBodyHtml(p);
    body.scrollTop = 0;
  } catch (e2) {
    body.innerHTML = '<div class="lw-err">渲染失败：' + String((e2 && e2.message) || e2) + '</div>';
  }
}

function lbWikiRender(){
  var ttl = lbWikiEl('lbWikiTitle'), tabs = lbWikiEl('lbWikiTabs'),
      meta = lbWikiEl('lbWikiMeta'), body = lbWikiEl('lbWikiBody');
  if (!ttl || !tabs || !meta || !body) return;
  if (LB_WIKI.mode === 'map'){ lbMapWikiRender(); return; }   // v5875：地图模式走同一面板

  var name = lbWikiKey(LB_WIKI.cur) || LB_WIKI.cur;
  // v72h：后端返回的中文名优先（DATA.zh）
  try {
    var _dk = lbWikiKey(LB_WIKI.cur);
    var _dz = ((LB_WIKI.data && LB_WIKI.data.DATA && LB_WIKI.data.DATA[_dk]) || {}).zh;
    if (_dz) name = _dz;
  } catch (eZ) {}
  try {
    if (typeof lbSpName === 'function'){
      var nm = lbSpName(LB_WIKI.cur);
      // nm.eng 在物种库未命中时会退回类名，故只在有中文时采纳
      if (nm && typeof nm === 'object') { if (nm.zh) name = nm.zh; }
      else if (nm) name = String(nm);
    }
  } catch (e) {}
  // v5688（用户口径「附件图标换成物种头像，记得反色」）：
  //   与物种选择按钮（#lbClassBtn）同一套图标链 —— lbIconForDinoClass(物种类名) + lbIconFilterStyle(url,'biology')
  //   取不到头像时回退 📖 emoji（与改前行为一致）
  var _spIco = '';
  try { _spIco = (typeof lbIconForDinoClass === 'function') ? (lbIconForDinoClass(LB_WIKI.cur) || '') : ''; } catch (eSI) {}
  if (_spIco) {
    var _spF = '';
    try {
      var _sf = lbIconFilterStyle(_spIco, 'biology') || '';
      var _sm = /filter:([^";]+)/.exec(_sf);
      if (_sm) _spF = 'filter:' + _sm[1] + ';';
    } catch (eSF) {}
    ttl.innerHTML = '<img src="' + _spIco + '" style="' + _spF + 'width:20px;height:20px;object-fit:contain;vertical-align:-4px;margin-right:6px" onerror="this.style.display=\'none\'">' + name + ' · Wiki';
  } else {
    ttl.textContent = '📖 ' + name + ' · Wiki';
  }

  // 加载中 / 失败
  var _spIds = { title: 'lbWikiTitle', tabs: 'lbWikiTabs', meta: 'lbWikiMeta', body: 'lbWikiBody' };
  if (!LB_WIKI.data && !LB_WIKI.err){
    try { var _sh0 = document.getElementById('lbWikiSrcHelp'); if (_sh0) { _sh0.setAttribute('hidden', 'hidden'); _sh0.removeAttribute('data-tip'); } } catch (eSH0) {}
    lbWikiPanelLoading(_spIds, LB_WIKI.progress, '首次加载约 4 秒，之后秒开');
    return;
  }
  if (LB_WIKI.err){
    /* v6107（用户口径「怎么卡住了」）：网络/超时类错误→ 直接报错 + 重试按钮，
       不再走下面的「物品回退」分支（那里在 fetch 挂死时会永久停在「正在初始化」）。 */
    var _ekind = '';
    try { _ekind = String((LB_WIKI.err && LB_WIKI.err.lbKind) || ''); } catch (eEK) {}
    if (_ekind === 'net'){
      try { CUR = lbWikiKey(LB_WIKI.cur); } catch (eC7) {}
      tabs.innerHTML = '';
      meta.textContent = ''; meta.style.display = 'none';
      try { var _sh1 = document.getElementById('lbWikiSrcHelp'); if (_sh1) { _sh1.setAttribute('hidden', 'hidden'); _sh1.removeAttribute('data-tip'); } } catch (eSH1) {}
      lbWikiPanelErr({ title: 'lbWikiTitle', tabs: 'lbWikiTabs', meta: 'lbWikiMeta', body: 'lbWikiBody' },
        name, '数据服务暂时不可用', 'lbWikiRetry()',
        String((LB_WIKI.err && LB_WIKI.err.message) || LB_WIKI.err));
      return;
    }
    /* v5848（用户口径「回退物品页 只用物品页的数据，而不是直接回退到物品页」）：
       物种在 wikily 无页面（载具/器械/未组装体）时，若本物种有对应物品（lbSeriesGears），
       则**在同一面板内**用该物品页的数据渲染（不跳转、不新开浮窗）。 */
    /* v5870（寒冰飞龙已 AI 整理却被回退成骨架时装）：
       该物种**已有 AI 整理结果**时不做物品回退 —— 整理内容就是它自己的资料，
       回退到一件无关物品（时装/附件）双足跏踏两头都不对。
       判据两条任一命中即算：① LB_WT 已 ready 且 slug 匹配 ② v5862 的 LB_WT_AI_PROBE 探到过（小写 slug）。
       首次进入且两者都未知时，先异步拉一次整理结果，回来后重绘。 */
    var _curSlug = String((LB_WIKI || {}).cur || '');
    var _hasWt = false;
    try { if (LB_WT && LB_WT.ready && String(LB_WT.slug || '') === _curSlug) _hasWt = true; } catch (eWH1) {}
    if (!_hasWt && _curSlug){
      try { if (LB_WT_AI_PROBE[String(_curSlug).toLowerCase()]) _hasWt = true; } catch (eWH2) {}
    }
    /* v6029：加一次性守卫 —— 无双保险时 fetch 失败会 callback 再 render，形成死循环 */
    if (!_hasWt && _curSlug && typeof lbWtLoad === 'function' && !LB_WT_TRIED[_curSlug]){
      try { lbWtLoad(function () { try { lbWikiRender(); } catch (eWL0) {} }); } catch (eWL1) {}
    }
    var _fbB = '';
    if (!_hasWt) {
      try { _fbB = (typeof lbWikiFbBase === 'function') ? lbWikiFbBase() : ''; } catch (eFB0) { _fbB = ''; }
    }
    if (_fbB){
      if (!LB_WIKI.itemFB || LB_WIKI.itemFB.base !== _fbB){
        LB_WIKI.itemFB = { base: _fbB, busy: false, data: null, err: null, n: 0 };
        try { lbWikiFbLoad(_fbB); } catch (eFB1) {}
      }
      var _fbs = LB_WIKI.itemFB || {};
      if (_fbs.data){ try { lbWikiFbRender(); } catch (eFB2) {} return; }
      if (!_fbs.err){
        var _idsFB = { title: 'lbWikiTitle', tabs: 'lbWikiTabs', meta: 'lbWikiMeta', body: 'lbWikiBody' };
        lbWikiPanelLoading(_idsFB, null, '正在读取物品资料…');
        return;
      }
    }
    /* v5829：战车/独木舟等载具在 wikily 上无页面，但有装备清单 ⇒ 只渲染「装备」TAB。
       v5831（用户口径「wikily没数据的 至少要保留技巧TAB」）：两源都失败时，
       TAB 条至少给「技巧」+「装备」（有装备才显示装备），不再整面板报错。 */
    /* v5843（用户口径「附件明明概览里永远有AI模块，怎么没显示概览」「附件为啥显示了技巧TAB，切过去内容也不对」）：
       原 v5829/v5831 兜底只给「装备 + 技巧」⇒ 概览 TAB 缺失；
       技巧 TAB 无条件出现，但无 AI 整理结果时切过去什么都不变。
       现改为：概览恒在（底部 AI 模块永远可用）→ 装备（有装备才给）→ 技巧（有 AI 整理结果才给）。 */
    var _okTabs = [{ i: 0, t: '概览' }];
    var _g3 = false; try { _g3 = lbSpHasGear(); } catch (eGG3) { _g3 = false; }
    if (_g3) _okTabs.push({ i: 9, t: '装备' });
    var _t3ok = false; try { _t3ok = (typeof lbTipsHasResult === 'function') ? lbTipsHasResult() : false; } catch (eTT3) { _t3ok = false; }
    if (_t3ok) _okTabs.push({ i: 7, t: '技巧' });
    /* v5843：err 模式不会过 lbWikiBind()，CUR 若不自行更新就会沿用上一个物种。 */
    try { CUR = lbWikiKey(LB_WIKI.cur); } catch (eC3) {}
    var _cur3 = 0;
    for (var _k3 = 0; _k3 < _okTabs.length; _k3++){ if (_okTabs[_k3].i === (LB_WIKI.tab | 0)) { _cur3 = _k3; break; } }
    var _th3 = '';
    _okTabs.forEach(function (x, i) {
      _th3 += '<span class="lw-tab' + (i === _cur3 ? ' on' : '') + '" data-i="' + x.i + '" onclick="lbWikiTab(' + x.i + ')">' + x.t + '</span>';
    });
    LB_WIKI.tab = _okTabs[_cur3].i;
    tabs.innerHTML = _th3;
    /* v5844（用户口径）：兜底提示改为推荐 AI 整理
       v5846（用户口径「这条只在概览里显示」）：仅概览 TAB 显示，其它 TAB 整行隐藏。 */
    if (LB_WIKI.tab === 0) { meta.textContent = '无权威信息，建议AI整理'; meta.style.display = ''; }
    else { meta.textContent = ''; meta.style.display = 'none'; }
    try {
      if (LB_WIKI.tab === 0) renderOverview();        // v5843：兜底也要有概览（AI 模块在底部）
      else if (LB_WIKI.tab === 9) renderGear();
      else renderTips();
    } catch (eR3) {
      body.innerHTML = '<div class="lw-err">渲染失败：' + String((eR3 && eR3.message) || eR3) + '</div>';
    }
    return;
  }

  var d = lbWikiCur();
  if (!d){
    tabs.innerHTML = '';
    meta.textContent = '';
    body.innerHTML = '<div class="lw-err">「' + name + '」暂无详细资料。<br>'
      + '该类物种的详细资料暂未收录。</div>';
    return;
  }

  // 顶部 tab
  var th = '';
  /* v5836（用户口径「物种 wiki 中 所有 TAB 都一样，如果没有数据就不显示」）：
     不再只看后端 _avail，统一走 lbWikiTabHasData() 逐 TAB 判定（概览恒显示）。 */
  var _wk = lbWikiKey(LB_WIKI.cur);
  LB_WIKI_TABS.forEach(function(lb, i){
    if (LB_WIKI_TAB_HIDE[i]) return;            // v5796：隐藏「收割」
    if (!lbWikiTabHasData(i, _wk)) return;      // v5836：无数据不占位
    th += '<span class="lw-tab' + (i === LB_WIKI.tab ? ' on' : '') + '" data-i="' + i + '" onclick="lbWikiTab(' + i + ')">' + lb + '</span>';
  });
  tabs.innerHTML = th;

  // P2：把 LB_WIKI.data 绑定到原型页全局名（每次渲染前刷新，CUR 随物种变化）
  lbWikiBind();
  lbWikiBind2();
  // v5745：读该物种的 wikily 原文整理结果（无则各 TAB 回落原文）
  try {
    var _wtSl = lbWtSlug();
    if (LB_WT.slug !== _wtSl && !LB_WT.busy){ lbWtLoad(function(){ try { lbWtRepaint(); } catch (e) {} }); }
  } catch (eW) {}

  // meta（一律用映射后的数据键，LB.curClass 是类名）
  var ov = (LB_WIKI.data.OVERVIEW || {})[_wk] || {};
  var ab = ((LB_WIKI.data.ABIL || {})[_wk] || {}).videos || [];
  var _pgNow = LB_WIKI.progress;
  /* v154：抓取中 -> 整行只剩进度条（不显示来源/时间/属性数等任何其它文字）
     · 进度 = 后端 /api/wiki/<key>/progress 的 done/total（真实值，非假动画）
     · 只更新内部 i 的 width（不重建节点）-> transition 平滑增长 */
  if (_pgNow) {
    meta.style.display = '';
    var _dn = _pgNow.done || 0, _tt = _pgNow.total || 5;
    var _pc = _tt > 0 ? Math.max(0, Math.min(100, Math.round(_dn / _tt * 100))) : 0;
    var _bar = document.getElementById('lwPgBar');
    var _lbl = document.getElementById('lwPgLbl');
    if (_bar && _lbl && meta.getAttribute('data-mode') === 'prog') {
      _bar.style.width = _pc + '%';
      _lbl.textContent = '其余 ' + _dn + '/' + _tt + ' 加载中';
    } else {
      meta.setAttribute('data-mode', 'prog');
      meta.innerHTML = '<span class="lw-pgw">'
        + '<span class="lw-pgl" id="lwPgLbl">其余 ' + _dn + '/' + _tt + ' 加载中</span>'
        + '<span class="lw-pgb"><i id="lwPgBar" style="width:' + _pc + '%"></i></span>'
        + '</span>';
    }
  } else {
    if (meta.getAttribute('data-mode') === 'prog') meta.removeAttribute('data-mode');
    // v5701（用户口径「不用展示」）：属性 N 项 · M 技能演示 整行不再显示
    meta.innerHTML = '';
    meta.style.display = 'none';
  }

  // v6107：右上角 tips 刷「数据来源」（wikily / wiki.gg / dododex）
  try { lbWikiSrcTip(); } catch (eST) {}
  // v6109：技能名/说明若仍是英文（wikily 中文站漏翻）→ 自动补译一次，完成后重绘技能 TAB
  try {
    if (lbSkillZhNeed().length) {
      lbSkillZhEnsure(function (changed) {
        if (!changed) return;
        try { lbWikiBind(); lbWikiBind2(); } catch (eSB) {}
        try { if (lbWikiTabIdx() === 5) renderAbilTab(); } catch (eSR) {}
      });
    }
  } catch (eSZ) {}
  // P2：按当前 tab 分发到真实渲染
  var _T = lbWikiTabIdx();
  try {
    if (_T === 0) { renderOverview(); return; }
    if (_T === 1) { renderTame(); return; }
    if (_T === 2) { renderBreed(); return; }
    if (_T === 3) { renderGather(); return; }
    if (_T === 4) { renderHarvest(); return; }
    if (_T === 6) { renderExp(); return; }
    if (_T === 5) { renderAbilTab(); return; }
    if (_T === 7) { renderTips(); return; }     // v5739：技巧（dododex 玩家心得）
    if (_T === 8) { renderSpawn(); return; }    // v5739：原 7（「生成指令」改名「生成」）
    if (_T === 9) { renderGear(); return; }     // v5826：装备（鞍 + 附件）
  } catch (e) {
    body.innerHTML = '<div class="lw-err">渲染失败：' + String((e && e.message) || e) + '</div>';
    return;
  }
  body.innerHTML = '<div class="lw-load">「' + LB_WIKI_TABS[_T] + '」将在后续批次接入（8 个 tab 全部接入）</div>';
}

/* v5836（用户口径「物种 wiki 中 所有 TAB 都一样，如果没有数据就不显示」）：
   逐 TAB 判定真实内容。**概览恒显示**（底部必有 AI 整理模块，不用按数据判定），其余按数据是否存在。
   k = 物种键（lbWikiKey 结果），不传则现算。 */
function lbWikiTabHasData(i, k){
  var D = (typeof LB_WIKI === 'object' && LB_WIKI && LB_WIKI.data) || {};
  if (!k){ try { k = lbWikiKey(LB_WIKI.cur); } catch (e0) { k = ''; } }
  var box = function (n) {
    var b = D[n];
    if (!b || typeof b !== 'object' || b._fail) return null;
    return b[k] || null;
  };
  var has = function (a) { return !!(a && a.length); };
  /* v5850（用户口径「能力 / 操作方法为啥都没取到」）：
     v5832 起 ark/载具回退只往各 TAB 写「置顶文案」（HOME.xxxIntro），
     但 TAB 显隐只看结构化块（TAME/ABIL/EXP）⇒ 明明有文案却不显示 TAB。这里补上「置顶文案也算有数据」。 */
  var _hi = function (n) {
    try { if (typeof wikiTabIntro === 'function') { var a = wikiTabIntro(n); if (a && a.length) return true; } } catch (eH1) {}
    return false;
  };
  try {
    if (i === 0) return true;      // 概览：恒显示
    if (i === 1) return !!box('TAME') || _hi('tameIntro');
    if (i === 2) return !!box('BREED');
    if (i === 3){ var g = box('GATHER'); return !!(g && (has(g.intro) || g.about || has(g.caps))); }
    if (i === 4) return false;     // 收割：全局隐藏
    if (i === 5){ var a5 = box('ABIL'); return !!(a5 && (has(a5.skills) || has(a5.notes) || has(a5.videos))) || _hi('abilIntro'); }
    if (i === 6) return !!box('EXP') || _hi('expIntro');
    if (i === 7) return (typeof lbTipsHasResult === 'function') ? lbTipsHasResult() : false;
    if (i === 8){ var sp = box('SPAWN'); return !!(sp && (has(sp.intro) || sp.main)) || _hi('spawnIntro'); }
    if (i === 9) return (typeof lbSpHasGear === 'function') ? lbSpHasGear() : false;
  } catch (e) { return true; }
  return true;
}

function lbWikiTabIdx(){
  var t = LB_WIKI.tab | 0;
  if (t < 0) t = 0;
  if (t >= LB_WIKI_TABS.length) t = 0;
  if (LB_WIKI_TAB_HIDE[t]) t = 3;   // v5796：收割已隐藏 -> 回落「采集」
  /* v5836：当前 TAB 已无数据（AI 结果变化 / ark 章节缺失等）-> 回落第一个有数据的 TAB */
  try {
    if (!lbWikiTabHasData(t)){
      for (var _i = 0; _i < LB_WIKI_TABS.length; _i++){
        if (LB_WIKI_TAB_HIDE[_i]) continue;
        if (lbWikiTabHasData(_i)) { t = _i; break; }
      }
    }
  } catch (eTb) {}
  if (LB_WIKI_TAB_HIDE[t]) t = 3;
  if (t === 9 && !lbSpHasGear()) t = 0;   // v5826：无装备的物种不落「装备」页
  return t;
}

/* ===== v5826（用户口径「有鞍或有附件的物种，加一个装备 TAB，一种装备一个卡片；
        战车这类加模块 TAB，和装备 TAB 同构」）=====
   数据源与「装备榜 · 缺 TAB 提示」同一口径（lbRankMissingTabs）：
     · kind === 'attachment' → lbItemSpAttachOf(base) 含该物种（走 dino_rules.json.attachSpecies）
     · kind === 'saddle' 且英文名含 Saddle → lbRankSpecies({class:base}) === 该物种
   去重：Mek 实测同物两类键（MekBackpack_MissilePod / PrimalItemArmor_MekBackpack_MissilePod）
         ⇒ 按 lbCanonBase() 归一后去重，避免同一件渲染两张卡。 */
var LB_GEAR_CACHE = {};
function lbSeriesGears(sp){
  try {
    sp = String(sp || '');
    if (!sp) return [];
    var zh = (typeof LB_ITEM_ZH !== 'undefined' && LB_ITEM_ZH) ? LB_ITEM_ZH : null;
    if (!zh) return [];
    var sig = sp + '|' + lbKeysLen(LB_KEYS_CACHE_ZH, zh) + '|' + (LB_ATTACH_SP ? 'A' : 'N');
    if (LB_GEAR_CACHE[sig]) return LB_GEAR_CACHE[sig];
    var out = [], seen = {};
    Object.keys(zh).forEach(function (base) {
      var mt = zh[base] || {}, kd = String(mt.kind || ''), hit = false;
      if (kd === 'attachment') {
        try { hit = (lbItemSpAttachOf(base).indexOf(sp) >= 0); } catch (e0) { hit = false; }
      } else if (kd === 'saddle' && /Saddle/i.test(String(mt.en || ''))) {
        try { hit = (lbRankSpecies({ 'class': base }) === sp); } catch (e1) { hit = false; }
      }
      if (!hit) return;
      var cb = ''; try { cb = String(lbCanonBase(base) || ''); } catch (e2) { cb = ''; }
      var dk = (cb || base) + '|' + kd;
      if (seen[dk]) return;
      seen[dk] = 1;
      out.push({ base: base, zh: String(mt.zh || base), en: String(mt.en || ''), kind: kd });
    });
    out.sort(function (a, b) {
      var ra = (a.kind === 'saddle') ? 0 : 1, rb = (b.kind === 'saddle') ? 0 : 1;
      if (ra !== rb) return ra - rb;
      try { return String(a.zh).localeCompare(String(b.zh), 'zh'); } catch (e3) { return 0; }
    });
    LB_GEAR_CACHE[sig] = out;
    return out;
  } catch (e) { return []; }
}
/* 当前物种桶键（ASB 权威名；与装备榜同源） */
function lbCurSpKey(){
  try { return String(lbRankSpecies({ 'class': (LB_WIKI || {}).cur || '' }) || ''); } catch (e) { return ''; }
}
function lbSpHasGear(){
  try { return lbSeriesGears(lbCurSpKey()).length > 0; } catch (e) { return false; }
}
/* 一张装备卡（物种「装备」TAB 专用；v5829 起物品侧不再有「模块」TAB） */
function lbGearCardHtml(g, curBase){
  g = g || {};
  var u = '';
  try { u = (typeof lbItemIconUrl === 'function') ? (lbItemIconUrl(g.base) || '') : ''; } catch (e0) {}
  var img;
  if (u) {
    var f = '';
    try {
      var fs = lbIconFilterStyleByName('', u) || '';
      var mf = /filter:([^";]+)/.exec(fs);
      if (mf) f = 'filter:' + mf[1] + ';';
    } catch (e1) {}
    img = '<img src="' + u + '" style="' + f + 'width:34px;height:34px;object-fit:contain;flex:0 0 auto" onerror="this.style.display=\'none\'">';
  } else {
    img = '<span class="mdi mdi-package-variant" style="font-size:26px;color:#8b93a7;flex:0 0 auto"></span>';
  }
  /* v5840（用户口径「附件没必要吧？重复了」）：卡片右侧的「鞍/附件」徽章与上方分组标题
     （「鞍 N 件」/「附件 N 件」）完全重复 ⇒ 删掉，卡片只留图标 + 中文名 + 英文名。 */
  var on = (String(curBase || '') && String(curBase) === String(g.base)) ? 'border-color:#a78bfa !important;' : '';
  return '<div class="lb-gear-card" onclick="lbGearOpen(' + "'" + String(g.base || '') + "'" + ')" title="' + tcEsc(String(g.zh || '')) + '（点击查看 Wiki）"'
    + ' style="' + on + 'display:flex;align-items:center;gap:9px;min-width:0;padding:8px 10px;border-radius:9px;background:#16161f;border:1px solid #2a2a38;cursor:pointer">'
    + img
    + '<div style="min-width:0;flex:1 1 auto">'
    + '<div style="font-size:12.5px;color:#d6d9e8;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + tcEsc(String(g.zh || '')) + '</div>'
    + (g.en ? ('<div style="font-size:10.5px;color:#8b93a7;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + tcEsc(String(g.en)) + '</div>') : '')
    + '</div>'
    + '</div>';
}
function lbGearCardsHtml(list, curBase){
  var out = '';
  (list || []).forEach(function (g) { out += lbGearCardHtml(g, curBase); });
  return out;
}
/* 点装备卡 -> 打开该物品的 Wiki（复用既有物品浮窗） */
function lbGearOpen(base){
  try {
    base = String(base || '');
    if (!base) return;
    LB.pickItem = { base: base };
    if (typeof lbWikiItemOpen === 'function') lbWikiItemOpen();
  } catch (e) {}
}

function lbWikiTab(i){
  LB_WIKI.tab = i | 0;
  lbWikiRender();
}

/* v5826：装备 TAB —— 一种装备一张卡；顶部显示 AI 整理出的「装备要点」（若有） */
function renderGear(){
  var body = lbWikiEl('lbWikiBody');
  if (!body) return;
  var list = lbSeriesGears(lbCurSpKey());
  var h = '';
  /* v5838：跳过对象 / 已污染的 "[object Object]"（历史脏缓存直接不显示），全空则整块不渲染 */
  var _rawTips = (LB_WT && LB_WT.data && LB_WT.data.gearTips) ? LB_WT.data.gearTips : [];
  var tips = [];
  (_rawTips || []).forEach(function (t) {
    if (t && typeof t === 'object') return;
    var tx = String(t === null || t === undefined ? '' : t).trim();
    if (!tx || tx === '[object Object]') return;
    if (tips.indexOf(tx) < 0) tips.push(tx);
  });
  if (tips.length){
    /* v5868：装备要点与置顶文案块同一实现（.tc-intro） */
    h += '<div class="tc-sec"><div class="tc-h" data-keep="1">装备要点<em>AI 整理</em></div>'
       + '<div class="tc-intro tc-ai">' + tips.map(function (t) { return '<p>' + tcEsc(t) + '</p>'; }).join('') + '</div>'
       + '</div>';
  }
  if (!list.length){
    body.innerHTML = h + '<div class="lw-err">该物种暂无可装备物品资料。</div>';
    return;
  }
  var groups = [{ k: 'saddle', zh: '鞍' }, { k: 'attachment', zh: '附件' }];
  groups.forEach(function (g) {
    var arr = list.filter(function (x) { return x.kind === g.k; });
    if (!arr.length) return;
    h += '<div class="tc-sec"><div class="tc-h" data-keep="1">' + g.zh + '<em>' + arr.length + ' 件</em></div>';
    h += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:8px">';
    h += lbGearCardsHtml(arr, '');
    h += '</div></div>';
  });
  body.innerHTML = h;
}

function lbWikiAgo(ts){
  var s = Math.max(0, Math.floor(Date.now() / 1000) - (ts || 0));
  if (!ts) return '未知时间';
  if (s < 60) return '刚刚';
  if (s < 3600) return Math.floor(s / 60) + ' 分钟前';
  if (s < 86400) return Math.floor(s / 3600) + ' 小时前';
  return Math.floor(s / 86400) + ' 天前';
}

/* ===== v5875：地图 Wiki（**复用**物种 wiki 的现成 DOM / 样式 / 方法，不造轮子）=====
   用户口径（2026-11-01）：
     · 「不光是照抄，而是完全复用wiki现有的样式js或方法，而不是重复造轮子」
     · 「按照wiki里的规则，在没有AI整理之前 只显示从wikily取到的中文内容」
     · 「Bob 是被整个项目过滤掉的，直接别考虑」
   复用清单（一条新样式都不加）：
     面板 DOM   #lbWikiOverlay / #lbWikiTitle / #lbWikiTabs / #lbWikiMeta / #lbWikiBody（同一个）
     入口绘制   lbWikiBtnPaint()             （35x35 / 圆角8 / 实心·虚线两态）
     加载/错误  lbWikiPanelLoading / lbWikiPanelErr
     TAB 条     lbWikiPanelTabs()
     置顶文案   wikiIntroHtml()              （含 .tc-ai 标记与术语正名）
     AI 模块    lbTipsAiBoxHtml()            （大肥鱼水印 + 模型/token + ⚙配置 + 主按钮）
     布局修正   lbWikiLayoutFix / lbWikiLayoutWatch（作用 #lbWikiBody）
     术语/正名  lbWtGlossDom / lbZhFixDom / lbEnMark（已由 lbWikiLayoutFix 内部调用）
     AI 请求    lbAiCfgGet / lbAiNormModel / lbAiParseJson / lbAiErrText（与物种同一套）
   本文件只新增：数据拉取、把数据喂给上面这些现成函数的少量胶水代码。 */
/* v6110（用户口径「为啥地图 wiki 入口不见了」）：
   LB_MW_API / LB_MW_SLUGS 已**移到 app_data.js**（首屏必加载）。
   原因：app_core.js 的 lbRenderFuncBar() 需要用 LB_MW_SLUGS 判断入口显隐，
   而本文件自 v6105 起是**按需加载**的 ⇒ 首屏取不到，入口被永久判为不可见。
   约定：**纯配置/纯数据放 app_data.js；本文件只留行为与运行时状态**（LB_MW / LB_MW_IDX / LB_MW_NAMES / LB_MW_TABS 仍留在此处）。 */
var LB_MW_NAMES = { Isl:'孤岛', Sco:'焦土', Cen:'核心岛', Abe:'畸变', Ext:'灭绝',
                    Ast:'星耀', Rag:'仙境', Val:'瓦尔盖罗', Los:'失落地', Gen:'创世' };
/* TAB：与物种侧同口径 —— 有原文或有 AI 整理才显示，空块不显示 */
var LB_MW_TABS = [['OVERVIEW','概览'], ['BIOME','群系'], ['RES','资源'], ['CAVE','洞穴'],
                  ['CREATURE','生物'], ['BOSS','首领'],
                  ['TIPS','技巧'], ['BASE','基地'], ['LORE','笔记'], ['STATS','统计']];
var LB_MW = { cur:'', data:null, err:null, tab:0, vlist:[], text:null, p:null, busy:false, msg:'' };
var LB_MW_IDX = null, LB_MW_IDX_P = null;

function lbMapWikiName(id){ return LB_MW_NAMES[id] || id || '地图'; }
/* v5877（用户口径「绝不允许暴露 wikily 的说法」）：后端错误串里可能带站点/URL，展示前统一脱敏 */
function lbMapWikiNoSite(s){
  return String(s == null ? '' : s)
    .replace(/https?:\/\/\S+/g, '')
    .replace(/wikily(\.gg)?/ig, '')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

/* 后端已抓好的地图清单（入口两态判定用，与 lbWikiHasData 同思路） */
/* v5890（与物种侧 lbWikiIndexApi / lbWikiHasData 完全同构）：
   · 守卫改成「**非空**才算已加载」—— 空对象不再当成已加载（v5890 之前正是被空对象锁死）
   · 失败/空结果 60 秒内不重试（避免每次 lbRenderFuncBar 都打后端） */
var LB_MW_IDX_AT = 0;
function lbMapWikiIndexLoad(force){
  if (LB_MW_IDX && Object.keys(LB_MW_IDX).length && !force) return Promise.resolve(LB_MW_IDX);
  if (LB_MW_IDX_P) return LB_MW_IDX_P;
  if (!force && LB_MW_IDX_AT && (Date.now() - LB_MW_IDX_AT) < 60000) return Promise.resolve(LB_MW_IDX || {});
  LB_MW_IDX_AT = Date.now();
  LB_MW_IDX_P = fetch(LB_MW_API + 'index?t=' + Date.now(), { cache: 'no-store' })
    .then(function(r){ if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(function(j){ var m = (j && j.maps) || null; if (m && Object.keys(m).length) LB_MW_IDX = m; LB_MW_IDX_P = null; return LB_MW_IDX || {}; })
    .catch(function(e){ LB_MW_IDX_P = null; throw e; });
  return LB_MW_IDX_P;
}
/* v5890（与物种侧 lbWikiHasData 三层判定同构）：
   ① 本次会话已拉到该地图数据  ② 已探到 AI 整理结果  ③ 后端缓存清单 ready */
function lbMapWikiHas(id){
  if (!id) return false;
  var slug = '';
  try { slug = String(LB_MW_SLUGS[id] || ''); } catch (eS) { slug = ''; }
  try {
    var d = LB_MW.data;
    if (String(LB_MW.cur || '') === String(id) && d && d.blocks && Object.keys(d.blocks).length) return true;
  } catch (e1) {}
  try { if (slug && LB_MW_AI_PROBE[slug]) return true; } catch (e2) {}
  try { if (LB_MW_IDX && LB_MW_IDX[id] && LB_MW_IDX[id].ready) return true; } catch (e3) {}
  return false;
}

/* 打开：复用 #lbWikiOverlay，切到 map 模式（面板/样式/布局全部沿用物种那一套） */
function lbMapWikiOpen(){
  var id = '';
  try { id = String((typeof lbVolcServer === 'function') ? lbVolcServer() : (LB.tab || '')); } catch (e) {}
  if (!id || !LB_MW_SLUGS[id]) { try { lbToast('请先进入一张地图'); } catch (e2) {} return; }
  LB_MW.cur = id;
  LB_MW.data = null; LB_MW.err = null; LB_MW.text = null; LB_MW.tab = 0; LB_MW.msg = ''; LB_MW.p = null;
  LB_WIKI.mode = 'map';          // 让 lbWikiRender 分派到地图渲染
  LB_WIKI.data = null;
  LB_WIKI.err = null;
  var ov = document.getElementById('lbWikiOverlay');
  if (!ov) return;
  ov.classList.add('show');
  lbWikiLayoutWatch();           // 现成布局修正（作用 #lbWikiBody）
  lbWikiRender();
  lbMapWikiEnsure().then(function(){ lbWikiRender(); })
    .catch(function(e){ LB_MW.err = e; lbWikiRender(); });
  lbMapWikiTextLoad();
}
function lbMapWikiClose(){ lbWikiClose(); }

function lbMapWikiReload(){
  LB_MW.data = null; LB_MW.err = null; LB_MW.p = null;
  lbWikiRender();
  lbMapWikiEnsure().then(function(){ lbWikiRender(); })
    .catch(function(e){ LB_MW.err = e; lbWikiRender(); });
}

function lbMapWikiEnsure(){
  var id = String(LB_MW.cur || '');
  if (!id) return Promise.reject(new Error('no map id'));
  if (LB_MW.data) return Promise.resolve(LB_MW.data);
  if (LB_MW.p) return LB_MW.p;
  LB_MW.p = fetch(LB_MW_API + encodeURIComponent(id) + '?t=' + Date.now(), { cache: 'no-store' })
    .then(function(r){ if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(function(j){
      LB_MW.p = null;
      /* v5890（用户口径「这个明明已经有缓存数据了，为啥还是虚线形态」）：**病根在这里** ——
         原写法拉单图数据时顺手来一句 `LB_MW_IDX = LB_MW_IDX || {}`，把「索引未加载(null)」变成「空索引({})」；
         而 lbMapWikiIndexLoad() 的守卫是 `if (LB_MW_IDX && !force) return` ⇒ {} 是真值 ⇒ 之后**永不拉取**，
         lbMapWikiHas() 恒 false ⇒ 入口永远虚线。此赋值毫无用处，直接删除。 */
      if (j && j.status === 'ready' && j.data){ LB_MW.data = j.data; return j.data; }
      throw new Error((j && j.err) || '加载失败');
    }, function(e){ LB_MW.p = null; throw e; });
  return LB_MW.p;
}

function lbMapWikiTextLoad(cb){
  var id = LB_MW.cur;
  if (!id) return;
  fetch(LB_MW_API + 'text?slug=' + encodeURIComponent(id) + '&t=' + Date.now(), { cache: 'no-store' })
    .then(function(r){ return r.json(); })
    .then(function(j){
      if (LB_MW.cur !== id) return;
      if (j && j.ok && j.blocks) LB_MW.text = j.blocks;
      if (LB_WIKI.mode === 'map') lbWikiRender();
      if (typeof cb === 'function') cb();
    })
    .catch(function(){ if (typeof cb === 'function') cb(); });
}

/* v5878（用户口径「喂给AI应该是三个源的所有数据信息 而不是只有wikily」）：
   收集**全部素材源**（后端 data.ai 里各源分块）。界面仍只展示中文原文那一份。 */
function lbMapWikiCollectSrc(){
  var d = (LB_MW.data || {});
  var ai = d.ai || null;
  var out = [];
  var zh = (ai && ai.wikily) || d.blocks || {};
  if (Object.keys(zh).length) out.push(['中文原文', zh]);
  if (ai && ai.ark && Object.keys(ai.ark).length) out.push(['英文原文', ai.ark]);
  if (ai && ai.dodo && Object.keys(ai.dodo).length) out.push(['玩家心得', ai.dodo]);
  return out;
}

function lbMapWikiTab(i){
  var ix = (LB_MW.vlist || [])[Number(i) || 0];
  if (ix === undefined) ix = 0;
  LB_MW.tab = ix;
  lbWikiRender();
}

function lbMapWikiHasKey(ix){
  var k = (LB_MW_TABS[ix] || [''])[0];
  if (!k) return false;
  var blocks = (LB_MW.data && LB_MW.data.blocks) || {};
  if ((blocks[k] || []).length) return true;
  return (((LB_MW.text || {})[k] || []).length > 0);
}
/* v5930（用户口径「Gen 的 wiki 里没有基地 TAB，基地 TAB 应该要常驻，因为地形图肯定要显示，地形图也算是内容」）：
   基地 TAB 的正文由 lbMapWikiPointsHtml() 出**本地底图**，与后端 blocks 完全无关 ⇒ 只要有底图就一定有内容。
   原判定只看 blocks.BASE / text.BASE，而 Gen 后端只回 STATS ⇒ 基地被判空隐藏。 */
function lbMapWikiHasMapImg(){
  try {
    var m = (typeof lbMapForServer === 'function') ? lbMapForServer(LB_MW.cur) : null;
    return !!(m && m.img);
  } catch (eHM) { return false; }
}

/* AI 模块 = 现成 lbTipsAiBoxHtml（与 lbWtEntryHtml 同一调用形态） */
function lbMapWikiAiEntryHtml(){
  var st;
  if (LB_MW.busy) st = lbTipsEsc(LB_MW.msg || '整理中…');
  else if (LB_MW.text) st = '该地图信息已整理';
  else if (LB_MW.msg) st = lbTipsEsc(LB_MW.msg);
  else st = '原文尚未整理 —— 整理后各 TAB 的说明会重新分配';
  return lbTipsAiBoxHtml({
    state: st,
    style: 'margin-top:14px',
    disabled: !!LB_MW.busy,
    btn: { txt: (LB_MW.text ? '重新整理' : 'AI 整理原文'), fn: 'lbMapWikiDigest()' }
  });
}

/* 置顶文案 = 现成 wikiIntroHtml（AI 结果优先，无 AI 才用 wikily 原文；与 renderTame 同一条规则） */
/* v5905（用户口径「获取的基地坐标各图标准不同……整理后的基地TAB置顶文案里也不许出现坐标以防误导，但可以允许存在文字表述的大概位置」）：
   剥离文本中的**数字坐标**，保留括号里的文字方位：
     「传送门（肥沃区，45,30）」→「传送门（肥沃区）」
     「Highlands Lighthouse (17,79)」→「Highlands Lighthouse」
   只处理「括号内含 数字,数字」的片段；无括号的裸数字（如「24 小时」「1,550」千分位）一律不动。 */
function lbMapWikiStripCoord(s){
  var t = String(s == null ? '' : s);
  return t.replace(/[\uff08(]([^\uff09)]{0,24})[\uff09)]/g, function (m, inner) {
    var m2 = /^\s*(.*?)[,，]?\s*\d{1,3}(?:\.\d+)?\s*[,，]\s*\d{1,3}(?:\.\d+)?\s*$/.exec(inner);
    if (!m2) return m;                                  // 括号内不是坐标 → 原样
    var area = String(m2[1] || '').replace(/[\s,，:：]+$/, '').trim();
    return area ? ('\uff08' + area + '\uff09') : '';
  });
}
function lbMapWikiStripCoordLines(arr){
  var out = [], i;
  for (i = 0; i < (arr || []).length; i++) out.push(lbMapWikiStripCoord(arr[i]));
  return out;
}
function lbMapWikiIntroHtml(ix){
  var k = (LB_MW_TABS[ix] || [''])[0] || '';
  var blocks = (LB_MW.data && LB_MW.data.blocks) || {};
  var raw = blocks[k] || [];
  var ai = (LB_MW.text || {})[k] || [];
  if (ix === 7){ raw = lbMapWikiStripCoordLines(raw); ai = lbMapWikiStripCoordLines(ai); }   // v5905：基地 TAB 去坐标（原文+AI 整理后都去）
  /* v5912（用户口径「第 10 项也统一成同一条渲染链」）：
     置顶文案不再单独调 wikiIntroHtml，改与其它 TAB 走**同一个** lbMapWikiSentHtml：
       · 容器规则同源：.tc-intro[.tc-ai] + <p>（照抄 wikiIntroHtml 的写法）
       · 另加「一句一行」切句（用户 v5820 口径「其他置顶文案 尽量一句一行」）
     AI 结果 → 带 .tc-ai 参与标注（英文小字 + 俗名正名）；原文回退 → 只 .tc-intro（不参与标注）。
     至此全图 Wiki 只剩这一条正文渲染链，不再有「基地一套、其它一套」。 */
  if (ai.length) return lbMapWikiSentHtml(ai, true);
  if (raw.length) return lbMapWikiSentHtml(raw, false);
  return '';
}

/* v5880（用户口径「基地位置 也要加一个地图，直接将点位渲染到地图上」「点位名称要跟着翻译」）：
   底图/坐标换算/点位样式全部复用项目现成实现：
     lbMapForServer(id)  取该地图的底图对象
     lbWorldToPx(x,y,map) 世界坐标 -> 百分比
     .settle-btn > .settle-map > .settle-dot  现成点位样式
   AI 整理过的点位中文名存在 LB_MW.text.BASEPTS（与原文点按顺序一一对应）。 */
/* v5896：基地点位统一解析（地图渲染 + AI 素材共用同一份）——
   ① 优先后端 points.BASE；② 为空时从 BASE 文字行兜底解析（螰变等「名称 (区域名, x,y)」写法）。
   之前 AI 整理只喂 points.BASE，而螰变该值为空 ⇒ AI 收不到点位 ⇒ 不产出 BASEPTS ⇒ 徽章一直显示英文原文。 */
/* v5897：从「名称（区域名, x,y）：说明」这类文字行解析点位（AI 中文段落 / 原文段落通用） */
function lbMapWikiParsePts(lines){
  var out = [];
  var reB = /[\uff08(][^\uff09)]{0,24}?(\d{1,3}(?:\.\d+)?)\s*[,，]\s*(\d{1,3}(?:\.\d+)?)\s*[\uff09)]/;
  for (var i = 0; i < (lines || []).length; i++){
    var sB = lbWikiNoBullet(lines[i]);
    var mB = reB.exec(sB);
    if (!mB) continue;
    var xB = Number(mB[1]), yB = Number(mB[2]);
    if (!(xB >= 0 && xB <= 100 && yB >= 0 && yB <= 100)) continue;
    var nB = sB.slice(0, mB.index).replace(/^[\s\u2022\u00b7]+/, '').replace(/[\s：:]+$/, '').trim();
    out.push({ n: String(nB || sB).slice(0, 28), x: xB, y: yB });
  }
  return out;
}
function lbMapWikiBasePts(){
  var raw = (((LB_MW.data || {}).points || {}).BASE) || [];
  var zh = ((LB_MW.text || {}).BASEPTS) || [];
  var pts = [], i;
  for (i = 0; i < raw.length; i++){
    var p = raw[i] || {};
    var nm = (zh[i] && zh[i].n) ? String(zh[i].n) : String(p.n || '');
    pts.push({ n: nm, x: Number(p.x), y: Number(p.y) });
  }
  if (pts.length) return pts;
  /* v5897（用户反馈「点了还是英文的」根因修复）：
     后端 points.BASE 为空的图（螰变），AI 整理后的 text.BASE **本身就是中文名+坐标**
     （如「传送门（肥沃区，45,30）：…」），直接从这里解析即可得到中文徽章名，
     不必等 AI 再产出 BASEPTS。原文段落仅作最后兜底（英文名）。 */
  var aiPts = lbMapWikiParsePts(((LB_MW.text || {}).BASE) || []);
  if (aiPts.length) return aiPts;
  return lbMapWikiParsePts((((LB_MW.data || {}).blocks) || {}).BASE || []);
}

/* v5896（用户口径「基地地图中的徽章不允许重叠」）：
   徽章常驻显示（v5883），密集点位必然互相压住。渲染后按「上→下→右→左」四向试位，
   仍冲突则垂直逐级错开；越出地图边界同样视为冲突。只调位置，样式/字号/颜色全部沿用 .lbwxz-tip。 */
function lbMapWikiTipsDeclash(){
  var root = document.getElementById('lbWikiBody');
  if (!root) return;
  var img = root.querySelector('img[alt="基地点位地图"]');
  if (!img || !img.getBoundingClientRect().width) return;
  var cRect = img.getBoundingClientRect();
  var dots = root.querySelectorAll('.lbwxz-dot');
  var CANDS = [
    'display:block;left:50%;right:auto;top:auto;bottom:12px;transform:translateX(-50%)',
    'display:block;left:50%;right:auto;top:12px;bottom:auto;transform:translateX(-50%)',
    'display:block;left:calc(50% + 11px);right:auto;top:50%;bottom:auto;transform:translateY(-50%)',
    'display:block;right:calc(50% + 11px);left:auto;top:50%;bottom:auto;transform:translateY(-50%)'
  ];
  var placed = [];
  function hitTest(r){
    if (r.left < cRect.left - 1 || r.right > cRect.right + 1 || r.top < cRect.top - 1 || r.bottom > cRect.bottom + 1) return true;
    for (var k = 0; k < placed.length; k++){
      var p = placed[k];
      if (!(r.right <= p.left || r.left >= p.right || r.bottom <= p.top || r.top >= p.bottom)) return true;
    }
    return false;
  }
  for (var i = 0; i < dots.length; i++){
    var tip = dots[i].querySelector('.lbwxz-tip');
    if (!tip) continue;
    var ok = false, c, r;
    for (c = 0; c < CANDS.length && !ok; c++){
      tip.style.cssText = CANDS[c];
      r = tip.getBoundingClientRect();
      if (!hitTest(r)) ok = true;
    }
    if (ok){ placed.push(r); continue; }
    for (var n = 1; n <= 8 && !ok; n++){
      tip.style.cssText = 'display:block;left:50%;right:auto;top:auto;bottom:' + (12 + n * 15) + 'px;transform:translateX(-50%)';
      r = tip.getBoundingClientRect();
      if (!hitTest(r)) ok = true;
    }
    if (!ok){ tip.style.cssText = CANDS[0]; r = tip.getBoundingClientRect(); }
    placed.push(r);
  }
}

/* v5902（用户口径「只允许复用，不许重新校准」）：地图 wiki 基地点位的「坐标写法」表。
   只作用于基地点位这一处解析，**不动 LB_MAP_INFO 的任何 shift/mult/经纬度边界，也不影响其它打点功能**。
     lonlat = (经度, 纬度) 先经度；latlon = (纬度, 经度) 先纬度（ARK 惯例，默认值）。
   已实测验证：Isl=lonlat（Hidden Lake 真实 lat≈40/lon≈70、Footpaw 在南海岸）；
               Sco/Cen=lonlat（焦土：绿方尖碑左上/高山高原右侧岩山/南部峡谷右下/西部高地在西 5/5；
                              核心岛：浮空岛北部岛/北极半岛雪区/中央湖泊正中/骷髅岛小岛 7/7）；
               Rag=latlon（wiki 原文「The Highlands 东北部」，(17,79) 只有 lat17/lon79 才落在东北）。
   ① 后缀 F = **上下翻转**（top = 100 - top）：Ext 实测—不翻转时「沙漠穹顶入口」被画到左下荒地，
     翻转后落在右下深红圆（玩家指认的沙漠穹顶）边缘；城市两点也在城内。
   以后发现哪张图不对，只需在这张表里改一个单词。 */
var LB_MW_PT_ORDER = { Isl: 'lonlat', Sco: 'lonlat', Cen: 'lonlat', Rag: 'latlon', Ext: 'lonlatF' };
function lbMapWikiPointsHtml(){
  /* v5902（用户口径「只允许复用，不许重新校准」）：
     wiki「战略基地位置」写的是 (a,b)，但**不同地图页面写法相反**（同一套模板、不同编辑）：
       孤岛：Hidden Lake (70,40) 真实在 lat≈40 / lon≈70；Footpaw (40,80) 在南海岸 → **(经度,纬度)**
       仙境：wiki 原文「The Highlands 东北部」，(17,79) 只有 lat17/lon79 才落在东北 → **(纬度,经度)**
     所以这里只记一笔「已验证的写法」，**不动 LB_MAP_INFO 的任何 shift/mult/边界，也不影响其它打点功能**；
     未列入的图按 ARK 惯例 (纬度,经度)。以后验证哪张图不对，在这张表里改一个单词即可。 */
  /* v5905（用户口径「获取的基地坐标各图标准不同，直接在基地里不显示点位了，只显示地图」）：
     实测五图各一套写法（Isl/Sco/Cen=经度先、Rag=纬度先、Ext 还要上下翻转，且 Sco/Cen 仍有整体偏移），
     继续画徽章必然误导 ⇒ **基地 TAB 只保留底图，不画任何点位**。
     `LB_MW_PT_ORDER` / `lbMapWikiBasePts()` 保留（AI 素材仍用），以后要恢复画点再重新接入。 */
  var map = null;
  try { if (typeof lbMapForServer === 'function') map = lbMapForServer(LB_MW.cur); } catch (e0) { map = null; }
  if (!map || !map.img) return '';
  /* v5930（用户口径「Gen 是有 2 个图的，别搞忘了」）：创世分陆地/海洋两张底图（LB_MAP_INFO.Gen.oceanImg），
     原来只画 map.img（陆地）⇒ 海洋图永远看不到。先出主图，再按配置追加海洋图；其它地图无 oceanImg 行为不变。 */
  var _out = lbMapWikiFigHtml('地形图', map.img);
  try {
    var _mi = (typeof LB_MAP_INFO !== 'undefined' && LB_MAP_INFO) ? LB_MAP_INFO[LB_MW.cur] : null;
    if (_mi && _mi.oceanImg && _mi.oceanImg !== map.img) _out += lbMapWikiFigHtml('海洋地形图', _mi.oceanImg);
  } catch (eOI) {}
  return _out;
}
/* v5930：单张地形图（与 v5905 原写法同款，仅抽出复用；样式零改动） */
function lbMapWikiFigHtml(title, imgName){
  var src = LB_MAP_BASE + imgName + LB_MAP_EXT;
  return '<div class="tc-sec"><div class="tc-h" data-keep="1">' + tcEsc(title) + '</div>'
    + '<div style="position:relative;margin:6px auto 2px;max-width:560px;border-radius:8px;border:1px solid #2a2a3a">'
    + '<img src="' + lbResURL(src) + '" data-lbasset="' + src + '" alt="' + tcEsc(title) + '" loading="lazy"'
    + ' style="width:100%;display:block;opacity:.92;border-radius:7px" onerror="lbImgRetry(this)">'
    + '</div></div>';
}

/* v5884（用户口径「群系、统计 要序列样式」「技巧要复用物种 技巧的样式」）：
   全部复用物种技巧 TAB 的现成样式类（作用域同为 #lbWikiOverlay）：
     .tc-tipd / .tc-tipd-sec / .tc-tipd-h / .tc-tipd-n（紫色圆形序号）/ .tc-tipd-t / .tc-tipd-p
     .tc-auth / .tc-auth-h / .tc-auth-bdg / .tc-auth-i（琥珀金块「原文权威要点」）
   不新增任何样式。 */
function lbMapWikiTipdHtml(lines){
  /* v5887（用户口径「我要的是完全和物种的技巧样式一致……序号行物种的似乎没有包裹吧？」）：
     严格照物种 lbTipsListHtml 的结构：
       <div class="tc-tipd">
         <div class="tc-tipd-sec">
           <div class="tc-tipd-h"><span class="tc-tipd-n">序号</span>小标题</div>
           <div class="tc-tipd-t"><div class="tc-tipd-p">正文</div></div>
         </div>
       </div>
     序号只出现在 .tc-tipd-h 里，**不塞进正文段落**；正文段落用 .tc-tipd-p（纯文字）。
     条目标题来自 AI 输出里的「小标题：正文」冒号前缀；无冒号的条目只出正文段落。 */
  if (!lines || !lines.length) return '';
  var h = '<div class="tc-tipd">', n = 0;
  for (var i = 0; i < lines.length; i++){
    var s = lbWikiNoBullet(lines[i]).trim();
    if (!s) continue;
    var k = s.indexOf('\uff1a');
    if (k > 0 && k <= 20){
      n++;
      h += '<div class="tc-tipd-sec">'
        + '<div class="tc-tipd-h"><span class="tc-tipd-n">' + n + '</span>' + tcEsc(s.slice(0, k)) + '</div>'
        + '<div class="tc-tipd-t"><div class="tc-tipd-p">' + tcEsc(s.slice(k + 1)) + '</div></div>'
        + '</div>';
    } else {
      h += '<div class="tc-tipd-sec"><div class="tc-tipd-t"><div class="tc-tipd-p">' + tcEsc(s) + '</div></div></div>';
    }
  }
  h += '</div>';
  return h;
}

function lbMapWikiAuthHtml(lines, badge){
  /* 与物种技巧的琥珀金块完全一致：徽章带图标（📜）＋ .tc-auth-i 逐条 */
  if (!lines || !lines.length) return '';
  var h = '<div class="tc-auth"><div class="tc-auth-h"><span class="tc-auth-bdg">'
        + (badge || '📜 权威心得') + '</span></div>';
  for (var i = 0; i < lines.length; i++) h += '<div class="tc-auth-i">' + tcEsc(lbWikiNoBullet(lines[i])) + '</div>';
  h += '</div>';
  return h;
}

/* 一句一行：按中文句号/问号/叹号切句，每句一个 <p>（沿用现成 .tc-intro 样式）
   v5889（用户口径「地图wiki是不是没有用标注样式的规则啊？你怎么做了这个漏了那个」）：
   根因 —— 标注引擎 lbEnMark / lbZhFixDom 有**准入白名单**，只认
     `.tc-ai / .tc-auth-i / .tc-tipd-p / .tc-tipd-t / .abil-desc`
   技巧(.tc-tipd-p/.tc-auth-i)、基地置顶(走现成 wikiIntroHtml 自带 .tc-ai) 都命中，
   而概览/资源/洞穴/生物/首领/笔记这些走本函数，容器只有 `.tc-intro` ⇒ 英文小字与正名全漏。
   修法照抄物种侧 wikiIntroHtml() 的既定写法（v5765/v5780：**只有 AI 整理结果才加 .tc-ai**）：
     '<div class="tc-intro' + (isAi ? ' tc-ai' : '') + '">'
   AI 结果 → 带 .tc-ai 参与标注；无 AI 回退原文 → 仍只 .tc-intro（与物种侧一致，不擅自扩大范围）。 */
function lbMapWikiSentHtml(lines, isAi){
  if (!lines || !lines.length) return '';
  var h = '<div class="tc-intro' + (isAi ? ' tc-ai' : '') + '">';
  for (var i = 0; i < lines.length; i++){
    var s = lbWikiNoBullet(lines[i]).trim();
    if (!s) continue;
    var parts = s.split(/(?<=[\u3002\uff01\uff1f])/);
    for (var j = 0; j < parts.length; j++){
      var p = String(parts[j] || '').trim();
      if (p) h += '<p>' + tcEsc(p) + '</p>';
    }
  }
  h += '</div>';
  return h;
}

/* 一行一条，无序号（群系 / 统计）
   v5889：同 lbMapWikiSentHtml —— AI 结果时容器追加 .tc-ai 以进入标注白名单。 */
function lbMapWikiLinesHtml(lines, isAi){
  if (!lines || !lines.length) return '';
  var h = '<div class="tc-intro' + (isAi ? ' tc-ai' : '') + '">';
  for (var i = 0; i < lines.length; i++){
    var s = lbWikiNoBullet(lines[i]).trim();
    if (s) h += '<p>' + tcEsc(s) + '</p>';
  }
  h += '</div>';
  return h;
}

/* v5887（用户口径「笔记的坐标详细信息为啥还在？」）：
   后端过滤要重启才生效，前端再兜一层——带坐标/计数/条目编号的行直接不渲染。 */
var LB_MW_LORE_BAD = /已找到|未找到|列表显示|记录进度|Record #|Note #|Dossier|图鉴#|\d{1,3}\.\d+\s*[,，]\s*\d{1,3}\.\d+/i;
function lbMapWikiLoreFilter(lines){
  var out = [];
  for (var i = 0; i < (lines || []).length; i++){
    var s = String(lines[i] || '').trim();
    if (s.length < 12) continue;
    if (LB_MW_LORE_BAD.test(s)) continue;
    if (out.indexOf(s) < 0) out.push(s);
  }
  return out.slice(0, 10);
}

/* v5892（用户口径「统计改成表格样式，复用物种 wiki 浮窗里的表格样式，不要重复造轮子」）：
   统计数据本身就是「生物 76 / 资源 11 …」的键值行（AI 版是一行逗号串），直接出两列表格。
   样式**零新增** —— 复用物种侧的 table.tc-tb（与驯服/属性表同一套 CSS）。 */
function lbMapWikiStatRows(lines){
  var rows = [];
  (lines || []).forEach(function(raw){
    var s = lbWikiNoBullet(raw).trim();
    if (!s) return;
    var parts = /[，,]/.test(s) ? s.split(/[，,]/) : [s];
    parts.forEach(function(p){
      p = String(p || '').replace(/[。.;；\s]+$/, '').trim();
      if (!p) return;
      var m = p.match(/^(.+?)[\s:：]*([0-9][0-9,\.]*)$/);
      if (m) rows.push([m[1].replace(/[\s:：]+$/, '').trim(), m[2].replace(/[,\s]/g, '')]);
      else rows.push([p, '']);
    });
  });
  return rows;
}
function lbMapWikiStatsHtml(lines){
  var rows = lbMapWikiStatRows(lines);
  if (!rows.length) return '';
  var h = '<div class="tc-sec"><div class="tc-h" data-keep="1">地图统计<em>数据条目数量</em></div>'
        + '<table class="tc-tb"><thead><tr><th>项目</th><th class="num">数量</th></tr></thead><tbody>';
  for (var i = 0; i < rows.length; i++){
    h += '<tr><td class="ov-k">' + tcEsc(rows[i][0]) + '</td><td class="num">' + tcEsc(rows[i][1]) + '</td></tr>';
  }
  h += '</tbody></table></div>';
  return h;
}
/* ===== v5957（用户口径）：概览的置顶文案块下方显示该地图的宣传图 =====
   源图 img.whiterober.ccwu.cc/ASA/misc/<地图Id>_compressed.jpg（1280×720）
   ⇒ 本地转 WebP q70 → tmp/_map_assets/<地图id>_promo.webp → 随 maps/ 打包上 CF。
   图片缺失时**整块移除**（不留空标题、不破图）。 */
function lbMapWikiPromoHtml(){
  try{
    var id = String(LB_MW.cur || '');
    if (!id || id === 'Bob') return '';               // Bob 无地图
    var src = LB_MAP_BASE + id.toLowerCase() + '_promo' + LB_MAP_EXT;
    var uid = 'lbMwPromo_' + id.toLowerCase();
    return '<div class="tc-sec" id="' + uid + '"><div class="tc-h" data-keep="1">地图宣传图</div>'
      + '<div style="position:relative;margin:6px auto 2px;max-width:560px;border-radius:8px;border:1px solid #2a2a3a">'
      + '<img src="' + lbResURL(src) + '" data-lbasset="' + src + '" alt="地图宣传图" loading="lazy"'
      + ' style="width:100%;display:block;opacity:.92;border-radius:7px"'
      + ' onerror="var _p=document.getElementById(\'' + uid + '\');if(_p&&_p.parentNode)_p.parentNode.removeChild(_p)">'
      + '</div></div>';
  }catch(e){ return ''; }
}

function lbMapWikiBodyHtml(ix){
  var k = (LB_MW_TABS[ix] || [''])[0] || '';
  var ai = ((LB_MW.text || {})[k] || []);
  var raw = (((LB_MW.data || {}).blocks || {})[k] || []);
  var h = '<div class="tc">';
  if (ix === 7){                                  // 基地：置顶文案 + 点位地图
    var introB = lbMapWikiIntroHtml(ix);
    if (introB) h += introB;
    h += lbMapWikiPointsHtml();
  } else if (ix === 6){                           // 技巧：📜 原文要点（金块）+ AI 分节长文（紫块）
    h += lbMapWikiAuthHtml(raw, '📜 原文要点');
    h += lbMapWikiTipdHtml(ai);
    if (!raw.length && !ai.length) h += '<div class="lw-err">该章节暂无原文资料。</div>';
  } else if (ix === 9){                           // 统计：表格（原文结构最完整优先；无原文才用 AI 串）
    var _st = raw.length ? raw : ai;
    if (_st.length) h += lbMapWikiStatsHtml(_st);
    else h += '<div class="lw-err">该章节暂无原文资料。</div>';
  } else if (ix === 1){                           // 群系：一行一条，无序号
    h += lbMapWikiLinesHtml(ai.length ? ai : raw, ai.length > 0);
    if (!raw.length && !ai.length) h += '<div class="lw-err">该章节暂无原文资料。</div>';
  } else if (ix === 8){                           // 笔记：过滤坐标/计数类数据行
    var lore = lbMapWikiLoreFilter(ai.length ? ai : raw);
    if (lore.length) h += lbMapWikiSentHtml(lore, ai.length > 0);
    else h += '<div class="lw-err">该章节暂无原文资料。</div>';
  } else {                                        // 其余：置顶文案，一句一行
    var lines = ai.length ? ai : raw;
    if (lines.length) h += lbMapWikiSentHtml(lines, ai.length > 0);
    else h += '<div class="lw-err">该章节暂无原文资料。</div>';
  }
  if (ix === 0) h += lbMapWikiPromoHtml();   // v5957：置顶文案块下方显示地图宣传图
  if (ix === 0) h += lbMapWikiAiEntryHtml();
  h += '</div>';
  return h;
}

/* v5938（用户口径「其他 wiki 有的样式、结构都允许」）：把 AI 输出的扁平结构重组成**分区子卡片**。
   识别规则：形如 `<p><b>主题名</b></p>`（整段只有一个 <b>、且文字 ≤ 30 字）视为「主题头」，
   它后面紧跟的 <ul>/<ol>/<table>/<p> 全部收进同一张 `.lb-nsub` 子卡片，直到遇到下一个主题头。
   纯 DOM 重组，不改文本内容；发生任何异常都静默跳过（不影响原文渲染）。 */
function lbNewsEnhance(root){
  try {
    if (!root) return;
    var intros = root.querySelectorAll('.tc-intro');
    Array.prototype.forEach.call(intros, function(intro){
      var kids = Array.prototype.slice.call(intro.childNodes);
      var cur = null;
      for (var i = 0; i < kids.length; i++){
        var node = kids[i];
        if (node.nodeType !== 1) continue;
        var tag = node.tagName;
        var isHead = false, headTxt = '';
        if (tag === 'P'){
          var bs = node.querySelectorAll('b');
          if (bs.length === 1 && node.textContent.trim() === bs[0].textContent.trim()){
            headTxt = bs[0].textContent.trim();
            if (headTxt && headTxt.length <= 30) isHead = true;
          }
        }
        if (isHead){
          cur = document.createElement('div');
          cur.className = 'lb-nsub';
          var hd = document.createElement('div');
          hd.className = 'lb-nsub-h';
          hd.textContent = headTxt;
          cur.appendChild(hd);
          intro.insertBefore(cur, node);
          intro.removeChild(node);
          continue;
        }
        if (cur && /^(UL|OL|TABLE|P)$/.test(tag)){
          cur.appendChild(node);
        } else {
          cur = null;
        }
      }
    });
    /* v5940：表格首列补 ov-k（wiki 的「行标签列」观感）—— AI 只输出裸 <td> */
    Array.prototype.forEach.call(root.querySelectorAll('table.tc-tb tbody tr'), function(tr){
      var tds = tr.children;
      if (!tds || !tds.length) return;
      var first = tds[0];
      if (first && first.tagName === 'TD' && !first.className) first.className = 'ov-k';
    });
    /* v5940（用户口径「新闻里有视频的也要直接放出来」）：AI 常把视频写成单独一段裸 URL，
       播放器已在卡片里 ⇒ 这行 URL 改成可点的「▶ 观看视频」（没播放器时也不丢入口） */
    Array.prototype.forEach.call(root.querySelectorAll('.tc-intro p'), function(p){
      var t = (p.textContent || '').trim();
      if (!/^https?:\/\/\S+$/i.test(t)) return;
      var sec = p.parentNode;
      while (sec && sec !== root && !(sec.classList && sec.classList.contains('tc-sec'))) sec = sec.parentNode;
      /* v5942：卡片里已有视频播放器（.tc-video）⇒ 这行重复的裸 URL 直接去掉；
         若它所在的子卡片只剩标题（如「观看视频」），连子卡片一并去掉 */
      var hasFrame = (sec && sec.querySelector) ? !!sec.querySelector('.tc-video, iframe') : false;
      if (hasFrame){
        var box = p.parentNode;
        var isSub = !!(box && box.classList && box.classList.contains('lb-nsub'));
        if (box) box.removeChild(p);
        if (isSub && box && !box.querySelectorAll('ul,ol,table,p').length && box.parentNode) box.parentNode.removeChild(box);
        return;
      }
      /* v5946（用户口径「不需要 在新窗口打开 功能」）：无播放器时也不再生成跳转按钮，保留纯文字即可 */
    });
  } catch (e) {}
}
/* 由 lbWikiRender 在 map 模式下调用；写的是同一套 #lbWiki* 节点 */
function lbMapWikiRender(){
  var ttl = document.getElementById('lbWikiTitle'), meta = document.getElementById('lbWikiMeta'),
      body = document.getElementById('lbWikiBody');
  if (!ttl || !meta || !body) return;
  var ids = { title:'lbWikiTitle', tabs:'lbWikiTabs', meta:'lbWikiMeta', body:'lbWikiBody' };
  var id = String(LB_MW.cur || '');
  var name = lbMapWikiName(id);
  /* v5888（用户口径「孤岛 · Wiki 这前面应该用地图的mdi图标」）：
     图标复用项目统一的服务器地图图标表 LB_SERVER_MDI + 现成 lbMdiSvg()（内联 SVG，不依赖字体）；
     取不到时回退通用 mdi-map（同样走 lbMdiSvg），最后才退回 emoji。 */
  var _icoSvg = '';
  try {
    var _icoName = (typeof LB_SERVER_MDI !== 'undefined' && LB_SERVER_MDI && LB_SERVER_MDI[id]) ? LB_SERVER_MDI[id] : 'mdi-map';
    if (typeof lbMdiSvg === 'function') _icoSvg = lbMdiSvg(_icoName, 15) || '';
  } catch (eIco) { _icoSvg = ''; }
  ttl.innerHTML = (_icoSvg ? ('<span style="display:inline-flex;align-items:center;margin-right:6px;vertical-align:-2px">' + _icoSvg + '</span>') : '📖 ')
    + tcEsc(name) + ' · Wiki';
  if (!LB_MW.data && !LB_MW.err){
    meta.style.display = '';
    lbWikiPanelLoading(ids, null, '首次加载约 4 秒，之后秒开');
    return;
  }
  if (LB_MW.err){
    lbWikiPanelErr(ids, name, '暂无 wiki 资料', 'lbMapWikiReload', lbMapWikiNoSite((LB_MW.err && LB_MW.err.message) || LB_MW.err || ''));
    return;
  }
  var list = [0], i;   // v5898（用户口径「AI模板不算内容？就算没抓到数据 AI模块也应该有」）：概览恒显示——它就是 AI 整理入口，无原文时也必须能进去整理
  /* v5930：基地（索引 7）常驻 —— 正文里的地形图来自本地底图，与后端 blocks 无关，\u201c有底图\u201d即算有内容 */
  for (i = 1; i < LB_MW_TABS.length; i++){ if (lbMapWikiHasKey(i) || (i === 7 && lbMapWikiHasMapImg())) list.push(i); }
  var _mwAny = lbMapWikiHasKey(0) || list.length > 1;
  if (!list.length) list = [0];
  if (list.indexOf(LB_MW.tab) < 0) LB_MW.tab = list[0];
  LB_MW.vlist = list;
  var names = list.map(function(ix){ return LB_MW_TABS[ix][1]; });
  lbWikiPanelTabs(ids, names, list.indexOf(LB_MW.tab), 'lbMapWikiTab');
  /* v5876（用户口径「不要显示来源」）：与物种侧 meta 完全同规则 ——
     正常状态一律清空并隐藏（不显示站点名 / slug / 章节数 / 整理状态）；
     只有完全没有资料时才给一句提示（同物种的「无权威信息，建议AI整理」）。 */
  if (_mwAny){ meta.textContent = ''; meta.style.display = 'none'; }
  else { meta.textContent = '无权威信息，建议AI整理'; meta.style.display = ''; }
  body.innerHTML = lbMapWikiBodyHtml(LB_MW.tab);
  try { lbWikiLayoutFix(); } catch (eLF) {}
  try { if (LB_MW.tab === 7) lbMapWikiTipsDeclash(); } catch (eTD) {}   // v5896：基地点位徽章防重叠
  try { tcSyncNotes('lbWikiBody', 'lbWikiHelp'); } catch (eTN) {}
}

/* AI 整理（lbWtDigest 同款流程；结果全服共享一份，只读缓存、绝不自动重跑） */
function lbMapWikiDigest(){
  if (LB_MW.busy) return;
  var id = LB_MW.cur;
  if (!id) return;
  var cfg = null; try { cfg = lbAiCfgGet(); } catch (e1) {}
  if (!cfg || !cfg.token){
    LB_MW.msg = '请先在「⚙ 配置」里填大肥鱼 token';
    try { if (typeof lbToast === 'function') lbToast(LB_MW.msg); } catch (e2) {}
    try { lbOpenConfigModal(); } catch (e3) {}
    lbWikiRender();
    return;
  }
  /* v5878：把所有素材源一起喂给 AI（中文原文 + 英文原文 + 玩家心得），不是只喂一个源 */
  var parts = [], total = 0;
  lbMapWikiCollectSrc().forEach(function (src) {
    var lab = src[0], bx = src[1] || {};
    LB_MW_TABS.forEach(function (t) {
      var arr = bx[t[0]] || [];
      if (!arr.length) return;
      total += arr.length;
      parts.push('【' + lab + '·' + t[1] + '（' + t[0] + '）】\n'
        + arr.map(function (s, n) { return (n + 1) + '. ' + s; }).join('\n'));
    });
  });
  if (!total){ LB_MW.msg = '该地图没有可整理的原文'; lbWikiRender(); return; }
  var zh = lbMapWikiName(id);
  var SYS = '你是《方舟：生存飞升》(ARK: Survival Ascended) 的地图资料编辑。\n'
    + '下面是一张地图从 wiki（中文站）抓来的全部原文段落，已按章节分好组。\n'
    + '任务：把这些原文**整理归纳后重新分配到同名区块**。\n\n'
    + '硬性要求：\n'
    + '0) **多源合并**：素材按来源分组（中文原文 / 英文原文 / 玩家心得）。'
    + '中文原文是主素材；英文原文与玩家心得里**独有的事实、数字、机制、注意事项必须吸收进来**，'
    + '与中文原文重复的不要另写一条。最终只输出中文，不得残留英文单词或句子。\n'
    + '1) **去重**：同一知识点只保留一处；两段讲同一件事时合并成完整表述。\n'
    + '2) **按内容重新分配**（可以搬走，不必留在原位置）：\n'
    + '   · OVERVIEW（概览）= 地图定位、地形地貌、整体特色、玩法难度\n'
    + '   · BIOME（群系）= 各区域/生物群系的地貌与环境特点\n'
    + '   · RES（资源）= 可采资源、分布区域与采集要点\n'
    + '   · CAVE（洞穴神器）= 洞穴与神器名称、数量、进入条件、风险\n'
    + '   · TIPS（技巧）= 开局与实战建议；**每条写成「小标题：正文」，小标题 ≤10 字**（如「开局选址：…」），一条一个主题\n'
    + '   · BASE（基地位置）= 推荐建家点及坐标\n'
    + '   · LORE（笔记故事）= 探险家笔记与背景故事\n'
    + '   · STATS（数据统计）= 生物/资源/洞穴等数量\n'
    + '3) **措辞**：简体中文、玩家习惯译法；每条 1~3 句；不要 markdown 符号（不要 #、*、-）；\n'
    + '   不要出现「原文」「来源」「wiki」之类字样。\n'
    + '4) **宁缺勿滥**：某区块没有合适内容就返回空数组，绝不硬凑。\n'
    + '5) **细节不丢**：具体数字（坐标、数量、等级、倍率、时长）必须保留。\n'
    + '6) **术语强制中文化（硬性）**：地名、生物群系、生物名、物品名、机制名一律中文；'
    + '除 ASA / PvE / PvP / DPS 这类通用缩写外，正文不得残留英文单词或词组；'
    + '确实无通行译法的写成「中文（原词）」且全文只出现一次。\n'
    + '7) **地图名一律用正式译名（硬性）**：本图正式中文名为「' + zh + '」。\n\n'
    + '输出严格 JSON（不要代码块），键名必须与上面完全一致：\n'
    + '{"OVERVIEW":[],"BIOME":[],"RES":[],"CAVE":[],"CREATURE":[],"BOSS":[],"TIPS":[],"BASE":[],"LORE":[],"STATS":[],'
    + '"BASEPTS":[{"n":"点位中文名","x":0,"y":0}]}\n'
    + '8) **BASEPTS（基地点位中文名，硬性）**：用户消息【基地点位】里每一条都要返回一条 **同名同坐标** 的中文译名，'
    + 'x/y 必须原样照抄（不改数值、不改顺序）；名称是地名/地貌名时按中文玩家习惯译法翻译，不得保留英文。'
    + '没有【基地点位】就返回 []。';
  var _pts = lbMapWikiBasePts();   // v5896：与地图渲染同一份（螰变等 points.BASE 为空时用兜底解析结果喂 AI，AI 才会产出 BASEPTS 中文名）
  var _ptBlock = '';
  if (_pts.length){
    _ptBlock = '【基地点位（坐标为游戏内 x,y）】\n'
      + _pts.map(function (p, n) { return (n + 1) + '. ' + (p.n || '') + ' (' + p.x + ',' + p.y + ')'; }).join('\n') + '\n\n';
  }
  var usr = '地图：' + id + ' ' + zh + '\n\n' + _ptBlock + parts.join('\n\n');
  LB_MW.busy = true; LB_MW.msg = '整理中…'; lbWikiRender();
  fetch(String(cfg.base || LB_AI_BASE).replace(/\/+$/, '') + '/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + cfg.token },
    body: JSON.stringify({
      model: lbAiNormModel(cfg.model),
      messages: [{ role: 'system', content: SYS }, { role: 'user', content: usr }],
      temperature: 0.25, max_tokens: 8000,
      thinking: { type: 'disabled' },
      response_format: { type: 'json_object' }
    })
  }).then(function (r) { return r.text().then(function (tx) { return { s: r.status, t: tx }; }); })
    .then(function (x) {
      if (x.s !== 200){
        LB_MW.busy = false;
        LB_MW.msg = '接口错误 ' + x.s + '：' + String(lbAiErrText(x.s) || '');
        lbWikiRender();
        return;
      }
      var j = null; try { j = JSON.parse(x.t); } catch (eJ) {}
      var ch0 = (j && j.choices && j.choices[0]) ? j.choices[0] : null;
      var m0 = (ch0 && ch0.message) ? ch0.message : null;
      var content = (m0 && m0.content) ? String(m0.content) : '';
      var d = null;
      try { d = lbAiParseJson(content); } catch (eP) {}
      if (!d && m0 && m0.reasoning_content){ try { d = lbAiParseJson(String(m0.reasoning_content)); } catch (eR) {} }
      if (!d || typeof d !== 'object'){
        LB_MW.busy = false; LB_MW.msg = '整理结果无法解析'; lbWikiRender(); return;
      }
      var out = {}, cnt = 0;
      LB_MW_TABS.forEach(function (t) {
        var v = d[t[0]];
        if (!v) return;
        if (!Array.isArray(v)) v = [v];
        var a2 = [];
        v.slice(0, 40).forEach(function (e) {
          var tx = '';
          if (typeof e === 'string') tx = e.trim();
          else if (typeof e === 'number' || typeof e === 'boolean') tx = String(e);
          else if (e && typeof e === 'object'){
            var ks = ['t', 'text', 'point', 'zh', 'desc', 'title', 'name', 'note', 'n', 'd', 'v', 'k', 'a', 'p'];
            for (var q = 0; q < ks.length; q++){ if (typeof e[ks[q]] === 'string' && e[ks[q]].trim()){ tx = e[ks[q]].trim(); break; } }
          }
          if (tx && tx !== '[object Object]' && a2.indexOf(tx) < 0) a2.push(tx);
        });
        if (a2.length){ out[t[0]] = a2; cnt += a2.length; }
      });
      /* v5880：点位中文名（与原文点按顺序对应） */
      try {
        var _src = lbMapWikiBasePts();   // v5897：保存点位中文名时也用同一份（原用 points.BASE，螰变为空 ⇒ 循环 0 次 ⇒ BASEPTS 永不保存）
        var _bpIn = d.BASEPTS;
        var _bpOut = [];
        if (Array.isArray(_bpIn)){
          for (var _i = 0; _i < _bpIn.length && _i < _src.length; _i++){
            var _e = _bpIn[_i];
            var _nm = (_e && typeof _e === 'object') ? String(_e.n || _e.name || '').trim() : String(_e || '').trim();
            if (_nm) _bpOut.push({ n: _nm, x: _src[_i].x, y: _src[_i].y });
          }
        }
        if (_bpOut.length) out.BASEPTS = _bpOut;
      } catch (eBP) {}
      if (!cnt){ LB_MW.busy = false; LB_MW.msg = 'AI 没有返回可用内容'; lbWikiRender(); return; }
      LB_MW.msg = '已整理 ' + cnt + ' 条，正在保存…';
      fetch(LB_MW_API + 'text', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slug: id, blocks: out, force: !!LB_MW.text })
      }).then(function (r) { return r.json(); })
        .then(function (sj) {
          LB_MW.busy = false;
          LB_MW.msg = (sj && sj.ok) ? '已保存' : '保存失败';
          lbMapWikiTextLoad(function(){ try { lbWikiRender(); } catch (e0) {} });
        })
        .catch(function () { LB_MW.busy = false; LB_MW.msg = '保存失败（网络）'; lbWikiRender(); });
    })
    .catch(function (e) {
      LB_MW.busy = false;
      LB_MW.msg = '网络错误：' + String((e && e.message) || e);
      lbWikiRender();
    });
}

// v155（用户口径）：只允许右上角按钮关闭 —— 已移除 ESC 关闭监听
