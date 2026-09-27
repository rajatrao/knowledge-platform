import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";

export function Investigation({ user, setUser }) {
  const { slug } = useParams();
  const [page, setPage] = useState(null);
  const [error, setError] = useState("");
  const [showEvidence, setShowEvidence] = useState(false);

  useEffect(() => {
    setPage(null);
    api(`/v1/investigations/${slug}`)
      .then(setPage)
      .catch((err) => setError(err.message));
  }, [slug]);

  const navigate = useNavigate();
  return (
    <div className="investigation-screen">
      <header className="topbar">
        <Link to="/">Back to chat</Link>
        <span>{user.username}</span>
        <button
          type="button"
          className="text"
          onClick={async () => {
            await api("/v1/auth/logout", { method: "POST" });
            setUser(null);
            navigate("/");
          }}
        >
          Log out
        </button>
      </header>
      {error ? <p className="form-error">{error}</p> : null}
      {!page && !error ? <p className="muted">Loading the investigation…</p> : null}
      {page ? <InvestigationBody page={page} showEvidence={showEvidence} setShowEvidence={setShowEvidence} /> : null}
    </div>
  );
}

function InvestigationBody({ page, showEvidence, setShowEvidence }) {
  return (
    <article className="investigation">
      <p className="eyebrow">Investigation</p>
      <h1>{page.name}</h1>
      <div className="headline">
        <div>
          <span>Customer complaints this period</span>
          <strong>{page.current_period_count}</strong>
        </div>
        <div>
          <span>Change vs previous period</span>
          <strong>{page.trend_percent}%</strong>
        </div>
      </div>
      <section>
        <h2>Why it is happening</h2>
        <ul className="causes">
          {page.causes.map((cause) => (
            <li key={cause.cause}>
              <div className="cause-label">
                <span>{cause.label}</span>
                <span>{cause.count} · {Math.round(cause.share * 1000) / 10}%</span>
              </div>
              <div className="bar"><span style={{ width: `${cause.share * 100}%` }} /></div>
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h2>Customer voice</h2>
        {page.quotes.map((quote) => (
          <blockquote key={quote.id}>
            <p>{quote.quote}</p>
            <footer>{quote.id} · {quote.region} · {quote.date}</footer>
          </blockquote>
        ))}
      </section>
      <section>
        <h2>Evidence</h2>
        <div className="metric-grid">
          <div className="metric"><span>Support conversations</span><strong>{page.evidence_counts.support_conversations}</strong></div>
          <div className="metric"><span>Operations tickets</span><strong>{page.evidence_counts.operations_tickets}</strong></div>
          <div className="metric"><span>Related incidents</span><strong>{page.evidence_counts.related_incidents}</strong></div>
        </div>
        <button type="button" onClick={() => setShowEvidence((value) => !value)}>
          {showEvidence ? "Hide evidence" : "View evidence"}
        </button>
        {showEvidence ? <EvidenceLists page={page} /> : null}
      </section>
      <section>
        <h2>Recommended actions</h2>
        <ol className="actions">
          {page.recommended_actions.map((action) => (
            <li key={action.document_id}>
              <p>{action.text}</p>
              <small>{action.document_id}</small>
            </li>
          ))}
        </ol>
      </section>
      <Link to="/">Back to chat</Link>
    </article>
  );
}

function EvidenceLists({ page }) {
  return (
    <div className="evidence-columns">
      <RecordList title="Support conversations" records={page.support_conversations} />
      <RecordList title="Operations tickets" records={page.operations_tickets} />
      <RecordList title="Related incidents" records={page.related_incidents} />
    </div>
  );
}

function RecordList({ title, records }) {
  return (
    <div>
      <h3>{title}</h3>
      <ul className="evidence">
        {records.map((record) => (
          <li key={record.id}>
            <strong>{record.id}</strong>
            <span>{record.date} · {record.region || "—"}{record.blocker ? ` · ${record.blocker}` : ""}</span>
            <p>{record.text}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
