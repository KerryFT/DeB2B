import V2DataPage from "../components/v2-data-page";

export default function CashFlowPage() {
  return <V2DataPage title="Probabilistic cash flow" eyebrow="V2 · P10 / P50 / P90" endpoint="/api/v2/cash-flow?horizon_days=30" description="Forecast reconcile về từng invoice và hiển thị riêng theo currency. Đây không phải accounting cash position." />;
}
