const connectors = [
  { name: "Gmail", account: "ar@example.com", state: "CONNECTED", detail: "Đồng bộ 2 phút trước", action: "Sync now" },
  { name: "Outlook", account: "ar@outlook.example", state: "SANDBOX", detail: "Mail.ReadWrite · delta folder AR-Agent · draft only", action: "Test delta" },
  { name: "MISA", account: "Tenant sandbox", state: "READ_ONLY", detail: "Incremental sync · write-back disabled", action: "Test sync" },
  { name: "Zalo OA", account: "OA sandbox", state: "DRY_RUN", detail: "Verified recipients · approved templates", action: "Test policy" },
  { name: "Gmail", account: "expired@example.com", state: "AUTH_REQUIRED", detail: "Refresh token đã bị thu hồi", action: "Reconnect" },
];

export default function Settings() { return <><div className="eyebrow">Tenant settings</div><h1>Connectors & policy</h1><div className="grid">
  {connectors.map((connector) => <article className="card" key={`${connector.name}-${connector.account}`}><h2>{connector.name}</h2><span className={`badge ${connector.state === "CONNECTED" ? "" : "warn"}`}>{connector.state}</span><p>{connector.account}</p><p className="muted">{connector.detail}</p><button className="button secondary">{connector.action}</button></article>)}
  <article className="card"><h2>LLM route</h2><p className="muted">Fake provider · offline-safe · external fallback disabled by default</p></article>
</div></>; }
