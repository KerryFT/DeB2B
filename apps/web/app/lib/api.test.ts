import { describe, expect, it } from "vitest";

import { resolveApiBase } from "./api";

describe("API base URL", () => {
  it("uses the configured API origin and removes trailing slashes", () => {
    expect(resolveApiBase("https://api.example.com/", "production")).toBe(
      "https://api.example.com",
    );
  });

  it("fails safe to the deployed API when the Vercel variable is absent", () => {
    expect(resolveApiBase(undefined, "production")).toBe("https://api.deb2b.id.vn");
  });

  it("uses the local API during development", () => {
    expect(resolveApiBase(undefined, "development")).toBe("http://localhost:8000");
  });
});
