import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { ActionToast } from "./ActionToast";

test("announces a successful action and dismisses it", () => {
  vi.useFakeTimers();
  const dismiss = vi.fn();
  render(<ActionToast message="Приглашение скопировано в буфер" onDismiss={dismiss} />);

  expect(screen.getByRole("status")).toHaveTextContent("Приглашение скопировано");
  vi.advanceTimersByTime(3200);
  expect(dismiss).toHaveBeenCalledOnce();
  vi.useRealTimers();
});
