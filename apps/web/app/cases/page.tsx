"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiBase, apiHeaders } from "../lib/api";

type CaseRow = {
  id: string;
  status: string;
  invoice_number: string;
  customer: string;
  outstanding_minor: number;
  currency: string;
};

export default function Cases() {
  const [rows, setRows] = useState<CaseRow[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    fetch(`${apiBase}/api/v1/cases`, { headers: apiHeaders(), credentials: "include" })
      .then(async (response) => {
        if (!response.ok) throw new Error("API unavailable");
        setRows(await response.json());
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, []);

  return <>
    <div className="eyebrow">Operations queue</div><h1>Payment cases</h1>
    <div className="card">
      <div className="actions"><Link className="button" href="/imports">Import công nợ</Link><Link className="button secondary" href="/agent">Phân tích bằng AI Agent</Link></div>
      {status === "loading" && <p aria-live="polite">Đang tải case…</p>}
      {status === "error" && <p role="alert">Không thể tải API. Dữ liệu hiện tại có thể đã cũ.</p>}
      {status === "ready" && rows.length === 0 && <p className="muted">Chưa có case. Hãy import fixture smoke.</p>}
      {rows.length > 0 && <table className="table"><thead><tr><th>Hóa đơn</th><th>Khách hàng</th><th>Còn phải thu</th><th>Trạng thái</th></tr></thead><tbody>
        {rows.map((row) => <tr key={row.id}><td><Link href={`/cases/${row.id}`}>{row.invoice_number}</Link></td><td>{row.customer}</td><td>{row.outstanding_minor.toLocaleString("vi-VN")} {row.currency}</td><td><span className="badge">{row.status}</span></td></tr>)}
      </tbody></table>}
    </div>
  </>;
}
