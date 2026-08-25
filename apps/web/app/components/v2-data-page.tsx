"use client";

import { useEffect, useMemo, useState } from "react";
import { apiBase, apiHeaders } from "../lib/api";

function label(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function display(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Có" : "Không";
  if (typeof value === "number") return value.toLocaleString("vi-VN");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

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
  const summary = useMemo(() => Object.entries(data ?? {}).filter(([, value]) => !Array.isArray(value) && (typeof value !== "object" || value === null)).slice(0, 8), [data]);
  const collection = useMemo(() => Object.entries(data ?? {}).find(([, value]) => Array.isArray(value) && value.length > 0 && typeof value[0] === "object") as [string, Array<Record<string, unknown>>] | undefined, [data]);
  const columns = useMemo(() => collection ? Array.from(new Set(collection[1].slice(0, 10).flatMap((row) => Object.keys(row)))).filter((key) => !key.endsWith("_id") && key !== "tenant_id").slice(0, 7) : [], [collection]);
  return <>
    <header className="page-header"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p className="lede">{description}</p></div>{data && <span className="data-freshness"><i/>Dữ liệu đã đồng bộ</span>}</header>
    {!data && !error && <div className="analytics-loading"><div/><div/><div/></div>}
    {error && <div className="empty-state"><div className="empty-icon">!</div><h2>Không thể tải dữ liệu</h2><p>{error}. Kiểm tra phiên đăng nhập hoặc kết nối API.</p></div>}
    {data && <>
      {summary.length > 0 && <section className="data-summary" aria-label="Thông tin tổng quan">{summary.map(([key, value]) => <article key={key}><small>{label(key)}</small><strong>{display(value)}</strong></article>)}</section>}
      {collection ? <section className="business-table card"><div className="table-heading"><div><h2>{label(collection[0])}</h2><p>{collection[1].length} bản ghi trong phạm vi hiện tại</p></div><span className="badge">Evidence-aware</span></div><div className="table-scroll"><table className="table"><thead><tr>{columns.map((key) => <th key={key}>{label(key)}</th>)}</tr></thead><tbody>{collection[1].map((row, index) => <tr key={String(row.id ?? row.case_id ?? index)}>{columns.map((key) => <td key={key} title={display(row[key])}>{display(row[key])}</td>)}</tr>)}</tbody></table></div></section> : <div className="empty-state embedded"><div className="empty-icon">◇</div><h2>Chưa có bản ghi</h2><p>Dữ liệu sẽ xuất hiện sau khi có hồ sơ phù hợp trong khoảng phân tích.</p></div>}
      <details className="technical-data"><summary>Dữ liệu kỹ thuật và provenance</summary><pre className="json-view">{JSON.stringify(data, null, 2)}</pre></details>
    </>}
  </>;
}
