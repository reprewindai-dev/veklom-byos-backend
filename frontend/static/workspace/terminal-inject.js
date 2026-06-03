/**
 * UACP Quantum Terminal inject
 * 1. Injects a "Terminal" link into the sidebar.
 * 2. When #/terminal is active, hides <main> children and shows Terminal iframe.
 * 3. When navigating away, removes the iframe and restores originals.
 */
(function () {
  'use strict';
  var TERMINAL_URL = '/terminal';

  function injectSidebarLink() {
    var navLinks = document.querySelectorAll('nav a[href]');
    var overviewLink = null;
    for (var i = 0; i < navLinks.length; i++) {
      var href = navLinks[i].getAttribute('href');
      if (href === '#/' || href === '/') { overviewLink = navLinks[i]; break; }
    }
    if (!overviewLink || document.querySelector('a[href="#/terminal"]')) return;

    var link = overviewLink.cloneNode(true);
    link.setAttribute('href', '#/terminal');

    var svg = link.querySelector('svg');
    if (svg) {
      svg.innerHTML = '<polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>';
      svg.setAttribute('fill', 'none');
      svg.setAttribute('stroke', 'currentColor');
      svg.setAttribute('stroke-width', '1.5');
      svg.setAttribute('stroke-linecap', 'round');
      svg.setAttribute('stroke-linejoin', 'round');
    }

    var spans = link.querySelectorAll('span');
    var labelSet = false;
    for (var j = 0; j < spans.length; j++) {
      var sp = spans[j];
      if (sp.children.length === 0 && sp.textContent.trim()) {
        if (sp.textContent.trim().toLowerCase() === 'live') continue;
        sp.textContent = 'Terminal';
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
      if (nodes.length) nodes[0].textContent = 'Terminal';
    }

    overviewLink.parentNode.insertBefore(link, overviewLink);
    link.addEventListener('click', function (e) {
      e.preventDefault();
      window.location.hash = '#/terminal';
    });
  }

  function getMain() { return document.querySelector('main'); }

  function showTerminal() {
    var main = getMain();
    if (!main || document.getElementById('terminal-page')) return;
    for (var i = 0; i < main.children.length; i++) {
      main.children[i].setAttribute('data-term-hidden', '');
      main.children[i].style.display = 'none';
    }
    var div = document.createElement('div');
    div.id = 'terminal-page';
    div.style.cssText = 'flex:1;height:100%;min-height:0;position:relative;background:#050505;overflow:hidden;';
    div.innerHTML = '<iframe src="' + TERMINAL_URL + '" style="width:100%;height:100%;border:none;background:#050505;" allow="clipboard-read;clipboard-write"></iframe>';
    main.appendChild(div);
    main.style.flex = '1';
    main.style.display = 'flex';
    main.style.flexDirection = 'column';
    main.style.overflow = 'hidden';
  }

  function hideTerminal() {
    var div = document.getElementById('terminal-page');
    if (!div) return;
    var main = getMain();
    div.parentNode.removeChild(div);
    if (main) {
      var hidden = main.querySelectorAll('[data-term-hidden]');
      for (var i = 0; i < hidden.length; i++) {
        hidden[i].style.display = '';
        hidden[i].removeAttribute('data-term-hidden');
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
    var was = currentRoute === '#/terminal';
    currentRoute = hash;
    if (hash === '#/terminal') { showTerminal(); }
    else if (was) { hideTerminal(); }
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
