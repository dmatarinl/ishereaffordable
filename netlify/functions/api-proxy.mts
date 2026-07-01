declare const Netlify: {
  env: {
    get(name: string): string | undefined;
  };
};

const EXPECTED_API_ORIGIN = "https://is-here-affordable-api.onrender.com";
const PROXY_PREFIXES = ["/.netlify/functions/api-proxy", "/api-proxy"];
const STABLE_READ_PATHS = new Set([
  "/api/public-transport/fares",
  "/api/sources/rules",
  "/api/trash-tax/rules",
]);
const STABLE_READ_CACHE =
  "public, durable, max-age=3600, stale-while-revalidate=86400";
const AFFORDABILITY_CACHE =
  "public, durable, max-age=300, stale-while-revalidate=900";
const BROWSER_REVALIDATE = "public, max-age=0, must-revalidate";

function jsonResponse(body: unknown, status: number) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });
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
  let apiPath = incomingUrl.pathname;
  for (const prefix of PROXY_PREFIXES) {
    if (apiPath.startsWith(prefix)) {
      apiPath = apiPath.slice(prefix.length);
      break;
    }
  }
  if (!apiPath.startsWith("/")) {
    apiPath = `/${apiPath}`;
  }

  const upstreamPath = apiPath === "/api" || apiPath.startsWith("/api/")
    ? apiPath
    : `/api${apiPath}`;
  const backendUrl = new URL(upstreamPath, apiOrigin);
  backendUrl.search = incomingUrl.search;
  return backendUrl;
}

function cdnCacheControlFor(backendUrl: URL, status: number) {
  if (status < 200 || status >= 300) {
    return null;
  }

  if (backendUrl.pathname === "/api/affordability") {
    return AFFORDABILITY_CACHE;
  }

  if (STABLE_READ_PATHS.has(backendUrl.pathname)) {
    return STABLE_READ_CACHE;
  }

  return null;
}

export default async (req: Request) => {
  if (!["GET", "HEAD"].includes(req.method)) {
    return jsonResponse({ detail: "Method not allowed" }, 405);
  }

  let backendUrl: URL | null;
  try {
    backendUrl = backendUrlFor(req);
    if (!backendUrl) {
      return jsonResponse(
        {
          detail:
            "API_ORIGIN is not configured. Deploy the Python API and set the Netlify environment variable to enable live data.",
        },
        503,
      );
    }
  } catch {
    return jsonResponse({ detail: "Backend API origin is not allowed" }, 503);
  }

  const proxySecret = Netlify.env.get("BACKEND_PROXY_SECRET");
  if (!proxySecret) {
    return jsonResponse({ detail: "Backend proxy secret is not configured" }, 503);
  }

  try {
    const upstream = await fetch(backendUrl, {
      method: req.method,
      headers: {
        accept: req.headers.get("accept") ?? "application/json",
        "x-ishereaffordable-proxy-secret": proxySecret,
        "user-agent": "IsHereAffordableNetlifyProxy/0.1",
      },
    });
    const headers = new Headers(upstream.headers);
    headers.delete("content-encoding");
    headers.delete("content-length");
    headers.delete("transfer-encoding");
    const cdnCacheControl = cdnCacheControlFor(backendUrl, upstream.status);
    if (cdnCacheControl) {
      headers.set("Netlify-CDN-Cache-Control", cdnCacheControl);
      headers.set("Cache-Control", BROWSER_REVALIDATE);
    } else {
      headers.set("Cache-Control", "no-store");
    }

    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers,
    });
  } catch {
    return jsonResponse({ detail: "Backend API is unavailable" }, 502);
  }
};

export const config = {
  path: [
    "/api/public-transport/fares",
    "/api/sources/rules",
    "/api/trash-tax/rules",
  ],
};
