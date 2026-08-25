"use client";

import { useEffect, useState } from "react";
import { apiBase, apiHeaders } from "./lib/api";

type Metrics = { outstanding_minor: number; currency: string; open_cases: number; active_blockers: number; as_of: string };

export default function Dashboard() {
  const [metrics, setMetrics] = useState<Metrics>();
  const [stale, setStale] = useState(false);
  const [visitor, setVisitor] = useState(false);
  useEffect(() => { fetch(`${apiBase}/api/v1/dashboard`, { headers: apiHeaders(), credentials: "include" }).then(async (response) => {
    if (response.status === 401) { setVisitor(true); return; }
    if (!response.ok) throw new Error("dashboard unavailable");
    setMetrics(await response.json());
  }).catch(() => setStale(true)); }, []);
  const cards = metrics ? [
    ["Outstanding", `${metrics.outstanding_minor.toLocaleString("vi-VN")} ${metrics.currency}`],
    ["Open cases", String(metrics.open_cases)],
    ["Active blockers", String(metrics.active_blockers)],
  ] : [];
  if (visitor) return <>
    <div className="eyebrow">Production-oriented student portfolio</div>
    <h1>DeB2B AR Operations Agent</h1>
    <p className="lede">Nền tảng evidence-first hỗ trợ nhập công nợ MISA, quản lý payment case, reconciliation và Outlook draft có human approval. Bản public không hiển thị dữ liệu email và không có quyền gửi thư.</p>
    <section className="grid" aria-label="Khả năng hệ thống">
      <article className="card"><h2>MISA Import</h2><p>CSV/XLSX preview, validation, fingerprint và idempotent commit.</p></article>
      <article className="card"><h2>Outlook</h2><p>OAuth delegated, manual delta sync, encrypted refresh token và allowlisted draft.</p></article>
      <article className="card"><h2>Safety</h2><p>Tenant RLS, database session, CSRF, audit log và external send kill switch.</p></article>
      <article className="card"><h2>Deployment</h2><p>Next.js, FastAPI, PostgreSQL, HTTPS custom domains và CI/CD.</p></article>
    </section>
    <a className="button" href={`${apiBase}/api/v1/auth/microsoft/login`}>Đăng nhập owner demo</a>
  </>;
  return <><div className="eyebrow">{metrics ? `Dữ liệu: ${new Date(metrics.as_of).toLocaleString("vi-VN")}` : "Đang tải dữ liệu"}</div><h1>Dòng tiền cần hành động</h1><p className="lede">Ưu tiên case theo bằng chứng và blocker, không chỉ theo số ngày quá hạn.</p>{stale && <p role="alert" className="badge warn">API unavailable · số liệu có thể stale</p>}<section className="grid" aria-label="Tổng quan">{cards.map(([label, value]) => <article className="card" key={label}><div className="muted">{label}</div><div className="metric">{value}</div></article>)}</section></>;
}
