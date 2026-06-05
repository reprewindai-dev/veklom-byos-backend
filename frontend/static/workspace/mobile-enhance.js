/**
 * mobile-enhance.js
 * Injects responsive CSS and a dynamic mobile drawer menu to optimize 
 * the Control Plane workspace for mobile and tablet devices, 
 * specifically improving portrait mode and adding a 120Hz "snappy" feel.
 */
(function() {
  "use strict";

  // 1. Inject 120Hz Snappy Feel & Mobile CSS Overrides
  const style = document.createElement('style');
  style.textContent = `
    /* Disable default highlight and enable fast touch */
    * { 
      -webkit-tap-highlight-color: transparent !important; 
    }
    
    html, body {
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }

    /* 120Hz Snappy Button Animations */
    button, a, [role="button"] { 
      touch-action: manipulation !important; 
      transition: transform 0.12s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.12s ease !important; 
      will-change: transform;
    }
    
    button:active, a:active, [role="button"]:active { 
      transform: scale(0.94) !important; 
      opacity: 0.8 !important;
    }

    /* Prevent iOS auto-zoom on form inputs */
    input, select, textarea { 
      font-size: 16px !important; 
    }
    
    /* Native scrolling feel */
    .overflow-y-auto, .overflow-auto {
      -webkit-overflow-scrolling: touch !important;
      overscroll-behavior-y: contain;
    }

    /* Mobile Drawer Classes */
    @media (max-width: 900px) {
      .mobile-sidebar-hidden { 
        display: none !important; 
      }
      .mobile-sidebar-visible { 
        position: fixed !important; 
        top: 0; left: 0; bottom: 0; z-index: 99999 !important; 
        width: 280px !important; 
        background: #0a0a0a !important; 
        border-right: 1px solid rgba(255,255,255,0.1) !important;
        box-shadow: 4px 0 32px rgba(0,0,0,0.8) !important;
        display: flex !important; 
        flex-direction: column !important;
        overflow-y: auto !important;
      }
      .mobile-menu-btn {
        display: flex !important;
      }
      /* Force main content to use full width on mobile */
      .mobile-main-content {
        width: 100vw !important;
        padding-top: 60px !important; /* Space for the hamburger */
      }
      /* Ensure modals fit the screen */
      [id$="-modal"] > div {
        width: 95vw !important;
        max-width: 95vw !important;
        max-height: 85vh !important;
        overflow-y: auto !important;
        padding: 20px !important;
      }
    }
    @media (min-width: 901px) {
      .mobile-menu-btn { display: none !important; }
      .mobile-sidebar-hidden, .mobile-sidebar-visible { display: flex !important; }
    }
  `;
  document.head.appendChild(style);

  // 2. Setup Mobile Drawer Menu
  let menuSetupDone = false;
  
  function setupMobileMenu() {
    if (menuSetupDone || document.getElementById('mobile-hamburger')) return;
    
    // Find the root layout container (usually #root > div)
    const rootDiv = document.querySelector('#root > div');
    if (!rootDiv) return;
    
    const children = Array.from(rootDiv.children);
    if (children.length < 2) return;
    
    // Heuristic: The first child is usually the Sidebar, second is Main Content
    const sidebar = children[0];
    const mainContent = children[1];
    
    // Only apply if it looks like a sidebar layout (e.g. sidebar is narrower than main)
    sidebar.classList.add('mobile-sidebar-hidden');
    mainContent.classList.add('mobile-main-content');
    
    menuSetupDone = true;

    // Create Hamburger Button
    const btn = document.createElement('button');
    btn.id = 'mobile-hamburger';
    btn.className = 'mobile-menu-btn';
    btn.style.cssText = `
      position: fixed; top: 12px; left: 12px; z-index: 99990;
      background: rgba(15,15,15,0.8); border: 1px solid rgba(255,255,255,0.15);
      border-radius: 8px; width: 44px; height: 44px;
      align-items: center; justify-content: center; color: #fff;
      font-size: 20px; cursor: pointer; backdrop-filter: blur(10px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    `;
    // Simple SVG Hamburger
    btn.innerHTML = \`<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>\`;
    document.body.appendChild(btn);

    // Create Backdrop Overlay
    const overlay = document.createElement('div');
    overlay.style.cssText = `
      position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 99998;
      display: none; backdrop-filter: blur(4px); transition: opacity 0.2s; opacity: 0;
    `;
    document.body.appendChild(overlay);

    let isOpen = false;
    function toggleMenu() {
      isOpen = !isOpen;
      if (isOpen) {
        sidebar.classList.remove('mobile-sidebar-hidden');
        sidebar.classList.add('mobile-sidebar-visible');
        overlay.style.display = 'block';
        // Small delay for CSS transition if we added one
        requestAnimationFrame(() => { overlay.style.opacity = '1'; });
      } else {
        overlay.style.opacity = '0';
        sidebar.classList.remove('mobile-sidebar-visible');
        setTimeout(() => {
          sidebar.classList.add('mobile-sidebar-hidden');
          overlay.style.display = 'none';
        }, 200);
      }
    }

    btn.onclick = toggleMenu;
    overlay.onclick = toggleMenu;
    
    // Auto-hide menu when clicking navigation links inside the sidebar
    sidebar.addEventListener('click', (e) => {
      if (window.innerWidth <= 900 && e.target.closest('a, button, [role="button"], li')) {
        setTimeout(() => { if (isOpen) toggleMenu(); }, 150);
      }
    });

    // Handle Resize Events
    window.addEventListener('resize', () => {
      if (window.innerWidth > 900) {
        sidebar.classList.remove('mobile-sidebar-hidden');
        sidebar.classList.remove('mobile-sidebar-visible');
        overlay.style.display = 'none';
        isOpen = false;
      } else if (!isOpen) {
        sidebar.classList.add('mobile-sidebar-hidden');
      }
    });
  }

  // Since it's a SPA (React), wait for the DOM to populate
  const observer = new MutationObserver(() => {
    if (document.querySelector('#root > div > div')) {
      setupMobileMenu();
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
  
  // Try immediate execution just in case
  setTimeout(setupMobileMenu, 500);

})();
