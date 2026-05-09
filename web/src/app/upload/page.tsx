"use client";

import { addDocument, listKnowledgeBases } from "@/lib/api";
import { useEffect, useMemo, useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function UploadPage() {
  const [kbs, setKbs] = useState<Array<{ id: string; name: string }>>([]);
  const [kbId, setKbId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await listKnowledgeBases();
        setKbs(data);
        if (data.length > 0) setKbId(data[0]!.id);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const canUpload = useMemo(
    () => Boolean(kbId) && Boolean(file) && !uploading,
    [file, kbId, uploading],
  );


async function onUpload() {
    if (!kbId || !file) return;
    setError(null);
    setResult(null);
    setUploading(true);

    try {
      const res = await addDocument({ knowledgeBaseId: kbId, file });
      setResult(`已提交：${res.file_name}（id=${res.id}）`);
      setFile(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border bg-card p-6">
        <h1 className="text-lg font-semibold tracking-tight">上传 PDF</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          仅支持可复制文本的 PDF。扫描版 PDF 暂不支持。
        </p>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div className="space-y-1">
            <div className="text-xs font-medium">知识库</div>
            <Select value={kbId} onValueChange={(v) => setKbId(v ?? "")} disabled={loading || kbs.length === 0}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="选择知识库" />
              </SelectTrigger>
              <SelectContent>
                {kbs.map((kb) => (
                  <SelectItem key={kb.id} value={kb.id}>{kb.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <label className="space-y-1">
            <div className="text-xs font-medium">PDF 文件</div>
            <input
              type="file"
              accept="application/pdf"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="block w-full text-sm text-muted-foreground file:mr-4 file:rounded-md file:border file:border-border file:bg-card file:px-3 file:py-2 file:text-sm file:font-medium file:text-foreground"
            />
          </label>
        </div>

        <div className="mt-4 flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            onClick={() => void onUpload()}
            disabled={!canUpload}
            className="h-10 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground disabled:opacity-60"
          >
            {uploading ? "上传中…" : "开始上传"}
          </button>
        </div>

        {error ? (
          <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
            失败：{error}
          </div>
        ) : null}
        {result ? (
          <div className="mt-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">
            {result}
          </div>
        ) : null}
      </div>
    </div>
  );
}
