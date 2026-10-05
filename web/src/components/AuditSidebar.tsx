import {
  Beaker,
  FileText,
  FlaskConical,
  GitBranch,
  Layers,
  ListChecks,
  Microscope,
  ScrollText,
  Settings,
  Table2,
  type LucideIcon,
} from "lucide-react";
import { cn } from "../lib/utils";

export type AuditSection =
  | "overview"
  | "claims"
  | "evidence"
  | "experiments"
  | "logs"
  | "paper"
  | "methods"
  | "datasets"
  | "results"
  | "run-history"
  | "environment"
  | "parameters"
  | "provenance";

interface NavItem {
  id: AuditSection;
  label: string;
  icon: LucideIcon;
}

const AUDIT_NAV: NavItem[] = [
  { id: "overview",     label: "Overview",     icon: Layers },
  { id: "claims",       label: "Claims",       icon: ListChecks },
  { id: "evidence",     label: "Evidence",     icon: Microscope },
  { id: "experiments",  label: "Experiments",  icon: FlaskConical },
  { id: "logs",         label: "Logs",         icon: ScrollText },
];

const PAPER_NAV: NavItem[] = [
  { id: "paper",    label: "Paper",    icon: FileText },
  { id: "methods",  label: "Methods",  icon: Beaker },
  { id: "datasets", label: "Datasets", icon: Table2 },
  { id: "results",  label: "Results",  icon: Table2 },
];

const EXPERIMENT_NAV: NavItem[] = [
  { id: "run-history",  label: "Run history",  icon: GitBranch },
  { id: "environment",  label: "Environment",  icon: Settings },
  { id: "parameters",   label: "Parameters",   icon: Settings },
  { id: "provenance",   label: "Provenance",   icon: GitBranch },
];

function NavList({
  items,
  active,
  onSelect,
}: {
  items: NavItem[];
  active: AuditSection;
  onSelect: (s: AuditSection) => void;
}) {
  return (
    <ul className="flex flex-col gap-0.5">
      {items.map((item) => {
        const Icon = item.icon;
        const selected = active === item.id;
        return (
          <li key={item.id}>
            <button
              type="button"
              onClick={() => onSelect(item.id)}
              aria-current={selected ? "true" : undefined}
              className="audit-nav-item"
            >
              <Icon size={14} aria-hidden="true" className="shrink-0" />
              <span>{item.label}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

/**
 * 220px audit navigation sidebar.
 * Groups: Audit · Paper · Experiment
 * On mobile it renders inside a full-height left drawer controlled by the parent.
 */
export default function AuditSidebar({
  active,
  status,
  onSelect,
}: {
  active: AuditSection;
  status: string;
  onSelect: (s: AuditSection) => void;
}) {
  const statusDone = status === "done";

  return (
    <nav aria-label="Audit sections" className="flex flex-col gap-4 text-[13px]">

      {/* ── AUDIT group ── */}
      <section aria-labelledby="audit-nav-audit" className="flex flex-col gap-1.5">
        <h2
          id="audit-nav-audit"
          className="cl-meta px-3 font-semibold uppercase tracking-[0.1em]"
        >
          Audit
        </h2>
        <NavList items={AUDIT_NAV} active={active} onSelect={onSelect} />
      </section>

      <hr className="border-[var(--border)]" />

      {/* ── PAPER group ── */}
      <section aria-labelledby="audit-nav-paper" className="flex flex-col gap-1.5">
        <h2
          id="audit-nav-paper"
          className="cl-meta px-3 font-semibold uppercase tracking-[0.1em]"
        >
          Paper
        </h2>
        <NavList items={PAPER_NAV} active={active} onSelect={onSelect} />
      </section>

      <hr className="border-[var(--border)]" />

      {/* ── EXPERIMENT group ── */}
      <section aria-labelledby="audit-nav-experiment" className="flex flex-col gap-1.5">
        <h2
          id="audit-nav-experiment"
          className="cl-meta px-3 font-semibold uppercase tracking-[0.1em]"
        >
          Experiment
        </h2>
        <NavList items={EXPERIMENT_NAV} active={active} onSelect={onSelect} />
      </section>

      <hr className="border-[var(--border)]" />

      {/* ── Status ── */}
      <section aria-labelledby="audit-nav-status" className="px-3">
        <h2
          id="audit-nav-status"
          className="cl-meta font-semibold uppercase tracking-[0.1em]"
        >
          Audit status
        </h2>
        <p className="mt-1.5 flex items-center gap-1.5 text-[13px]">
          <span
            aria-hidden="true"
            className={cn(
              "inline-block h-2 w-2 rounded-full",
              statusDone
                ? "bg-[var(--ok)]"
                : status === "failed"
                ? "bg-[var(--bad)]"
                : "bg-[var(--warn)]",
            )}
          />
          {statusDone
            ? "Complete"
            : status === "failed"
            ? "Failed"
            : status === "cancelled"
            ? "Cancelled"
            : status}
        </p>
      </section>
    </nav>
  );
}
