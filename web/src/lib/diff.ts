/** Minimal line-based diff for the Code tab (no verdict logic). */

export interface DiffRow {
  type: "same" | "del" | "add";
  oldLineNo: number | null;
  newLineNo: number | null;
  text: string;
}

/**
 * Diff two texts line by line. Uses LCS for files under 500 lines and a
 * prefix/suffix fallback above that so large files stay fast.
 */
export function diffLines(oldText: string, newText: string): DiffRow[] {
  const a = oldText.split("\n");
  const b = newText.split("\n");
  if (a.length > 500 || b.length > 500) {
    return diffPrefixSuffix(a, b);
  }
  const n = a.length;
  const m = b.length;
  const dp: number[][] = Array.from({ length: n + 1 }, () =>
    new Array<number>(m + 1).fill(0),
  );
  for (let i = n - 1; i >= 0; i -= 1) {
    for (let j = m - 1; j >= 0; j -= 1) {
      dp[i][j] =
        a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  const rows: DiffRow[] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      rows.push({ type: "same", oldLineNo: i + 1, newLineNo: j + 1, text: a[i] });
      i += 1;
      j += 1;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      rows.push({ type: "del", oldLineNo: i + 1, newLineNo: null, text: a[i] });
      i += 1;
    } else {
      rows.push({ type: "add", oldLineNo: null, newLineNo: j + 1, text: b[j] });
      j += 1;
    }
  }
  while (i < n) {
    rows.push({ type: "del", oldLineNo: i + 1, newLineNo: null, text: a[i] });
    i += 1;
  }
  while (j < m) {
    rows.push({ type: "add", oldLineNo: null, newLineNo: j + 1, text: b[j] });
    j += 1;
  }
  return rows;
}

function diffPrefixSuffix(a: string[], b: string[]): DiffRow[] {
  let prefix = 0;
  while (prefix < a.length && prefix < b.length && a[prefix] === b[prefix]) {
    prefix += 1;
  }
  let suffix = 0;
  while (
    suffix < a.length - prefix &&
    suffix < b.length - prefix &&
    a[a.length - 1 - suffix] === b[b.length - 1 - suffix]
  ) {
    suffix += 1;
  }
  const rows: DiffRow[] = [];
  for (let k = 0; k < prefix; k += 1) {
    rows.push({ type: "same", oldLineNo: k + 1, newLineNo: k + 1, text: a[k] });
  }
  for (let k = prefix; k < a.length - suffix; k += 1) {
    rows.push({ type: "del", oldLineNo: k + 1, newLineNo: null, text: a[k] });
  }
  for (let k = prefix; k < b.length - suffix; k += 1) {
    rows.push({ type: "add", oldLineNo: null, newLineNo: k + 1, text: b[k] });
  }
  for (let k = 0; k < suffix; k += 1) {
    const ai = a.length - suffix + k;
    const bi = b.length - suffix + k;
    rows.push({ type: "same", oldLineNo: ai + 1, newLineNo: bi + 1, text: a[ai] });
  }
  return rows;
}
