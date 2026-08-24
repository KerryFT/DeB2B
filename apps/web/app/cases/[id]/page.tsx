"use client";

import { use, useEffect, useState } from "react";

type Detail = {
  id: string;
  status: string;
  invoices: Array<{ id: string; invoice_number: string; outstanding_minor: number; currency: string }>;
  blockers: Array<{ type: string; active: boolean }>;
  approvals: Array<{ id: string; status: string }>;
  evidence: Array<{ field: string; page?: number; sheet?: string; cell_range?: string; quote: string }>;
  timeline: Array<{ action: string; occurred_at: string }>;
};

export default function CaseDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [detail, setDetail] = useState<Detail>();
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    fetch(`${api}/api/v1/cases/${id}`, { headers: {
      "x-dev-user-id": "00000000-0000-0000-0000-000000000002",
      "x-dev-tenant-id": "00000000-0000-0000-0000-000000000001",
    } }).then(async (response) => {
      if (!response.ok) throw new Error("Case unavailable");
      setDetail(await response.json());
    }).catch(() => setFailed(true));
  }, [id]);
  return <>
    <div className="eyebrow">Case detail</div><h1>Payment case</h1><p className="muted">ID: {id}</p>
    {!detail && !failed && <p aria-live="polite">Đang tải evidence…</p>}
    {failed && <p role="alert">Không thể tải case hoặc case không thuộc tenant hiện tại.</p>}
    {detail && <>
      <span className="badge">{detail.status}</span>
      <div className="grid">
        <section className="card"><h2>Timeline</h2>{detail.timeline.length ? detail.timeline.map((item) => <p key={`${item.occurred_at}-${item.action}`}><strong>{item.action}</strong><br/><span className="muted">{new Date(item.occurred_at).toLocaleString("vi-VN")}</span></p>) : <p className="muted">Chưa có audit event.</p>}</section>
        <section className="card"><h2>Evidence</h2>{detail.evidence.length ? detail.evidence.map((item) => <p key={`${item.field}-${item.cell_range ?? item.page}`}><strong>{item.field}</strong>: {item.quote}<br/><span className="muted">{item.sheet ? `${item.sheet}!${item.cell_range}` : `Trang ${item.page}`}</span></p>) : <p className="muted">Chưa liên kết evidence.</p>}</section>
        <section className="card"><h2>Blockers</h2>{detail.blockers.length ? detail.blockers.map((item) => <p key={item.type}>{item.type}</p>) : <p>Không có blocker đang mở.</p>}</section>
        <section className="card"><h2>Approvals</h2>{detail.approvals.length ? detail.approvals.map((item) => <p key={item.id}>{item.status}</p>) : <p className="muted">Chưa có yêu cầu duyệt.</p>}</section>
      </div>
    </>}
  </>;
}
