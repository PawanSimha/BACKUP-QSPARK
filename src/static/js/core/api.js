/* QSPARK core: central API client. Session-cookie auth; JSON in, JSON out. */
(function (global) {
  'use strict';

  function redirectToLogin() {
    if (location.pathname !== '/login') {
      location.href = '/login?error=session_expired';
    }
  }

  function csrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  async function request(url, options) {
    const opts = Object.assign({ method: 'GET', credentials: 'same-origin' }, options || {});
    let body = opts.body;
    const headers = Object.assign({ Accept: 'application/json' }, opts.headers || {});

    const method = (opts.method || 'GET').toUpperCase();
    if (method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS') {
      headers['X-CSRFToken'] = csrfToken();
    }

    if (body instanceof FormData) {
      // let the browser set the multipart boundary
      delete headers['Content-Type'];
    } else if (body !== undefined && body !== null) {
      headers['Content-Type'] = 'application/json';
      body = JSON.stringify(body);
    }
    opts.headers = headers;
    opts.body = body;

    let res;
    try {
      res = await fetch(url, opts);
    } catch (err) {
      const e = new Error('Network unavailable. Check your connection and try again.');
      e.status = 0;
      e.network = true;
      throw e;
    }

    if (res.status === 401) {
      redirectToLogin();
      const e = new Error('Your session has expired. Please sign in again.');
      e.status = 401;
      throw e;
    }

    const ctype = res.headers.get('content-type') || '';
    let payload = null;
    if (ctype.indexOf('application/json') !== -1) {
      try { payload = await res.json(); } catch (_) { payload = null; }
    } else if (opts.raw) {
      payload = await res;
    } else {
      payload = await res.text();
    }

    if (!res.ok) {
      const message = (payload && (payload.error || payload.message)) || 'Request failed (' + res.status + ')';
      const e = new Error(message);
      e.status = res.status;
      e.payload = payload;
      if (res.status >= 500 && !(payload && payload.error)) {
        e.message = 'Server error. Please retry shortly.';
      }
      throw e;
    }
    return payload;
  }

  const api = {
    request: request,
    get: (url) => request(url),
    post: (url, body) => request(url, { method: 'POST', body: body }),
    put: (url, body) => request(url, { method: 'PUT', body: body }),
    patch: (url, body) => request(url, { method: 'PATCH', body: body }),
    del: (url) => request(url, { method: 'DELETE' }),
    download: (url) => request(url, { raw: true }),
  };

  global.QS = Object.assign(global.QS || {}, api);
})(window);

