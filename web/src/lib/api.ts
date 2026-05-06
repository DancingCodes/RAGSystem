import { API_BASE_URL } from "@/lib/env";

export type KnowledgeBase = {
  id: string;
  name: string;
};

export type UploadedFile = {
  id: string;
  file_name: string;
  status?: string;
};

export type ChatResponse = {
  answer: string;
  citations?: Array<{
    file_name: string;
    page_number?: number;
    text?: string;
  }>;
};

async function request<T>(
  path: string,
  init?: RequestInit & { timeoutMs?: number },
): Promise<T> {
  const { timeoutMs, ...rest } = init ?? {};
  const controller = new AbortController();
  const timer =
    typeof timeoutMs === "number"
      ? setTimeout(() => controller.abort(), timeoutMs)
      : undefined;

  try {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      ...rest,
      signal: controller.signal,
      headers: {
        ...(rest.headers ?? {}),
      },
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(
        `HTTP ${res.status} ${res.statusText}${text ? `: ${text}` : ""}`,
      );
    }
    return (await res.json()) as T;
  } finally {
    if (timer) clearTimeout(timer);
  }
}

export async function listKnowledgeBases(): Promise<KnowledgeBase[]> {
  return request<KnowledgeBase[]>("/api/knowledge-bases", { timeoutMs: 8000 });
}

export async function createKnowledgeBase(name: string): Promise<KnowledgeBase> {
  return request<KnowledgeBase>("/api/knowledge-bases", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
    timeoutMs: 10000,
  });
}

export async function uploadPdf(params: {
  knowledgeBaseId: string;
  file: File;
}): Promise<UploadedFile> {
  const form = new FormData();
  form.append("knowledge_base_id", params.knowledgeBaseId);
  form.append("file", params.file);

  return request<UploadedFile>("/api/files", {
    method: "POST",
    body: form,
    timeoutMs: 60000,
  });
}

export async function chat(params: {
  knowledgeBaseId: string;
  question: string;
}): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      knowledge_base_id: params.knowledgeBaseId,
      question: params.question,
    }),
    timeoutMs: 60000,
  });
}

