"use client";

import { CheckCircle } from "@phosphor-icons/react";
import { useEffect } from "react";

export function ActionToast({
  message,
  onDismiss,
}: {
  message: string;
  onDismiss: () => void;
}) {
  useEffect(() => {
    if (!message) return;
    const timer = window.setTimeout(onDismiss, 3200);
    return () => window.clearTimeout(timer);
  }, [message, onDismiss]);
  if (!message) return null;
  return (
    <div className="actionToast" role="status" aria-live="polite">
      <CheckCircle size={20} weight="fill" />
      <span>{message}</span>
    </div>
  );
}
