// ==UserScript==
// @name         Wikily ARK Dino Importer
// @version      8.0
// @match        https://wikily.gg/zh-cn/ark-survival-ascended/profile/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';
    let h = location.hash;
    if (!h.startsWith('#import=')) return;
    let d;
    try { d = JSON.parse(decodeURIComponent(escape(atob(h.substring(8))))); } catch(e) { return; }
    if (!d.blueprint) return;
    history.replaceState(null, '', location.pathname + location.search);

    function btn(t) {
        let b = document.getElementById('wib');
        if (!b) { b = document.createElement('button'); b.id = 'wib';
            b.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:99999;background:linear-gradient(135deg,#7c3aed,#a855f7);color:white;padding:14px 24px;border-radius:12px;border:none;font-size:14px;font-weight:600';
            document.body.appendChild(b); }
        b.textContent = t; return b;
    }

    async function go() {
        btn('\u23f3 Importing...');

        let usePrecalc = d._solver === 'asb' && d.wildLevels && d.domLevels;
        let wildLevels, domLevels;

        if (usePrecalc) {
            wildLevels = d.wildLevels;
            domLevels = d.domLevels;
            btn('\u23f3 ASB precalc...');
        } else {
            btn('\u23f3 Fallback: all dom...');
            wildLevels = {}; domLevels = {};
            let keys = ['health','stamina','oxygen','food','weight','melee_damage_multiplier','torpidity','speed_multiplier'];
            for (let k of keys) { wildLevels[k] = 0; domLevels[k] = 0; }
            if (d.statsByName) {
                for (let k of ['health','stamina','oxygen','food','weight','melee_damage_multiplier']) {
                    let v = d.statsByName[k];
                    if (typeof v === 'number' && v > 10) domLevels[k] = Math.max(0, Math.round(v / 10));
                }
            }
        }

        let TE_pct = d.tamingEffectiveness ? ((d.tamingEffectiveness.min + d.tamingEffectiveness.max) / 2) : 100;
        let payload = {
            species_blueprint: d.blueprint,
            name: d.name || null,
            sex: d.sex || 'female',
            wild_levels: wildLevels,
            dom_levels: domLevels,
            tags: d.tags || [], notes: d.notes || null,
            mutations_maternal: d.matMutations || 0,
            mutations_paternal: d.patMutations || 0,
            mutations: d.mutations || null,
            imprint_bonus: (typeof d.imprintingQuality === 'number') ? d.imprintingQuality / 100 : null,
            tame_effectiveness: TE_pct / 100,
            traits: [], colors: d.colors && d.colors.length > 0 ? d.colors : null
        };

        try {
            let r = await fetch('/api/ark/user-creatures/create/', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (!r.ok) {
                let e = await r.json().catch(function(){ return {}; });
                throw new Error(e.error || 'HTTP ' + r.status);
            }
            let sumW = Object.values(wildLevels).reduce((a,b)=>a+b,0);
            btn('\u2705 Done! (wild=' + (sumW+1) + ')');
            setTimeout(function(){ let x = document.getElementById('wib'); if (x) x.remove(); }, 4000);
            setTimeout(function(){ location.reload(); }, 2000);
        } catch(e) { btn('\u274c ' + e.message); }
    }

    setTimeout(go, 500);
})();
