"use client";

import { useEffect, useState } from "react";

type Metrics = { outstanding_minor: number; currency: string; open_cases: number; active_blockers: number; as_of: string };
const headers = { "x-dev-user-id": "00000000-0000-0000-0000-000000000002", "x-dev-tenant-id": "00000000-0000-0000-0000-000000000001" };

export default function Dashboard() {
  const [metrics, setMetrics] = useState<Metrics>();
  const [stale, setStale] = useState(false);
  useEffect(() => { fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/dashboard`, { headers }).then(async (response) => {
    if (!response.ok) throw new Error("dashboard unavailable");
    setMetrics(await response.json());
  }).catch(() => setStale(true)); }, []);
  const cards = metrics ? [
    ["Outstanding", `${metrics.outstanding_minor.toLocaleString("vi-VN")} ${metrics.currency}`],
    ["Open cases", String(metrics.open_cases)],
    ["Active blockers", String(metrics.active_blockers)],
  ] : [];
  return <><div className="eyebrow">{metrics ? `Dữ liệu: ${new Date(metrics.as_of).toLocaleString("vi-VN")}` : "Đang tải dữ liệu"}</div><h1>Dòng tiền cần hành động</h1><p className="lede">Ưu tiên case theo bằng chứng và blocker, không chỉ theo số ngày quá hạn.</p>{stale && <p role="alert" className="badge warn">API unavailable · số liệu có thể stale</p>}<section className="grid" aria-label="Tổng quan">{cards.map(([label, value]) => <article className="card" key={label}><div className="muted">{label}</div><div className="metric">{value}</div></article>)}</section></>;
}
