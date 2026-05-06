import Link from "next/link";
import type { ReactNode } from "react";

const navItems = [
  { href: "/knowledge-bases", label: "知识库" },
  { href: "/upload", label: "上传 PDF" },
  { href: "/chat", label: "问答" },
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-dvh flex flex-col bg-zinc-50 text-zinc-950">
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-3">
          <Link href="/" className="text-sm font-semibold">
            RAG 系统
          </Link>
          <nav className="flex items-center gap-4 text-sm text-zinc-700">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-md px-2 py-1 hover:bg-zinc-100 hover:text-zinc-950"
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
        {children}
      </main>
      <footer className="border-t border-zinc-200 bg-white">
        <div className="mx-auto w-full max-w-5xl px-4 py-4 text-xs text-zinc-500">
          PDF RAG MVP
        </div>
      </footer>
    </div>
  );
}

