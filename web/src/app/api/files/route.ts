import { db } from "@/app/api/_mock/store";

export async function POST(request: Request) {
  const form = await request.formData();
  const knowledgeBaseId = String(form.get("knowledge_base_id") ?? "").trim();
  const file = form.get("file");

  if (!knowledgeBaseId)
    return Response.json(
      { error: "knowledge_base_id required" },
      { status: 400 },
    );
  if (!(file instanceof File))
    return Response.json({ error: "file required" }, { status: 400 });

  const record = {
    id: crypto.randomUUID(),
    knowledge_base_id: knowledgeBaseId,
    file_name: file.name || "unknown.pdf",
    size: file.size ?? 0,
    status: "succeeded" as const,
    created_at: new Date().toISOString(),
  };
  db().files.unshift(record);

  return Response.json({
    id: record.id,
    file_name: record.file_name,
    status: record.status,
  });
}

