import { afterEach, describe, expect, it, vi } from "vitest";
import { api, audioFilename } from "./api";

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
      expect.objectContaining({ credentials: "include", headers: expect.objectContaining({"Accept-Language":"en"}) }),
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

  it("refreshes an expired access token and retries the request", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ email: "family@example.com" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ email: "family@example.com" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }));

    await expect(api<{ email: string }>("/me")).resolves.toEqual({ email: "family@example.com" });
    expect(fetchMock.mock.calls.map(([path]) => path)).toEqual([
      "/api/v1/me", "/api/v1/auth/refresh", "/api/v1/me",
    ]);
  });

  it("uses a filename matching browser audio MIME types", () => {
    expect(audioFilename("audio/webm;codecs=opus")).toBe("voice.webm");
    expect(audioFilename("audio/mp4;codecs=mp4a.40.2")).toBe("voice.m4a");
    expect(audioFilename("video/mp4")).toBe("voice.m4a");
  });
});
