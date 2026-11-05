export type ToastSeverity = 'info' | 'warning' | 'error';

export interface Toast {
  id: string;
  message: string;
  severity: ToastSeverity;
  at: string;
  dismissed: boolean;
}

export interface VisibleToast extends Toast {
  repeats: number;
  autoDismissMs: number | null;
}

export interface PresentedToasts {
  visible: VisibleToast[];
  hidden: number;
}

const MAX_VISIBLE = 3;

// An error stays until someone deals with it; the rest clear themselves.
const DISMISS_AFTER: Record<ToastSeverity, number | null> = {
  info: 5000,
  warning: 10000,
  error: null,
};

const RANK: Record<ToastSeverity, number> = { error: 2, warning: 1, info: 0 };

export function queueToasts(toasts: Toast[], _now: Date): PresentedToasts {
  const live = toasts.filter((toast) => !toast.dismissed);

  const byMessage = new Map<string, Toast[]>();
  for (const toast of live) {
    byMessage.set(toast.message, [...(byMessage.get(toast.message) ?? []), toast]);
  }

  const collapsed = [...byMessage.values()].map((group) => {
    const [newest] = [...group].sort((a, b) => Date.parse(b.at) - Date.parse(a.at));
    return {
      ...newest,
      repeats: group.length,
      autoDismissMs: DISMISS_AFTER[newest.severity],
    };
  });

  // Severity first, so an error is never pushed off by chatter.
  const ordered = collapsed.sort(
    (a, b) => RANK[b.severity] - RANK[a.severity] || Date.parse(b.at) - Date.parse(a.at),
  );

  return {
    visible: ordered.slice(0, MAX_VISIBLE),
    hidden: Math.max(0, ordered.length - MAX_VISIBLE),
  };
}
