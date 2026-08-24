const connectors = [
  { account: "ar@example.com", state: "CONNECTED", detail: "Đồng bộ 2 phút trước", action: "Sync now" },
  { account: "expired@example.com", state: "AUTH_REQUIRED", detail: "Refresh token đã bị thu hồi", action: "Reconnect" },
  { account: "stale@example.com", state: "STALE", detail: "History cursor cũ hơn 24 giờ", action: "Retry full sync" },
];

export default function Settings() { return <><div className="eyebrow">Tenant settings</div><h1>Connectors & policy</h1><div className="grid">
  {connectors.map((connector) => <article className="card" key={connector.account}><h2>Gmail</h2><span className={`badge ${connector.state === "CONNECTED" ? "" : "warn"}`}>{connector.state}</span><p>{connector.account}</p><p className="muted">{connector.detail} · Label AR-Agent</p><button className="button secondary">{connector.action}</button></article>)}
  <article className="card"><h2>LLM route</h2><p className="muted">Fake provider · offline-safe · external fallback disabled by default</p></article>
</div></>; }
