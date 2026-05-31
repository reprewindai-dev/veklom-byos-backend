/**
 * Auth Gate — Veklom multi-tenant authentication.
 *
 * Flow:
 *  - Real user (has stored non-eval token) → load workspace silently
 *  - /workspace/login OR no token → show Sign In / Sign Up overlay
 *  - GitHub OAuth button shown when backend reports it configured
 *  - On successful auth: store token, dismiss overlay, workspace loads
 *  - fetch() monkey-patched to inject Bearer on all /api/ calls
 */
(function () {
  'use strict';

  var TOKEN_KEY  = 'veklom_token';
  var REFRESH_KEY = 'veklom_refresh';
  var USER_KEY   = 'veklom_user';
  var API_BASE   = window.__VEKLOM_API_BASE__ || '/api/v1';

  var isLoginPage = location.pathname === '/workspace/login' ||
                    location.pathname === '/login' ||
                    location.search.indexOf('login') !== -1;

  // ---------------------------------------------------------------------------
  // Token helpers
  // ---------------------------------------------------------------------------
  function getToken()  { return localStorage.getItem(TOKEN_KEY); }
  function setTokens(a, r) {
    if (a) localStorage.setItem(TOKEN_KEY, a);
    if (r) localStorage.setItem(REFRESH_KEY, r);
  }
  function clearTokens() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
  }
  function isEvalUser(user) {
    return user && (
      (user.email && user.email.indexOf('@eval.veklom.local') !== -1) ||
      user.is_eval === true ||
      user.plan === 'free' && user.role === 'viewer'
    );
  }

  // ---------------------------------------------------------------------------
  // fetch patch — inject Bearer on every /api/ call
  // ---------------------------------------------------------------------------
  var originalFetch = window.fetch;
  window.fetch = function (url, opts) {
    opts = opts || {};
    var token = getToken();
    if (token && typeof url === 'string' && (url.startsWith('/api/') || url.startsWith(API_BASE))) {
      opts.headers = opts.headers || {};
      if (opts.headers instanceof Headers) {
        if (!opts.headers.has('Authorization')) opts.headers.set('Authorization', 'Bearer ' + token);
      } else if (!opts.headers['Authorization'] && !opts.headers['authorization']) {
        opts.headers['Authorization'] = 'Bearer ' + token;
      }
    }
    return originalFetch.call(this, url, opts);
  };

  // ---------------------------------------------------------------------------
  // Auth overlay — shown on /workspace/login or when no real account exists
  // ---------------------------------------------------------------------------
  var overlayEl = null;

  function showAuthOverlay(githubConfigured) {
    if (overlayEl) return;
    overlayEl = document.createElement('div');
    overlayEl.id = 'veklom-auth-overlay';
    overlayEl.style.cssText = [
      'position:fixed;inset:0;z-index:99999;background:#080b0f;',
      'display:flex;align-items:center;justify-content:center;',
      'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;'
    ].join('');

    var ghBtn = githubConfigured
      ? '<button id="vk-gh-btn" style="width:100%;padding:11px;background:#21262d;color:#e6edf3;border:1px solid rgba(255,255,255,0.15);border-radius:8px;font-size:14px;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;margin-bottom:12px;">'
        + '<svg width="18" height="18" viewBox="0 0 24 24" fill="#e6edf3"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>'
        + 'Continue with GitHub</button>'
      : '';

    overlayEl.innerHTML = '<div style="width:100%;max-width:400px;padding:20px;">'
      + '<div style="text-align:center;margin-bottom:32px;">'
      + '<img src="/static/branding/veklom-wordmark.png" alt="Veklom" style="height:40px;margin-bottom:16px;" onerror="this.style.display=\'none\'">'
      + '<p style="color:#6b7280;font-size:13px;margin:0;">Sovereign AI execution layer</p>'
      + '</div>'
      + '<div id="vk-tabs" style="display:flex;gap:4px;background:rgba(255,255,255,0.05);border-radius:8px;padding:4px;margin-bottom:20px;">'
      + '<button id="vk-tab-in" onclick="window.__vkTab(\'in\')" style="flex:1;padding:8px;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:500;background:#f97316;color:#fff;">Sign In</button>'
      + '<button id="vk-tab-up" onclick="window.__vkTab(\'up\')" style="flex:1;padding:8px;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:500;background:transparent;color:#9ca3af;">Create Account</button>'
      + '</div>'
      + '<div id="vk-err" style="display:none;background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.3);border-radius:6px;padding:10px 12px;color:#fca5a5;font-size:13px;margin-bottom:12px;"></div>'
      + '<div id="vk-ok" style="display:none;background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.3);border-radius:6px;padding:10px 12px;color:#86efac;font-size:13px;margin-bottom:12px;"></div>'
      + ghBtn
      + (githubConfigured ? '<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;"><div style="flex:1;height:1px;background:rgba(255,255,255,0.08)"></div><span style="color:#4b5563;font-size:12px;">or</span><div style="flex:1;height:1px;background:rgba(255,255,255,0.08)"></div></div>' : '')
      + '<div id="vk-name-wrap" style="display:none;margin-bottom:10px;"><input id="vk-name" placeholder="Full name" style="width:100%;box-sizing:border-box;padding:11px 12px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:8px;color:#e5e7eb;font-size:14px;" /></div>'
      + '<input id="vk-email" type="email" placeholder="Email address" style="width:100%;box-sizing:border-box;padding:11px 12px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:8px;color:#e5e7eb;font-size:14px;margin-bottom:10px;" />'
      + '<input id="vk-pass" type="password" placeholder="Password (min 8 chars)" style="width:100%;box-sizing:border-box;padding:11px 12px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:8px;color:#e5e7eb;font-size:14px;margin-bottom:16px;" />'
      + '<button id="vk-submit" style="width:100%;padding:11px;background:#f97316;color:#fff;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;">Sign In</button>'
      + '<p style="text-align:center;color:#4b5563;font-size:12px;margin-top:16px;">Each account gets its own private workspace.</p>'
      + '</div>';

    document.body.appendChild(overlayEl);

    // Tab switching
    window.__vkTab = function (tab) {
      var isSignup = tab === 'up';
      document.getElementById('vk-tab-in').style.background = isSignup ? 'transparent' : '#f97316';
      document.getElementById('vk-tab-in').style.color = isSignup ? '#9ca3af' : '#fff';
      document.getElementById('vk-tab-up').style.background = isSignup ? '#f97316' : 'transparent';
      document.getElementById('vk-tab-up').style.color = isSignup ? '#fff' : '#9ca3af';
      document.getElementById('vk-name-wrap').style.display = isSignup ? 'block' : 'none';
      document.getElementById('vk-submit').textContent = isSignup ? 'Create Account' : 'Sign In';
      document.getElementById('vk-err').style.display = 'none';
      window.__vkIsSignup = isSignup;
    };
    window.__vkIsSignup = false;

    // Keyboard submit
    function handleKey(e) { if (e.key === 'Enter') document.getElementById('vk-submit').click(); }
    document.getElementById('vk-email').addEventListener('keydown', handleKey);
    document.getElementById('vk-pass').addEventListener('keydown', handleKey);

    // Submit handler
    document.getElementById('vk-submit').addEventListener('click', function () {
      var email = document.getElementById('vk-email').value.trim();
      var pass  = document.getElementById('vk-pass').value;
      var name  = (document.getElementById('vk-name').value || '').trim();
      var errEl = document.getElementById('vk-err');
      var okEl  = document.getElementById('vk-ok');
      var btn   = document.getElementById('vk-submit');

      errEl.style.display = 'none';
      okEl.style.display  = 'none';
      if (!email || !pass) { errEl.textContent = 'Email and password are required.'; errEl.style.display = 'block'; return; }

      var endpoint = window.__vkIsSignup ? '/api/v1/auth/register' : '/api/v1/auth/login';
      var payload  = window.__vkIsSignup
        ? { email: email, password: pass, full_name: name }
        : { email: email, password: pass };

      btn.textContent = '...';
      btn.disabled = true;

      originalFetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        if (!res.ok) {
          var msg = res.data.detail || (window.__vkIsSignup ? 'Registration failed.' : 'Invalid email or password.');
          if (Array.isArray(msg)) msg = msg.map(function(e){ return e.msg || JSON.stringify(e); }).join(', ');
          errEl.textContent = msg;
          errEl.style.display = 'block';
          btn.textContent = window.__vkIsSignup ? 'Create Account' : 'Sign In';
          btn.disabled = false;
          return;
        }
        setTokens(res.data.access_token, res.data.refresh_token);
        if (res.data.user) {
          localStorage.setItem(USER_KEY, JSON.stringify(res.data.user));
          window.__VEKLOM_USER__ = res.data.user;
        }
        if (window.__vkIsSignup) {
          okEl.textContent = 'Account created! Your private workspace is ready.';
          okEl.style.display = 'block';
          setTimeout(dismissOverlay, 800);
        } else {
          dismissOverlay();
        }
      })
      .catch(function (e) {
        errEl.textContent = 'Network error. Please try again.';
        errEl.style.display = 'block';
        btn.textContent = window.__vkIsSignup ? 'Create Account' : 'Sign In';
        btn.disabled = false;
      });
    });

    // GitHub OAuth button
    if (githubConfigured) {
      document.getElementById('vk-gh-btn').addEventListener('click', function () {
        location.href = '/api/v1/auth/github/login';
      });
    }
  }

  function dismissOverlay() {
    if (overlayEl) { overlayEl.remove(); overlayEl = null; }
  }

  // ---------------------------------------------------------------------------
  // Eval session (silent, for workspace demo mode)
  // ---------------------------------------------------------------------------
  function createEvalSession() {
    return originalFetch(API_BASE + '/auth/eval-session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fingerprint: (navigator.userAgent || '').slice(0, 64) })
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.access_token) {
        setTokens(data.access_token, data.refresh_token);
        if (data.user) { localStorage.setItem(USER_KEY, JSON.stringify(data.user)); window.__VEKLOM_USER__ = data.user; }
      }
      return data;
    })
    .catch(function (e) { console.warn('[auth-gate] eval-session failed:', e); });
  }

  // ---------------------------------------------------------------------------
  // Bootstrap
  // ---------------------------------------------------------------------------
  function bootstrap() {
    // If arriving from GitHub OAuth callback with token in URL, store it
    var ghMatch = location.search.match(/[?&]token=([^&]+)/);
    if (ghMatch) {
      setTokens(decodeURIComponent(ghMatch[1]), '');
      history.replaceState(null, '', location.pathname);
    }

    var token = getToken();
    var cachedUser = null;
    try { cachedUser = JSON.parse(localStorage.getItem(USER_KEY) || 'null'); } catch(e) {}
    if (cachedUser) window.__VEKLOM_USER__ = cachedUser;

    // If on login page, always show overlay
    if (isLoginPage) {
      clearTokens();
      checkGitHubAndShowOverlay();
      return;
    }

    // If no token, show overlay (real sign-in required for workspace)
    if (!token) {
      checkGitHubAndShowOverlay();
      return;
    }

    // Verify token + check if real user (not eval)
    originalFetch(API_BASE + '/auth/me', {
      headers: { 'Authorization': 'Bearer ' + token }
    }).then(function (r) {
      if (r.ok) {
        return r.json().then(function (user) {
          localStorage.setItem(USER_KEY, JSON.stringify(user));
          window.__VEKLOM_USER__ = user;
          // Eval users still get workspace access (limited plan)
        });
      } else if (r.status === 401) {
        clearTokens();
        checkGitHubAndShowOverlay();
      }
    }).catch(function () {
      // Network error — keep existing token, continue
    });
  }

  function checkGitHubAndShowOverlay() {
    originalFetch(API_BASE + '/auth/github/status')
      .then(function (r) { return r.json(); })
      .then(function (d) { showAuthOverlay(d.configured === true); })
      .catch(function () { showAuthOverlay(false); });
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  window.__VEKLOM_AUTH__ = {
    getToken:    getToken,
    setTokens:   setTokens,
    clearTokens: clearTokens,
    getUser:     function () { try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); } catch { return null; } },
    logout:      function () { clearTokens(); location.href = '/'; },
    showLogin:   function () { checkGitHubAndShowOverlay(); },
  };

  bootstrap();
})();
