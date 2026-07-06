"""Systematic comparison of base editor image-related functions between v1095 and v1105"""
old = open(r"b:\项目\Hass ASA Server Monitor\bak\asa-admin_backup_20260706_144138.html", encoding="utf-8").read()
new = open(r"b:\项目\Hass ASA Server Monitor\www\asa-admin.html", encoding="utf-8").read()

functions = [
    "selectDeviceIconFromEl",
    "selectDeviceIcon",
    "selectItemIcon",
    "openIconPicker(si, bi, ri, ci, ii)",
    "saveBaseTab",
    "renderBaseRef",
    "addBaseStorageRow",
    "addBaseCat",
    "addBaseItem",
    "clearIconSelection",
    "saveComboDevice",
    "composeIcons",
]

print("=== Function existence check ===")
for fn in functions:
    in_old = fn in old
    in_new = fn in new
    status = "OK" if in_old == in_new else "MISMATCH"
    if not in_old and not in_new:
        status = "ABSENT_BOTH"
    elif in_old and not in_new:
        status = "DELETED"
    elif not in_old and in_new:
        status = "NEW"
    print(f"  {fn:30s} old={in_old} new={in_new} [{status}]")

# Check new functions
new_fns = ["selectBaseIcon", "clearBaseIconSelection", "clearBaseItemIconSelection"]
print("\n=== New functions ===")
for fn in new_fns:
    in_new = fn in new
    print(f"  {fn:30s} exists={in_new}")

# Check key logic sections in saveBaseTab
print("\n=== saveBaseTab row images logic ===")
# Old: images: (ic?.value)?[{image_url:ic.value,quantity:0,image_auto_color_mode:'off',image_native_luminance:null}]:[]
# New: reads from baseData
old_save = old.split("saveBaseTab")[1][:8000] if "saveBaseTab" in old else ""
new_save = new.split("saveBaseTab")[1][:8000] if "saveBaseTab" in new else ""

old_has_hardcoded = "image_auto_color_mode:'off'" in old_save
new_has_hardcoded = "image_auto_color_mode:'off'" in new_save
print(f"  Old hardcoded 'off': {old_has_hardcoded}")
print(f"  New hardcoded 'off': {new_has_hardcoded}")
print(f"  New reads baseData: {'baseData' in new_save}")

# Check renderBaseRef normalization
print("\n=== renderBaseRef normalization ===")
old_norm = "r.device_icon_url = r.images" in old
new_norm = "r.device_icon_url = r.images" in new
old_mode_norm = "_dev_icon_mode" in old
new_mode_norm = "_dev_icon_mode" in new
print(f"  Old URL normalize: {old_norm}")
print(f"  New URL normalize: {new_norm}")
print(f"  Old mode normalize: {old_mode_norm}")
print(f"  New mode normalize: {new_mode_norm}")

# Check onclick patterns in renderBaseRef
print("\n=== renderBaseRef onclick patterns ===")
for pattern in ["openIconPicker(si,bi,ri)", "openIconPicker({mode:", "openIconPicker_ic", "openIconPicker_desc", "selectDeviceIcon"]:
    old_cnt = old.count(pattern)
    new_cnt = new.count(pattern)
    if old_cnt != new_cnt:
        print(f"  {pattern:40s} old={old_cnt} new={new_cnt} [DIFF]")
