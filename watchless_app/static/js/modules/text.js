export function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function cleanSummaryText(markdown = "") {
  return String(markdown || "")
    .replace(/^Source:\s+\S+\s*/gim, "")
    .replace(/^Model:\s+.+\s*/gim, "")
    .trim();
}

export function markdownToHtml(markdown) {
  const safeMarkdown = escapeHtml(markdown || "");
  if (window.marked) return window.marked.parse(safeMarkdown);
  return basicMarkdownToHtml(safeMarkdown);
}

export function chatMarkdownToHtml(markdown) {
  const safeMarkdown = escapeHtml(markdown || "");
  if (window.marked) return window.marked.parse(safeMarkdown);
  return basicMarkdownToHtml(safeMarkdown);
}

function basicMarkdownToHtml(safeMarkdown) {
  const blocks = [];
  let listItems = [];
  let orderedListItems = [];
  let paragraphLines = [];
  let codeFenceLines = [];
  let inCodeFence = false;

  function flushParagraph() {
    if (!paragraphLines.length) return;
    blocks.push(`<p>${renderInlineMarkdown(paragraphLines.join(" "))}</p>`);
    paragraphLines = [];
  }

  function flushList() {
    if (!listItems.length) return;
    blocks.push(`<ul>${listItems.map((item) => `<li>${item}</li>`).join("")}</ul>`);
    listItems = [];
  }

  function flushOrderedList() {
    if (!orderedListItems.length) return;
    blocks.push(`<ol>${orderedListItems.map((item) => `<li>${item}</li>`).join("")}</ol>`);
    orderedListItems = [];
  }

  function flushCodeFence() {
    if (!codeFenceLines.length) return;
    blocks.push(`<pre><code>${codeFenceLines.join("\n")}</code></pre>`);
    codeFenceLines = [];
  }

  function flushAll() {
    flushParagraph();
    flushList();
    flushOrderedList();
  }

  for (const rawLine of safeMarkdown.split(/\r?\n/)) {
    const line = rawLine.trimEnd();
    const trimmed = line.trim();
    if (trimmed.startsWith("```")) {
      if (inCodeFence) {
        flushCodeFence();
        inCodeFence = false;
      } else {
        flushAll();
        inCodeFence = true;
      }
      continue;
    }
    if (inCodeFence) {
      codeFenceLines.push(line);
      continue;
    }
    if (!trimmed) {
      flushAll();
      continue;
    }
    const heading = trimmed.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      flushAll();
      blocks.push(`<h${heading[1].length}>${renderInlineMarkdown(heading[2])}</h${heading[1].length}>`);
      continue;
    }
    const blockquote = trimmed.match(/^>\s+(.+)$/);
    if (blockquote) {
      flushAll();
      blocks.push(`<blockquote><p>${renderInlineMarkdown(blockquote[1])}</p></blockquote>`);
      continue;
    }
    const bullet = trimmed.match(/^[-*]\s+(.+)$/);
    if (bullet) {
      flushParagraph();
      flushOrderedList();
      listItems.push(renderInlineMarkdown(bullet[1]));
      continue;
    }
    const orderedBullet = trimmed.match(/^\d+\.\s+(.+)$/);
    if (orderedBullet) {
      flushParagraph();
      flushList();
      orderedListItems.push(renderInlineMarkdown(orderedBullet[1]));
      continue;
    }
    paragraphLines.push(trimmed);
  }
  flushAll();
  if (inCodeFence) flushCodeFence();
  return blocks.join("");
}

function renderInlineMarkdown(text) {
  return String(text || "")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/__([^_]+)__/g, "<strong>$1</strong>")
    .replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, "<em>$1</em>")
    .replace(/(?<!_)_([^_]+)_(?!_)/g, "<em>$1</em>");
}
