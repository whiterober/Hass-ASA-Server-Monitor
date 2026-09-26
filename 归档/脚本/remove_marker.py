"""Remove brCatMarker ■, show_marker, and ■ from buildStorageBody"""
import re

with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'rb') as f:
    c = f.read()

changes = 0
square = b'\xe2\x96\xa0'

# ============================================================
# 1. Render template: remove brCatMarker label line
# ============================================================
# Line: html += '<label style="..."><input type="checkbox" id="brCatMarker...'+(cat.show_marker?...)+'>■</label>';
# Find exact pattern
idx1 = c.find(b"id=\\brCatMarker'+si+'_'+bi+'_'+ri+'_'+ci+'\\\" '+(cat.show_marker?'checked':'')+'>")
if idx1 > 0:
    # Find start of this line (html += '<label)
    line_start = c.rfind(b'\n', 0, idx1) + 1
    # Find end of line
    line_end = c.find(b'\n', idx1)
    # Confirm it contains ■
    if square in c[line_start:line_end]:
        c = c[:line_start] + c[line_end+1:]  # remove the line
        changes += 1
        print('1. Render template: brCatMarker label removed')
    else:
        print('1. ■ not in line')
else:
    print('1. NOT FOUND')

# ============================================================
# 2. Render template: remove brCatMarkerColor select line
# ============================================================
idx2 = c.find(b"id=\\brCatMarkerColor'+si+'_'+bi+'_'+ri+'_'+ci+'\\\"")
if idx2 > 0:
    line_start = c.rfind(b'\n', 0, idx2) + 1
    line_end = c.find(b'\n', idx2)
    c = c[:line_start] + c[line_end+1:]
    changes += 1
    print('2. Render template: brCatMarkerColor select removed')
else:
    print('2. NOT FOUND')

# ============================================================
# 3. addStorageCat: remove brCatMarker label line
# ============================================================
# Find second occurrence (after addStorageCat function)
pos_ac = c.find(b'function addStorageCat')
idx3 = c.find(b"id=\\brCatMarker'+si+'_'+bi+'_'+ri+'_'+ci+'\\\">", pos_ac)
if idx3 > 0:
    line_start = c.rfind(b'\n', 0, idx3) + 1
    line_end = c.find(b'\n', idx3)
    if square in c[line_start:line_end] or b'brCatMarker' in c[line_start:line_end]:
        c = c[:line_start] + c[line_end+1:]
        changes += 1
        print('3. addStorageCat: brCatMarker label removed')
    else:
        print('3. ■ not in addStorageCat line')
else:
    print('3. NOT FOUND')

# ============================================================
# 4. addStorageCat: remove brCatMarkerColor select line
# ============================================================
idx4 = c.find(b"id=\\brCatMarkerColor'+si+'_'+bi+'_'+ri+'_'+ci+'\\\"", pos_ac)
if idx4 > 0:
    line_start = c.rfind(b'\n', 0, idx4) + 1
    line_end = c.find(b'\n', idx4)
    c = c[:line_start] + c[line_end+1:]
    changes += 1
    print('4. addStorageCat: brCatMarkerColor select removed')
else:
    print('4. NOT FOUND')

# ============================================================
# 5. saveBaseTab: remove mkEl line (var mkEl = catDiv.querySelector...)
# ============================================================
idx5 = c.find(b"var mkEl = catDiv.querySelector('[id^=brCatMarker]');")
if idx5 > 0:
    line_end = c.find(b'\n', idx5)
    c = c[:idx5] + c[line_end+1:]
    changes += 1
    print('5. saveBaseTab: mkEl line removed')
else:
    print('5. NOT FOUND')

# ============================================================
# 6. saveBaseTab: remove show_marker from cats.push
# ============================================================
# Pattern: show_marker: mkEl?.checked||false,
old6 = b'show_marker: mkEl?.checked||false, '
if old6 in c:
    c = c.replace(old6, b'')
    changes += 1
    print('6. saveBaseTab: show_marker removed from cats.push')
else:
    print('6. NOT FOUND')

# ============================================================
# 7. buildStorageBody: remove ■ from rendering
# ============================================================
# The buildStorageBody has two ■ rendering paths. Need to simplify.
# Find the block that renders show_marker with ■

# Path A: if (cat.show_marker && cat.marker_color && cm[cat.marker_color])
# Path B: else if (lc && cm[lc])
# Path C: else (no ■)

# Replace the entire conditional with just the label rendering (no ■)

# Find the start of show_marker condition
idx7 = c.find(b'if (cat.show_marker && cat.marker_color && cm[cat.marker_color]) {')
if idx7 > 0:
    # Find the closing of this entire if/else block
    # It ends with: h += '<div>'+cat.label+'</div>';
    end_marker = c.find(b"h += '<div>'+cat.label+'</div>';", idx7)
    if end_marker > 0:
        # The new code: just render label
        new_code = b"""if (lb) {
            h += '<div><span class=\"text-bold\">'+cat.label+'</span></div>';
          } else {
            h += '<div>'+cat.label+'</div>';
          }"""
        # Find the start of this block more precisely
        # Look for: // Category label with optional marker
        block_start = c.rfind(b'\n', 0, idx7) - 50
        # Actually let me find the // comment
        comment_pos = c.rfind(b'//', block_start, idx7)
        if comment_pos > 0:
            block_start = c.rfind(b'\n', 0, comment_pos) + 1
        c = c[:block_start] + new_code + b'\n' + c[end_marker + len(b"h += '<div>'+cat.label+'</div>';") + 1:]
        changes += 1
        print('7. buildStorageBody: ■ rendering removed, simplified to label only')
    else:
        print('7. end_marker NOT FOUND')
else:
    print('7. show_marker block NOT FOUND')

# ============================================================
# 8. enhanceBlockCollapse: remove marker creation
# ============================================================
# Remove the lines that create brCatMarker and brCatMarkerColor
idx8 = c.find(b"var mkId = el.id.replace('brCatLabel','brCatMarker');")
if idx8 > 0:
    # Find the end of marker-related code (before next section)
    # Search for the end of the block that creates marker label
    end8 = c.find(b"var bqId = el.id.replace('brCatLabel','brCatBQ');", idx8)
    if end8 > 0:
        c = c[:idx8] + c[end8:]
        changes += 1
        print('8. enhanceBlockCollapse: marker creation removed')
    else:
        # Alternative end marker
        end8 = c.find(b"var colEl = document.getElementById", idx8)
        if end8 > 0:
            c = c[:idx8] + c[end8:]
            changes += 1
            print('8. enhanceBlockCollapse: marker creation removed (alt)')
        else:
            print('8. end8 NOT FOUND')
else:
    print('8. mkId NOT FOUND')

# ============================================================
# 9. reorderCatCard: remove brCatMarker from order array
# ============================================================
old9 = b'"brCatMarker","brCatMarkerColor",'
if old9 in c:
    c = c.replace(old9, b'')
    changes += 1
    print('9. reorderCatCard: marker removed from order')
else:
    print('9. NOT FOUND')

# ============================================================
# 10. toggleBQControls: remove marker visibility
# ============================================================
old10a = b"var mkEl = card.querySelector('[id^=brCatMarker]');\n  if (mkEl) { "
if old10a in c:
    # Find full marker block
    idx10 = c.find(old10a)
    # Find end of marker block: ...style.visibility = show; }
    end10 = c.find(b"style.visibility = show; }\n  var mcEl = card.querySelector('[id^=brCatMarkerColor]');", idx10)
    if end10 > 0:
        end10 = c.find(b'\n', end10) + 1  # end of mcEl line
        c = c[:idx10] + c[end10:]
        changes += 1
        print('10. toggleBQControls: marker visibility removed')
    else:
        print('10. end10 NOT FOUND')
else:
    print('10. NOT FOUND — may have been partly removed')
    # Try partial
    idx10b = c.find(b"var mkEl = card.querySelector('[id^=brCatMarker]')")
    if idx10b > 0:
        print(f'   Found at {idx10b}: {c[idx10b:idx10b+200]!r}')

with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'wb') as f:
    f.write(c)
print(f'\nTotal changes: {changes}')
