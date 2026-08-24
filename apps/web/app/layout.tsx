import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = { title: "AR Operations", description: "Evidence-first receivables operations" };

const nav = [
  ["Dashboard", "/"], ["Case queue", "/cases"], ["Approvals", "/approvals"],
  ["Imports", "/imports"], ["Reconciliation", "/reconciliation"], ["Settings", "/settings"],
];

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="vi"><body><div className="shell"><aside className="sidebar"><div className="brand">AR Operations</div><nav className="nav" aria-label="Chính">{nav.map(([label, href]) => <Link key={href} href={href}>{label}</Link>)}</nav></aside><main className="content">{children}</main></div></body></html>;
}

