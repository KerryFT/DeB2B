"use client";

import { useEffect, useState } from "react";
import { apiBase, apiFetch } from "../lib/api";

type Connector = {
  provider: string;
  environment: string;
  capabilities: string[];
  enabled: boolean;
};

export default function Settings() {
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [authenticated, setAuthenticated] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    apiFetch("/api/v1/me")
      .then(async (me) => {
        if (!active) return;
        setAuthenticated(me.ok);
        if (!me.ok) return;
        const response = await apiFetch("/api/v1/connectors");
        if (active && response.ok) setConnectors(await response.json());
      })
      .catch(() => { if (active) setMessage("Không thể tải trạng thái connector."); });
    return () => { active = false; };
  }, []);

  async function syncOutlook() {
    setBusy(true);
    setMessage("");
    try {
      const response = await apiFetch("/api/v1/connectors/outlook/sync", { method: "POST" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Đồng bộ thất bại");
      setMessage(`Đã nhập ${result.created} email mới; bỏ qua ${result.duplicates} bản trùng.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Đồng bộ thất bại");
    } finally {
      setBusy(false);
    }
  }

  const outlook = connectors.find((item) => item.provider === "outlook");
  return <>
    <div className="eyebrow">Portfolio-safe integrations</div>
    <h1>Connectors & policy</h1>
    <p className="lede">Outlook chạy manual delta sync và chỉ tạo draft. Webhook, sendMail và MISA API bị khóa ở backend.</p>
    {message && <p role="status">{message}</p>}
    <div className="grid">
      <article className="card">
        <h2>Outlook</h2>
        <span className={`badge ${outlook?.enabled ? "" : "warn"}`}>{outlook?.enabled ? "CONNECTED" : "NOT CONNECTED"}</span>
        <p className="muted">Mail.ReadWrite delegated · inbox delta · allowlisted draft only</p>
        {!authenticated || !outlook?.enabled
          ? <a className="button" href={`${apiBase}/api/v1/auth/microsoft/login`}>Kết nối Microsoft</a>
          : <button className="button" disabled={busy} onClick={syncOutlook}>{busy ? "Đang đồng bộ…" : "Sync now"}</button>}
      </article>
      <article className="card">
        <h2>MISA</h2><span className="badge">FILE IMPORT</span>
        <p className="muted">CSV/XLSX mapping · idempotent commit · API/write-back disabled</p>
        <a className="button secondary" href="/imports">Mở Import MISA</a>
      </article>
      <article className="card">
        <h2>Safety</h2><span className="badge">LOCKED</span>
        <p className="muted">Auto-send off · webhook off · Temporal/OCR off · synthetic portfolio data only</p>
      </article>
    </div>
  </>;
}
