import "../styles/MethodologyArticlePage.scss";
import { useMemo } from "react";
import { Link, useParams, Navigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { ARTICLES, getArticle } from "../methodology/articles";

// All markdown imported at build time — live in the methodology chunk.
const RAW_MD = import.meta.glob("../methodology/*.md", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

function getMarkdown(slug: string): string | null {
  const key = `../methodology/${slug}.md`;
  return RAW_MD[key] ?? null;
}

function slugify(text: string): string {
  return text
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

// Extract h2 headings from markdown for the sidebar TOC.
function extractHeadings(md: string): { id: string; text: string }[] {
  return Array.from(md.matchAll(/^## (.+)$/gm)).map((m) => ({
    text: m[1].trim(),
    id: slugify(m[1]),
  }));
}

// Custom renderers: add id to h2 so TOC anchor links work.
const MD_COMPONENTS: Components = {
  h2({ children }) {
    const text =
      typeof children === "string" ? children : String(children ?? "");
    return <h2 id={slugify(text)}>{children}</h2>;
  },
};

export function MethodologyArticlePage() {
  const { slug = "" } = useParams<{ slug: string }>();
  const article = getArticle(slug);
  const markdown = getMarkdown(slug);

  if (!article || !markdown) return <Navigate to="/methodology" replace />;

  const idx = ARTICLES.indexOf(article);
  const prev = ARTICLES[idx - 1];
  const next = ARTICLES[idx + 1];

  const headings = useMemo(() => extractHeadings(markdown), [markdown]);

  return (
    <div className="app">
      <div className="methodology-article-wrap">
        <article className="methodology-article">
          <Link to="/methodology" className="methodology-article-back">
            ← Methodology
          </Link>

          <div className="methodology-body">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={MD_COMPONENTS}
            >
              {markdown}
            </ReactMarkdown>
          </div>

          <nav className="methodology-article-nav">
            {prev ? (
              <Link
                to={`/methodology/${prev.slug}`}
                className="methodology-nav-link prev"
              >
                <span className="nav-label">← Previous</span>
                <span className="nav-title">{prev.title}</span>
              </Link>
            ) : (
              <span />
            )}
            {next && (
              <Link
                to={`/methodology/${next.slug}`}
                className="methodology-nav-link next"
              >
                <span className="nav-label">Next →</span>
                <span className="nav-title">{next.title}</span>
              </Link>
            )}
          </nav>
        </article>

        {headings.length > 0 && (
          <aside className="methodology-toc">
            <div className="methodology-toc-title">On this page</div>
            <ul className="methodology-toc-list">
              {headings.map((h) => (
                <li key={h.id} className="methodology-toc-item">
                  <a href={`#${h.id}`}>{h.text}</a>
                </li>
              ))}
            </ul>
          </aside>
        )}
      </div>
    </div>
  );
}
