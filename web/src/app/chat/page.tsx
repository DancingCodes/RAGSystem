"use client";

import { chat, listKnowledgeBases } from "@/lib/api";
import { useMemo, useState } from "react";

export default function ChatPage() {
  const [kbs, setKbs] = useState<Array<{ id: string; name: string }>>([]);
  const [kbId, setKbId] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [citations, setCitations] = useState<
    Array<{ file_name: string; page_number?: number; text?: string }>
  >([]);

  const canSend = useMemo(
    () => Boolean(kbId) && question.trim().length > 0 && !sending,
    [kbId, question, sending],
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

  async function onSend() {
    const q = question.trim();
    if (!kbId || !q) return;
    setSending(true);
    setError(null);
    setAnswer(null);
    setCitations([]);
    try {
      const res = await chat({ knowledgeBaseId: kbId, question: q });
      setAnswer(res.answer);
      setCitations(res.citations ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-zinc-200 bg-white p-6">
        <h1 className="text-lg font-semibold tracking-tight">问答</h1>
        <p className="mt-2 text-sm text-zinc-600">
          选择知识库后提问，系统会检索相关片段并生成答案。
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
          <div className="flex items-end">
            <button
              type="button"
              onClick={() => void loadKbs()}
              className="h-10 w-full rounded-md border border-zinc-200 bg-white px-4 text-sm font-medium text-zinc-900 hover:bg-zinc-50 disabled:opacity-60"
              disabled={loading}
            >
              刷新知识库
            </button>
          </div>
        </div>

        <div className="mt-3 space-y-2">
          <div className="text-xs font-medium text-zinc-700">问题</div>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="例如：这个产品的保修期是多久？"
            className="min-h-28 w-full rounded-md border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-zinc-200"
          />
          <div className="flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={() => void onSend()}
              disabled={!canSend}
              className="h-10 rounded-md bg-zinc-900 px-4 text-sm font-medium text-white disabled:opacity-60"
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
              className="h-10 rounded-md border border-zinc-200 bg-white px-4 text-sm font-medium text-zinc-900 hover:bg-zinc-50"
            >
              清空
            </button>
          </div>
        </div>

        {error ? (
          <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
            后端未就绪或请求失败：{error}
          </div>
        ) : null}
      </div>

      <div className="rounded-xl border border-zinc-200 bg-white">
        <div className="border-b border-zinc-200 px-6 py-3 text-sm font-medium text-zinc-900">
          回答
        </div>
        <div className="px-6 py-4">
          {answer ? (
            <div className="whitespace-pre-wrap text-sm leading-6 text-zinc-900">
              {answer}
            </div>
          ) : (
            <div className="text-sm text-zinc-600">暂无回答</div>
          )}
          {citations.length > 0 ? (
            <div className="mt-5 space-y-2">
              <div className="text-xs font-medium text-zinc-700">引用</div>
              <ul className="space-y-2">
                {citations.map((c, idx) => (
                  <li
                    key={`${c.file_name}-${c.page_number ?? "na"}-${idx}`}
                    className="rounded-md border border-zinc-200 px-3 py-2 text-xs text-zinc-700"
                  >
                    <div className="font-medium text-zinc-900">
                      {c.file_name}
                      {typeof c.page_number === "number"
                        ? ` · 第 ${c.page_number} 页`
                        : ""}
                    </div>
                    {c.text ? (
                      <div className="mt-1 whitespace-pre-wrap text-zinc-600">
                        {c.text}
                      </div>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
