import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { api } from "@/lib/api";
import { PushSetup } from "./PushSetup";

vi.mock("@/lib/api", () => ({ api: vi.fn() }));

const apiMock = vi.mocked(api);

function browserPush(permission: NotificationPermission, subscription: object | null = null) {
  const registration = {
    pushManager: {
      getSubscription: vi.fn().mockResolvedValue(subscription),
      subscribe: vi.fn(),
    },
  };
  Object.defineProperty(navigator, "serviceWorker", {
    configurable: true,
    value: { ready: Promise.resolve(registration) },
  });
  vi.stubGlobal("PushManager", class PushManager {});
  vi.stubGlobal("Notification", {
    permission,
    requestPermission: vi.fn(),
  });
  return registration;
}

afterEach(() => {
  cleanup();
  apiMock.mockReset();
  vi.unstubAllGlobals();
});

test("highlights disabled notifications on every screen", async () => {
  browserPush("default");
  apiMock.mockResolvedValue({ configured: false });

  render(<PushSetup compact />);

  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Notifications are off"));
  expect(screen.getByRole("button", { name: "Enable" })).toBeVisible();
  expect(screen.getByText("Timers and tasks cannot alert you.")).toBeVisible();
});

test("explains recovery when browser permission is blocked", async () => {
  browserPush("denied");

  render(<PushSetup compact />);

  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Notifications are blocked"));
  expect(screen.getByRole("button", { name: "How to allow" })).toBeVisible();
  expect(apiMock).not.toHaveBeenCalled();
});

test("checks real server delivery when notifications look enabled", async () => {
  browserPush("granted", {});
  apiMock.mockImplementation(async (path) => {
    if (path === "/push/status") return { configured: true };
    if (path === "/push/test") return { id: "test-reminder" };
    return { status: "delivered" };
  });

  render(<PushSetup />);

  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Notifications are on"));
  fireEvent.click(screen.getByRole("button", { name: "Test notification" }));
  await waitFor(
    () => expect(screen.getByText("Test notification sent to this device.")).toBeVisible(),
    { timeout: 2500 },
  );
});

test("does not consume chat space when notifications are enabled", async () => {
  browserPush("granted", {});
  apiMock.mockResolvedValue({ configured: true });
  render(<PushSetup compact />);
  await waitFor(() => expect(apiMock).toHaveBeenCalledWith("/push/status"));
  expect(screen.queryByRole("status")).toBeNull();
});
