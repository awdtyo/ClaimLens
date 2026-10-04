import { useState } from "react";
import type { ParsedPaper, Table, TableMismatch } from "../api/models";
import { cn } from "../lib/utils";
import { Chip, EmptyState } from "./ui";

function mismatchKey(m: Pick<TableMismatch, "row" | "col">): string {
  return `${m.row}:${m.col}`;
}

/**
 * Compare the two reads (text layer vs vision) of one table cell by cell.
 * Cells that differ are highlighted; hovering or focusing a highlighted
 * cell shows both values. Mismatches are flagged, never resolved: the
 * view shows both readings side by side.
 */
function TableCompare({
  tableId,
  textTable,
  visionTable,
  mismatches,
}: {
  tableId: string;
  textTable: Table | undefined;
  visionTable: Table | undefined;
  mismatches: TableMismatch[];
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const byKey = new Map(mismatches.map((m) => [mismatchKey(m), m]));
  const rowCount = Math.max(
    textTable?.rows.length ?? 0,
    visionTable?.rows.length ?? 0,
  );
  const colCount = Math.max(
    ...[textTable, visionTable].flatMap((t) => (t?.rows ?? []).map((r) => r.length)),
    0,
  );
  const caption = textTable?.caption || visionTable?.caption || "";
  const page = textTable?.page ?? visionTable?.page ?? null;

  if (rowCount === 0) return null;

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-800">
      <div className="flex flex-wrap items-center gap-2 border-b border-gray-200 px-4 py-2 dark:border-gray-800">
        <h3 className="font-medium">
          Table {tableId}
          {page != null && <span className="font-normal text-gray-500"> · page {page}</span>}
        </h3>
        {mismatches.length > 0 ? (
          <Chip className="bg-amber-100 text-amber-800 ring-amber-600/20 dark:bg-amber-900/40 dark:text-amber-200">
            {mismatches.length} {mismatches.length === 1 ? "mismatch" : "mismatches"} flagged
          </Chip>
        ) : (
          <Chip>text and vision agree</Chip>
        )}
      </div>
      {caption && (
        <p className="px-4 pt-2 text-sm text-gray-600 dark:text-gray-400">{caption}</p>
      )}
      <div className="overflow-x-auto p-4">
        <table className="w-full border-collapse text-sm">
          <caption className="sr-only">
            Table {tableId}: text-layer reading with vision differences flagged
          </caption>
          <tbody>
            {Array.from({ length: rowCount }, (_, r) => (
              <tr key={r}>
                {Array.from({ length: colCount }, (_, c) => {
                  const key = `${r}:${c}`;
                  const mismatch = byKey.get(key);
                  const textValue = textTable?.rows[r]?.[c] ?? "";
                  const isHeader = r === 0;
                  const Cell = isHeader ? "th" : "td";
                  return (
                    <Cell
                      key={c}
                      scope={isHeader ? "col" : undefined}
                      className={cn(
                        "border border-gray-300 px-2 py-1 text-left dark:border-gray-700",
                        isHeader && "bg-gray-50 font-medium dark:bg-gray-800",
                        mismatch &&
                          "cursor-pointer bg-amber-100 underline decoration-amber-600 decoration-dotted underline-offset-2 dark:bg-amber-950",
                      )}
                      tabIndex={mismatch ? 0 : undefined}
                      aria-label={
                        mismatch
                          ? `Row ${r + 1}, column ${c + 1}: text reads ${mismatch.text_value}, vision reads ${mismatch.vision_value}`
                          : undefined
                      }
                      title={
                        mismatch
                          ? `Text: ${mismatch.text_value} · Vision: ${mismatch.vision_value}`
                          : undefined
                      }
                      onClick={() => mismatch && setSelected(selected === key ? null : key)}
                      onKeyDown={(e) => {
                        if (mismatch && (e.key === "Enter" || e.key === " ")) {
                          e.preventDefault();
                          setSelected(selected === key ? null : key);
                        }
                      }}
                    >
                      {textValue}
                      {mismatch && (
                        <span className="sr-only">
                          {" "}
                          (differs from vision read)
                        </span>
                      )}
                    </Cell>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {mismatches.length > 0 && (
        <ul aria-label={`Flagged cells in table ${tableId}`} className="flex flex-col gap-1 border-t border-gray-200 px-4 py-3 text-sm dark:border-gray-800">
          {mismatches.map((m) => {
            const key = mismatchKey(m);
            const open = selected === key;
            return (
              <li key={key}>
                <button
                  type="button"
                  onClick={() => setSelected(open ? null : key)}
                  aria-expanded={open}
                  className="text-left text-amber-800 underline decoration-dotted underline-offset-2 dark:text-amber-200"
                >
                  Row {m.row + 1}, column {m.col + 1}: text “{m.text_value}” vs
                  vision “{m.vision_value}”
                </button>
                {open && (
                  <dl className="mt-1 grid grid-cols-2 gap-2 rounded-md bg-gray-50 p-2 text-xs dark:bg-gray-800">
                    <div>
                      <dt className="text-gray-500 dark:text-gray-400">Text layer</dt>
                      <dd className="font-mono">{m.text_value}</dd>
                    </div>
                    <div>
                      <dt className="text-gray-500 dark:text-gray-400">Vision read</dt>
                      <dd className="font-mono">{m.vision_value}</dd>
                    </div>
                  </dl>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

/**
 * Table cross-check view: every table read from the PDF text layer and
 * from page images, with differences highlighted. A key differentiator
 * of ClaimLens, so the flagged state is unmissable.
 */
export default function TablesView({ parsed }: { parsed: ParsedPaper }) {
  const ids = [...new Set(parsed.tables.map((t) => t.id))];
  if (ids.length === 0) {
    return (
      <EmptyState
        title="No tables were extracted from this paper."
        hint="Tables appear here once the ingest stage finishes."
      />
    );
  }
  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-gray-600 dark:text-gray-400">
        Each table is read twice: from the PDF text layer and from page
        images. Highlighted cells differ between the two reads. ClaimLens
        flags these mismatches instead of silently picking one value.
      </p>
      {ids.map((id) => (
        <TableCompare
          key={id}
          tableId={id}
          textTable={parsed.tables.find((t) => t.id === id && t.source === "text")}
          visionTable={parsed.tables.find((t) => t.id === id && t.source === "vision")}
          mismatches={parsed.table_mismatches.filter((m) => m.table_id === id)}
        />
      ))}
    </div>
  );
}
