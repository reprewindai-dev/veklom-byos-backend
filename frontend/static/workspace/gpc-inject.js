/**
 * GPC — Governed Plan Compiler
 * 1. Injects a "GPC" link into the sidebar between Playground and Marketplace.
 * 2. When #/gpc is active, HIDES the <main> children and shows the user's
 *    Deterministic Engine (uacpgemini) full-width inside <main>.
 *    The sidebar (aside) and header stay exactly as on every other page.
 * 3. When navigating away, removes the GPC div and un-hides the originals.
 */
(function () {
  'use strict';
  var UACPGEMINI_URL = '/gpc-engine/';

  /* ================================================================
   *  Sidebar injection — add GPC link between Playground & Marketplace
   * ================================================================ */
  function injectSidebarLink() {
    var navLinks = document.querySelectorAll('nav a[href]');
    var playgroundLink = null;
    for (var i = 0; i < navLinks.length; i++) {
      var href = navLinks[i].getAttribute('href');
      if (href === '#/playground' || href === '/playground') {
        playgroundLink = navLinks[i];
        break;
      }
    }
    if (!playgroundLink || document.querySelector('a[href="#/gpc"]')) return;

    var gpcLink = playgroundLink.cloneNode(true);
    gpcLink.setAttribute('href', '#/gpc');

    var svg = gpcLink.querySelector('svg');
    if (svg) {
      svg.innerHTML = '<path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>';
      svg.setAttribute('fill', 'none');
      svg.setAttribute('stroke', 'currentColor');
      svg.setAttribute('stroke-width', '1.5');
      svg.setAttribute('stroke-linecap', 'round');
      svg.setAttribute('stroke-linejoin', 'round');
    }

    var spans = gpcLink.querySelectorAll('span');
    var labelSet = false;
    for (var j = 0; j < spans.length; j++) {
      var sp = spans[j];
      if (sp.children.length === 0 && sp.textContent.trim()) {
        if (sp.textContent.trim().toLowerCase() === 'live') continue;
        sp.textContent = 'GPC';
        labelSet = true;
        break;
      }
    }
    if (!labelSet) {
      var textNodes = [];
      for (var k = 0; k < gpcLink.childNodes.length; k++) {
        var n = gpcLink.childNodes[k];
        if (n.nodeType === 3 && n.textContent.trim()) textNodes.push(n);
      }
      if (textNodes.length) textNodes[0].textContent = 'GPC';
    }

    playgroundLink.parentNode.insertBefore(gpcLink, playgroundLink.nextSibling);

    gpcLink.addEventListener('click', function (e) {
      e.preventDefault();
      window.location.hash = '#/gpc';
    });
  }

  /* ================================================================
   *  GPC page — hide/show approach (keeps React alive)
   * ================================================================ */
  function getMain() { return document.querySelector('main'); }

  function showGPC() {
    var main = getMain();
    if (!main) return;
    if (document.getElementById('gpc-page')) return;

    // Hide all existing children of <main>
    for (var i = 0; i < main.children.length; i++) {
      main.children[i].setAttribute('data-gpc-hidden', '');
      main.children[i].style.display = 'none';
    }

    // Create GPC container — center black box only (left/right columns hidden)
    var gpc = document.createElement('div');
    gpc.id = 'gpc-page';
    gpc.style.cssText = 'flex:1;height:100%;min-height:0;position:relative;background:#050505;overflow:hidden;';

    gpc.innerHTML =
      '<iframe id="gpc-engine-frame" src="' + UACPGEMINI_URL + '" ' +
        'style="width:300%;height:100%;border:none;background:#050505;position:absolute;left:-100%;top:0;" ' +
        'allow="clipboard-read;clipboard-write"></iframe>';

    main.appendChild(gpc);

    // Adjust main styles for flex fill
    main.style.flex = '1';
    main.style.display = 'flex';
    main.style.flexDirection = 'column';
    main.style.overflow = 'hidden';
  }

  function hideGPC() {
    var gpc = document.getElementById('gpc-page');
    if (!gpc) return;

    var main = getMain();
    gpc.parentNode.removeChild(gpc);

    // Un-hide original children
    if (main) {
      var hidden = main.querySelectorAll('[data-gpc-hidden]');
      for (var i = 0; i < hidden.length; i++) {
        hidden[i].style.display = '';
        hidden[i].removeAttribute('data-gpc-hidden');
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

    var wasGPC = currentRoute === '#/gpc';
    currentRoute = hash;

    if (hash === '#/gpc') {
      showGPC();
    } else if (wasGPC) {
      hideGPC();
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
    if (nav && (nav.querySelector('a[href="#/playground"]') || nav.querySelector('a[href="/playground"]'))) {
      injectSidebarLink();
      observer.disconnect();
      setTimeout(handleRoute, 200);
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });

  setTimeout(function () { injectSidebarLink(); handleRoute(); }, 1500);
})();
