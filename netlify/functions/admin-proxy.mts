declare const Netlify: {
  env: {
    get(name: string): string | undefined;
  };
};

const EXPECTED_API_ORIGIN = "https://is-here-affordable-api.onrender.com";
const ADMIN_PREFIXES = ["/.netlify/functions/admin-proxy", "/admin-api"];

function jsonResponse(body: unknown, status: number) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}

function secretFromRequest(req: Request) {
  const authorization = req.headers.get("authorization") ?? "";
  const [scheme, token] = authorization.split(/\s+/, 2);
  if (scheme?.toLowerCase() === "bearer" && token) {
    return token;
  }
  return req.headers.get("x-ishereaffordable-admin-secret");
}

function secretsEqual(left: string, right: string) {
  if (left.length !== right.length) {
    return false;
  }

  let difference = 0;
  for (let index = 0; index < left.length; index += 1) {
    difference |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return difference === 0;
}

function backendUrlFor(req: Request) {
  const apiOrigin = Netlify.env.get("API_ORIGIN");
  if (!apiOrigin) {
    return null;
  }

  const parsedApiOrigin = new URL(apiOrigin);
  if (parsedApiOrigin.origin !== EXPECTED_API_ORIGIN) {
    throw new Error("API_ORIGIN is not allowlisted");
  }

  const incomingUrl = new URL(req.url);
  let adminPath = incomingUrl.pathname;
  for (const prefix of ADMIN_PREFIXES) {
    if (adminPath.startsWith(prefix)) {
      adminPath = adminPath.slice(prefix.length);
      break;
    }
  }
  if (!adminPath.startsWith("/")) {
    adminPath = `/${adminPath}`;
  }

  const backendUrl = new URL(`/api/admin${adminPath}`, apiOrigin);
  backendUrl.search = incomingUrl.search;
  return backendUrl;
}

export default async (req: Request) => {
  if (!["GET", "POST"].includes(req.method)) {
    return jsonResponse({ detail: "Method not allowed" }, 405);
  }

  const adminSecret = Netlify.env.get("ADMIN_API_SECRET");
  const proxySecret = Netlify.env.get("BACKEND_PROXY_SECRET");
  if (!adminSecret || !proxySecret) {
    return jsonResponse({ detail: "Admin proxy is not configured" }, 503);
  }

  const providedSecret = secretFromRequest(req);
  if (!providedSecret || !secretsEqual(providedSecret, adminSecret)) {
    return jsonResponse({ detail: "Admin credentials required" }, 401);
  }

  let backendUrl: URL | null;
  try {
    backendUrl = backendUrlFor(req);
    if (!backendUrl) {
      return jsonResponse({ detail: "API_ORIGIN is not configured" }, 503);
    }
  } catch {
    return jsonResponse({ detail: "Backend API origin is not allowed" }, 503);
  }

  try {
    const headers: Record<string, string> = {
      accept: req.headers.get("accept") ?? "application/json",
      "x-ishereaffordable-admin-secret": adminSecret,
      "x-ishereaffordable-proxy-secret": proxySecret,
      "user-agent": "IsHereAffordableAdminProxy/0.1",
    };
    const contentType = req.headers.get("content-type");
    if (contentType) {
      headers["content-type"] = contentType;
    }

    const upstream = await fetch(backendUrl, {
      method: req.method,
      headers,
      body: req.method === "POST" ? await req.text() : undefined,
    });
    const responseHeaders = new Headers(upstream.headers);
    responseHeaders.delete("content-encoding");
    responseHeaders.delete("content-length");
    responseHeaders.delete("transfer-encoding");
    responseHeaders.set("cache-control", "no-store");

    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
  } catch {
    return jsonResponse({ detail: "Backend admin API is unavailable" }, 502);
  }
};

export const config = {
  path: ["/admin-api/sources/status", "/admin-api/refresh"],
};
