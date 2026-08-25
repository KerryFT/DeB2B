import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import Approvals from "./page";

describe("Approval inbox", () => {
  it("renders the review workflow and safe initial loading state", () => {
    const html = renderToStaticMarkup(<Approvals />);

    expect(html).toContain("Hộp thư phê duyệt");
    expect(html).toContain("Human-in-the-loop");
    expect(html).toContain("Tạo yêu cầu từ hồ sơ");
    expect(html).toContain('aria-label="Bộ lọc"');
  });
});
