import io, re
p = 'src/templates/booking.html'
s = open(p, encoding='utf-8').read()

old = '''          <label class="label" for="durationHours">Duration</label>
          <select class="select" id="durationHours" aria-describedby="scheduleError">
            <option value="1">1 hour</option>
            <option value="2" selected>2 hours</option>
            <option value="3">3 hours</option>
            <option value="4">4 hours</option>
            <option value="6">6 hours</option>
            <option value="8">8 hours</option>
            <option value="12">12 hours</option>
          </select>
        </div>'''
new = '''          <label class="label" for="durationHours">Duration</label>
          <select class="select" id="durationHours" aria-describedby="scheduleError">
            <option value="1">1 hour</option>
            <option value="2" selected>2 hours</option>
            <option value="3">3 hours</option>
            <option value="4">4 hours</option>
            <option value="6">6 hours</option>
            <option value="8">8 hours</option>
            <option value="12">12 hours</option>
          </select>
        </div>
      </div>
      <div class="rounded-lg border p-3" style="border-color:var(--border);margin-top:0.75rem">
        <div class="flex items-center justify-between text-sm mb-1">
          <span class="font-semibold" id="rangeStartLabel">05:00 AM</span>
          <span class="font-semibold" id="rangeEndLabel">11:00 PM</span>
        </div>
        <input type="range" id="startRange" min="300" max="1380" step="15" value="540" style="width:100%">
        <input type="range" id="durRange" min="1" max="18" step="1" value="2" style="width:100%">
        <div class="grid mt-2" style="grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:0.75rem">
          <div><div class="text-xs text-muted">START TIME</div><div class="font-semibold" id="rangeStartTime">—</div></div>
          <div><div class="text-xs text-muted">END TIME</div><div class="font-semibold" id="rangeEndTime">—</div></div>
          <div><div class="text-xs text-muted">TOTAL HOURS</div><div class="font-semibold" id="rangeTotalHours">—</div></div>
          <div><div class="text-xs text-muted">TOTAL AMOUNT</div><div class="font-semibold" id="rangeTotalAmount">—</div></div>
        </div>
      </div>'''
assert old in s, 'HTML block not found'
s = s.replace(old, new, 1)

# sync JS: insert before the existing listeners line
old2 = ''' [dateEl, startEl, durEl].forEach(function (el) { el.addEventListener('change', updatePreview); el.addEventListener('input', updatePreview); });'''
new2 = '''   var rangeEl = document.getElementById('startRange');
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
     document.getElementById('rangeStartLabel').textContent = fmtTime(300);
     document.getElementById('rangeEndLabel').textContent = fmtTime(1380);
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
 [dateEl, startEl, durEl].forEach(function (el) { el.addEventListener('change', updatePreview); el.addEventListener('input', updatePreview); });'''
assert old2 in s, 'JS anchor not found'
s = s.replace(old2, new2, 1)

# update labels in updatePreview
old3 = '''   function updatePreview() {
     var w = currentWindow();
     document.getElementById('previewStart').textContent = w ? w.start.toLocaleString() : '—';
     document.getElementById('previewEnd').textContent = w ? w.end.toLocaleString() : '—';
     document.getElementById('previewFare').textContent = (w && state.vehicleType)
       ? U.money(w.hours * Number(state.vehicleType.hourly_rate)) : '—';
   }'''
new3 = '''   function updatePreview() {
     var w = currentWindow();
     document.getElementById('previewStart').textContent = w ? w.start.toLocaleString() : '—';
     document.getElementById('previewEnd').textContent = w ? w.end.toLocaleString() : '—';
     document.getElementById('previewFare').textContent = (w && state.vehicleType)
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
   }'''
assert old3 in s, 'updatePreview not found'
s = s.replace(old3, new3, 1)

open(p, 'w', encoding='utf-8').write(s)
print('patched')
