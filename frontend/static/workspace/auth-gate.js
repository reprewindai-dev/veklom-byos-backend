/**
 * Auth Gate — runs BEFORE the compiled workspace bundle.
 *
 * 1. Checks localStorage for an existing JWT token.
 * 2. If no token → auto-creates a free evaluation session via POST /api/v1/auth/eval-session.
 * 3. Monkey-patches window.fetch to inject Authorization: Bearer on all /api/ calls.
 * 4. Exposes window.__VEKLOM_USER__ for enhancement scripts to read.
 *
 * This ensures the compiled bundle (which cannot be modified) always sends
 * authenticated requests, even though its internal k1 variable starts null.
 */
(function () {
  'use strict';

  var TOKEN_KEY = 'veklom_token';
  var REFRESH_KEY = 'veklom_refresh';
  var USER_KEY = 'veklom_user';
  var API_BASE = window.__VEKLOM_API_BASE__ || '/api/v1';

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function setTokens(access, refresh) {
    if (access) localStorage.setItem(TOKEN_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  }

  function clearTokens() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
  }

  // --- Monkey-patch fetch to inject Bearer token ---
  var originalFetch = window.fetch;
  window.fetch = function (url, opts) {
    opts = opts || {};
    var token = getToken();
    if (token && typeof url === 'string' && (url.startsWith('/api/') || url.startsWith(API_BASE))) {
      opts.headers = opts.headers || {};
      // Don't override if already set
      if (opts.headers instanceof Headers) {
        if (!opts.headers.has('Authorization')) {
          opts.headers.set('Authorization', 'Bearer ' + token);
        }
      } else if (typeof opts.headers === 'object' && !opts.headers.Authorization) {
        opts.headers.Authorization = 'Bearer ' + token;
      }
    }
    return originalFetch.call(this, url, opts);
  };

  // --- Handle 401 responses: clear token and create new eval session ---
  var handle401Count = 0;
  var _origThen = Promise.prototype.then;

  // Intercept responses to detect 401 and auto-refresh
  var patchedFetch = window.fetch;
  window.fetch = function () {
    var args = arguments;
    return patchedFetch.apply(this, args).then(function (response) {
      if (response.status === 401 && handle401Count < 3) {
        handle401Count++;
        var url = typeof args[0] === 'string' ? args[0] : (args[0]?.url || '');
        // Don't intercept auth endpoints themselves
        if (!url.includes('/auth/eval-session') && !url.includes('/auth/login') && !url.includes('/auth/register')) {
          clearTokens();
          return createEvalSession().then(function () {
            handle401Count--;
            return patchedFetch.apply(window, args);
          });
        }
      }
      return response;
    });
  };

  // --- Create free evaluation session ---
  function createEvalSession() {
    return originalFetch(API_BASE + '/auth/eval-session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fingerprint: navigator.userAgent.slice(0, 64) })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.access_token) {
          setTokens(data.access_token, data.refresh_token);
          if (data.user) {
            localStorage.setItem(USER_KEY, JSON.stringify(data.user));
            window.__VEKLOM_USER__ = data.user;
          }
        }
        return data;
      })
      .catch(function (err) {
        console.warn('[auth-gate] Eval session creation failed:', err);
      });
  }

  // --- Bootstrap: check token validity, create eval session if needed ---
  function bootstrap() {
    var token = getToken();
    if (!token) {
      createEvalSession();
      return;
    }

    // Verify existing token is still valid
    originalFetch(API_BASE + '/auth/me', {
      headers: { 'Authorization': 'Bearer ' + token }
    }).then(function (r) {
      if (r.ok) {
        return r.json().then(function (user) {
          localStorage.setItem(USER_KEY, JSON.stringify(user));
          window.__VEKLOM_USER__ = user;
        });
      } else if (r.status === 401) {
        clearTokens();
        createEvalSession();
      }
    }).catch(function () {
      // Network error — don't clear tokens, just continue
    });
  }

  // --- Expose for enhancement scripts ---
  window.__VEKLOM_AUTH__ = {
    getToken: getToken,
    setTokens: setTokens,
    clearTokens: clearTokens,
    getUser: function () {
      try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); } catch { return null; }
    },
    logout: function () {
      clearTokens();
      location.href = '/';
    }
  };

  // Load cached user immediately
  try {
    var cached = JSON.parse(localStorage.getItem(USER_KEY) || 'null');
    if (cached) window.__VEKLOM_USER__ = cached;
  } catch (e) {}

  bootstrap();
})();
