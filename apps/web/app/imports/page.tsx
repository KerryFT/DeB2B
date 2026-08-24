"use client";

import { FormEvent, useState } from "react";

type Preview = {
  valid: Array<{ invoice_number: string; customer_name: string; amount: string }>;
  invalid: Array<{ row_number: number; errors: Array<{ msg?: string }> }>;
};

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Imports() {
  const [file, setFile] = useState<File>();
  const [preview, setPreview] = useState<Preview>();
  const [state, setState] = useState<"idle" | "loading" | "ready" | "error" | "committed">("idle");
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent, action: "preview" | "commit") {
    event.preventDefault();
    if (!file) return;
    setState("loading");
    const body = new FormData();
    body.append("file", file);
    try {
      const response = await fetch(`${API}/api/v1/imports/${action}`, {
        method: "POST",
        headers: {
          "x-dev-user-id": "00000000-0000-0000-0000-000000000002",
          "x-dev-tenant-id": "00000000-0000-0000-0000-000000000001",
          "x-dev-role": "operator",
        },
        body,
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Import failed");
      if (action === "preview") {
        setPreview(result);
        setState("ready");
      } else {
        setMessage(`Đã tạo ${result.invoices_created} hóa đơn và ${result.cases_created} case.`);
        setState("committed");
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Import failed");
      setState("error");
    }
  }

  return (
    <>
      <div className="eyebrow">Data intake</div>
      <h1>Import CSV/XLSX</h1>
      <form className="card" onSubmit={(event) => submit(event, "preview")}>
        <label htmlFor="ar-file">File công nợ synthetic</label>
        <input id="ar-file" type="file" accept=".csv,.xlsx" onChange={(event) => {
          setFile(event.target.files?.[0]);
          setPreview(undefined);
          setState("idle");
        }} />
        <div className="actions">
          <button className="button" disabled={!file || state === "loading"}>
            {state === "loading" ? "Đang kiểm tra…" : "Xem trước"}
          </button>
          {preview && preview.invalid.length === 0 && (
            <button type="button" className="button secondary" onClick={(event) => submit(event, "commit")}>
              Commit an toàn
            </button>
          )}
        </div>
        {state === "error" && <p role="alert">{message}</p>}
        {state === "committed" && <p role="status">{message}</p>}
      </form>
      {preview && (
        <section className="card" aria-live="polite">
          <h2>Kết quả mapping</h2>
          <p>{preview.valid.length} hợp lệ · {preview.invalid.length} lỗi</p>
          {preview.invalid.map((row) => (
            <p key={row.row_number} className="muted">Dòng {row.row_number}: {row.errors.map((error) => error.msg).join(", ")}</p>
          ))}
          <table className="table">
            <thead><tr><th>Hóa đơn</th><th>Khách hàng</th><th>Số tiền</th></tr></thead>
            <tbody>{preview.valid.slice(0, 20).map((row) => <tr key={row.invoice_number}><td>{row.invoice_number}</td><td>{row.customer_name}</td><td>{row.amount}</td></tr>)}</tbody>
          </table>
        </section>
      )}
    </>
  );
}
