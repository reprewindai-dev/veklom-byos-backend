/**
 * Addons Inject — unified handler for all injected pages.
 * Uses a fixed overlay approach that works regardless of React Router state.
 * 
 * Routes:
 *   #/command-center → /command-center/ (Truth Command Center)
 *   #/gpc            → https://uacpv3.onrender.com (GPC / UACP V3)
 *   #/irongrid       → /irongrid/ (PYO3 IronGrid Simulator)
 *   #/terminal       → /terminal (UACP Quantum Terminal)
 */
(function () {
  'use strict';

  // Access tier rules:
  // ownerOnly   → OWNER / SUPER_ADMIN only (the platform super-admin, not regular tenants)
  // paidOnly    → sovereign / pro plan (paid customers)
  // adminOnly   → OWNER + ADMIN
  // (none)      → all authenticated users
  var ALL_ROUTES = {
    '#/command-center': {
      url: '/command-center/',
      label: 'Command Center',
      icon: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
      ownerOnly: true  // SUPER ADMIN ONLY — never shown to tenants
    },
    '#/gpc': {
      url: '/gpc',
      label: 'GPC',
      icon: '<path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>',
      paidOnly: true   // Paid customers only (sovereign / pro plan)
    },
    '#/irongrid': {
      url: '/irongrid/',
      label: 'IronGrid',
      icon: '<rect x="2" y="2" width="20" height="20" rx="2"/><line x1="2" y1="9" x2="22" y2="9"/><line x1="2" y1="15" x2="22" y2="15"/><line x1="9" y1="2" x2="9" y2="22"/><line x1="15" y1="2" x2="15" y2="22"/>',
      paidOnly: true   // Paid customers only
    },
    '#/terminal': {
      url: '/terminal',
      label: 'Terminal',
      icon: '<polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>',
      ownerOnly: false, paidOnly: false  // Available to all authenticated users
    }
  };

  function getUser() {
    return window.__VEKLOM_USER__ || window._veklomUser
      || (window.__VEKLOM_AUTH__ && window.__VEKLOM_AUTH__.getUser ? window.__VEKLOM_AUTH__.getUser() : null);
  }

  function isOwner() {
    var user = getUser();
    if (!user) return false;
    var role = (user.role || '').toUpperCase();
    return role === 'OWNER' || role === 'SUPER_ADMIN';
  }

  function isPaid() {
    var user = getUser();
    if (!user) return false;
    var role = (user.role || '').toUpperCase();
    var plan = (user.plan || '').toLowerCase();
    // Owner/admin always get paid access; sovereign/pro plan users also qualify
    return role === 'OWNER' || role === 'SUPER_ADMIN' || role === 'ADMIN'
      || plan === 'sovereign' || plan === 'pro' || plan === 'founding'
      || plan === 'standard' || plan === 'regulated';
  }

  function isAdmin() {
    var user = getUser();
    if (!user) return false;
    var role = (user.role || '').toUpperCase();
    return role === 'OWNER' || role === 'SUPER_ADMIN' || role === 'ADMIN';
  }

  function getVisibleRoutes() {
    var routes = {};
    Object.keys(ALL_ROUTES).forEach(function (key) {
      var cfg = ALL_ROUTES[key];
      if (cfg.ownerOnly && !isOwner()) return;
      if (cfg.paidOnly && !isPaid()) return;
      routes[key] = cfg;
    });
    return routes;
  }

  var ROUTES = getVisibleRoutes();

  var OVERLAY_ID = 'addon-overlay';
  var activeRoute = null;

  /* ================================================================
   *  Overlay — sits on top of everything, doesn't fight React
   * ================================================================ */
  function showOverlay(route) {
    var existing = document.getElementById(OVERLAY_ID);
    if (existing) existing.remove();

    var config = ROUTES[route];
    if (!config) return;

    // Find the layout container (aside + main area)
    var aside = document.querySelector('aside') || document.querySelector('nav');
    var sidebarWidth = aside ? aside.offsetWidth : 240;

    var overlay = document.createElement('div');
    overlay.id = OVERLAY_ID;
    overlay.style.cssText = 'position:fixed;top:0;right:0;bottom:0;left:' + sidebarWidth + 'px;z-index:9999;background:#050505;display:flex;flex-direction:column;';
    overlay.innerHTML = '<iframe src="' + config.url + '" style="flex:1;width:100%;height:100%;border:none;background:#050505;" allow="clipboard-read;clipboard-write;microphone;camera"></iframe>';
    document.body.appendChild(overlay);
    activeRoute = route;
  }

  function hideOverlay() {
    var overlay = document.getElementById(OVERLAY_ID);
    if (overlay) overlay.remove();
    activeRoute = null;
  }

  /* ================================================================
   *  Sidebar injection — add links for each addon
   * ================================================================ */
  function injectSidebarLinks() {
    // Re-evaluate routes each time (user data may have arrived)
    ROUTES = getVisibleRoutes();

    // Try multiple selectors for the sidebar navigation
    var nav = document.querySelector('nav') || document.querySelector('aside nav') || document.querySelector('[class*="sidebar"] nav') || document.querySelector('aside');
    if (!nav) return false;

    var links = nav.querySelectorAll('a[href]');
    if (links.length === 0) return false;

    // Find a reference link to clone (use the first one with an SVG icon)
    var refLink = null;
    for (var i = 0; i < links.length; i++) {
      if (links[i].querySelector('svg')) { refLink = links[i]; break; }
    }
    if (!refLink) refLink = links[0];

    // Find insertion point — after Settings or at the end
    var lastLink = links[links.length - 1];
    var insertParent = lastLink.parentNode;

    Object.keys(ROUTES).forEach(function (hash) {
      if (document.querySelector('a[href="' + hash + '"]')) return; // already injected

      var config = ROUTES[hash];
      var link = refLink.cloneNode(true);
      link.setAttribute('href', hash);

      // Set icon
      var svg = link.querySelector('svg');
      if (svg) {
        svg.innerHTML = config.icon;
        svg.setAttribute('fill', 'none');
        svg.setAttribute('stroke', 'currentColor');
        svg.setAttribute('stroke-width', '1.5');
        svg.setAttribute('stroke-linecap', 'round');
        svg.setAttribute('stroke-linejoin', 'round');
      }

      // Set label
      var spans = link.querySelectorAll('span');
      var labelSet = false;
      for (var j = 0; j < spans.length; j++) {
        var sp = spans[j];
        if (sp.children.length === 0 && sp.textContent.trim()) {
          if (sp.textContent.trim().toLowerCase() === 'live') continue;
          sp.textContent = config.label;
          labelSet = true;
          break;
        }
      }
      if (!labelSet) {
        var textNodes = [];
        for (var k = 0; k < link.childNodes.length; k++) {
          var n = link.childNodes[k];
          if (n.nodeType === 3 && n.textContent.trim()) textNodes.push(n);
        }
        if (textNodes.length) textNodes[0].textContent = config.label;
      }

      // Remove any "active" styling class from clone
      link.className = link.className.replace(/active|selected|current/gi, '').trim();

      link.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        window.location.hash = hash;
      });

      // Insert after the last link's parent element
      if (insertParent && insertParent.parentNode) {
        insertParent.parentNode.appendChild(link.parentNode === refLink.parentNode ? link : link);
      } else {
        nav.appendChild(link);
      }
    });

    return true;
  }

  /* ================================================================
   *  Route handling
   * ================================================================ */
  function handleRoute() {
    var hash = window.location.hash || '#/';
    ROUTES = getVisibleRoutes();

    if (ROUTES[hash]) {
      if (activeRoute !== hash) {
        showOverlay(hash);
      }
    } else if (ALL_ROUTES[hash] && ALL_ROUTES[hash].adminOnly && !isAdmin()) {
      // Non-admin tried to access admin route — redirect away
      window.location.hash = '#/';
    } else {
      if (activeRoute) {
        hideOverlay();
      }
    }
  }

  /* ================================================================
   *  Init — aggressive approach to ensure it works
   * ================================================================ */
  window.addEventListener('hashchange', function () {
    handleRoute();
  });

  // Also intercept popstate
  window.addEventListener('popstate', function () {
    setTimeout(handleRoute, 10);
  });

  // Initial injection attempts — longer delays to wait for auth
  injectSidebarLinks();
  setTimeout(injectSidebarLinks, 500);
  setTimeout(injectSidebarLinks, 1500);
  setTimeout(injectSidebarLinks, 3000);
  setTimeout(injectSidebarLinks, 6000);  // Extra wait for slow auth load

  // Persistent MutationObserver — re-inject whenever nav/sidebar DOM changes
  var navObserver = new MutationObserver(function () {
    var missing = Object.keys(ALL_ROUTES).some(function (hash) {
      return !document.querySelector('a[href="' + hash + '"]');
    });
    if (missing) injectSidebarLinks();
  });
  navObserver.observe(document.body, { childList: true, subtree: true });

  // Listen for auth state changes from workspace-enhance.js
  window.addEventListener('veklom:user-loaded', function () {
    setTimeout(injectSidebarLinks, 100);
    setTimeout(handleRoute, 150);
  });

  // Expose globally so workspace-enhance.js can trigger
  window._addonHandleRoute = handleRoute;
  window._addonInjectLinks = injectSidebarLinks;

  // Handle route immediately and on short delay
  handleRoute();
  setTimeout(handleRoute, 100);
  setTimeout(handleRoute, 500);
  setTimeout(handleRoute, 1500);
})();
