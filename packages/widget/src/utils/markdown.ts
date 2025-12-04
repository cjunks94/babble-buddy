/**
 * Simple markdown renderer for chat messages
 * Supports: code blocks, inline code, bold, italic, links
 */
export function renderMarkdown(text: string): string {
  let html = escapeHtml(text);

  // Code blocks (```language\ncode```)
  html = html.replace(
    /```(\w*)\n?([\s\S]*?)```/g,
    (_match, lang, code) => {
      const langClass = lang ? ` data-lang="${lang}"` : '';
      return `<pre class="bb-code-block"${langClass}><code>${code.trim()}</code></pre>`;
    }
  );

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

  // Line breaks
  html = html.replace(/\n/g, '<br>');

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
