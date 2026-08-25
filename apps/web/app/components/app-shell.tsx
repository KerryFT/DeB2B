"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import AuthControls from "./auth-controls";

const groups = [
  {
    label: "Vận hành",
    items: [
      ["Tổng quan", "/", "⌂"],
      ["AI Agent", "/agent", "✦"],
      ["Hồ sơ công nợ", "/cases", "□"],
      ["Phê duyệt", "/approvals", "✓"],
      ["Đối soát", "/reconciliation", "↔"],
      ["Nhập dữ liệu", "/imports", "↑"],
    ],
  },
  {
    label: "Phân tích",
    items: [
      ["Dự báo", "/forecast", "↗"],
      ["Xác suất thu", "/probability", "%"],
      ["Dòng tiền", "/cash-flow", "₫"],
      ["Hành vi khách hàng", "/customer-behavior", "◎"],
      ["Hiệu suất đội ngũ", "/team-benchmark", "◫"],
    ],
  },
  {
    label: "Kiểm soát",
    items: [
      ["Tranh chấp", "/disputes", "!"],
      ["Escalation", "/escalation", "△"],
      ["Tự động hóa", "/automation", "⚡"],
      ["Chất lượng AI", "/llm-analytics", "✦"],
      ["Luật thanh toán", "/rules", "≡"],
    ],
  },
];

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const active = (href: string) => href === "/" ? pathname === href : pathname.startsWith(href);

  return <div className="shell">
    <aside className="sidebar">
      <div className="brand-lockup">
        <div className="brand-mark" aria-hidden="true">D</div>
        <div><div className="brand">DeB2B</div><div className="brand-subtitle">AR workspace</div></div>
      </div>
      <AuthControls />
      <nav className="nav" aria-label="Điều hướng chính">
        {groups.map((group) => <div className="nav-group" key={group.label}>
          <div className="nav-label">{group.label}</div>
          {group.items.map(([label, href, icon]) => <Link
            key={href}
            href={href}
            className={active(href) ? "active" : undefined}
            aria-current={active(href) ? "page" : undefined}
          ><span className="nav-icon" aria-hidden="true">{icon}</span><span>{label}</span></Link>)}
        </div>)}
      </nav>
      <div className="sidebar-footer">
        <Link href="/settings" className={active("/settings") ? "active" : undefined}>
          <span className="nav-icon" aria-hidden="true">⚙</span><span>Cài đặt</span>
        </Link>
        <div className="environment"><span /> Sandbox · Draft only</div>
      </div>
    </aside>
    <main className="content">{children}</main>
  </div>;
}
