"use client";

import { useEffect, useState } from "react";
import { apiBase, apiHeaders } from "../lib/api";


export default function EscalationPage() {
  const [data, setData] = useState<Record<string, unknown>>();
  const [message, setMessage] = useState("Đang tìm case demo…");
  useEffect(() => {
    const controller = new AbortController();
    const headers = apiHeaders("ar_manager");
    fetch(`${apiBase}/api/v1/cases`, { headers, credentials: "include", signal: controller.signal })
      .then(async response => { if (!response.ok) throw new Error(`API ${response.status}`); return response.json(); })
      .then(async (cases: Array<{ id: string }>) => {
        if (!cases.length) { setMessage("Chưa có case. Hãy chạy seed demo."); return; }
        const response = await fetch(`${apiBase}/api/v2/escalation/${cases[0].id}/generate`, { method: "POST", headers, credentials: "include", signal: controller.signal });
        if (!response.ok) throw new Error(`API ${response.status}`);
        setData(await response.json()); setMessage("");
      }).catch((reason: unknown) => {
        if (reason instanceof Error && reason.name !== "AbortError") setMessage(`Không thể tải: ${reason.message}`);
      });
    return () => controller.abort();
  }, []);
  return <><div className="eyebrow">V2 · human decision support</div><h1>Escalation strategy</h1><p className="lede">So sánh phương án có evidence và reason code. Hệ thống không tự escalation hoặc gửi legal notice.</p>{message && <p role="status">{message}</p>}{data && <div className="card"><pre className="json-view">{JSON.stringify(data, null, 2)}</pre></div>}</>;
}
