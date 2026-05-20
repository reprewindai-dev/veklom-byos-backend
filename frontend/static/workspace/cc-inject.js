/**
 * Command Center — Admin-only page
 * 1. Injects a "Command Center" link into the sidebar above Overview.
 * 2. When #/command-center is active, HIDES the <main> children and shows
 *    the two terminals (UACP Quantum Terminal + Veklom Terminal) side by side.
 *    The sidebar (aside) and header stay exactly as on every other page.
 * 3. When navigating away, removes the CC div and un-hides the originals.
 */
(function () {
  'use strict';

  /* ================================================================
   *  Sidebar injection — add Command Center link above Overview
   * ================================================================ */
  function injectSidebarLink() {
    var navLinks = document.querySelectorAll('nav a[href]');
    var overviewLink = null;
    for (var i = 0; i < navLinks.length; i++) {
      var href = navLinks[i].getAttribute('href');
      if (href === '#/' || href === '/') {
        overviewLink = navLinks[i];
        break;
      }
    }
    if (!overviewLink || document.querySelector('a[href="#/command-center"]')) return;

    var ccLink = overviewLink.cloneNode(true);
    ccLink.setAttribute('href', '#/command-center');

    var svg = ccLink.querySelector('svg');
    if (svg) {
      svg.innerHTML = '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>';
      svg.setAttribute('fill', 'none');
      svg.setAttribute('stroke', 'currentColor');
      svg.setAttribute('stroke-width', '1.5');
      svg.setAttribute('stroke-linecap', 'round');
      svg.setAttribute('stroke-linejoin', 'round');
    }

    var spans = ccLink.querySelectorAll('span');
    var labelSet = false;
    for (var j = 0; j < spans.length; j++) {
      var sp = spans[j];
      if (sp.children.length === 0 && sp.textContent.trim()) {
        if (sp.textContent.trim().toLowerCase() === 'live') continue;
        sp.textContent = 'Command Center';
        labelSet = true;
        break;
      }
    }
    if (!labelSet) {
      var textNodes = [];
      for (var k = 0; k < ccLink.childNodes.length; k++) {
        var n = ccLink.childNodes[k];
        if (n.nodeType === 3 && n.textContent.trim()) textNodes.push(n);
      }
      if (textNodes.length) textNodes[0].textContent = 'Command Center';
    }

    overviewLink.parentNode.insertBefore(ccLink, overviewLink);

    ccLink.addEventListener('click', function (e) {
      e.preventDefault();
      window.location.hash = '#/command-center';
    });
  }

  /* ================================================================
   *  Command Center page — hide/show approach (keeps React alive)
   * ================================================================ */
  function getMain() { return document.querySelector('main'); }

  function showCC() {
    var main = getMain();
    if (!main) return;
    if (document.getElementById('cc-page')) return;

    // Hide all existing children of <main>
    for (var i = 0; i < main.children.length; i++) {
      main.children[i].setAttribute('data-cc-hidden', '');
      main.children[i].style.display = 'none';
    }

    // Create Command Center container with two terminal iframes
    var cc = document.createElement('div');
    cc.id = 'cc-page';
    cc.style.cssText = 'flex:1;height:100%;min-height:0;display:flex;flex-direction:column;background:#080b0f;overflow:hidden;';

    cc.innerHTML =
      // Header
      '<div style="padding:16px 24px 12px;flex-shrink:0;">' +
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">' +
          '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#f97316" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>' +
          '<span style="font-size:16px;font-weight:700;letter-spacing:0.02em;color:#e0e0e0;">Command Center</span>' +
          '<span style="font-size:9px;padding:2px 8px;border-radius:3px;border:1px solid rgba(249,115,22,0.3);color:#f97316;text-transform:uppercase;letter-spacing:0.12em;font-weight:600;">Admin</span>' +
        '</div>' +
      '</div>' +
      // Terminal tabs
      '<div id="cc-tabs" style="display:flex;gap:0;padding:0 24px;flex-shrink:0;">' +
        '<button id="cc-tab-quantum" class="cc-tab active" style="padding:8px 20px;font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;border:1px solid rgba(255,255,255,0.1);border-bottom:none;border-radius:6px 6px 0 0;background:#0d1117;color:#00c8ff;cursor:pointer;font-family:monospace;">UACP Quantum Terminal</button>' +
        '<button id="cc-tab-veklom" class="cc-tab" style="padding:8px 20px;font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;border:1px solid rgba(255,255,255,0.06);border-bottom:none;border-radius:6px 6px 0 0;background:transparent;color:rgba(255,255,255,0.3);cursor:pointer;font-family:monospace;margin-left:-1px;">Veklom Terminal</button>' +
      '</div>' +
      // Terminal frames
      '<div style="flex:1;min-height:0;position:relative;border-top:1px solid rgba(255,255,255,0.1);margin:0 24px;">' +
        '<iframe id="cc-frame-quantum" src="/command-center/quantum-terminal/" style="position:absolute;inset:0;width:100%;height:100%;border:none;background:#080b0f;" allow="clipboard-read;clipboard-write"></iframe>' +
        '<iframe id="cc-frame-veklom" src="/command-center/veklom-terminal/" style="position:absolute;inset:0;width:100%;height:100%;border:none;background:#0a0a0a;display:none;" allow="clipboard-read;clipboard-write"></iframe>' +
      '</div>';

    main.appendChild(cc);

    main.style.flex = '1';
    main.style.display = 'flex';
    main.style.flexDirection = 'column';
    main.style.overflow = 'hidden';

    // Wire tab switching
    var tabQ = document.getElementById('cc-tab-quantum');
    var tabV = document.getElementById('cc-tab-veklom');
    var frameQ = document.getElementById('cc-frame-quantum');
    var frameV = document.getElementById('cc-frame-veklom');

    if (tabQ && tabV && frameQ && frameV) {
      tabQ.addEventListener('click', function () {
        frameQ.style.display = '';
        frameV.style.display = 'none';
        tabQ.style.background = '#0d1117';
        tabQ.style.color = '#00c8ff';
        tabQ.style.borderColor = 'rgba(255,255,255,0.1)';
        tabV.style.background = 'transparent';
        tabV.style.color = 'rgba(255,255,255,0.3)';
        tabV.style.borderColor = 'rgba(255,255,255,0.06)';
      });
      tabV.addEventListener('click', function () {
        frameQ.style.display = 'none';
        frameV.style.display = '';
        tabV.style.background = '#0d1117';
        tabV.style.color = '#00c8ff';
        tabV.style.borderColor = 'rgba(255,255,255,0.1)';
        tabQ.style.background = 'transparent';
        tabQ.style.color = 'rgba(255,255,255,0.3)';
        tabQ.style.borderColor = 'rgba(255,255,255,0.06)';
      });
    }
  }

  function hideCC() {
    var cc = document.getElementById('cc-page');
    if (!cc) return;

    var main = getMain();
    cc.parentNode.removeChild(cc);

    if (main) {
      var hidden = main.querySelectorAll('[data-cc-hidden]');
      for (var i = 0; i < hidden.length; i++) {
        hidden[i].style.display = '';
        hidden[i].removeAttribute('data-cc-hidden');
      }
      main.style.flex = '';
      main.style.display = '';
      main.style.flexDirection = '';
      main.style.overflow = '';
    }
  }

  /* ================================================================
   *  Route handling
   * ================================================================ */
  var currentRoute = null;

  function handleRoute() {
    var hash = window.location.hash || '#/';
    if (hash === currentRoute) return;

    var wasCC = currentRoute === '#/command-center';
    currentRoute = hash;

    if (hash === '#/command-center') {
      showCC();
    } else if (wasCC) {
      hideCC();
    }
  }

  /* ================================================================
   *  Init
   * ================================================================ */
  window.addEventListener('hashchange', function () {
    setTimeout(handleRoute, 60);
  });

  var observer = new MutationObserver(function () {
    var nav = document.querySelector('nav');
    if (nav && (nav.querySelector('a[href="#/"]') || nav.querySelector('a[href="/"]'))) {
      injectSidebarLink();
      observer.disconnect();
      setTimeout(handleRoute, 200);
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });

  setTimeout(function () { injectSidebarLink(); handleRoute(); }, 1500);
})();
