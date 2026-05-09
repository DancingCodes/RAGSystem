import Link from "next/link";

export default function Home() {
  return (
    <div className="space-y-6">
      <div className="rounded-xl border bg-card p-6">
        <h1 className="text-xl font-semibold tracking-tight">PDF RAG MVP</h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          上传可复制文本的 PDF，系统进行切分与向量化入库；提问时基于向量检索结果生成答案并返回引用来源。
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Link
          href="/knowledge-bases"
          className="rounded-xl border bg-card p-5 hover:border-foreground/20"
        >
          <div className="text-sm font-medium">知识库</div>
          <div className="mt-2 text-xs text-muted-foreground">创建/查看知识库</div>
        </Link>
        <Link
          href="/upload"
          className="rounded-xl border bg-card p-5 hover:border-foreground/20"
        >
          <div className="text-sm font-medium">上传 PDF</div>
          <div className="mt-2 text-xs text-muted-foreground">选择知识库并上传文件</div>
        </Link>
        <Link
          href="/chat"
          className="rounded-xl border bg-card p-5 hover:border-foreground/20"
        >
          <div className="text-sm font-medium">问答</div>
          <div className="mt-2 text-xs text-muted-foreground">基于向量检索进行回答</div>
        </Link>
      </div>
    </div>
  );
}
