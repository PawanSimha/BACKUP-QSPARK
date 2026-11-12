/* QSPARK core UI helpers: formatting, toasts, confirm dialogs, small DOM utils. */
(function (global) {
  'use strict';

  function esc(value) {
    return String(value === null || value === undefined ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function money(value) {
    const n = Number(value || 0);
    return '₹' + n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function parseDate(value) {
    if (!value) return null;
    const d = new Date(String(value).replace(' ', 'T'));
    return isNaN(d.getTime()) ? null : d;
  }

  function dateTime(value) {
    const d = parseDate(value);
    if (!d) return '—';
    return d.toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: true });
  }

  function dateOnly(value) {
    const d = parseDate(value);
    return d ? d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—';
  }

  function debounce(fn, wait) {
    let t;
    return function () {
      const args = arguments, ctx = this;
      clearTimeout(t);
      t = setTimeout(() => fn.apply(ctx, args), wait || 250);
    };
  }

  function toast(message, type) {
    const region = document.getElementById('toastRegion');
    if (!region) return;
    const tone = type === 'error' ? 'border-red-200 bg-red-50 text-red-800'
      : type === 'warning' ? 'border-amber-200 bg-amber-50 text-amber-900'
      : 'border-emerald-200 bg-emerald-50 text-emerald-900';
    const el = document.createElement('div');
    el.className = 'pointer-events-auto w-full max-w-sm rounded-lg border px-4 py-3 text-sm shadow-lg ' + tone;
    el.setAttribute('role', type === 'error' ? 'alert' : 'status');
    el.textContent = message;
    region.appendChild(el);
    setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity .3s'; }, 4200);
    setTimeout(() => el.remove(), 4600);
  }

  function confirmDialog(opts) {
    const dlg = document.getElementById('appDialog');
    if (!dlg || typeof dlg.showModal !== 'function') {
      return Promise.resolve(window.confirm(opts.message || 'Are you sure?'));
    }
    document.getElementById('appDialogTitle').textContent = opts.title || 'Please confirm';
    document.getElementById('appDialogMessage').textContent = opts.message || '';
    const ok = document.getElementById('appDialogOk');
    ok.textContent = opts.confirmLabel || 'Confirm';
    ok.className = 'btn ' + (opts.danger ? 'btn-danger' : 'btn-primary');
    return new Promise((resolve) => {
      function done(value) {
        dlg.removeEventListener('close', onClose);
        ok.removeEventListener('click', onOk);
        resolve(value);
      }
      function onOk() { done(true); dlg.close(); }
      function onClose() { done(dlg.returnValue === 'ok'); }
      ok.addEventListener('click', onOk);
      dlg.addEventListener('close', onClose);
      dlg.showModal();
    });
  }

  function setBusy(button, busy, busyLabel) {
    if (!button) return;
    if (busy) {
      button.dataset.label = button.textContent;
      button.disabled = true;
      button.textContent = busyLabel || 'Working…';
    } else {
      button.disabled = false;
      if (button.dataset.label) button.textContent = button.dataset.label;
    }
  }

  function statusBadge(status) {
    const map = {
      HELD: 'badge badge-amber', CONFIRMED: 'badge badge-blue', COMPLETED: 'badge badge-green',
      CANCELLED: 'badge badge-slate', EXPIRED: 'badge badge-slate',
      ACTIVE: 'badge badge-green', ADMIN_RESERVED: 'badge badge-amber', MAINTENANCE: 'badge badge-slate',
      INACTIVE: 'badge badge-slate', OPEN: 'badge badge-green', CLOSED: 'badge badge-slate',
      BLOCKED: 'badge badge-red', DELETED: 'badge badge-slate', PENDING: 'badge badge-amber',
      AVAILABLE: 'badge badge-green', RESERVED: 'badge badge-amber', OCCUPIED: 'badge badge-red',
    };
    return '<span class="' + (map[status] || 'badge badge-slate') + '">' + esc(status || '') + '</span>';
  }

  function emptyRow(cols, message) {
    return '<tr><td colspan="' + cols + '" class="px-4 py-10 text-center text-sm text-slate-500">' + esc(message) + '</td></tr>';
  }

  global.QSUI = { esc, money, dateTime, dateOnly, parseDate, debounce, toast, confirmDialog, setBusy, statusBadge, emptyRow };
})(window);
