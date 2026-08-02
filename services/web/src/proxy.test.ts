import { describe, expect, it } from "vitest";
import { NextRequest } from "next/server";
import { proxy } from "./proxy";

describe("protected routes", () => {
  it("redirects an anonymous home request", () => {
    const response = proxy(new NextRequest("https://planner.umec.space/"));
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("https://planner.umec.space/login");
  });

  it("allows setup and authenticated home", () => {
    expect(proxy(new NextRequest("https://planner.umec.space/setup")).status).toBe(200);
    const request = new NextRequest("https://planner.umec.space/", {
      headers: { cookie: "access_token=test" },
    });
    expect(proxy(request).status).toBe(200);
  });
});
