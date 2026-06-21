N = bytes([13, 10])
with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'rb') as f:
    c = f.read()

# Find the broken addEventListener (without if guard)
marker = b"document.addEventListener('click', function(e){" + N + b"      if (!e.target.closest('.cat-input-wrap')) {"
idx = c.find(marker)
if idx > 0:
    # Find end of this broken block
    end1 = c.find(b'});' + N + b'  }', idx)
    if end1 > 0:
        end1 += len(b'});' + N + b'  }')
        fixed = (
            b'if (!document.body.dataset.popupCloser) {' + N +
            b"    document.body.dataset.popupCloser = '1';" + N +
            b"    document.addEventListener('click', function(e){" + N +
            b"      if (!e.target.closest('.cat-input-wrap')) {" + N +
            b"        document.querySelectorAll('.cat-bc-popup.show').forEach(function(p){ p.classList.remove('show'); });" + N +
            b"      }" + N +
            b"      if (!e.target.closest('.cat-color-dot') && !e.target.closest('.cat-color-popup')) {" + N +
            b"        var cp = document.getElementById('catColorPopup');" + N +
            b"        if (cp) cp.classList.remove('show');" + N +
            b"      }" + N +
            b"    });" + N +
            b"  }"
        )
        c = c[:idx] + fixed + c[end1:]
        print('Fixed')
    else:
        print('end1 not found')
else:
    print('marker not found')

print('Braces:', c.count(b'{'), c.count(b'}'))
with open(r'B:\项目\Hass ASA Server Monitor\www\asa-admin.html', 'wb') as f:
    f.write(c)
