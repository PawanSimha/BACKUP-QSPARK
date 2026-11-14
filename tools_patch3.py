p = 'src/templates/booking.html'
s = open(p, encoding='utf-8').read()

# add sync JS after updatePreview listeners
anchor = "[dateEl, startEl, durEl].forEach(function (el) { el.addEventListener('change', updatePreview); el.addEventListener('input', updatePreview); });"
sync = '''   var rangeEl = document.getElementById('startRange');
   var durRangeEl = document.getElementById('durRange');
   function fmtTime(mins) {
     var h = Math.floor(mins/60), m = mins%60;
     var ampm = h >= 12 ? 'PM' : 'AM';
     var h12 = h % 12 || 12;
     return String(h12).padStart(2,'0') + ':' + String(m).padStart(2,'0') + ' ' + ampm;
   }
   function syncFromRange() {
     var mins = Number(rangeEl.value);
     var h = Math.floor(mins/60), m = mins%60;
     startEl.value = String(h).padStart(2,'0') + ':' + String(m).padStart(2,'0');
     durEl.value = durRangeEl.value;
     updatePreview();
   }
   if (rangeEl && durRangeEl) {
     rangeEl.addEventListener('input', syncFromRange);
     durRangeEl.addEventListener('input', syncFromRange);
     startEl.addEventListener('input', function () {
       var parts = (startEl.value || '').split(':');
       if (parts.length === 2) { rangeEl.value = Number(parts[0])*60 + Number(parts[1]); syncFromRange(); }
     });
     durEl.addEventListener('change', function () { durRangeEl.value = durEl.value; });
   }
''' + anchor
s = s.replace(anchor, sync, 1)

# add range label updates in updatePreview
old = """     document.getElementById('previewFare').textContent = (w && state.vehicleType)
       ? U.money(w.hours * Number(state.vehicleType.hourly_rate)) : '—';
   }"""
new = """     document.getElementById('previewFare').textContent = (w && state.vehicleType)
       ? U.money(w.hours * Number(state.vehicleType.hourly_rate)) : '—';
     var st = document.getElementById('rangeStartTime');
     var en = document.getElementById('rangeEndTime');
     var th = document.getElementById('rangeTotalHours');
     var ta = document.getElementById('rangeTotalAmount');
     if (st && en && th && ta) {
       st.textContent = w ? w.start.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}) : '—';
       en.textContent = w ? w.end.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}) : '—';
       th.textContent = w ? w.hours + ' HR' : '—';
       ta.textContent = (w && state.vehicleType) ? U.money(w.hours * Number(state.vehicleType.hourly_rate)) : '—';
     }
   }"""
assert old in s
s = s.replace(old, new, 1)

open(p, 'w', encoding='utf-8').write(s)
print('js patched')
