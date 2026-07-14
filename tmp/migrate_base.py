"""
Phase 2.1: 部落基地数据结构迁移
旧格式: {servers: {serverId: {tabs: [{sections: [{content_blocks: [base_*]}]}]}}}
新格式: {tabs: [{name, type: "mixed_content", content_blocks: [info_card, divider, map_filter]}]}

策略: 
- 每个 server → 一个 tab（合并所有 section）
- section.name → divider block
- base_* → info_card（保留数据结构以便后续手动填充）
"""
import json, os, copy

SRC = r'B:\项目\Hass ASA Server Monitor\bak\asa_20260714_182557\asa_base_quick_ref.json'
DST = r'B:\项目\Hass ASA Server Monitor\tmp\asa_base_quick_ref_new.json'
BAK = SRC + '.pre_phase2'

# Backup original
import shutil
shutil.copy2(SRC, BAK)
print(f'Backup: {BAK}')

data = json.load(open(SRC, encoding='utf-8'))
servers = data.get('servers', {})

# Server name mapping
SERVER_NAMES = {
    'Isl': '孤岛', 'Sco': '焦土', 'Cen': '核心岛', 'Abe': '畸变',
    'Ext': '灭绝', 'Ast': '繁星', 'Rag': '仙境', 'Val': '瓦尔盖罗',
    'Bob': '俱乐部', 'Los': '失落地', 'Gen': '创世模拟', '*': '通用'
}

new_tabs = []

for sid, sv in servers.items():
    old_tabs = sv.get('tabs', [])
    if not old_tabs:
        continue
    
    server_name = SERVER_NAMES.get(sid, sid)
    
    for ti, old_tab in enumerate(old_tabs):
        tab_name = old_tab.get('name', f'{server_name}基地')
        sections = old_tab.get('sections', [])
        
        new_blocks = []
        
        # Add map_filter block for server context
        new_blocks.append({
            "block_type": "map_filter",
            "highlight": sid
        })
        
        for si, sec in enumerate(sections):
            sec_name = sec.get('name', f'分区{si+1}')
            old_blocks = sec.get('content_blocks', [])
            
            # Section name → divider
            if sec_name:
                new_blocks.append({
                    "block_type": "divider",
                    "title": sec_name
                })
            
            for bi, old_block in enumerate(old_blocks):
                bt = old_block.get('block_type', '')
                
                if bt == 'base_storage':
                    # Convert storage rows to info_card blocks
                    for ri, row in enumerate(old_block.get('rows', [])):
                        descriptions = []
                        
                        # Capacity
                        cap_main = row.get('capacity_main', '')
                        cap_sub = row.get('capacity_sub', '')
                        if cap_main or cap_sub:
                            descriptions.append({
                                "text": f"容量: {cap_main}/{cap_sub}" if cap_sub else f"容量: {cap_main}",
                                "bold": True
                            })
                        
                        # Actions as icon_group
                        actions = row.get('actions', [])
                        if actions:
                            icons = []
                            for act in actions:
                                icons.append({"image_url": "", "label": act})
                            descriptions.append({
                                "type": "icon_group",
                                "title": "行动",
                                "icons": icons
                            })
                        
                        # Categories
                        for ci, cat in enumerate(row.get('categories', [])):
                            cat_name = cat.get('name', '')
                            cat_color = cat.get('color', '')
                            cat_bold = cat.get('bold')
                            
                            if cat_name and cat_bold:
                                badge_text = f"[{cat_name}]"
                                descriptions.append({"text": badge_text, "color": cat_color or ''})
                            elif cat_name:
                                descriptions.append({"text": cat_name, "color": cat_color or ''})
                            
                            # Category items as icon_group
                            items = cat.get('items', [])
                            if items:
                                icons = []
                                for item in items:
                                    icons.append({
                                        "image_url": item.get('icon_url', ''),
                                        "label": item.get('name', '')
                                    })
                                descriptions.append({
                                    "type": "icon_group",
                                    "title": cat_name,
                                    "icons": icons
                                })
                        
                        info_card = {
                            "block_type": "info_card",
                            "title": row.get('device_name', '') or f"存储设备 {ri+1}",
                            "images": [{}],
                            "descriptions": descriptions,
                            "server_states": {sid: 2} if sid != '*' else {},
                            "fold": True if len(descriptions) > 2 else False
                        }
                        
                        # Device icon
                        icon_url = row.get('device_icon_url', '')
                        if icon_url:
                            info_card["images"].append({
                                "image_url": icon_url,
                                "image_auto_color_mode": "off"
                            })
                        
                        new_blocks.append(info_card)
                
                elif bt == 'base_device':
                    new_blocks.append({
                        "block_type": "info_card",
                        "title": old_block.get('name', '') or '设备',
                        "images": [{}],
                        "descriptions": [],
                        "server_states": {sid: 2} if sid != '*' else {},
                        "fold": False
                    })
                
                elif bt == 'base_other_device':
                    new_blocks.append({
                        "block_type": "info_card",
                        "title": old_block.get('name', '') or '其他设备',
                        "images": [{}],
                        "descriptions": [],
                        "server_states": {sid: 2} if sid != '*' else {},
                        "fold": False
                    })
                
                elif bt == 'base_creature':
                    new_blocks.append({
                        "block_type": "info_card",
                        "title": old_block.get('name', '') or '生物',
                        "images": [{}],
                        "descriptions": [],
                        "server_states": {sid: 2} if sid != '*' else {},
                        "fold": False
                    })
                
                elif bt == 'base_other_creature':
                    new_blocks.append({
                        "block_type": "info_card",
                        "title": old_block.get('name', '') or '其他生物',
                        "images": [{}],
                        "descriptions": [],
                        "server_states": {sid: 2} if sid != '*' else {},
                        "fold": False
                    })
                
                elif bt == 'base_badge':
                    new_blocks.append({
                        "block_type": "info_card",
                        "title": old_block.get('name', '') or '徽章',
                        "images": [{}],
                        "descriptions": [],
                        "server_states": {sid: 2} if sid != '*' else {},
                        "fold": False
                    })
        
        # Only add tab if it has content
        if len(new_blocks) > 1:  # >1 because map_filter is always added
            new_tabs.append({
                "name": f"{server_name}-{tab_name}" if len(old_tabs) > 1 else f"{server_name}基地",
                "type": "mixed_content",
                "content_blocks": new_blocks
            })

# Build new structure
new_data = {"tabs": new_tabs}

# Save
with open(DST, 'w', encoding='utf-8') as f:
    json.dump(new_data, f, ensure_ascii=False, indent=2)

print(f'\nOutput: {DST}')
print(f'Old tabs: {sum(len(sv.get("tabs",[])) for sv in servers.values())}')
print(f'New tabs: {len(new_tabs)}')
print(f'Old file: {os.path.getsize(SRC)}B')
print(f'New file: {os.path.getsize(DST)}B')
