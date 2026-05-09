import { api } from "@/lib/http";

export type KnowledgeBase = {
  id: string;
  name: string;
};

export type UploadedFile = {
  id: string;
  file_name: string;
};

export type ChatResponse = {
  answer: string;
  citations?: Array<{
    file_name: string;
    page_number?: number;
    text?: string;
  }>;
};

export type Citation = {
  file_name: string;
  page_number?: number;
  text?: string;
};

export type SSEEvent =
  | { type: "token"; content: string }
  | { type: "done"; citations: Citation[] }
  | { type: "error"; message: string };

export async function listKnowledgeBases(): Promise<KnowledgeBase[]> {
  return api.get("/api/knowledge-bases").json();
}

export async function createKnowledgeBase(name: string): Promise<KnowledgeBase> {
  return api
    .post("/api/knowledge-bases", { json: { name } })
    .json();
}

export async function deleteKnowledgeBase(id: string): Promise<void> {
  await api.delete(`/api/knowledge-bases/${id}`);
}

export async function addDocument(params: {
  knowledgeBaseId: string;
  file: File;
}): Promise<UploadedFile> {
  const form = new FormData();
  form.append("file", params.file);
  form.append("knowledge_base_id", params.knowledgeBaseId);

  return api
    .post("/api/documents", {
      body: form,
      timeout: 120000,
    })
    .json();
}

export async function chat(params: {
  knowledgeBaseId: string;
  question: string;
}): Promise<ChatResponse> {
  return api
    .post("/api/chat", {
      json: {
        knowledge_base_id: params.knowledgeBaseId,
        question: params.question,
      },
      timeout: 60000,
    })
    .json();
}

export async function* chatStream(params: {
  knowledgeBaseId: string;
  question: string;
}): AsyncGenerator<SSEEvent> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      knowledge_base_id: params.knowledgeBaseId,
      question: params.question,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ msg: "request failed" }));
    throw new Error(err.msg || "request failed");
  }

  const ct = res.headers.get("content-type") || "";
  if (!ct.includes("text/event-stream")) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.msg || "request failed");
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";

    for (const part of parts) {
      const trimmed = part.trim();
      if (trimmed.startsWith("data: ")) {
        yield JSON.parse(trimmed.slice(6));
      }
    }
  }
}
