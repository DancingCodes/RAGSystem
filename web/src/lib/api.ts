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

export async function listKnowledgeBases(): Promise<KnowledgeBase[]> {
  return api.get("/api/knowledge-bases").json();
}

export async function createKnowledgeBase(name: string): Promise<KnowledgeBase> {
  return api
    .post("/api/knowledge-bases", { json: { name } })
    .json();
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
