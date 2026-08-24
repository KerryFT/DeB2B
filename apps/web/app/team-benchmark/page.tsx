import V2DataPage from "../components/v2-data-page";

export default function BenchmarkPage() {
  return <V2DataPage title="Account manager benchmark" eyebrow="V2 · portfolio-adjusted" endpoint="/api/v2/account-manager-benchmark" description="Raw và adjusted metric đi cạnh nhau; cohort nhỏ bị suppress. Chỉ dùng cho operational coaching, không dùng ra quyết định nhân sự." />;
}
