declare const Netlify: {
  env: {
    get(name: string): string | undefined;
  };
};

const PROXY_PREFIXES = ["/.netlify/functions/api-proxy", "/api-proxy"];

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

export default async (req: Request) => {
  if (!["GET", "HEAD"].includes(req.method)) {
    return jsonResponse({ detail: "Method not allowed" }, 405);
  }

  const backendUrl = backendUrlFor(req);
  if (!backendUrl) {
    return jsonResponse(
      {
        detail:
          "API_ORIGIN is not configured. Deploy the Python API and set the Netlify environment variable to enable live data.",
      },
      503,
    );
  }

  try {
    const upstream = await fetch(backendUrl, {
      method: req.method,
      headers: {
        accept: req.headers.get("accept") ?? "application/json",
        "user-agent": "IsHereAffordableNetlifyProxy/0.1",
      },
    });
    const headers = new Headers(upstream.headers);
    headers.delete("content-encoding");
    headers.delete("content-length");
    headers.delete("transfer-encoding");

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
    "/api/affordability",
    "/api/cities",
    "/api/electricity/profiles",
    "/api/gas/profiles",
    "/api/public-transport/fares",
    "/api/sources/rules",
    "/api/sources/status",
    "/api/trash-tax/rules",
    "/api/water/profiles",
  ],
};
