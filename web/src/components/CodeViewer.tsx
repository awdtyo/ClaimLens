import { useMemo, useState } from "react";
import hljs from "highlight.js/lib/common";
import "highlight.js/styles/github.css";
import { cn } from "../lib/utils";

function languageForFile(name: string): string | null {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  if (ext === "py") return "python";
  if (ext === "js" || ext === "jsx") return "javascript";
  if (ext === "ts" || ext === "tsx") return "typescript";
  if (ext === "json") return "json";
  if (ext === "md") return "markdown";
  if (ext === "sh") return "bash";
  if (ext === "yaml" || ext === "yml") return "yaml";
  if (ext === "toml" || ext === "ini" || ext === "cfg") return "ini";
  return null;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

interface CodeViewerProps {
  fileName: string;
  code: string;
  truncated: boolean;
  binary: boolean;
  highlightLine?: number | null;
  anchorPrefix: string;
}

/**
 * Read-only code viewer with syntax highlighting, line numbers, line
 * anchors and a copy button. Display only: never executes code.
 */
export default function CodeViewer({
  fileName,
  code,
  truncated,
  binary,
  highlightLine,
  anchorPrefix,
}: CodeViewerProps) {
  const [copied, setCopied] = useState(false);

  const lines = useMemo(() => {
    if (binary) return [];
    const language = languageForFile(fileName);
    let html: string;
    try {
      html =
        language && hljs.getLanguage(language)
          ? hljs.highlight(code, { language }).value
          : hljs.highlightAuto(code).value;
    } catch {
      html = escapeHtml(code);
    }
    return html.split("\n");
  }, [code, fileName, binary]);

  if (binary) {
    return (
      <p role="note" className="text-sm text-gray-600 dark:text-gray-400">
        This file is binary and cannot be shown. Download the code archive to
        inspect it.
      </p>
    );
  }

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <p className="truncate font-mono text-xs text-gray-600 dark:text-gray-400">
          {fileName}
        </p>
        <button
          type="button"
          onClick={() => void copy()}
          aria-label={`Copy ${fileName} to clipboard`}
          className="rounded-md border border-gray-300 px-2 py-1 text-xs hover:bg-gray-100 dark:border-gray-700 dark:hover:bg-gray-800"
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      {truncated && (
        <p role="note" className="rounded-md bg-amber-50 px-2 py-1 text-xs text-amber-900 ring-1 ring-inset ring-amber-300 dark:bg-amber-950 dark:text-amber-200 dark:ring-amber-800">
          This file is very large; only the first part is shown.
        </p>
      )}
      <pre
        aria-label={`Code for ${fileName}`}
        className="overflow-auto rounded-lg border border-gray-200 bg-white p-0 text-xs dark:border-gray-800 dark:bg-gray-950"
      >
        <code className="block min-w-max">
          {lines.map((lineHtml, i) => {
            const lineNo = i + 1;
            const id = `${anchorPrefix}-L${lineNo}`;
            const active = highlightLine === lineNo;
            return (
              <span
                key={lineNo}
                id={id}
                className={cn(
                  "flex scroll-mt-24 border-l-2 border-transparent px-0 hover:bg-gray-50 dark:hover:bg-gray-800/50",
                  active && "border-amber-500 bg-amber-50 dark:bg-amber-950/60",
                )}
              >
                <a
                  href={`#${id}`}
                  aria-label={`Line ${lineNo}`}
                  className={cn(
                    "w-12 shrink-0 select-none px-2 py-px text-right font-mono text-gray-400 hover:text-gray-700 hover:underline dark:text-gray-600 dark:hover:text-gray-300",
                    active && "font-bold text-amber-700 dark:text-amber-300",
                  )}
                >
                  {lineNo}
                </a>
                <span
                  className="flex-1 whitespace-pre px-2 py-px font-mono"
                  dangerouslySetInnerHTML={{
                    __html: lineHtml.length > 0 ? lineHtml : " ",
                  }}
                />
              </span>
            );
          })}
        </code>
      </pre>
    </div>
  );
}
