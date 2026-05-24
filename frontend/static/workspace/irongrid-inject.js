/**
 * PYO3 IronGrid inject
 * 1. Injects an "IronGrid" link into the sidebar.
 * 2. When #/irongrid is active, hides <main> children and shows IronGrid iframe.
 * 3. When navigating away, removes the iframe and restores originals.
 */
(function () {
  'use strict';
  var IRONGRID_URL = '/irongrid/';

  function injectSidebarLink() {
    var navLinks = document.querySelectorAll('nav a[href]');
    var overviewLink = null;
    for (var i = 0; i < navLinks.length; i++) {
      var href = navLinks[i].getAttribute('href');
      if (href === '#/' || href === '/') { overviewLink = navLinks[i]; break; }
    }
    if (!overviewLink || document.querySelector('a[href="#/irongrid"]')) return;

    var link = overviewLink.cloneNode(true);
    link.setAttribute('href', '#/irongrid');

    var svg = link.querySelector('svg');
    if (svg) {
      svg.innerHTML = '<rect x="2" y="2" width="20" height="20" rx="2"/><line x1="2" y1="9" x2="22" y2="9"/><line x1="2" y1="15" x2="22" y2="15"/><line x1="9" y1="2" x2="9" y2="22"/><line x1="15" y1="2" x2="15" y2="22"/>';
      svg.setAttribute('fill', 'none');
      svg.setAttribute('stroke', 'currentColor');
      svg.setAttribute('stroke-width', '1.5');
      svg.setAttribute('stroke-linecap', 'round');
    }

    var spans = link.querySelectorAll('span');
    var labelSet = false;
    for (var j = 0; j < spans.length; j++) {
      var sp = spans[j];
      if (sp.children.length === 0 && sp.textContent.trim()) {
        if (sp.textContent.trim().toLowerCase() === 'live') continue;
        sp.textContent = 'IronGrid';
        labelSet = true;
        break;
      }
    }
    if (!labelSet) {
      var nodes = [];
      for (var k = 0; k < link.childNodes.length; k++) {
        var n = link.childNodes[k];
        if (n.nodeType === 3 && n.textContent.trim()) nodes.push(n);
      }
      if (nodes.length) nodes[0].textContent = 'IronGrid';
    }

    overviewLink.parentNode.insertBefore(link, overviewLink);
    link.addEventListener('click', function (e) {
      e.preventDefault();
      window.location.hash = '#/irongrid';
    });
  }

  function getMain() { return document.querySelector('main'); }

  function showIronGrid() {
    var main = getMain();
    if (!main || document.getElementById('irongrid-page')) return;
    for (var i = 0; i < main.children.length; i++) {
      main.children[i].setAttribute('data-ig-hidden', '');
      main.children[i].style.display = 'none';
    }
    var div = document.createElement('div');
    div.id = 'irongrid-page';
    div.style.cssText = 'flex:1;height:100%;min-height:0;position:relative;background:#050505;overflow:hidden;';
    div.innerHTML = '<iframe src="' + IRONGRID_URL + '" style="width:100%;height:100%;border:none;background:#050505;" allow="clipboard-read;clipboard-write"></iframe>';
    main.appendChild(div);
    main.style.flex = '1';
    main.style.display = 'flex';
    main.style.flexDirection = 'column';
    main.style.overflow = 'hidden';
  }

  function hideIronGrid() {
    var div = document.getElementById('irongrid-page');
    if (!div) return;
    var main = getMain();
    div.parentNode.removeChild(div);
    if (main) {
      var hidden = main.querySelectorAll('[data-ig-hidden]');
      for (var i = 0; i < hidden.length; i++) {
        hidden[i].style.display = '';
        hidden[i].removeAttribute('data-ig-hidden');
      }
      main.style.flex = '';
      main.style.display = '';
      main.style.flexDirection = '';
      main.style.overflow = '';
    }
  }

  var currentRoute = null;
  function handleRoute() {
    var hash = window.location.hash || '#/';
    if (hash === currentRoute) return;
    var was = currentRoute === '#/irongrid';
    currentRoute = hash;
    if (hash === '#/irongrid') { showIronGrid(); }
    else if (was) { hideIronGrid(); }
  }

  window.addEventListener('hashchange', function () { setTimeout(handleRoute, 60); });

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
