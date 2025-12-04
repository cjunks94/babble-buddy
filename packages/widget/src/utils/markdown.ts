/**
 * Simple markdown renderer for chat messages
 * Supports: code blocks, inline code, bold, italic, links, headers
 */
export function renderMarkdown(text: string): string {
  // Preserve code blocks first (before escaping)
  const codeBlocks: string[] = [];
  let processed = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (_match, lang, code) => {
    const index = codeBlocks.length;
    const langLabel = lang ? `<div class="bb-code-lang">${lang}</div>` : '';
    codeBlocks.push(`${langLabel}<pre class="bb-code-block"><code>${escapeHtml(code.trim())}</code></pre>`);
    return `__CODE_BLOCK_${index}__`;
  });

  // Now escape HTML
  let html = escapeHtml(processed);

  // Restore code blocks
  codeBlocks.forEach((block, i) => {
    html = html.replace(`__CODE_BLOCK_${i}__`, block);
  });

  // Headers (## Header)
  html = html.replace(/^### (.+)$/gm, '<strong class="bb-h3">$1</strong>');
  html = html.replace(/^## (.+)$/gm, '<strong class="bb-h2">$1</strong>');
  html = html.replace(/^# (.+)$/gm, '<strong class="bb-h1">$1</strong>');

  // Inline code (`code`)
  html = html.replace(/`([^`]+)`/g, '<code class="bb-inline-code">$1</code>');

  // Bold (**text**)
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

  // Italic (*text* or _text_)
  html = html.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '<em>$1</em>');
  html = html.replace(/(?<!_)_([^_]+)_(?!_)/g, '<em>$1</em>');

  // Links [text](url)
  html = html.replace(
    /\[([^\]]+)\]\(([^)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener">$1</a>'
  );

  // Double line breaks = paragraph
  html = html.replace(/\n\n/g, '</p><p>');

  // Single line breaks
  html = html.replace(/\n/g, '<br>');

  // Wrap in paragraph if we added </p><p>
  if (html.includes('</p><p>')) {
    html = '<p>' + html + '</p>';
  }

  return html;
}

function escapeHtml(text: string): string {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  };
  return text.replace(/[&<>"']/g, (char) => map[char]);
}
