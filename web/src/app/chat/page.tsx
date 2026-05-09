"use client";

import { chatStream, listKnowledgeBases, type Citation } from "@/lib/api";
import { useEffect, useMemo, useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function ChatPage() {
  const [kbs, setKbs] = useState<Array<{ id: string; name: string }>>([]);
  const [kbId, setKbId] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [citations, setCitations] = useState<Citation[]>([]);

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

  const canSend = useMemo(
    () => Boolean(kbId) && question.trim().length > 0 && !sending,
    [kbId, question, sending],
  );


async function onSend() {
    const q = question.trim();
    if (!kbId || !q) return;
    setSending(true);
    setError(null);
    setAnswer(null);
    setCitations([]);
    try {
      let full = "";
      for await (const ev of chatStream({ knowledgeBaseId: kbId, question: q })) {
        if (ev.type === "token") {
          full += ev.content;
          setAnswer(full);
        } else if (ev.type === "done") {
          setCitations(ev.citations);
        } else if (ev.type === "error") {
          setError(ev.message);
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border bg-card p-6">
        <h1 className="text-lg font-semibold tracking-tight">问答</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          选择知识库后提问，系统会检索相关片段并生成答案。
        </p>

        <div className="mt-4 space-y-1">
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

        <div className="mt-3 space-y-2">
          <div className="text-xs font-medium">问题</div>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="例如：这个产品的保修期是多久？"
            className="min-h-28 w-full rounded-md border bg-card px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
          />
          <div className="flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={() => void onSend()}
              disabled={!canSend}
              className="h-10 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground disabled:opacity-60"
            >
              {sending ? "生成中…" : "发送"}
            </button>
            <button
              type="button"
              onClick={() => {
                setQuestion("");
                setAnswer(null);
                setCitations([]);
                setError(null);
              }}
              className="h-10 rounded-md border bg-card px-4 text-sm font-medium text-foreground hover:bg-accent"
            >
              清空
            </button>
          </div>
        </div>

        {error ? (
          <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
            后端未就绪或请求失败：{error}
          </div>
        ) : null}
      </div>

      <div className="rounded-xl border bg-card">
        <div className="border-b px-6 py-3 text-sm font-medium text-foreground">
          回答
        </div>
        <div className="px-6 py-4">
          {answer ? (
            <div className="whitespace-pre-wrap text-sm leading-6 text-foreground">
              {answer}
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">暂无回答</div>
          )}
          {citations.length > 0 ? (
            <div className="mt-5 space-y-2">
              <div className="text-xs font-medium">引用</div>
              <div className="flex flex-wrap gap-2">
                {citations.map((c, idx) => (
                  <span
                    key={`${c.file_name}-${c.page_number ?? "na"}-${idx}`}
                    className="inline-flex items-center rounded-md border px-2.5 py-1 text-xs text-muted-foreground"
                  >
                    {c.file_name}
                    {typeof c.page_number === "number"
                      ? ` · 第 ${c.page_number} 页`
                      : ""}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
