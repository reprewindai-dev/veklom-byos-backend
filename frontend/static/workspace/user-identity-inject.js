(function () {
  const base = (window.__VEKLOM_API_BASE__ || "/api/v1").replace(/\/+$/, "");

  function authHeaders() {
    const token =
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
        return await res.json();
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

    const name = userData.name || userData.full_name || userData.email || "User";
    const email = userData.email || "";
    const initials = getInitials(name);

    // Find and replace placeholder names in dropdown menus
    const nameElements = document.querySelectorAll(
      "[class*='name'], [class*='user'], [class*='profile'], span, div"
    );
    nameElements.forEach((el) => {
      const text = el.textContent.trim();
      // Replace common placeholder patterns
      if (
        text === "User" ||
        text === "John Doe" ||
        text === "Your Name" ||
        text === "placeholder" ||
        text === "EJ" ||
        text === "JD" ||
        text === "AB"
      ) {
        el.textContent = name;
      }
    });

    // Find and replace placeholder emails
    const emailElements = document.querySelectorAll(
      "[class*='email'], [class*='contact']"
    );
    emailElements.forEach((el) => {
      const text = el.textContent.trim();
      if (
        text === "user@example.com" ||
        text === "email@example.com" ||
        text === "your@email.com"
      ) {
        el.textContent = email;
      }
    });

    // Find and replace placeholder initials in avatars/logos
    const avatarElements = document.querySelectorAll(
      "[class*='avatar'], [class*='initial'], [class*='logo'], [class*='user-icon'], div[style*='border-radius:50%'], div[style*='border-radius: 50%']"
    );
    avatarElements.forEach((el) => {
      const text = el.textContent.trim();
      if (
        text === "EJ" ||
        text === "JD" ||
        text === "AB" ||
        text === "??" ||
        text === "??"
      ) {
        el.textContent = initials;
      }
    });

    // Also update elements with data attributes
    document.querySelectorAll("[data-user-name]").forEach((el) => {
      el.dataset.userName = name;
    });
    document.querySelectorAll("[data-user-initials]").forEach((el) => {
      el.dataset.userInitials = initials;
    });
  }

  async function initUserIdentityInjection() {
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

    // Also re-inject periodically (every 10 seconds)
    setInterval(() => {
      fetchUserData().then((data) => {
        if (data) injectUserIdentity(data);
      });
    }, 10000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initUserIdentityInjection);
  } else {
    initUserIdentityInjection();
  }
})();
