"use client";

import { useEffect, useState } from "react";
import { apiBase, apiHeaders } from "../lib/api";


export default function V2DataPage({ title, eyebrow, description, endpoint }: { title: string; eyebrow: string; description: string; endpoint: string }) {
  const [data, setData] = useState<Record<string, unknown>>();
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${apiBase}${endpoint}`, { headers: apiHeaders("ar_manager"), credentials: "include", signal: controller.signal }).then(async (response) => {
      if (!response.ok) throw new Error(`API ${response.status}`);
      setData(await response.json());
    }).catch((reason: unknown) => {
      if (reason instanceof Error && reason.name !== "AbortError") setError(reason.message);
    });
    return () => controller.abort();
  }, [endpoint]);
  return <>
    <div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p className="lede">{description}</p>
    {!data && !error && <p role="status">Đang tải dữ liệu point-in-time…</p>}
    {error && <p role="alert" className="badge warn">Không thể tải: {error}</p>}
    {data && <section className="card data-panel" aria-label={`${title} data`}><div className="actions">
      {"as_of" in data && <span className="badge">as_of: {String(data.as_of)}</span>}
      {"model_version" in data && <span className="badge">{String(data.model_version)}</span>}
      {"taxonomy_version" in data && <span className="badge">{String(data.taxonomy_version)}</span>}
      {"metric_version" in data && <span className="badge">{String(data.metric_version)}</span>}
    </div><pre className="json-view">{JSON.stringify(data, null, 2)}</pre></section>}
  </>;
}
