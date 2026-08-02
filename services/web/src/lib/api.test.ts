import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";

describe("api client", () => {
  afterEach(() => vi.restoreAllMocks());

  it("uses same-site credentials and returns JSON", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ email: "family@example.com" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    await expect(api<{ email: string }>("/me")).resolves.toEqual({ email: "family@example.com" });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/me",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("surfaces safe API errors", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Registration is invitation-only" }), {
        status: 403,
        headers: { "Content-Type": "application/json" },
      }),
    );
    await expect(api("/auth/register", { method: "POST" })).rejects.toThrow(
      "Registration is invitation-only",
    );
  });
});
