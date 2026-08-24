import V2DataPage from "../components/v2-data-page";

export default function ProbabilityPage() {
  return <V2DataPage title="Probability to pay" eyebrow="V2 · calibrated baseline" endpoint="/api/v2/probability-to-pay" description="Xác suất theo horizon 7/14/30 ngày, có as_of, version và cờ chất lượng; không tự kích hoạt hành động." />;
}
