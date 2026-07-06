fp = r"b:\项目\Hass ASA Server Monitor\www\asa-admin.html"
with open(fp, "r", encoding="utf-8") as f:
    c = f.read()

# Find selectBaseIcon function
start = c.find("function selectBaseIcon(item, ctx) {")
end_marker = "function clearBaseIconSelection(el) {"
end = c.find(end_marker)

if start < 0 or end < 0:
    print("ERROR: cannot find selectBaseIcon")
    exit(1)

new_fn = '''function selectBaseIcon(item, ctx) {
  var url = item.getAttribute("data-url") || "";
  if (!url) return;
  var colorBtnId = ICON_DISPATCH[ctx.mode].colorBtnId(ctx);
  var modeBtn = colorBtnId ? document.getElementById(colorBtnId) : null;
  var mode = modeBtn ? modeBtn.getAttribute("data-mode") || "off" : "off";
  var isRev = (mode === "reverse");

  // Write URL to hidden input
  var isRow = ctx.mode === "base_row";
  var inputId = isRow
    ? "brSRIcon" + ctx.si + "_" + ctx.bi + "_" + ctx.ri
    : "brItemIcon" + ctx.si + "_" + ctx.bi + "_" + ctx.ri + "_" + ctx.ci + "_" + ctx.ii;
  var inputEl = document.getElementById(inputId);
  if (inputEl) inputEl.value = url;

  // Update visual with SPAN wrapper (for blue dot ::after CSS)
  var parent = inputEl ? inputEl.parentElement : null;
  var img = null;
  if (parent) {
    var existingImg = parent.querySelector("img[onclick*='openIconPicker']");
    if (existingImg) { existingImg.src = url; existingImg.style.display = ""; img = existingImg; }
    else {
      var wrapper = document.createElement("span");
      wrapper.style.cssText = "position:relative;display:inline-flex;flex-shrink:0";
      var newImg = document.createElement("img");
      newImg.src = url; newImg.style.cssText = "width:28px;height:28px;object-fit:contain;cursor:pointer;flex-shrink:0";
      newImg.setAttribute("onclick", "event.stopPropagation();openIconPicker(" + JSON.stringify(ctx) + ")");
      newImg.title = "\\u70b9\\u51fb\\u6362\\u56fe\\u6807"; newImg.onerror = function(){ this.hidden = true; };
      wrapper.appendChild(newImg);
      if (inputEl) inputEl.after(wrapper);
      img = newImg;
    }
  }

  // Write to baseData
  try {
    var srv = baseData.servers[brSelectedServer];
    var tab = (srv.tabs || [])[brSelectedTab];
    if (tab && tab.sections && tab.sections[ctx.si] && tab.sections[ctx.si].content_blocks && tab.sections[ctx.si].content_blocks[ctx.bi]) {
      var blk = tab.sections[ctx.si].content_blocks[ctx.bi];
      if (blk.rows && blk.rows[ctx.ri]) {
        var row = blk.rows[ctx.ri];
        if (isRow) {
          row.images = [{ image_url: url, quantity: 0, image_auto_color_mode: mode, image_native_luminance: null }];
        } else {
          var cat = (row.categories || [])[ctx.ci];
          if (cat && cat.items && cat.items[ctx.ii]) {
            cat.items[ctx.ii].icon_url = url;
            cat.items[ctx.ii].images = [{ image_url: url, quantity: 0, image_auto_color_mode: mode, image_native_luminance: null }];
          }
        }
      }
    }
  } catch(e) { console.error("selectBaseIcon baseData write failed:", e); }

  // Wrapper class management (align with selectInfoCardIcon)
  if (img) {
    var w = img.parentElement;
    if (w && w.tagName === "SPAN") {
      w.classList.remove("ic-mode-normal", "ic-mode-reverse", "ic-mode-failed");
      if (mode === "normal") w.classList.add("ic-mode-normal");
      else if (mode === "reverse") w.classList.add("ic-mode-reverse");
      applyAutoColorClass(img, null);
      w.classList.remove("ic-auto-dark", "ic-auto-light", "ic-auto-color");
    }
  }

  // Brightness detection (align with selectInfoCardIcon)
  if (mode !== "off" && url && img) {
    _pendingBrightnessChecks++;
    _updateSaveBtnState();
    var _ctx = ctx;
    detectImageBrightness(url, function(luminance, errMsg) {
      _pendingBrightnessChecks--;
      if (luminance >= 0) {
        applyAutoColorClassWithLum(img, isRev ? (1 - luminance) : luminance);
        var w2 = img.parentElement;
        if (w2 && w2.tagName === "SPAN") {
          w2.classList.remove("ic-auto-dark", "ic-auto-light", "ic-auto-color");
          var ic = img.className.match(/ic-auto-(light|dark|color)/);
          if (ic) w2.classList.add(ic[0]);
          w2.classList.add("ic-mode-normal");
          w2.setAttribute("data-lum", luminance.toFixed(3));
        }
        try {
          var s2 = baseData.servers[brSelectedServer];
          var t2 = (s2.tabs || [])[brSelectedTab];
          var b2 = t2.sections[_ctx.si].content_blocks[_ctx.bi];
          var r2 = b2.rows[_ctx.ri];
          if (isRow) {
            if (r2.images && r2.images[0]) r2.images[0].image_native_luminance = luminance;
          } else {
            var c2 = (r2.categories || [])[_ctx.ci];
            if (c2 && c2.items && c2.items[_ctx.ii] && c2.items[_ctx.ii].images && c2.items[_ctx.ii].images[0]) {
              c2.items[_ctx.ii].images[0].image_native_luminance = luminance;
            }
          }
        } catch(e) {}
        _detectToast(true, luminance.toFixed(3));
      } else {
        if (errMsg) {
          if (img.parentElement && img.parentElement.tagName === "SPAN") {
            img.parentElement.classList.add("ic-mode-failed");
            img.parentElement.setAttribute("data-failed", errMsg);
          }
        }
        _detectToast(false, errMsg || "\\u7f51\\u7edc\\u9519\\u8bef\\u6216\\u56fe\\u7247\\u65e0\\u6cd5\\u8bbf\\u95ee");
      }
      _updateSaveBtnState();
      renderBaseRef();
    });
  }

  // Close overlay
  var overlay = item.closest(".icon-picker-overlay");
  if (overlay) overlay.remove();

  renderBaseRef();
  setTimeout(showPreview, 200);
}

'''

c = c[:start] + new_fn + c[end:]
print("selectBaseIcon rewritten")

with open(fp, "w", encoding="utf-8") as f:
    f.write(c)
print(f"DONE. {len(c)} bytes")
