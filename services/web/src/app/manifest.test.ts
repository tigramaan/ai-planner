import { describe, expect, it } from "vitest";
import manifest from "./manifest";

describe("PWA manifest", () => {
  it("is installable and starts at the protected application", () => {
    const value = manifest();
    expect(value.display).toBe("standalone");
    expect(value.start_url).toBe("/");
    expect(value.icons).toHaveLength(1);
  });
});
