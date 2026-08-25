"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { apiFetch } from "../lib/api";

type Approval = { id: string; status: string; expires_at: string; case_id: string; case_status: string; case_version: number; invoice_number: string; customer: string; outstanding_minor: number; currency: string; due_date?: string; active_blockers: number; evidence_count: number };
type DraftSnapshot = { approval_id: string; content: string; case_id: string; to: string[]; cc: string[]; subject: string; body: string };
type Dialog = "reject" | "edit" | "bulk" | null;

const statusLabels: Record<string, string> = { PENDING: "Chờ duyệt", APPROVED: "Đã duyệt", REJECTED: "Đã từ chối", INVALIDATED: "Hết hiệu lực" };
const money = (value: number, currency: string) => new Intl.NumberFormat("vi-VN", { style: "currency", currency, maximumFractionDigits: 0 }).format(value);
function timeLeft(value: string, now: number) { const minutes = Math.round((new Date(value).getTime() - now) / 60_000); return minutes <= 0 ? "Đã hết hạn" : minutes < 60 ? `Còn ${minutes} phút` : `Còn ${Math.round(minutes / 60)} giờ`; }
function readSnapshots(): Record<string, DraftSnapshot> { if (typeof window === "undefined") return {}; try { return JSON.parse(sessionStorage.getItem("deb2b-draft-approvals") ?? "{}"); } catch { return {}; } }
function writeSnapshot(snapshot: DraftSnapshot) { const current = readSnapshots(); current[snapshot.approval_id] = snapshot; sessionStorage.setItem("deb2b-draft-approvals", JSON.stringify(current)); }

export default function Approvals() {
  const [items, setItems] = useState<Approval[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [filter, setFilter] = useState("PENDING");
  const [query, setQuery] = useState("");
  const [activeId, setActiveId] = useState<string>();
  const [selected, setSelected] = useState<string[]>([]);
  const [snapshots, setSnapshots] = useState<Record<string, DraftSnapshot>>(readSnapshots);
  const [now] = useState(() => Date.now());
  const [dialog, setDialog] = useState<Dialog>(null);
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string }>();
  const [busy, setBusy] = useState(false);
  const [edit, setEdit] = useState({ to: "", subject: "", body: "" });
  const [bulkPreview, setBulkPreview] = useState<{ eligible: string[]; excluded: Array<{ id: string; reason: string }>; total_minor: number }>();

  const load = useCallback(() => apiFetch("/api/v1/approvals")
    .then(async (response) => {
      if (!response.ok) throw new Error("approval API unavailable");
      const result: Approval[] = await response.json();
      setItems(result);
      setActiveId((current) => current && result.some((item) => item.id === current) ? current : result.find((item) => item.status === "PENDING")?.id ?? result[0]?.id);
      setState("ready");
    })
    .catch(() => setState("error")), []);

  useEffect(() => { void load(); }, [load]);
  const filtered = useMemo(() => items.filter((item) => { const search = query.trim().toLocaleLowerCase("vi"); return (filter === "ALL" || item.status === filter) && (!search || `${item.invoice_number} ${item.customer}`.toLocaleLowerCase("vi").includes(search)); }), [filter, items, query]);
  const active = filtered.find((item) => item.id === activeId) ?? filtered[0];
  const snapshot = active ? snapshots[active.id] : undefined;
  const pending = items.filter((item) => item.status === "PENDING");
  const expiring = pending.filter((item) => new Date(item.expires_at).getTime() - now < 30 * 60_000).length;
  const selectedItems = items.filter((item) => selected.includes(item.id));

  function toggleSelected(id: string) { setSelected((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]); }
  async function parseError(response: Response, fallback: string) { try { const result = await response.json(); return result.detail ?? fallback; } catch { return fallback; } }

  async function reject() {
    if (!active || reason.trim().length < 3) return;
    setBusy(true);
    const response = await apiFetch(`/api/v1/approvals/${active.id}/reject`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ reason }) });
    if (response.ok) { setDialog(null); setReason(""); setMessage({ kind: "success", text: `${active.invoice_number} đã được trả lại để chỉnh sửa.` }); await load(); }
    else setMessage({ kind: "error", text: await parseError(response, "Không thể từ chối yêu cầu.") });
    setBusy(false);
  }

  async function approveAndCreate() {
    if (!active || !snapshot) return;
    setBusy(true); setMessage(undefined);
    const approvalResponse = await apiFetch(`/api/v1/approvals/${active.id}/approve`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ content: snapshot.content }) });
    if (!approvalResponse.ok) { setMessage({ kind: "error", text: await parseError(approvalResponse, "Phê duyệt thất bại.") }); setBusy(false); return; }
    const draftResponse = await apiFetch("/api/v1/connectors/outlook/drafts/create", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ ...snapshot, idempotency_key: `outlook:${snapshot.case_id}:${active.id}` }) });
    setMessage(draftResponse.ok ? { kind: "success", text: "Đã phê duyệt và tạo Outlook draft. Hệ thống không gửi email tự động." } : { kind: "error", text: `Đã phê duyệt nhưng chưa tạo được draft: ${await parseError(draftResponse, "Outlook chưa sẵn sàng.")}` });
    await load(); setBusy(false);
  }

  function openEdit() { if (!snapshot) return; setEdit({ to: snapshot.to.join(", "), subject: snapshot.subject, body: snapshot.body }); setDialog("edit"); }
  async function saveEdit() {
    if (!active || !snapshot) return;
    setBusy(true);
    const recipients = edit.to.split(",").map((value) => value.trim()).filter(Boolean);
    const previewResponse = await apiFetch("/api/v1/connectors/outlook/drafts/preview", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ case_id: active.case_id, to: recipients, cc: snapshot.cc, subject: edit.subject, body: edit.body }) });
    if (!previewResponse.ok) { setMessage({ kind: "error", text: await parseError(previewResponse, "Không thể lưu nội dung mới.") }); setBusy(false); return; }
    const created: { approval_id: string; content: string } = await previewResponse.json();
    writeSnapshot({ ...snapshot, approval_id: created.approval_id, content: created.content, to: recipients, subject: edit.subject, body: edit.body });
    await apiFetch(`/api/v1/approvals/${active.id}/reject`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ reason: "Nội dung đã được chỉnh sửa và tạo phiên bản duyệt mới" }) });
    setSnapshots(readSnapshots()); setDialog(null); setMessage({ kind: "success", text: "Đã lưu phiên bản mới và đưa lại vào hàng chờ duyệt." }); await load(); setBusy(false);
  }

  async function previewBulk() {
    const candidates = selectedItems.filter((item) => item.status === "PENDING" && snapshots[item.id]);
    if (!candidates.length) { setMessage({ kind: "error", text: "Các mục đã chọn không còn nội dung khóa trong phiên này." }); return; }
    setBusy(true);
    const response = await apiFetch("/api/v1/approvals/bulk/preview", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ items: candidates.map((item) => ({ approval_id: item.id, case_id: item.case_id, version: item.case_version, expected_version: item.case_version, channel: "outlook", recipient: snapshots[item.id].to[0], amount_minor: item.outstanding_minor, attachment_count: 0, risk_flags: item.active_blockers ? ["active_blocker"] : [], permitted: true, policy_valid: true })) }) });
    if (response.ok) { setBulkPreview(await response.json()); setDialog("bulk"); } else setMessage({ kind: "error", text: await parseError(response, "Không thể tạo bản xem trước.") });
    setBusy(false);
  }
  async function commitBulk() {
    if (!bulkPreview) return;
    const eligible = selectedItems.filter((item) => bulkPreview.eligible.includes(item.id) && snapshots[item.id]);
    setBusy(true);
    const response = await apiFetch("/api/v1/approvals/bulk/commit", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ idempotency_key: `web-bulk:${Date.now()}`, items: eligible.map((item) => ({ approval_id: item.id, expected_case_version: item.case_version, content: snapshots[item.id].content })) }) });
    if (response.ok) { const result = await response.json(); setDialog(null); setSelected([]); setMessage({ kind: "success", text: `Đã duyệt ${result.approved} mục; ${result.excluded} mục được giữ lại để kiểm tra.` }); await load(); }
    else setMessage({ kind: "error", text: await parseError(response, "Duyệt hàng loạt thất bại.") });
    setBusy(false);
  }

  return <>
    <header className="page-header"><div><div className="eyebrow">Kiểm soát trước hành động</div><h1>Hộp thư phê duyệt</h1><p className="lede">Kiểm tra đúng người nhận, bằng chứng và nội dung trước khi tạo draft.</p></div><Link className="button secondary" href="/cases">＋ Tạo yêu cầu từ hồ sơ</Link></header>
    <section className="stat-strip" aria-label="Tổng quan phê duyệt"><div><span className="stat-dot amber"/><strong>{pending.length}</strong><span>Đang chờ</span></div><div><span className="stat-dot red"/><strong>{expiring}</strong><span>Sắp hết hạn</span></div><div><span className="stat-dot green"/><strong>{items.filter((item) => item.status === "APPROVED").length}</strong><span>Đã duyệt</span></div><div className="stat-note"><span className="shield">✓</span><span><strong>Human-in-the-loop</strong><small>Không có quyền gửi email</small></span></div></section>
    {message && <div className={`toast ${message.kind}`} role="status"><span>{message.kind === "success" ? "✓" : "!"}</span>{message.text}<button aria-label="Đóng thông báo" onClick={() => setMessage(undefined)}>×</button></div>}
    <section className="approval-toolbar" aria-label="Bộ lọc"><div className="tabs">{[["PENDING", "Chờ duyệt"], ["APPROVED", "Đã duyệt"], ["REJECTED", "Đã từ chối"], ["ALL", "Tất cả"]].map(([value, label]) => <button key={value} className={filter === value ? "active" : ""} onClick={() => setFilter(value)}>{label}</button>)}</div><label className="search-box"><span aria-hidden="true">⌕</span><input aria-label="Tìm theo hóa đơn hoặc khách hàng" placeholder="Tìm hóa đơn, khách hàng…" value={query} onChange={(event) => setQuery(event.target.value)} /></label>{selected.length > 0 && <button className="button" onClick={previewBulk} disabled={busy}>Xem trước {selected.length} mục</button>}</section>
    {state === "loading" && <div className="approval-layout"><div className="queue-panel"><div className="skeleton-row"/><div className="skeleton-row"/><div className="skeleton-row"/></div><div className="detail-panel skeleton-detail"/></div>}
    {state === "error" && <div className="empty-state"><div className="empty-icon">↻</div><h2>Chưa kết nối được dữ liệu phê duyệt</h2><p>Kiểm tra API hoặc phiên đăng nhập rồi thử tải lại. Không có dữ liệu mẫu nào được hiển thị thay dữ liệu thật.</p><button className="button" onClick={() => { setState("loading"); void load(); }}>Thử lại</button></div>}
    {state === "ready" && filtered.length === 0 && <div className="empty-state"><div className="empty-icon">✓</div><h2>{query ? "Không tìm thấy kết quả" : "Không còn yêu cầu cần xử lý"}</h2><p>{query ? "Thử một từ khóa khác hoặc chuyển sang tab Tất cả." : "Tạo draft từ một hồ sơ công nợ; yêu cầu sẽ xuất hiện tại đây để người có quyền kiểm tra."}</p>{!query && <Link className="button" href="/cases">Đi tới hồ sơ công nợ</Link>}</div>}
    {state === "ready" && filtered.length > 0 && <div className="approval-layout"><section className="queue-panel" aria-label="Danh sách yêu cầu"><div className="queue-heading"><span>{filtered.length} yêu cầu</span>{filter === "PENDING" && <button onClick={() => setSelected(selected.length === filtered.length ? [] : filtered.map((item) => item.id))}>{selected.length === filtered.length ? "Bỏ chọn" : "Chọn tất cả"}</button>}</div>{filtered.map((item) => <article key={item.id} className={`queue-item ${activeId === item.id ? "active" : ""}`} onClick={() => setActiveId(item.id)}>{item.status === "PENDING" && <input aria-label={`Chọn ${item.invoice_number}`} type="checkbox" checked={selected.includes(item.id)} onClick={(event) => event.stopPropagation()} onChange={() => toggleSelected(item.id)} />}<div className="queue-main"><div className="queue-top"><strong>{item.customer}</strong><span className={`status-pill ${item.status.toLowerCase()}`}>{statusLabels[item.status] ?? item.status}</span></div><div className="invoice-line">{item.invoice_number} · {money(item.outstanding_minor, item.currency)}</div><div className="queue-meta"><span>{item.evidence_count} bằng chứng</span>{item.active_blockers > 0 && <span className="risk-text">{item.active_blockers} blocker</span>}<span>{timeLeft(item.expires_at, now)}</span></div></div></article>)}</section>
      {active && <section className="detail-panel" aria-label="Chi tiết yêu cầu"><div className="detail-header"><div><span className={`status-pill ${active.status.toLowerCase()}`}>{statusLabels[active.status] ?? active.status}</span><h2>{active.invoice_number}</h2><p>{active.customer}</p></div><Link href={`/cases/${active.case_id}`} className="text-link">Mở hồ sơ ↗</Link></div><div className="review-progress" aria-label="Tiến trình kiểm tra"><div className="done"><span>1</span><small>Hồ sơ</small></div><i/><div className="done"><span>2</span><small>Bằng chứng</small></div><i/><div className={active.status === "PENDING" ? "current" : "done"}><span>3</span><small>Quyết định</small></div></div><div className="summary-grid"><div><small>Còn phải thu</small><strong>{money(active.outstanding_minor, active.currency)}</strong></div><div><small>Hạn thanh toán</small><strong>{active.due_date ? new Date(active.due_date).toLocaleDateString("vi-VN") : "—"}</strong></div><div><small>Trạng thái hồ sơ</small><strong>{active.case_status.replaceAll("_", " ")}</strong></div></div>
        <div className="check-section"><div className="section-title"><h3>Kiểm tra an toàn</h3><span>{active.active_blockers ? "Cần chú ý" : "Đạt yêu cầu"}</span></div><ul className="check-list"><li className={snapshot?.to.length ? "ok" : "warn"}><span>{snapshot?.to.length ? "✓" : "!"}</span><div><strong>Người nhận</strong><small>{snapshot?.to.join(", ") || "Mở từ đúng phiên tạo yêu cầu để xem dữ liệu nhạy cảm"}</small></div></li><li className={active.evidence_count ? "ok" : "warn"}><span>{active.evidence_count ? "✓" : "!"}</span><div><strong>Bằng chứng nguồn</strong><small>{active.evidence_count ? `${active.evidence_count} nguồn đã liên kết với hồ sơ` : "Chưa có bằng chứng được liên kết"}</small></div></li><li className={active.active_blockers ? "warn" : "ok"}><span>{active.active_blockers ? "!" : "✓"}</span><div><strong>Blocker đang mở</strong><small>{active.active_blockers ? `${active.active_blockers} blocker cần được đánh giá trước khi duyệt` : "Không có blocker đang hoạt động"}</small></div></li></ul></div>
        <div className="message-preview"><div className="section-title"><h3>Nội dung draft</h3>{snapshot && active.status === "PENDING" && <button className="text-link" onClick={openEdit}>Chỉnh sửa</button>}</div>{snapshot ? <><dl><div><dt>Đến</dt><dd>{snapshot.to.join(", ")}</dd></div><div><dt>Tiêu đề</dt><dd>{snapshot.subject}</dd></div></dl><div className="email-body">{snapshot.body}</div></> : <div className="privacy-note"><span>⌁</span><div><strong>Nội dung không được lưu dài hạn</strong><p>Vì lý do riêng tư, bản nội dung chỉ có trong phiên đã tạo yêu cầu. Mở hồ sơ để tạo lại một phiên duyệt mới.</p></div></div>}</div>
        {active.status === "PENDING" && <div className="decision-bar"><button className="button danger-ghost" onClick={() => setDialog("reject")}>Từ chối</button><button className="button secondary" onClick={openEdit} disabled={!snapshot}>Chỉnh sửa</button><button className="button approve" onClick={approveAndCreate} disabled={!snapshot || busy || active.active_blockers > 0}>{busy ? "Đang xử lý…" : "Duyệt & tạo draft"}</button></div>}</section>}</div>}
    {dialog && <div className="modal-backdrop" onMouseDown={() => !busy && setDialog(null)}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title" onMouseDown={(event) => event.stopPropagation()}><button className="modal-close" aria-label="Đóng" onClick={() => setDialog(null)}>×</button>
      {dialog === "reject" && <><div className="modal-icon danger">!</div><h2 id="modal-title">Từ chối yêu cầu?</h2><p className="muted">Yêu cầu sẽ được trả lại hồ sơ. Lý do được ghi vào audit trail.</p><label htmlFor="reject-reason">Lý do từ chối</label><textarea id="reject-reason" rows={4} placeholder="Ví dụ: Sai người nhận hoặc thiếu biên bản nghiệm thu…" value={reason} onChange={(event) => setReason(event.target.value)}/><div className="modal-actions"><button className="button secondary" onClick={() => setDialog(null)}>Hủy</button><button className="button danger" disabled={reason.trim().length < 3 || busy} onClick={reject}>Xác nhận từ chối</button></div></>}
      {dialog === "edit" && <><div className="eyebrow">Tạo phiên bản mới</div><h2 id="modal-title">Chỉnh sửa draft</h2><p className="muted">Nội dung cũ sẽ bị vô hiệu và phiên bản mới quay lại hàng chờ.</p><label htmlFor="edit-to">Người nhận</label><input id="edit-to" type="email" value={edit.to} onChange={(event) => setEdit({ ...edit, to: event.target.value })}/><label htmlFor="edit-subject">Tiêu đề</label><input id="edit-subject" value={edit.subject} onChange={(event) => setEdit({ ...edit, subject: event.target.value })}/><label htmlFor="edit-body">Nội dung</label><textarea id="edit-body" rows={8} value={edit.body} onChange={(event) => setEdit({ ...edit, body: event.target.value })}/><div className="modal-actions"><button className="button secondary" onClick={() => setDialog(null)}>Hủy</button><button className="button" disabled={!edit.to || !edit.subject || !edit.body || busy} onClick={saveEdit}>Lưu phiên bản mới</button></div></>}
      {dialog === "bulk" && bulkPreview && <><div className="modal-icon success">✓</div><h2 id="modal-title">Xác nhận duyệt hàng loạt</h2><p className="muted">Hệ thống đã kiểm tra lại phiên bản, channel, quyền và blocker.</p><div className="bulk-summary"><div><strong>{bulkPreview.eligible.length}</strong><span>Đủ điều kiện</span></div><div><strong>{bulkPreview.excluded.length}</strong><span>Giữ lại</span></div><div><strong>{money(bulkPreview.total_minor, selectedItems[0]?.currency ?? "VND")}</strong><span>Tổng giá trị</span></div></div>{bulkPreview.excluded.length > 0 && <div className="exclusion-note">{bulkPreview.excluded.length} mục có blocker hoặc dữ liệu đã thay đổi sẽ không được duyệt.</div>}<div className="modal-actions"><button className="button secondary" onClick={() => setDialog(null)}>Quay lại</button><button className="button approve" disabled={!bulkPreview.eligible.length || busy} onClick={commitBulk}>Duyệt {bulkPreview.eligible.length} mục</button></div></>}</section></div>}
  </>;
}
