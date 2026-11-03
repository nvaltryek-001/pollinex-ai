import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, tokenStore } from "../lib/api";

afterEach(() => { vi.unstubAllGlobals(); tokenStore.set(null); });

describe("api client", () => {
  it("sends the bearer token and parses JSON", async () => {
    tokenStore.set("abc");
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ ok: 1 }), { headers: { "content-type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    expect(await api.get<{ ok: number }>("/x")).toEqual({ ok: 1 });
    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer abc");
  });

  it("surfaces FastAPI error details", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: "File is not a readable image" }), { status: 415, headers: { "content-type": "application/json" } })));
    await expect(api.get("/x")).rejects.toMatchObject({ status: 415, message: "File is not a readable image" });
  });

  it("reports an unreachable backend clearly", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));
    const err = await api.get("/x").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(0);
    expect(err.message).toMatch(/unreachable/i);
  });
});
