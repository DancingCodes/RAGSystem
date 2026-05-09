"use client";

import { createKnowledgeBase, deleteKnowledgeBase, listKnowledgeBases } from "@/lib/api";
import { useEffect, useMemo, useState } from "react";
import { Loader2Icon, Trash2Icon } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export default function KnowledgeBasesPage() {
  const [items, setItems] = useState<Array<{ id: string; name: string }>>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<{ id: string; name: string } | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setError(null);
      try {
        setItems(await listKnowledgeBases());
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const canCreate = useMemo(
    () => name.trim().length > 0 && !creating,
    [creating, name],
  );

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const data = await listKnowledgeBases();
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function onDelete() {
    if (!confirmDelete) return;
    const { id } = confirmDelete;
    setConfirmDelete(null);
    setDeleting(id);
    setError(null);
    try {
      await deleteKnowledgeBase(id);
      setItems((prev) => prev.filter((it) => it.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setDeleting(null);
    }
  }

  async function onCreate() {
    const v = name.trim();
    if (!v) return;
    setCreating(true);
    setError(null);
    try {
      await createKnowledgeBase(v);
      setName("");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border bg-card p-6">
        <h1 className="text-lg font-semibold tracking-tight">知识库</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          创建一个知识库，用于隔离不同资料集合。
        </p>
        <div className="mt-4 flex flex-col gap-3 sm:flex-row">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="例如：产品手册"
            className="h-10 w-full rounded-md border border-border bg-card px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
          />
          <button
            type="button"
            onClick={() => void onCreate()}
            disabled={!canCreate}
            className="h-10 shrink-0 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground disabled:opacity-60"
          >
            创建
          </button>
          <button
            type="button"
            onClick={() => void refresh()}
            className="h-10 shrink-0 rounded-md border border-border bg-card px-4 text-sm font-medium text-foreground hover:bg-accent"
          >
            刷新
          </button>
        </div>
        {error ? (
          <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
            后端未就绪或请求失败：{error}
          </div>
        ) : null}
      </div>

      <div className="rounded-xl border border-border bg-card">
        <div className="border-b border-border px-6 py-3 text-sm font-medium text-foreground">
          列表
        </div>
        <div className="px-6 py-4">
          {loading ? (
            <div className="text-sm text-muted-foreground">加载中…</div>
          ) : items.length === 0 ? (
            <div className="text-sm text-muted-foreground">暂无知识库</div>
          ) : (
            <ul className="space-y-2">
              {items.map((it) => (
                <li
                  key={it.id}
                  className="flex items-center justify-between rounded-md border border-border px-3 py-2"
                >
                  <div className="text-sm font-medium text-foreground">
                    {it.name}
                  </div>
                  <div className="flex items-center gap-3">
                    {deleting === it.id ? (
                      <Loader2Icon className="size-3.5 animate-spin text-muted-foreground" />
                    ) : (
                      <>
                        <div className="text-xs text-muted-foreground">{it.id}</div>
                        <button
                          type="button"
                          onClick={() => setConfirmDelete(it)}
                          className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                        >
                          <Trash2Icon className="size-3.5" />
                        </button>
                      </>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <AlertDialog open={!!confirmDelete} onOpenChange={(open) => { if (!open) setConfirmDelete(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              将删除知识库「{confirmDelete?.name}」及其包含的所有文件和数据，此操作不可撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={() => void onDelete()}>确认删除</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
