import { db } from "@/app/api/_mock/store";

export async function GET() {
  const data = db().knowledge_bases.map((kb) => ({ id: kb.id, name: kb.name }));
  return Response.json(data);
}

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as
    | { name?: unknown }
    | null;
  const name = typeof body?.name === "string" ? body.name.trim() : "";
  if (!name) return Response.json({ error: "name required" }, { status: 400 });

  const kb = { id: crypto.randomUUID(), name, created_at: new Date().toISOString() };
  db().knowledge_bases.unshift(kb);
  return Response.json({ id: kb.id, name: kb.name });
}

