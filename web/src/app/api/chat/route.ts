import { db } from "@/app/api/_mock/store";

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as
    | { knowledge_base_id?: unknown; question?: unknown }
    | null;
  const knowledgeBaseId =
    typeof body?.knowledge_base_id === "string" ? body.knowledge_base_id : "";
  const question = typeof body?.question === "string" ? body.question.trim() : "";

  if (!knowledgeBaseId)
    return Response.json(
      { error: "knowledge_base_id required" },
      { status: 400 },
    );
  if (!question) return Response.json({ error: "question required" }, { status: 400 });

  const kb = db().knowledge_bases.find((x) => x.id === knowledgeBaseId);
  const files = db().files.filter((f) => f.knowledge_base_id === knowledgeBaseId);

  if (files.length === 0) {
    return Response.json({
      answer: `当前知识库「${kb?.name ?? "未命名"}」没有已上传的 PDF，无法基于资料回答。\n\n问题：${question}`,
      citations: [],
    });
  }

  const citations = files.slice(0, 3).map((f) => ({
    file_name: f.file_name,
    page_number: 1,
    text: `（模拟引用）来自 ${f.file_name} 的示例片段。`,
  }));

  return Response.json({
    answer: `（模拟回答）我将基于「${kb?.name ?? "未命名"}」中的资料回答：\n\n${question}\n\n目前为模拟接口返回，后续接入 FastAPI + 向量库后会替换为真实检索结果。`,
    citations,
  });
}

