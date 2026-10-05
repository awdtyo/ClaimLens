import { FileSearch } from "lucide-react";
import type { ButtonHTMLAttributes, HTMLAttributes } from "react";
import { cn } from "../lib/utils";

/** Minimal primitives bound to the editorial theme tokens in index.css. */

type ButtonVariant = "default" | "outline" | "ghost" | "destructive";
type ButtonSize = "sm" | "md";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

export function Button({
  variant = "default",
  size = "md",
  className,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        "cl-btn",
        variant === "default" && "cl-btn-primary",
        variant === "outline" && "cl-btn-outline",
        variant === "ghost" && "bg-transparent text-[var(--text-2)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]",
        variant === "destructive" &&
          "bg-[var(--bad)] text-white hover:brightness-110 dark:bg-[var(--bad-soft)] dark:text-[var(--bad)] dark:ring-1 dark:ring-inset dark:ring-[var(--bad)]",
        size === "sm" && "cl-btn-sm",
        className,
      )}
      {...props}
    />
  );
}

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("cl-surface p-4", className)} {...props} />;
}

export function EmptyState({
  title,
  hint,
  action,
}: {
  title: string;
  hint?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="cl-surface-2 flex flex-col items-center gap-2 border-dashed px-6 py-10 text-center">
      <FileSearch size={20} aria-hidden="true" className="text-[var(--text-2)]" />
      <p className="text-[0.9375rem] font-medium">{title}</p>
      {hint && <p className="cl-meta max-w-md">{hint}</p>}
      {action}
    </div>
  );
}

export function ErrorState({
  title,
  message,
  onRetry,
}: {
  title: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="flex flex-col items-start gap-2 rounded-[10px] border border-[var(--border)] bg-[var(--bad-soft)] px-4 py-3 text-sm text-[var(--bad)]"
    >
      <p className="flex items-center gap-1.5 font-medium">
        <span aria-hidden="true">⚠</span>
        <span>{title}</span>
      </p>
      <p className="opacity-90">{message}</p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}

export function LoadingState({ label }: { label: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="cl-surface flex items-center gap-3 px-4 py-5"
    >
      <span
        aria-hidden="true"
        className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-[var(--border)] border-t-[var(--accent)]"
      />
      <p className="cl-meta">{label}</p>
    </div>
  );
}

export function Chip({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full bg-[var(--muted-soft)] px-2 py-0.5 text-xs font-medium text-[var(--muted)] ring-1 ring-inset ring-[var(--border)]",
        className,
      )}
      {...props}
    />
  );
}
