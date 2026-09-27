import { useEffect, useRef, useState } from "react";
import { Route, Routes, useNavigate } from "react-router-dom";
import { api } from "./api";
import { Chat } from "./components/Chat";
import { Dashboard } from "./components/Dashboard";
import { Investigation } from "./components/Investigation";

function chooseSessionId(sessions, preferredId) {
  if (preferredId && sessions.some((session) => session.id === preferredId)) {
    return preferredId;
  }
  const recent = [...sessions].sort((left, right) => String(right.updated_at || "").localeCompare(String(left.updated_at || "")));
  return recent[0]?.id ?? null;
}

let sessionWrite = Promise.resolve();

function enqueueSessionWork(task) {
  const run = sessionWrite.then(task, task);
  sessionWrite = run.then(() => undefined, () => undefined);
  return run;
}

export function App() {
  const [user, setUser] = useState(undefined);
  const [sessionId, setSessionId] = useState(null);

  function updateUser(next) {
    setUser(next);
    if (!next) setSessionId(null);
  }

  useEffect(() => {
    api("/v1/auth/me")
      .then((me) => {
        setSessionId((current) => current || me.session_id);
        setUser(me);
      })
      .catch(() => updateUser(null));
  }, []);

  function openUser(me) {
    setSessionId(me.session_id);
    setUser(me);
  }

  if (user === undefined) {
    return <div className="boot">Loading the knowledge platform…</div>;
  }

  return (
    <Routes>
      <Route path="/investigations/:slug" element={user ? <Investigation user={user} setUser={updateUser} /> : <Login onLogin={openUser} />} />
      <Route path="/*" element={user ? <Workspace user={user} setUser={updateUser} sessionId={sessionId} setSessionId={setSessionId} /> : <Login onLogin={openUser} />} />
    </Routes>
  );
}

function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      const me = await api("/v1/auth/login", { method: "POST", body: { username, password } });
      onLogin(me);
    } catch (err) {
      setError(err.message || "Login failed");
    }
  }

  return (
    <main className="login-screen">
      <form className="login-card" onSubmit={submit}>
        <p className="eyebrow">Base Power</p>
        <h1>Knowledge platform</h1>
        <p className="lede">Sign in with your local persona account. The session stays in an httpOnly cookie.</p>
        <label>
          Username
          <input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" required />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required />
        </label>
        {error ? <p className="form-error">{error}</p> : null}
        <button type="submit">Sign in</button>
      </form>
    </main>
  );
}

function Workspace({ user, setUser, sessionId, setSessionId }) {
  const [sessions, setSessions] = useState([]);
  const [draft, setDraft] = useState("");
  const [sessionReady, setSessionReady] = useState(false);
  const navigate = useNavigate();
  const preferredOnVisit = useRef(sessionId || user.session_id);

  async function applySessions(rows, preferredId) {
    await enqueueSessionWork(async () => {
      let next = rows;
      let active = chooseSessionId(next, preferredId);
      if (!active) {
        const latest = await api("/v1/sessions");
        next = latest.sessions || [];
        active = chooseSessionId(next, preferredId);
      }
      if (!active) {
        const created = await api("/v1/sessions", { method: "POST" });
        const latest = await api("/v1/sessions");
        next = latest.sessions || [];
        active = chooseSessionId(next, created.id);
        if (!active) {
          next = [{ id: created.id, title: created.title, persona: created.persona }];
          active = created.id;
        }
      }
      setSessions(next);
      setSessionId(active);
    });
  }

  async function refreshSessions(activeId = sessionId) {
    const payload = await api("/v1/sessions");
    await applySessions(payload.sessions || [], activeId);
  }

  async function recoverMissing(missingId) {
    const payload = await api("/v1/sessions");
    const rows = (payload.sessions || []).filter((session) => session.id !== missingId);
    await applySessions(rows, null);
  }

  useEffect(() => {
    let cancelled = false;
    setSessionReady(false);
    refreshSessions(preferredOnVisit.current)
      .then(() => {
        if (!cancelled) setSessionReady(true);
      })
      .catch(() => {
        if (!cancelled) setUser(null);
      });
    return () => {
      cancelled = true;
    };
  }, [user.session_id]);

  async function logout() {
    await api("/v1/auth/logout", { method: "POST" });
    setUser(null);
    navigate("/");
  }

  async function newChat() {
    const created = await api("/v1/sessions", { method: "POST" });
    await refreshSessions(created.id);
  }

  async function deleteChat(session) {
    if (!window.confirm(`Delete “${session.title}”?`)) return;
    await api(`/v1/sessions/${session.id}`, { method: "DELETE" });
    const payload = await api("/v1/sessions");
    let next = (payload.sessions || []).filter((row) => row.id !== session.id);
    let active = chooseSessionId(next, session.id === sessionId ? null : sessionId);
    if (!active) {
      const created = await api("/v1/sessions", { method: "POST" });
      next = [{ id: created.id, title: created.title, persona: created.persona }];
      active = created.id;
    }
    setSessions(next);
    setSessionId(active || null);
    setDraft("");
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow light">Base Power</p>
          <strong>{user.username}</strong>
          <button type="button" className="text logout" onClick={logout}>Logout</button>
        </div>
        <button type="button" className="ghost" onClick={newChat}>New chat</button>
        <ul className="session-list">
          {sessions.map((session) => (
            <li key={session.id} className="session-row">
              <button type="button" className={session.id === sessionId ? "active" : ""} title={session.title} onClick={() => setSessionId(session.id)}>
                {session.title.length > 20 ? session.title.slice(0, 20) : session.title}
              </button>
              <button type="button" className="session-delete" aria-label={`Delete ${session.title}`} onClick={() => deleteChat(session)}>
                Delete
              </button>
            </li>
          ))}
        </ul>
      </aside>
      <section className="workspace">
        <Dashboard persona={user.persona} onAsk={setDraft} />
        {sessionReady && sessionId ? (
          <Chat
            key={sessionId}
            sessionId={sessionId}
            persona={user.persona}
            draft={draft}
            setDraft={setDraft}
            onActivity={refreshSessions}
            onMissing={recoverMissing}
          />
        ) : null}
        <button type="button" className="text logout" onClick={logout}>Logout</button>
      </section>
    </div>
  );
}

