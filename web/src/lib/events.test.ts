import { describe, expect, it } from "vitest";
import { eventKey, mergeEvents, parseEventLine } from "./events";

describe("mergeEvents", () => {
  const a = { ts: "t1", stage: "ingest", status: "started", message: "go" };
  const b = { ts: "t2", stage: "ingest", status: "progress", message: "half" };

  it("does not duplicate lines replayed after a reconnect", () => {
    const first = mergeEvents([], [a, b]);
    // Reconnect replays everything from the start, plus one new line.
    const c = { ts: "t3", stage: "ingest", status: "done", message: "ok" };
    const second = mergeEvents(first, [a, b, c]);
    expect(second).toHaveLength(3);
    expect(second.map(eventKey)).toEqual([eventKey(a), eventKey(b), eventKey(c)]);
  });

  it("keeps distinct events with the same stage", () => {
    const other = { ...a, message: "different" };
    expect(mergeEvents([a], [other])).toHaveLength(2);
  });
});

describe("parseEventLine", () => {
  it("parses SSE data lines and ignores heartbeats", () => {
    expect(parseEventLine("")).toBeNull();
    expect(parseEventLine("data: [DONE]")).toBeNull();
    expect(
      parseEventLine('data: {"stage": "plan", "status": "done"}'),
    ).toMatchObject({ stage: "plan", status: "done" });
  });

  it("rejects malformed payloads", () => {
    expect(parseEventLine("data: not-json")).toBeNull();
    expect(parseEventLine('data: {"nope": 1}')).toBeNull();
  });
});
