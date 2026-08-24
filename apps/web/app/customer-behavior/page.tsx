import V2DataPage from "../components/v2-data-page";

export default function BehaviorPage() {
  return <V2DataPage title="Customer payment behavior" eyebrow="V2 · evidence-based profile" endpoint="/api/v2/customer-behavior" description="Chỉ dùng nhãn mô tả consistent, variable hoặc insufficient_data; không phải credit score hay phán xét đạo đức." />;
}
