"use client";

import { useCallback, useEffect, useState } from "react";

const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const headers = { "content-type": "application/json", "x-dev-user-id": "00000000-0000-0000-0000-000000000002", "x-dev-tenant-id": "00000000-0000-0000-0000-000000000001", "x-dev-role": "tenant_admin" };

export default function AutomationPage() {
  const [policy, setPolicy] = useState<Record<string, unknown>>();
  const [message, setMessage] = useState("");
  const load = useCallback(() => fetch(`${api}/api/v2/automation/policy`, { headers }).then(async response => { if (!response.ok) throw new Error(`API ${response.status}`); setPolicy(await response.json()); }).catch((reason: unknown) => setMessage(reason instanceof Error ? reason.message : "API unavailable")), []);
  useEffect(() => { void load(); }, [load]);
  async function disable() {
    setMessage("Đang kích hoạt kill switch…");
    const response = await fetch(`${api}/api/v2/automation/policy`, { method: "POST", headers, body: JSON.stringify({ mode: "disabled", kill_switch: true }) });
    setMessage(response.ok ? "Automation đã disabled; kill switch đang bật." : `Không thể cập nhật: API ${response.status}`);
    if (response.ok) await load();
  }
  return <><div className="eyebrow">V2 · safe automation</div><h1>Low-risk email automation</h1><p className="lede">Mặc định disabled, global và tenant kill switch bật. Live delivery còn bị khóa độc lập bằng biến môi trường.</p><div className="card"><div className="actions"><span className={`badge ${policy?.kill_switch ? "warn" : ""}`}>Tenant kill: {String(policy?.kill_switch ?? "loading")}</span><span className="badge">Mode: {String(policy?.mode ?? "loading")}</span><span className={`badge ${policy?.external_delivery_enabled ? "warn" : ""}`}>External delivery: {String(policy?.external_delivery_enabled ?? false)}</span></div><p>{message}</p><button type="button" className="button" onClick={disable}>Disable + kill switch</button><pre className="json-view">{JSON.stringify(policy, null, 2)}</pre></div></>;
}
