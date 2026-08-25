"use client";

import { useEffect, useState } from "react";
import { apiBase, apiFetch, apiHeaders } from "../lib/api";

type Recommendation = { id: string; rank: number; strategy: string; reason_codes: string[]; evidence_ids: string[]; expected_outcome: string; risk: string; prerequisites: string[]; next_review_date: string; confidence: number };
type EscalationResult = { case_id: string; as_of: string; human_decision_required: boolean; recommendations: Recommendation[] };

export default function EscalationPage() {
  const [data, setData] = useState<EscalationResult>();
  const [message, setMessage] = useState("Đang tìm hồ sơ phù hợp…");
  const [feedback, setFeedback] = useState<Record<string, string>>({});
  useEffect(() => {
    const controller = new AbortController();
    const headers = apiHeaders("ar_manager");
    fetch(`${apiBase}/api/v1/cases`, { headers, credentials: "include", signal: controller.signal })
      .then(async response => { if (!response.ok) throw new Error(`API ${response.status}`); return response.json(); })
      .then(async (cases: Array<{ id: string }>) => {
        if (!cases.length) { setMessage("Chưa có hồ sơ. Hãy import dữ liệu trước."); return; }
        const response = await fetch(`${apiBase}/api/v2/escalation/${cases[0].id}/generate`, { method: "POST", headers, credentials: "include", signal: controller.signal });
        if (!response.ok) throw new Error(`API ${response.status}`);
        setData(await response.json()); setMessage("");
      }).catch((reason: unknown) => {
        if (reason instanceof Error && reason.name !== "AbortError") setMessage(`Không thể tải: ${reason.message}`);
      });
    return () => controller.abort();
  }, []);
  async function decide(id: string, decision: "accepted" | "edited" | "rejected") {
    const response = await apiFetch(`/api/v2/escalation/recommendations/${id}/feedback`, { method: "POST", headers: apiHeaders("ar_manager", true), body: JSON.stringify({ decision }) });
    if (response.ok) setFeedback((current) => ({ ...current, [id]: decision }));
  }

  return <><header className="page-header"><div><div className="eyebrow">Human decision support</div><h1>Chiến lược escalation</h1><p className="lede">So sánh phương án theo evidence và reason code. Hệ thống không tự escalation hoặc gửi thông báo pháp lý.</p></div>{data && <span className="data-freshness"><i/>As of {new Date(data.as_of).toLocaleDateString("vi-VN")}</span>}</header>
    {message && <div className="analytics-loading"><p role="status">{message}</p><div/><div/></div>}
    {data && <section className="recommendation-list">{data.recommendations.map((item) => <article className="recommendation-card card" key={item.id}><div className="rank">#{item.rank}</div><div className="recommendation-content"><div className="recommendation-title"><div><span className={`risk-badge ${item.risk.toLowerCase()}`}>{item.risk} RISK</span><h2>{item.strategy.replaceAll("_", " ")}</h2></div><b>{Math.round(item.confidence * 100)}%</b></div><p>{item.expected_outcome}</p><div className="reason-row">{item.reason_codes.map((reason) => <span key={reason}>{reason.replaceAll("_", " ")}</span>)}</div><div className="recommendation-meta"><span>Review: {new Date(item.next_review_date).toLocaleDateString("vi-VN")}</span><span>{item.evidence_ids.length} evidence</span><span>{item.prerequisites.join(", ")}</span></div></div><div className="recommendation-actions">{feedback[item.id] ? <span className="decision-done">✓ {feedback[item.id]}</span> : <><button className="button secondary" onClick={() => decide(item.id, "rejected")}>Từ chối</button><button className="button" onClick={() => decide(item.id, "accepted")}>Chấp nhận</button></>}</div></article>)}</section>}
  </>;
}
