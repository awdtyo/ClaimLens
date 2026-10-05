import {
  Beaker,
  FileText,
  FlaskConical,
  Layers,
  ListChecks,
  Microscope,
  ScrollText,
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
  | "results";

interface NavItem {
  id: AuditSection;
  label: string;
  icon: LucideIcon;
}

const AUDIT_NAV: NavItem[] = [
  { id: "overview", label: "Overview", icon: Layers },
  { id: "claims", label: "Claims", icon: ListChecks },
  { id: "evidence", label: "Evidence", icon: Microscope },
  { id: "experiments", label: "Experiments", icon: FlaskConical },
  { id: "logs", label: "Logs", icon: ScrollText },
];

const PAPER_NAV: NavItem[] = [
  { id: "paper", label: "Paper", icon: FileText },
  { id: "methods", label: "Methods", icon: Beaker },
  { id: "datasets", label: "Datasets", icon: Table2 },
  { id: "results", label: "Results", icon: Table2 },
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
              <Icon size={16} aria-hidden="true" className="shrink-0" />
              <span>{item.label}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

/**
 * 220px audit navigation sidebar. On mobile it renders inside a
 * full-height left drawer controlled by the parent.
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
  return (
    <nav aria-label="Audit sections" className="flex flex-col gap-4 text-[13px]">
      <section aria-labelledby="audit-nav-audit" className="flex flex-col gap-1.5">
        <h2 id="audit-nav-audit" className="cl-meta px-3 font-semibold uppercase tracking-[0.1em]">
          Audit
        </h2>
        <NavList items={AUDIT_NAV} active={active} onSelect={onSelect} />
      </section>
      <hr className="border-[var(--border)]" />
      <section aria-labelledby="audit-nav-paper" className="flex flex-col gap-1.5">
        <h2 id="audit-nav-paper" className="cl-meta px-3 font-semibold uppercase tracking-[0.1em]">
          Paper
        </h2>
        <NavList items={PAPER_NAV} active={active} onSelect={onSelect} />
      </section>
      <hr className="border-[var(--border)]" />
      <section aria-labelledby="audit-nav-status" className="px-3">
        <h2 id="audit-nav-status" className="cl-meta font-semibold uppercase tracking-[0.1em]">
          Audit status
        </h2>
        <p className="mt-1.5 flex items-center gap-1.5 text-[13px]">
          <span
            aria-hidden="true"
            className={cn(
              "inline-block h-2 w-2 rounded-full",
              status === "done" ? "bg-[var(--ok)]" : "bg-[var(--warn)]",
            )}
          />
          {status === "done" ? "Complete" : status}
        </p>
      </section>
    </nav>
  );
}
