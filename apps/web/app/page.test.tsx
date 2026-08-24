import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import Dashboard from "./page";

describe("Dashboard", () => {
  it("renders the initial accessible overview state", () => {
    const html = renderToStaticMarkup(<Dashboard />);

    expect(html).toContain("Dòng tiền cần hành động");
    expect(html).toContain("Đang tải dữ liệu");
    expect(html).toContain('aria-label="Tổng quan"');
  });
});
