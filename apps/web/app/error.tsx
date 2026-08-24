"use client";
export default function ErrorView({ reset }: { reset: () => void }) { return <div className="card" role="alert"><h2>Không thể tải dữ liệu</h2><button className="button" onClick={reset}>Thử lại</button></div>; }

