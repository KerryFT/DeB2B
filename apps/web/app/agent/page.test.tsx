import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import AgentPage from "./page";

describe("AI Agent workbench", () => {
  it("renders the guarded agent workflow", () => {
    const html = renderToStaticMarkup(<AgentPage />);
    expect(html).toContain("AI Agent Workbench");
    expect(html).toContain("Phân tích bằng chứng");
    expect(html).toContain("Human approval");
    expect(html).toContain("Agent không thay đổi số liệu hoặc gửi email");
  });
});
