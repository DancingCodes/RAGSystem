export type KnowledgeBase = {
  id: string;
  name: string;
  created_at: string;
};

export type StoredFile = {
  id: string;
  knowledge_base_id: string;
  file_name: string;
  size: number;
  status: "queued" | "processing" | "succeeded" | "failed";
  created_at: string;
};

type MockDB = {
  knowledge_bases: KnowledgeBase[];
  files: StoredFile[];
};

function nowIso() {
  return new Date().toISOString();
}

function initDb(): MockDB {
  return {
    knowledge_bases: [
      { id: crypto.randomUUID(), name: "示例知识库", created_at: nowIso() },
    ],
    files: [],
  };
}

export function db(): MockDB {
  const g = globalThis as unknown as { __RAG_MOCK_DB__?: MockDB };
  if (!g.__RAG_MOCK_DB__) g.__RAG_MOCK_DB__ = initDb();
  return g.__RAG_MOCK_DB__;
}
