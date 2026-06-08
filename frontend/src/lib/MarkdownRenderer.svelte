<script lang="ts">
  export let text = '';

  let lastText = '';
  let lastHtml = '';
  $: if (text !== lastText) {
    lastHtml = renderMarkdown(text);
    lastText = text;
  }

  function escapeHtml(unsafe: string): string {
    return unsafe
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function highlightCode(code: string, lang: string): string {
    const escaped = escapeHtml(code);
    if (!lang) return escaped;

    const lowerLang = lang.toLowerCase();
    let highlighted = escaped;

    // String literals
    highlighted = highlighted.replace(/(&quot;.*?&quot;)/g, '<span class="hl-string">$1</span>');
    highlighted = highlighted.replace(/(&#039;.*?&#039;)/g, '<span class="hl-string">$1</span>');

    // Comments
    if (lowerLang === 'python' || lowerLang === 'bash' || lowerLang === 'sh') {
      highlighted = highlighted.replace(/(#.*)$/gm, '<span class="hl-comment">$1</span>');
    } else {
      highlighted = highlighted.replace(/(\/\/.*)$/gm, '<span class="hl-comment">$1</span>');
    }

    // Keywords
    const keywords = [
      'def', 'class', 'import', 'from', 'as', 'return', 'if', 'else', 'elif',
      'for', 'while', 'in', 'and', 'or', 'not', 'is', 'try', 'except', 'pass',
      'const', 'let', 'var', 'function', 'async', 'await', 'export', 'default',
      'fn', 'pub', 'use', 'impl', 'struct', 'enum', 'let mut', 'match', 'cargo',
      'pip', 'python', 'npm', 'run', 'main', 'type', 'interface', 'true', 'false', 'null'
    ];

    const keywordRegex = new RegExp(`\\b(${keywords.join('|')})\\b`, 'g');
    highlighted = highlighted.replace(keywordRegex, '<span class="hl-keyword">$1</span>');

    // Numbers
    highlighted = highlighted.replace(/\b(\d+)\b/g, '<span class="hl-number">$1</span>');

    return highlighted;
  }

  function renderMarkdown(md: string): string {
    if (!md) return '';

    // Step 1: Extract and highlight code blocks
    const codeBlocks: string[] = [];
    let processed = md.replace(/```(\w*)\n([\s\S]*?)```/g, (match, lang, code) => {
      const highlighted = highlightCode(code.trim(), lang);
      const placeholder = `__CODE_BLOCK_PLACEHOLDER_${codeBlocks.length}__`;
      codeBlocks.push(`<pre class="code-block language-${lang || 'txt'}"><code>${highlighted}</code></pre>`);
      return placeholder;
    });

    // Step 2: Escape remaining HTML
    processed = escapeHtml(processed);

    // Step 3: Parse inline markdown constructs
    // Bold
    processed = processed.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Italic
    processed = processed.replace(/\*(.*?)\*/g, '<em>$1</em>');
    // Inline code
    processed = processed.replace(/`(.*?)`/g, '<code class="inline-code">$1</code>');
    // Headers
    processed = processed.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
    processed = processed.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
    processed = processed.replace(/^# (.*?)$/gm, '<h1>$1</h1>');
    // Bullet lists
    processed = processed.replace(/^\s*[-*]\s+(.*?)$/gm, '<li>$1</li>');
    // Wrap consecutive list items in <ul>
    processed = processed.replace(/(<li>.*?<\/li>\n?)+/g, '<ul>$&</ul>');

    // Line breaks & paragraphs
    processed = processed.replace(/\n\n/g, '</p><p>');
    processed = processed.replace(/\n/g, '<br/>');

    // Step 4: Reinsert code blocks
    codeBlocks.forEach((blockHtml, index) => {
      processed = processed.replace(`__CODE_BLOCK_PLACEHOLDER_${index}__`, blockHtml);
    });

    return `<p>${processed}</p>`;
  }
</script>

<div class="markdown-body">
  {@html lastHtml}
</div>

<style>
  .markdown-body {
    font-size: 14px;
    line-height: 1.6;
    color: var(--text-primary);
  }

  .markdown-body :global(p) {
    margin-bottom: 12px;
  }

  .markdown-body :global(strong) {
    font-weight: 600;
    color: var(--text-primary);
  }

  .markdown-body :global(em) {
    font-style: italic;
  }

  .markdown-body :global(h1),
  .markdown-body :global(h2),
  .markdown-body :global(h3) {
    font-weight: 600;
    margin-top: 18px;
    margin-bottom: 8px;
    color: var(--text-primary);
  }

  .markdown-body :global(h1) { font-size: 1.4em; }
  .markdown-body :global(h2) { font-size: 1.25em; }
  .markdown-body :global(h3) { font-size: 1.1em; }

  .markdown-body :global(ul) {
    margin: 8px 0 16px 20px;
    list-style-type: disc;
  }

  .markdown-body :global(li) {
    margin-bottom: 4px;
  }

  .markdown-body :global(.inline-code) {
    font-family: var(--font-mono);
    font-size: 12px;
    background: var(--bg-input);
    border: 1px solid var(--border-color);
    padding: 2px 6px;
    border-radius: 4px;
    color: var(--color-brand-hover);
  }

  .markdown-body :global(.code-block) {
    font-family: var(--font-mono);
    font-size: 12.5px;
    background: #0b0c10 !important;
    border: 1px solid var(--border-color);
    padding: 14px 18px;
    border-radius: 8px;
    margin: 14px 0;
    overflow-x: auto;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2);
    display: block;
    line-height: 1.5;
  }

  /* Syntax Highlighting Colors */
  .markdown-body :global(.hl-keyword) {
    color: #ff79c6; /* Pink keywords */
    font-weight: 600;
  }

  .markdown-body :global(.hl-string) {
    color: #f1fa8c; /* Yellow strings */
  }

  .markdown-body :global(.hl-comment) {
    color: #6272a4; /* Dracula gray comments */
    font-style: italic;
  }

  .markdown-body :global(.hl-number) {
    color: #bd93f9; /* Purple numbers */
  }
</style>
