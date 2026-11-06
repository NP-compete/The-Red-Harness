/**
 * Re-indent nested list items so CommonMark sees the nesting.
 *
 * Models indent sub-bullets by one space often enough that it is not
 * worth trying to prompt away. CommonMark nests a child only when it
 * reaches the parent's content column — 2 for `- `, 3 for `1. ` — so
 * one space makes the child a *sibling*, and the answer renders as a
 * flat list with the structure gone.
 *
 * This maps each distinct source indent to a level and re-emits the
 * line at that level's real content column, so one space, two spaces
 * or four all produce the same tree.
 */

const FENCE = /^\s*(```+|~~~+)/;
const ITEM = /^([ \t]*)([-*+]|\d{1,9}[.)])([ \t]+)(.*)$/;

type Level = { src: number; contentCol: number };

export function normalizeListIndent(markdown: string): string {
  const out: string[] = [];
  const stack: Level[] = [];
  let fence: string | null = null;

  for (const line of markdown.split("\n")) {
    const fenced = FENCE.exec(line);
    if (fenced) {
      const marker = fenced[1].slice(0, 3);
      if (fence && line.trimStart().startsWith(fence)) fence = null;
      else if (!fence) fence = marker;
      out.push(line);
      continue;
    }
    if (fence) {
      out.push(line);
      continue;
    }

    const item = ITEM.exec(line);
    if (!item) {
      // A non-blank line in column 0 ends any list above it.
      if (line.trim() !== "" && !/^[ \t]/.test(line)) stack.length = 0;
      out.push(line);
      continue;
    }

    const [, lead, marker, , text] = item;
    const src = lead.replace(/\t/g, "    ").length;

    while (stack.length && src < stack[stack.length - 1].src) stack.pop();

    let indent: number;
    if (!stack.length) {
      indent = 0;
    } else if (src > stack[stack.length - 1].src) {
      indent = stack[stack.length - 1].contentCol;
    } else {
      // Same level: drop the sibling and re-derive from its parent.
      stack.pop();
      indent = stack.length ? stack[stack.length - 1].contentCol : 0;
    }

    stack.push({ src, contentCol: indent + marker.length + 1 });
    out.push(" ".repeat(indent) + marker + " " + text);
  }

  return out.join("\n");
}
