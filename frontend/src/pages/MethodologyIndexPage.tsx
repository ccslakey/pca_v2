import "../styles/MethodologyIndexPage.scss";
import { Link } from "react-router-dom";
import { ARTICLES } from "../methodology/articles";

export function MethodologyIndexPage() {
  return (
    <div className="app">
      <div className="methodology-index">
        <Link to="/" className="methodology-back">
          ← Back to compare
        </Link>

        <div className="methodology-index-header">
          <h1>Methodology</h1>
          <p>
            Documentation for every statistical and algorithmic choice this site
            makes — what the numbers are, where they come from, and where they
            may diverge from other sources.
          </p>
        </div>

        <hr className="methodology-divider" />

        <div className="methodology-grid">
          {ARTICLES.map((article) => (
            <Link
              key={article.slug}
              to={`/methodology/${article.slug}`}
              className="methodology-card"
            >
              <div className="methodology-card-title">{article.title}</div>
              <div className="methodology-card-description">
                {article.description}
              </div>
              <div className="methodology-card-meta">
                {article.readingTimeMin} min read
              </div>
            </Link>
          ))}
        </div>

        <p className="footer-note" style={{ marginTop: 64 }}>
          Data: Baseball Reference · All WAR values are bWAR
        </p>
      </div>
    </div>
  );
}
