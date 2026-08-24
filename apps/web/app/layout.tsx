import type { Metadata } from "next";
import Link from "next/link";
import AuthControls from "./components/auth-controls";
import "./globals.css";

export const metadata: Metadata = { title: "AR Operations", description: "Evidence-first receivables operations" };

const nav = [
  ["Dashboard", "/"], ["Case queue", "/cases"], ["Approvals", "/approvals"],
  ["Forecast", "/forecast"], ["LLM quality", "/llm-analytics"], ["Payment rules", "/rules"],
  ["Automation", "/automation"], ["Escalation", "/escalation"], ["Disputes", "/disputes"],
  ["Probability", "/probability"], ["Cash flow V2", "/cash-flow"],
  ["Customer behavior", "/customer-behavior"], ["Team benchmark", "/team-benchmark"],
  ["Imports", "/imports"], ["Reconciliation", "/reconciliation"], ["Settings", "/settings"],
];

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="vi"><body><div className="shell"><aside className="sidebar"><div className="brand">DeB2B · AR Operations</div><AuthControls /><nav className="nav" aria-label="Chính">{nav.map(([label, href]) => <Link key={href} href={href}>{label}</Link>)}</nav></aside><main className="content">{children}</main></div></body></html>;
}
