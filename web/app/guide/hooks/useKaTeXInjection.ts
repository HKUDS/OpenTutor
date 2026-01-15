/**
 * Hook for injecting KaTeX support into HTML content
 */
export function useKaTeXInjection() {
  /**
   * Inject KaTeX CSS and JS into HTML if not already present
   */
  const injectKaTeX = (html: string): string => {
    // Check if KaTeX is already included (case-insensitive)
    const htmlLower = html.toLowerCase();
    const hasKaTeX =
      htmlLower.includes("katex.min.css") ||
      htmlLower.includes("katex.min.js") ||
      htmlLower.includes("katex@") ||
      htmlLower.includes("cdn.jsdelivr.net/npm/katex") ||
      htmlLower.includes("unpkg.com/katex");

    if (hasKaTeX) {
      console.log("KaTeX already included in HTML, skipping injection");
      return html;
    }

    // KaTeX CDN links (using version 0.16.9 for compatibility)
    const katexCSS =
      '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css" integrity="sha384-n8MVd4RsNIU0tAv4ct0nTaAbDJwPJzDEaqSD1odI+WdtXRGWt2kTvGFasHpSy3SV" crossorigin="anonymous">';
    const katexJS =
      '<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js" integrity="sha384-XjKyOOlGwcjNTAIQHIpgOno0Hl1YQqzUOEleOLALmuqehneUG+vnGctmUb0ZY0l8" crossorigin="anonymous"></script>';
    const katexAutoRender =
      '<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js" integrity="sha384-+VBxd3r6XgURycqtZ117n7w6ODWgRrA7TlVzRsFtwW3ZxUo8h4w20Z5J3d3xjfcw" crossorigin="anonymous" onload="renderMathInElement(document.body);"></script>';

    const katexInjection = `  ${katexCSS}\n  ${katexJS}\n  ${katexAutoRender}`;

    // Try to inject into </head> section (most common case)
    if (html.includes("</head>")) {
      console.log("Injecting KaTeX before </head> tag");
      return html.replace("</head>", `${katexInjection}\n</head>`);
    }

    // If no </head> tag, try to inject after <head> tag
    if (html.includes("<head>")) {
      console.log("Injecting KaTeX after <head> tag");
      // Use regex to handle <head> with attributes
      return html.replace(/<head([^>]*)>/i, `<head$1>\n${katexInjection}`);
    }

    // If HTML structure exists but no <head>, add it
    if (html.includes("<html")) {
      console.log("Adding <head> section with KaTeX");
      return html.replace(
        /(<html[^>]*>)/i,
        `$1\n<head>\n  <meta charset="UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n${katexInjection}\n</head>`,
      );
    }

    // If no HTML structure, wrap it with full HTML document
    console.log("Wrapping content with full HTML document including KaTeX");
    return `<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
${katexInjection}
</head>
<body>
${html}
</body>
</html>`;
  };

  return { injectKaTeX };
}
