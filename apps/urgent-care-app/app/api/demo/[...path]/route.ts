const ALLOWED_ROUTES = [
  { method: "POST", pattern: /^sessions$/ },
  { method: "GET", pattern: /^sessions\/[^/]+$/ },
  { method: "POST", pattern: /^sessions\/[^/]+\/respond$/ },
  {
    method: "POST",
    pattern: /^clinician\/sessions\/[^/]+\/complete$/,
  },
] as const;

export const dynamic = "force-dynamic";

type Context = { params: Promise<{ path: string[] }> };

async function proxy(request: Request, context: Context): Promise<Response> {
  const { path } = await context.params;
  const relativePath = path.map(encodeURIComponent).join("/");
  const allowed = ALLOWED_ROUTES.some(
    (route) =>
      route.method === request.method && route.pattern.test(relativePath),
  );
  if (!allowed) {
    return Response.json({ detail: "Route not allowed" }, { status: 404 });
  }

  const incomingUrl = new URL(request.url);
  const baseUrl = (
    process.env.ALIGN_API_BASE_URL ?? "http://localhost:8000"
  ).replace(/\/$/, "");
  const upstreamUrl = `${baseUrl}/${relativePath}${incomingUrl.search}`;
  const body =
    request.method === "GET" ? undefined : await request.arrayBuffer();

  try {
    const upstream = await fetch(upstreamUrl, {
      method: request.method,
      body,
      cache: "no-store",
      headers: {
        Accept: "application/json",
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
    });
    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "Content-Type":
          upstream.headers.get("Content-Type") ?? "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return Response.json(
      { detail: "Align API is unavailable" },
      { status: 502, headers: { "Cache-Control": "no-store" } },
    );
  }
}

export function GET(request: Request, context: Context) {
  return proxy(request, context);
}

export function POST(request: Request, context: Context) {
  return proxy(request, context);
}
