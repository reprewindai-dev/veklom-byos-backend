const BASE_NOTIFICATIONS_URL = "https://dashboard.base.org/api/v1/notifications";
const ADDRESS_RE = /^0x[a-fA-F0-9]{40}$/;

export const BASE_APP_URL =
  process.env.BASE_APP_URL || "https://veklomdiscovery.vercel.app";

function jsonError(message, status = 400) {
  return Response.json({ success: false, error: message }, { status });
}

export function requireAdmin(request) {
  const configuredKey = process.env.VEKLOM_ADMIN_API_KEY;

  if (!configuredKey) {
    return jsonError("Notification admin key is not configured", 503);
  }

  const authHeader = request.headers.get("authorization") || "";
  const bearer = authHeader.startsWith("Bearer ") ? authHeader.slice(7) : "";
  const adminHeader = request.headers.get("x-admin-key") || "";

  if (bearer !== configuredKey && adminHeader !== configuredKey) {
    return jsonError("Unauthorized", 401);
  }

  return null;
}

function requireDashboardKey() {
  if (!process.env.BASE_DASHBOARD_API_KEY) {
    return jsonError("Base Dashboard API key is not configured", 503);
  }

  return null;
}

async function callBaseNotifications(path, init = {}) {
  const configError = requireDashboardKey();
  if (configError) return configError;

  const upstream = await fetch(`${BASE_NOTIFICATIONS_URL}${path}`, {
    ...init,
    headers: {
      "x-api-key": process.env.BASE_DASHBOARD_API_KEY,
      "Content-Type": "application/json",
      ...(init.headers || {}),
    },
    cache: "no-store",
  });

  const payload = await upstream.json().catch(() => ({
    success: false,
    error: "Base notification service returned a non-JSON response",
  }));

  return Response.json(payload, {
    status: upstream.status,
    headers: {
      "Cache-Control": "no-store",
    },
  });
}

export function validateAddress(address) {
  return typeof address === "string" && ADDRESS_RE.test(address);
}

export function validateTargetPath(path) {
  return path === undefined || (typeof path === "string" && path.startsWith("/") && path.length <= 500);
}

export function validateNotificationPayload(payload) {
  if (!Array.isArray(payload.wallet_addresses) || payload.wallet_addresses.length < 1) {
    return "wallet_addresses must include at least one address";
  }

  if (payload.wallet_addresses.length > 1000) {
    return "wallet_addresses cannot exceed 1,000 addresses";
  }

  if (payload.wallet_addresses.some((address) => !validateAddress(address))) {
    return "wallet_addresses contains an invalid EVM address";
  }

  if (typeof payload.title !== "string" || payload.title.length < 1 || payload.title.length > 30) {
    return "title is required and must be 30 characters or fewer";
  }

  if (typeof payload.message !== "string" || payload.message.length < 1 || payload.message.length > 200) {
    return "message is required and must be 200 characters or fewer";
  }

  if (!validateTargetPath(payload.target_path)) {
    return "target_path must start with / and be 500 characters or fewer";
  }

  return null;
}

export async function getNotificationUsers(request) {
  const authError = requireAdmin(request);
  if (authError) return authError;

  const { searchParams } = new URL(request.url);
  const params = new URLSearchParams({
    app_url: BASE_APP_URL,
  });

  const notificationEnabled = searchParams.get("notification_enabled");
  const cursor = searchParams.get("cursor");
  const limit = searchParams.get("limit");

  if (notificationEnabled === "true" || notificationEnabled === "false") {
    params.set("notification_enabled", notificationEnabled);
  }

  if (cursor) params.set("cursor", cursor);

  if (limit) {
    const parsedLimit = Number(limit);
    if (!Number.isInteger(parsedLimit) || parsedLimit < 1 || parsedLimit > 500) {
      return jsonError("limit must be an integer from 1 to 500");
    }
    params.set("limit", String(parsedLimit));
  }

  return callBaseNotifications(`/app/users?${params.toString()}`, { method: "GET" });
}

export async function getNotificationStatus(request) {
  const authError = requireAdmin(request);
  if (authError) return authError;

  const payload = await request.json().catch(() => null);
  const walletAddress = payload?.wallet_address;

  if (!validateAddress(walletAddress)) {
    return jsonError("wallet_address must be a valid EVM address");
  }

  return callBaseNotifications("/app/user/status", {
    method: "POST",
    body: JSON.stringify({
      app_url: BASE_APP_URL,
      wallet_address: walletAddress,
    }),
  });
}

export async function sendNotification(request) {
  const authError = requireAdmin(request);
  if (authError) return authError;

  const payload = await request.json().catch(() => null);
  if (!payload) {
    return jsonError("Invalid JSON body");
  }

  const validationError = validateNotificationPayload(payload);
  if (validationError) {
    return jsonError(validationError);
  }

  return callBaseNotifications("/send", {
    method: "POST",
    body: JSON.stringify({
      app_url: BASE_APP_URL,
      wallet_addresses: [...new Set(payload.wallet_addresses)],
      title: payload.title,
      message: payload.message,
      ...(payload.target_path ? { target_path: payload.target_path } : {}),
    }),
  });
}
