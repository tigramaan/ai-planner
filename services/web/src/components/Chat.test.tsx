import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { api } from "@/lib/api";
import { Chat } from "./Chat";

vi.mock("@/lib/api", () => ({ api: vi.fn(), uploadAudio: vi.fn() }));

const apiMock = vi.mocked(api);

afterEach(() => {
  cleanup();
  apiMock.mockReset();
});

test("shows a typing status until the assistant response arrives", async () => {
  let finish: ((value: { message: string }) => void) | undefined;
  apiMock.mockImplementation((path, options) => {
    if (path === "/chat/messages" && options?.method === "POST") {
      return new Promise((resolve) => { finish = resolve; });
    }
    return Promise.resolve([]);
  });

  render(<Chat />);
  fireEvent.change(screen.getByRole("textbox", { name: "Command" }), {
    target: { value: "Find important mail" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));

  expect(await screen.findByRole("status", { name: "Planner is typing" })).toBeVisible();
  finish?.({ message: "Done" });
  await waitFor(() => expect(screen.queryByRole("status", { name: "Planner is typing" })).toBeNull());
  expect(screen.getByText("Done")).toBeVisible();
});
