import { describe, it, expect } from "vitest";
import { unified } from "unified";
import remarkParse from "remark-parse";
import remarkGfm from "remark-gfm";

import { normalizeListIndent } from "../normalize-list-indent.js";

/**
 * Nesting is asserted through the parser the UI actually renders
 * with, not by comparing strings.
 *
 * The bug was invisible in the markdown: a sub-bullet indented one
 * space looks nested to a person and is a sibling to CommonMark. A
 * test that checked the output text would have passed on an output
 * that still rendered flat, so these assert the depth remark gives
 * each item — which is the thing that was wrong on screen.
 */
function depths(markdown: string): number[] {
  const tree = unified().use(remarkParse).use(remarkGfm).parse(markdown);
  const out: number[] = [];
  (function walk(node: { type: string; children?: unknown[] }, depth = 0) {
    if (node.type === "listItem") out.push(depth);
    for (const child of (node.children ?? []) as typeof node[]) {
      walk(child, node.type === "listItem" ? depth + 1 : depth);
    }
  })(tree as never);
  return out;
}

describe("normalizeListIndent", () => {
  it("nests a one-space child that CommonMark reads as a sibling", () => {
    const md = "- Parent\n - Child A\n - Child B";
    expect(depths(md)).toEqual([0, 0, 0]);
    expect(depths(normalizeListIndent(md))).toEqual([0, 1, 1]);
  });

  it("reaches the wider content column of an ordered parent", () => {
    // `1. ` puts content at column 3, so two spaces would not nest
    // either — the indent has to follow the marker's width.
    const md = "1. Parent\n - Child";
    expect(depths(md)).toEqual([0, 0]);
    expect(depths(normalizeListIndent(md))).toEqual([0, 1]);
  });

  it("leaves correctly indented markdown alone", () => {
    const md = "- Parent\n  - Child\n- Sibling";
    expect(depths(normalizeListIndent(md))).toEqual(depths(md));
    expect(normalizeListIndent(md)).toBe(md);
  });

  it("keeps going for levels below the first", () => {
    const md = "- A\n - B\n  - C";
    expect(depths(normalizeListIndent(md))).toEqual([0, 1, 2]);
  });

  it("returns to the outer level when the indent does", () => {
    const md = "- A\n - B\n- C";
    expect(depths(normalizeListIndent(md))).toEqual([0, 1, 0]);
  });

  it("does not touch a dash inside a fenced block", () => {
    const md = "- A\n\n```sh\n - not a list item\n```\n\n- B";
    expect(normalizeListIndent(md)).toContain(" - not a list item");
    expect(depths(normalizeListIndent(md))).toEqual([0, 0]);
  });

  it("treats a tab as four columns rather than one", () => {
    expect(depths(normalizeListIndent("- A\n\t- B"))).toEqual([0, 1]);
  });

  it("starts a fresh list after a paragraph in column zero", () => {
    const md = "- A\n - B\n\nSome prose.\n\n- C\n - D";
    expect(depths(normalizeListIndent(md))).toEqual([0, 1, 0, 1]);
  });

  it("passes through text with no lists", () => {
    const md = "# Title\n\nA paragraph, and `- not a list` inline.";
    expect(normalizeListIndent(md)).toBe(md);
  });
});
