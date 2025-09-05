export async function POST(req: Request) {
  const body = await req.json();
  const upstream = await fetch(`${process.env.API_URL}/chat/stream`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!upstream.body) return new Response("No stream", { status: 502 });
  return new Response(upstream.body, {
    headers: { "content-type": "text/plain; charset=utf-8" },
  });
}
