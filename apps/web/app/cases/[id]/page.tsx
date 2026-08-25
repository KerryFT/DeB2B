"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { apiBase, apiFetch, apiHeaders } from "../../lib/api";

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
  const [draftTo, setDraftTo] = useState("");
  const [draftSubject, setDraftSubject] = useState("");
  const [draftBody, setDraftBody] = useState("");
  const [draftApproval, setDraftApproval] = useState<{ approval_id: string; content: string }>();
  const [draftConfirmed, setDraftConfirmed] = useState(false);
  const [draftMessage, setDraftMessage] = useState("");
  useEffect(() => {
    fetch(`${apiBase}/api/v1/cases/${id}`, { headers: apiHeaders(), credentials: "include" }).then(async (response) => {
      if (!response.ok) throw new Error("Case unavailable");
      setDetail(await response.json());
    }).catch(() => setFailed(true));
  }, [id]);

  async function previewDraft() {
    setDraftMessage("");
    const response = await apiFetch("/api/v1/connectors/outlook/drafts/preview", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ case_id: id, to: [draftTo], cc: [], subject: draftSubject, body: draftBody }),
    });
    const result = await response.json();
    if (!response.ok) {
      setDraftMessage(result.detail ?? "Không thể tạo yêu cầu duyệt.");
      return;
    }
    setDraftApproval(result);
    try {
      const storageKey = "deb2b-draft-approvals";
      const stored = JSON.parse(sessionStorage.getItem(storageKey) ?? "{}");
      stored[result.approval_id] = {
        approval_id: result.approval_id,
        content: result.content,
        case_id: id,
        to: [draftTo],
        cc: [],
        subject: draftSubject,
        body: draftBody,
      };
      sessionStorage.setItem(storageKey, JSON.stringify(stored));
    } catch { /* The approval still exists; only the cross-page preview is unavailable. */ }
    setDraftConfirmed(false);
    setDraftMessage("Đã khóa nội dung và đưa vào Hộp thư phê duyệt.");
  }

  async function approveAndCreateDraft() {
    if (!draftApproval || !draftConfirmed) return;
    setDraftMessage("");
    const approvalResponse = await apiFetch(`/api/v1/approvals/${draftApproval.approval_id}/approve`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ content: draftApproval.content }),
    });
    if (!approvalResponse.ok) {
      const result = await approvalResponse.json();
      setDraftMessage(result.detail ?? "Phê duyệt thất bại.");
      return;
    }
    const response = await apiFetch("/api/v1/connectors/outlook/drafts/create", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        case_id: id,
        to: [draftTo],
        cc: [],
        subject: draftSubject,
        body: draftBody,
        approval_id: draftApproval.approval_id,
        idempotency_key: `outlook:${id}:${draftApproval.approval_id}`,
      }),
    });
    const result = await response.json();
    setDraftMessage(response.ok ? "Draft đã được tạo trong Outlook; hệ thống không có quyền gửi." : (result.detail ?? "Tạo draft thất bại."));
  }
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
      <section className="card">
        <h2>Outlook draft có phê duyệt</h2>
        <p className="muted">Portfolio chỉ cho phép recipient nằm trong allowlist và không yêu cầu Mail.Send.</p>
        <label htmlFor="draft-to">To</label>
        <input id="draft-to" type="email" value={draftTo} onChange={(event) => { setDraftTo(event.target.value); setDraftApproval(undefined); }} />
        <label htmlFor="draft-subject">Subject</label>
        <input id="draft-subject" value={draftSubject} onChange={(event) => { setDraftSubject(event.target.value); setDraftApproval(undefined); }} />
        <label htmlFor="draft-body">Nội dung</label>
        <textarea id="draft-body" rows={7} value={draftBody} onChange={(event) => { setDraftBody(event.target.value); setDraftApproval(undefined); }} />
        <div className="actions">
          <button className="button secondary" disabled={!draftTo || !draftSubject || !draftBody} onClick={previewDraft}>Tạo yêu cầu duyệt</button>
          {draftApproval && <label><input type="checkbox" checked={draftConfirmed} onChange={(event) => setDraftConfirmed(event.target.checked)} /> Tôi đã kiểm tra recipient và nội dung</label>}
          {draftApproval && <button className="button" disabled={!draftConfirmed} onClick={approveAndCreateDraft}>Phê duyệt & tạo draft</button>}
        </div>
        {draftApproval && <pre className="json-view">{draftApproval.content}</pre>}
        {draftApproval && <Link className="button secondary" href="/approvals">Mở Hộp thư phê duyệt →</Link>}
        {draftMessage && <p role="status">{draftMessage}</p>}
      </section>
    </>}
  </>;
}
