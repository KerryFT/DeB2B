import V2DataPage from "../components/v2-data-page";

export default function DisputesPage() {
  return <V2DataPage title="Dispute root causes" eyebrow="V2 · taxonomy + evidence" endpoint="/api/v2/disputes" description="Root cause là suy luận có confidence và evidence, không được trình bày như quan hệ nhân quả đã chứng minh." />;
}
