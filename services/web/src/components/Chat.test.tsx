import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { api } from "@/lib/api";
import { Chat, shouldAutoSendTranscript, shouldStopForSilence } from "./Chat";

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

test("shows the time of each persisted message", async () => {
  apiMock.mockImplementation((path) => {
    if (path === "/chat/messages") {
      return Promise.resolve([
        {
          id: "message-1",
          role: "assistant",
          text: "Timer finished",
          created_at: "2026-08-04T05:14:00Z",
        },
      ]);
    }
    return Promise.resolve([]);
  });

  render(<Chat />);

  expect(await screen.findByText("Timer finished")).toBeVisible();
  expect(document.querySelector("time[datetime='2026-08-04T05:14:00Z']")).not.toBeNull();
});

test("inserts a clicked recipient candidate into the composer", async () => {
  apiMock.mockImplementation((path) => Promise.resolve(path === "/chat/messages" ? [{
    id: "message-choice",
    role: "assistant",
    text: "Choose: sorokinani@gmail.com, a.sorokina@blanc.ru",
    created_at: "2026-08-10T06:42:00Z",
  }] : []));

  render(<Chat />);
  fireEvent.click(await screen.findByRole("button", { name: "sorokinani@gmail.com" }));

  expect(screen.getByRole("textbox", { name: "Command" })).toHaveValue("sorokinani@gmail.com");
  expect(screen.getByRole("textbox", { name: "Command" })).toHaveFocus();
});

test("shows named active timers as a large countdown", async () => {
  apiMock.mockImplementation((path) => Promise.resolve(path === "/timers" ? [{
    id: "timer-1", title: "Макароны", status: "active",
    ends_at: new Date(Date.now() + 65000).toISOString(),
  }] : []));
  render(<Chat />);
  expect(await screen.findByRole("timer")).toHaveTextContent("Макароны");
  expect(screen.getByRole("timer")).toHaveTextContent(/01:0[4-6]/);
});

test("auto-sends only short simple voice transcripts", () => {
  expect(shouldAutoSendTranscript("Поставь таймер яйца на 7 минут")).toBe(true);
  expect(shouldAutoSendTranscript("Сначала найди все важные письма, потом изучи вложения, подготовь ответы и создай задачи по каждому из них на завтра утром")).toBe(false);
});

test("stops voice recording only after speech and a sustained pause", () => {
  expect(shouldStopForSilence(false, 3000, 4000)).toBe(false);
  expect(shouldStopForSilence(true, 1000, 4000)).toBe(false);
  expect(shouldStopForSilence(true, 1400, 2000)).toBe(true);
});
