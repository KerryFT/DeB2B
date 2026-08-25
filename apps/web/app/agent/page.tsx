"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { apiBase, apiFetch, apiHeaders } from "../lib/api";

type AgentStatus = { configured: boolean; provider: string; fast_model?: string; reasoning_model?: string; mode: string; guardrails: string[] };
type CaseRow = { id: string; status: string; invoice_number: string; customer: string; outstanding_minor: number; currency: string };
type Analysis = { summary: string; risk_level: string; detected_blockers: string[]; recommended_next_action: string; rationale: string[]; evidence_refs: string[]; confidence: number; requires_human_review: boolean };
type AnalysisResponse = { provider: string; model: string; prompt_version: string; analysis: Analysis };
type DraftResponse = { approval_id: string; content: string; case_id: string; to: string[]; cc: string[]; subject: string; body: string; evidence_refs: string[]; safety_notes: string[]; provider: string; model: string };

const guardrailLabels: Record<string, string> = {
  evidence_required: "Bắt buộc bằng chứng",
  prompt_injection_boundary: "Chặn prompt injection",
  human_approval_required: "Con người phê duyệt",
  external_send_disabled: "Không tự gửi email",
};

export default function AgentPage() {
  const [status, setStatus] = useState<AgentStatus>();
  const [cases, setCases] = useState<CaseRow[]>([]);
  const [caseId, setCaseId] = useState("");
  const [analysis, setAnalysis] = useState<AnalysisResponse>();
  const [draft, setDraft] = useState<DraftResponse>();
  const [recipient, setRecipient] = useState("");
  const [objective, setObjective] = useState("Nhắc khách hàng xác nhận tình trạng hồ sơ và thời gian thanh toán dự kiến.");
  const [busy, setBusy] = useState<"analyze" | "draft" | "">("");
  const [error, setError] = useState("");

  useEffect(() => {
    const headers = apiHeaders("approver");
    Promise.all([
      fetch(`${apiBase}/api/v1/ai/status`, { headers, credentials: "include" }).then((response) => response.ok ? response.json() : Promise.reject()),
      fetch(`${apiBase}/api/v1/cases`, { headers, credentials: "include" }).then((response) => response.ok ? response.json() : Promise.reject()),
    ]).then(([agentStatus, caseRows]: [AgentStatus, CaseRow[]]) => {
      setStatus(agentStatus); setCases(caseRows); setCaseId(caseRows[0]?.id ?? "");
    }).catch(() => setError("Không thể tải AI Agent hoặc danh sách hồ sơ."));
  }, []);

  const selectedCase = useMemo(() => cases.find((item) => item.id === caseId), [caseId, cases]);

  async function errorText(response: Response) {
    try { const data = await response.json(); return data.detail ?? "Yêu cầu thất bại."; }
    catch { return "Yêu cầu thất bại."; }
  }

  async function runAnalysis() {
    if (!caseId) return;
    setBusy("analyze"); setError(""); setAnalysis(undefined); setDraft(undefined);
    const response = await apiFetch(`/api/v1/ai/cases/${caseId}/analyze`, { method: "POST", headers: apiHeaders("approver") });
    if (response.ok) setAnalysis(await response.json()); else setError(await errorText(response));
    setBusy("");
  }

  async function generateDraft() {
    if (!caseId || !recipient || !objective) return;
    setBusy("draft"); setError(""); setDraft(undefined);
    const response = await apiFetch(`/api/v1/ai/cases/${caseId}/draft`, {
      method: "POST",
      headers: apiHeaders("approver", true),
      body: JSON.stringify({ to: [recipient], cc: [], objective }),
    });
    if (response.ok) {
      const result: DraftResponse = await response.json();
      setDraft(result);
      try {
        const key = "deb2b-draft-approvals";
        const stored = JSON.parse(sessionStorage.getItem(key) ?? "{}");
        stored[result.approval_id] = result;
        sessionStorage.setItem(key, JSON.stringify(stored));
      } catch { /* Approval remains valid; only cross-page session preview is unavailable. */ }
    } else setError(await errorText(response));
    setBusy("");
  }

  return <>
    <header className="page-header agent-header">
      <div><div className="eyebrow">Evidence-grounded copilot</div><h1>AI Agent Workbench</h1><p className="lede">Phân tích hồ sơ, đề xuất bước tiếp theo và soạn draft có kiểm soát. Agent không thay đổi số liệu hoặc gửi email.</p></div>
      <div className={`agent-live ${status?.configured ? "online" : "offline"}`}><span/><div><strong>{status?.configured ? "Gemini đang hoạt động" : "AI chưa được cấu hình"}</strong><small>{status?.configured ? `${status.provider} · live inference` : "offline mode"}</small></div></div>
    </header>

    <section className="agent-flow" aria-label="Luồng AI Agent">
      {["Chọn hồ sơ", "Phân tích bằng chứng", "Soạn hành động", "Human approval"].map((label, index) => <div key={label}><span>{index + 1}</span><strong>{label}</strong>{index < 3 && <i>→</i>}</div>)}
    </section>

    {status && <section className="agent-config card"><div><small>Reasoning model</small><strong>{status.reasoning_model ?? "Chưa cấu hình"}</strong></div><div><small>Fast model</small><strong>{status.fast_model ?? "Chưa cấu hình"}</strong></div><div className="guardrail-row">{status.guardrails.map((item) => <span key={item}>✓ {guardrailLabels[item] ?? item}</span>)}</div></section>}
    {error && <div className="toast error" role="alert"><span>!</span>{error}<button onClick={() => setError("")} aria-label="Đóng">×</button></div>}

    <div className="agent-workspace">
      <aside className="agent-cases card"><div className="section-title"><h2>Hồ sơ cần xử lý</h2><span>{cases.length} hồ sơ</span></div>{cases.length === 0 && <div className="mini-empty"><p>Chưa có hồ sơ để phân tích.</p><Link href="/imports" className="text-link">Import dữ liệu →</Link></div>}{cases.map((item) => <button key={item.id} className={caseId === item.id ? "active" : ""} onClick={() => { setCaseId(item.id); setAnalysis(undefined); setDraft(undefined); }}><span><strong>{item.customer}</strong><small>{item.invoice_number} · {item.outstanding_minor.toLocaleString("vi-VN")} {item.currency}</small></span><i>{item.status.replaceAll("_", " ")}</i></button>)}</aside>

      <main className="agent-main card">
        {!selectedCase && <div className="empty-state embedded"><div className="empty-icon">✦</div><h2>Chọn một hồ sơ</h2><p>Agent cần dữ liệu case và evidence trước khi có thể phân tích.</p></div>}
        {selectedCase && <>
          <div className="agent-case-head"><div><div className="eyebrow">Đang phân tích</div><h2>{selectedCase.invoice_number}</h2><p>{selectedCase.customer}</p></div><button className="button" disabled={!status?.configured || Boolean(busy)} onClick={runAnalysis}>{busy === "analyze" ? "Gemini đang phân tích…" : "✦ Phân tích hồ sơ"}</button></div>
          {!analysis && !busy && <div className="agent-placeholder"><span>✦</span><h3>Agent chỉ sử dụng dữ liệu có bằng chứng</h3><p>Nhấn “Phân tích hồ sơ” để nhận tóm tắt, blocker và hành động đề xuất. Kết quả không tự động thay đổi case.</p></div>}
          {busy === "analyze" && <div className="agent-thinking"><div className="thinking-orb">✦</div><div><strong>Đang đối chiếu hồ sơ và bằng chứng…</strong><span>Kiểm tra blocker · đánh giá rủi ro · tạo đề xuất</span></div></div>}
          {analysis && <section className="agent-result"><div className="result-heading"><div><span className={`risk-badge ${analysis.analysis.risk_level.toLowerCase()}`}>{analysis.analysis.risk_level} RISK</span><h3>Tóm tắt của Agent</h3></div><small>{analysis.model} · {analysis.prompt_version}</small></div><p className="agent-summary">{analysis.analysis.summary}</p><div className="recommendation"><span>→</span><div><small>Hành động tiếp theo được đề xuất</small><strong>{analysis.analysis.recommended_next_action}</strong></div><b>{Math.round(analysis.analysis.confidence * 100)}% confidence</b></div><div className="agent-detail-grid"><div><h4>Lý do</h4><ul>{analysis.analysis.rationale.map((item) => <li key={item}>{item}</li>)}</ul></div><div><h4>Evidence được dùng</h4><div className="evidence-tags">{analysis.analysis.evidence_refs.map((item) => <span key={item}>{item}</span>)}</div></div></div>
            <div className="draft-composer"><div className="section-title"><h3>Soạn follow-up bằng AI</h3><span>Luôn cần phê duyệt</span></div><div className="composer-grid"><label>Người nhận<input type="email" placeholder="ap@customer.com" value={recipient} onChange={(event) => setRecipient(event.target.value)}/></label><label>Mục tiêu email<textarea rows={3} value={objective} onChange={(event) => setObjective(event.target.value)}/></label></div><button className="button secondary" disabled={!recipient || !objective || Boolean(busy)} onClick={generateDraft}>{busy === "draft" ? "Đang soạn draft…" : "Tạo draft cần duyệt"}</button></div>
          </section>}
          {draft && <section className="generated-draft"><div className="draft-success"><span>✓</span><div><strong>Draft đã vào hàng chờ phê duyệt</strong><small>{draft.model} · chưa gửi ra ngoài</small></div><Link href="/approvals" className="button">Mở Approval inbox →</Link></div><dl><div><dt>Đến</dt><dd>{draft.to.join(", ")}</dd></div><div><dt>Tiêu đề</dt><dd>{draft.subject}</dd></div></dl><div className="email-body">{draft.body}</div><div className="safety-notes">{draft.safety_notes.map((item) => <span key={item}>ⓘ {item}</span>)}</div></section>}
        </>}
      </main>
    </div>
  </>;
}
