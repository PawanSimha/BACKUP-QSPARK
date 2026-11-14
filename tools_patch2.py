p = 'src/templates/booking.html'
lines = open(p, encoding='utf-8').read().splitlines(keepends=True)
i = [n for n, l in enumerate(lines) if 'for="durationHours"' in l][0]
j = [n for n, l in enumerate(lines) if '</select>' in l and n > i][0]
new = '''      <div class="rounded-lg border p-3" style="border-color:var(--border);margin-top:0.75rem">
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
      </div>
'''
lines.insert(j + 1, new)
open(p, 'w', encoding='utf-8').write(''.join(lines))
print('html inserted')
