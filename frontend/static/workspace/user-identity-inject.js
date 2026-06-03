(function () {
  const base = (window.__VEKLOM_API_BASE__ || "/api/v1").replace(/\/+$/, "");
  let cachedUserData = null;

  function authHeaders() {
    const token =
      localStorage.getItem("veklom_token") ||
      localStorage.getItem("veklom-auth-token") ||
      localStorage.getItem("auth_token") ||
      localStorage.getItem("token") ||
      sessionStorage.getItem("veklom-auth-token") ||
      "";
    return {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  }

  async function fetchUserData() {
    try {
      const res = await fetch(`${base}/auth/me`, {
        headers: authHeaders(),
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        cachedUserData = data;
        console.log("User data from /auth/me:", data);
        return data;
      }
    } catch (e) {
      console.error("Failed to fetch user data:", e);
    }
    return null;
  }

  function getInitials(name) {
    if (!name) return "?";
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) {
      return parts[0].charAt(0).toUpperCase();
    }
    return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
  }

  function injectUserIdentity(userData) {
    if (!userData) return;

    const name = userData.full_name || userData.name || userData.email || "User";
    const email = userData.email || "";
    const initials = getInitials(name);
    const workspaceId = userData.workspace?.id || userData.workspace_id || "";
    const workspaceName = userData.workspace?.name || "";

    console.log("Injecting user identity:", { name, email, initials, workspaceId, workspaceName });

    // Find and replace ALL placeholder names - be more aggressive
    const allTextElements = document.querySelectorAll("span, div, p, h1, h2, h3, h4, h5, h6, button, a");
    allTextElements.forEach((el) => {
      const text = el.textContent.trim();
      // Replace common placeholder patterns
      if (
        text === "User" ||
        text === "John Doe" ||
        text === "Your Name" ||
        text === "placeholder" ||
        text === "EJ" ||
        text === "JD" ||
        text === "AB" ||
        text === "Anthony Milner" ||
        text === "Anthony Millwater" ||
        text === "Acme Corp" ||
        text === "Demo User" ||
        text === "Test User"
      ) {
        el.textContent = name;
      }
    });

    // Find and replace placeholder emails - be more aggressive
    allTextElements.forEach((el) => {
      const text = el.textContent.trim();
      if (
        text === "user@example.com" ||
        text === "email@example.com" ||
        text === "your@email.com" ||
        text === "demo@example.com" ||
        text === "test@example.com" ||
        text === "anthony@acme.com" ||
        text === "anthony.milner@acme.com" ||
        text === "anthony.millwater@acme.com"
      ) {
        el.textContent = email;
      }
    });

    // Find and replace placeholder initials in avatars/logos - be more aggressive
    allTextElements.forEach((el) => {
      const text = el.textContent.trim();
      if (
        text === "EJ" ||
        text === "JD" ||
        text === "AB" ||
        text === "AM" ||
        text === "??" ||
        text === "??"
      ) {
        el.textContent = initials;
      }
    });

    // Inject workspace ID into dropdown if found
    if (workspaceId) {
      const dropdownElements = document.querySelectorAll("[class*='dropdown'], [class*='menu'], [class*='profile']");
      dropdownElements.forEach((el) => {
        const existingWorkspaceId = el.querySelector("[data-workspace-id]");
        if (!existingWorkspaceId) {
          const workspaceIdEl = document.createElement("div");
          workspaceIdEl.style.cssText = "font-size: 11px; color: #888; margin-top: 4px;";
          workspaceIdEl.textContent = `Workspace: ${workspaceId}`;
          workspaceIdEl.dataset.workspaceId = workspaceId;
          el.appendChild(workspaceIdEl);
        }
      });
    }

    // Also update elements with data attributes
    document.querySelectorAll("[data-user-name]").forEach((el) => {
      el.dataset.userName = name;
    });
    document.querySelectorAll("[data-user-initials]").forEach((el) => {
      el.dataset.userInitials = initials;
    });
    document.querySelectorAll("[data-user-email]").forEach((el) => {
      el.dataset.userEmail = email;
    });
    document.querySelectorAll("[data-workspace-id]").forEach((el) => {
      el.dataset.workspaceId = workspaceId;
    });
  }

  async function initUserIdentityInjection() {
    console.log("Initializing user identity injection...");
    const userData = await fetchUserData();
    if (userData) {
      injectUserIdentity(userData);
    }

    // Re-inject on page changes (SPA navigation)
    const originalPushState = history.pushState;
    const originalReplaceState = history.replaceState;

    history.pushState = function (...args) {
      originalPushState.apply(this, args);
      setTimeout(() => {
        fetchUserData().then((data) => {
          if (data) injectUserIdentity(data);
        });
      }, 500);
    };

    history.replaceState = function (...args) {
      originalReplaceState.apply(this, args);
      setTimeout(() => {
        fetchUserData().then((data) => {
          if (data) injectUserIdentity(data);
        });
      }, 500);
    };

    window.addEventListener("hashchange", () => {
      setTimeout(() => {
        fetchUserData().then((data) => {
          if (data) injectUserIdentity(data);
        });
      }, 500);
    });

    // Also re-inject periodically (every 5 seconds)
    setInterval(() => {
      fetchUserData().then((data) => {
        if (data) injectUserIdentity(data);
      });
    }, 5000);

    // Also re-inject when DOM changes (for dynamic content)
    const observer = new MutationObserver(() => {
      if (cachedUserData) {
        observer.disconnect();
        injectUserIdentity(cachedUserData);
        observer.observe(document.body, { childList: true, subtree: true });
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initUserIdentityInjection);
  } else {
    initUserIdentityInjection();
  }
})();
