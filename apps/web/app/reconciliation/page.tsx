"use client";

import { useEffect, useState } from "react";
import { apiBase, apiHeaders } from "../lib/api";

type Transaction = { id: string; booked_date: string; amount_minor: number; currency: string; reference: string; status: string };

export default function Reconciliation() {
  const [rows, setRows] = useState<Transaction[]>([]);
  const [failed, setFailed] = useState(false);
  useEffect(() => { fetch(`${apiBase}/api/v1/reconciliation`, { headers: apiHeaders(), credentials: "include" }).then(async (response) => {
    if (!response.ok) throw new Error("queue unavailable"); setRows(await response.json());
  }).catch(() => setFailed(true)); }, []);
  return <><div className="eyebrow">Bank CSV</div><h1>Reconciliation review</h1><div className="card"><p className="muted">Không case nào được chuyển PAID nếu allocation chưa được xác nhận và cân bằng outstanding.</p>{failed && <p role="alert">Không thể tải queue.</p>}{!failed && rows.length === 0 && <p>Chưa có giao dịch.</p>}{rows.length > 0 && <table className="table"><thead><tr><th>Ngày</th><th>Tham chiếu</th><th>Số tiền</th><th>Trạng thái</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id}><td>{row.booked_date}</td><td>{row.reference}</td><td>{row.amount_minor.toLocaleString("vi-VN")} {row.currency}</td><td><span className="badge">{row.status}</span></td></tr>)}</tbody></table>}</div></>;
}
