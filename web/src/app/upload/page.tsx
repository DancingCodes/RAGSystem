"use client";

import { addDocument, listKnowledgeBases } from "@/lib/api";
import { useMemo, useState } from "react";

const FILEHUB_UPLOAD_URL = "https://filehub.moonc.love/api/upload";

type Stage = "idle" | "uploading_filehub" | "registering_rag";

export default function UploadPage() {
  const [kbs, setKbs] = useState<Array<{ id: string; name: string }>>([]);
  const [kbId, setKbId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState<Stage>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const canUpload = useMemo(
    () => Boolean(kbId) && Boolean(file) && stage === "idle",
    [file, kbId, stage],
  );

  async function loadKbs() {
    setLoading(true);
    setError(null);
    try {
      const data = await listKnowledgeBases();
      setKbs(data);
      if (!kbId && data.length > 0) setKbId(data[0]!.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function onUpload() {
    if (!kbId || !file) return;
    setError(null);
    setResult(null);

    // Stage 1: upload to filehub
    setStage("uploading_filehub");
    const form = new FormData();
    form.append("file", file);
    let fileUrl = "";
    let fileName = file.name;

    try {
      const res = await fetch(FILEHUB_UPLOAD_URL, {
        method: "POST",
        body: form,
      });
      if (!res.ok) throw new Error(`filehub HTTP ${res.status}`);
      const json = await res.json();
      if (json.code !== 200) throw new Error(json.msg ?? "filehub upload failed");
      fileUrl = json.data?.file_url ?? "";
      fileName = json.data?.file_name ?? fileName;
      if (!fileUrl) throw new Error("filehub returned empty file_url");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setStage("idle");
      return;
    }

    // Stage 2: register with RAG backend
    setStage("registering_rag");
    try {
      const res = await addDocument({
        knowledgeBaseId: kbId,
        fileUrl,
        fileName,
      });
      setResult(`已提交：${res.file_name}（id=${res.id}${res.status ? `, status=${res.status}` : ""}）`);
      setFile(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setStage("idle");
    }
  }

  const stageLabel: Record<Stage, string> = {
    idle: "开始上传",
    uploading_filehub: "上传到文件服务…",
    registering_rag: "注册到 RAG…",
  };

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-zinc-200 bg-white p-6">
        <h1 className="text-lg font-semibold tracking-tight">上传 PDF</h1>
        <p className="mt-2 text-sm text-zinc-600">
          仅支持可复制文本的 PDF。扫描版 PDF 暂不支持。
        </p>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="space-y-1">
            <div className="text-xs font-medium text-zinc-700">知识库</div>
            <select
              value={kbId}
              onChange={(e) => setKbId(e.target.value)}
              disabled={loading || kbs.length === 0}
              className="h-10 w-full rounded-md border border-zinc-200 bg-white px-3 text-sm outline-none focus:ring-2 focus:ring-zinc-200 disabled:opacity-60"
            >
              {kbs.map((kb) => (
                <option key={kb.id} value={kb.id}>
                  {kb.name}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-1">
            <div className="text-xs font-medium text-zinc-700">PDF 文件</div>
            <input
              type="file"
              accept="application/pdf"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="block w-full text-sm text-zinc-700 file:mr-4 file:rounded-md file:border file:border-zinc-200 file:bg-white file:px-3 file:py-2 file:text-sm file:font-medium file:text-zinc-900"
            />
          </label>
        </div>

        <div className="mt-4 flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            onClick={() => void onUpload()}
            disabled={!canUpload}
            className="h-10 rounded-md bg-zinc-900 px-4 text-sm font-medium text-white disabled:opacity-60"
          >
            {stageLabel[stage]}
          </button>
          <button
            type="button"
            onClick={() => void loadKbs()}
            className="h-10 rounded-md border border-zinc-200 bg-white px-4 text-sm font-medium text-zinc-900 hover:bg-zinc-50"
          >
            刷新知识库
          </button>
        </div>

        {error ? (
          <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
            失败：{error}
          </div>
        ) : null}
        {result ? (
          <div className="mt-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-900">
            {result}
          </div>
        ) : null}
      </div>
    </div>
  );
}
