"use client";

import { useEffect, useState } from "react";

type Forecast = { as_of: string; model_version: string; warning?: string; buckets: Record<string, number>; predictions: Array<{ invoice_id: string; contractual_date: string; expected_date: string; expected_minor: number; interval: [number, number]; confidence: string }> };
const headers = { "x-dev-user-id": "00000000-0000-0000-0000-000000000002", "x-dev-tenant-id": "00000000-0000-0000-0000-000000000001", "x-dev-role": "ar_manager" };

export default function ForecastPage() {
  const [data, setData] = useState<Forecast>(); const [failed, setFailed] = useState(false);
  useEffect(() => { fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/forecast`, { headers }).then(async response => { if (!response.ok) throw new Error(); setData(await response.json()); }).catch(() => setFailed(true)); }, []);
  return <><div className="eyebrow">Decision support · baseline</div><h1>Aging & collection forecast</h1><p className="lede">Ngày hợp đồng và ngày dự kiến được hiển thị riêng. Forecast không tự đổi trạng thái case hay kích hoạt escalation.</p>{failed && <p role="alert">Không thể tải forecast.</p>}{!data && !failed && <p role="status">Đang tải dữ liệu…</p>}{data && <><p className={`badge ${data.warning ? "warn" : ""}`}>{data.warning ?? data.model_version}</p><section className="grid">{Object.entries(data.buckets).map(([bucket, amount]) => <article className="card" key={bucket}><div className="muted">{bucket}</div><div className="metric">{amount.toLocaleString("vi-VN")} VND</div></article>)}</section><div className="card"><table className="table"><thead><tr><th>Invoice</th><th>Contractual</th><th>Expected</th><th>Confidence</th><th>Interval</th></tr></thead><tbody>{data.predictions.map(item => <tr key={item.invoice_id}><td>{item.invoice_id.slice(0, 8)}</td><td>{item.contractual_date}</td><td>{item.expected_date}</td><td>{item.confidence}</td><td>{item.interval[0].toLocaleString("vi-VN")}–{item.interval[1].toLocaleString("vi-VN")}</td></tr>)}</tbody></table></div></>}</>;
}
