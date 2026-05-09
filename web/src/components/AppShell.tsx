import Link from "next/link";
import type { ReactNode } from "react";
import { ThemeToggle } from "./ThemeToggle";

const navItems = [
  { href: "/knowledge-bases", label: "知识库" },
  { href: "/upload", label: "上传 PDF" },
  { href: "/chat", label: "问答" },
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-dvh flex flex-col bg-background text-foreground">
      <header className="border-b bg-card">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-3">
          <Link href="/" className="text-sm font-semibold">
            RAG 系统
          </Link>
          <nav className="flex items-center gap-4 text-sm text-muted-foreground">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-md px-2 py-1 hover:bg-accent hover:text-accent-foreground"
              >
                {item.label}
              </Link>
            ))}
            <ThemeToggle />
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
        {children}
      </main>
      <footer className="border-t bg-card">
        <div className="mx-auto w-full max-w-5xl px-4 py-4 text-xs text-muted-foreground">
          PDF RAG MVP
        </div>
      </footer>
    </div>
  );
}

