with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'r', encoding='utf-8') as f:
    c = f.read()

# Find and merge the marker row into header div for BOTH render and addStorageCat

# Pattern for render template:
# 1. Find: html += '</div>'; (header close) → delete
# 2. Find: // Marker + style row comment + html += '<div style=... (marker open) → delete
# 3. Find: html += '</div>'; (marker close, after B label) → replace with header close
# This effectively moves ■/color/B into the header div

# Find the header close before marker
old1 = "html += '</div>';\n\n\n                // Marker + style row\n\n                html += '<div style=\"display:flex;align-items:center;gap:4px;margin-bottom:2px;flex-wrap:nowrap\">';"
new1 = ''
c = c.replace(old1, new1)
print('Step 1:', old1 not in c)

# Now find the marker close after B label and replace with header close + items div
# The marker close is: html += '</div>'; followed by items section
old2 = "html += '</div>';\n\n                html += '<div class=\"sr-items\""
new2 = "html += '</div>';\n\n                html += '<div class=\"sr-items\""
# Actually, the marker close needs to become the header close
# Let me find the specific pattern after brCatBold
idx = c.find('brCatBold')
if idx > 0:
    # Find the first html += '</div>'; after brCatBold
    close_idx = c.find("html += '</div>';", idx)
    if close_idx > 0 and (close_idx - idx) < 300:
        # This should be the marker close - keep it (it now closes the header div)
        print('Marker close found at', close_idx, '- keeping as header close')
    else:
        print('Marker close not found near B label')

# Now also fix toggleBQControls - no more second div to hide
# The function currently targets ':scope > div:nth-child(2)'
# After merge, there's no second div. Just hide label + colorInput.
old_toggle = "var markerRow = card.querySelector(':scope > div:nth-child(2)');\n  var colorInput = card.querySelector('[id^=brCatColor]');\n  if (labelEl) labelEl.style.visibility = show;\n  if (markerRow && !markerRow.classList.contains('sr-items')) markerRow.style.visibility = show;\n  if (colorInput) colorInput.style.visibility = show;"
new_toggle = "var colorInput = card.querySelector('[id^=brCatColor]');\n  if (labelEl) labelEl.style.visibility = show;\n  if (colorInput) colorInput.style.visibility = show;"
c = c.replace(old_toggle, new_toggle)
print('Toggle fixed:', new_toggle in c)

# Also do the same for addStorageCat version
# Find the second occurrence
# For addStorageCat, the pattern is similar but without the comment

with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'w', encoding='utf-8') as f:
    f.write(c)
print('Done')
