import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, askStream } from "../api";

const LOCAL_MODEL = "qwen3:8b";

export function Chat({ sessionId, persona, draft, setDraft, onActivity, onMissing }) {
  const [turns, setTurns] = useState([]);
  const [router, setRouter] = useState("llm");
  const [options, setOptions] = useState(null);
  const [pending, setPending] = useState(false);
  const [stage, setStage] = useState("routing ask");
  const [error, setError] = useState("");
  const sending = useRef(false);

  useEffect(() => {
    let cancelled = false;
    setError("");
    api(`/v1/sessions/${sessionId}`)
      .then((payload) => {
        if (!cancelled) setTurns(payload.turns);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err.status === 404 && onMissing) {
          Promise.resolve(onMissing(sessionId)).catch(() => setError(err.message));
          return;
        }
        setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  useEffect(() => {
    let cancelled = false;
    api("/v1/llm/options")
      .then((payload) => {
        if (cancelled) return;
        setOptions(payload);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  async function ask(raw, { fromDraft = false } = {}) {
    const query = String(raw || "").trim();
    if (!query || pending || sending.current) return;
    sending.current = true;
    setError("");
    if (fromDraft) setDraft("");
    setStage("routing ask");
    setPending(true);
    setTurns((current) => [...current, { id: "pending-user", role: "user", content: query }]);
    try {
      const result = await askStream(
        `/v1/sessions/${sessionId}/ask`,
        { query, channel: "web", router, provider: "ollama", model: options?.ollama?.model || LOCAL_MODEL },
        setStage,
      );
      const payload = await api(`/v1/sessions/${sessionId}`);
      setTurns((current) => rememberSuggestions(payload.turns, current, result?.suggested_questions));
      if (onActivity) onActivity(sessionId);
    } catch (err) {
      setError(err.message);
      setTurns((current) => current.filter((turn) => turn.id !== "pending-user"));
      if (fromDraft) setDraft(query);
    } finally {
      sending.current = false;
      setPending(false);
    }
  }

  function send(event) {
    event.preventDefault();
    void ask(draft, { fromDraft: true });
  }

  return (
    <div className="chat">
      <div className="thread">
        {turns.length === 0 ? (
          <>
            <p className="muted">
              Ask a question. Get the answer. Understand why. Drill into the evidence.
            </p>
          </>
        ) : null}
        {turns.map((turn) => (
          <article key={turn.id} className={`turn ${turn.role}`}>
            {turn.role === "assistant" ? (
              <Assistant turn={turn} pending={pending} onAsk={(question) => void ask(question)} />
            ) : (
              <p>{turn.content}</p>
            )}
          </article>
        ))}
        {pending ? (
          <article className="turn assistant pending">
            <span className="flywheel" aria-hidden="true" />
            <span className="flywheel-stage" role="status">{stage}</span>
          </article>
        ) : null}
        {error ? <p className="form-error">{error}</p> : null}
      </div>
      <form className="composer" onSubmit={send}>
        <div className="composer-tools">
          <div className="router" role="group" aria-label="Router">
            <button type="button" aria-pressed={router === "llm"} onClick={() => setRouter("llm")}>LLM</button>
            <button type="button" aria-pressed={router === "jev"} onClick={() => setRouter("jev")}>JEV</button>
          </div>
        </div>
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault();
              send(event);
            }
          }}
          rows={3}
          placeholder="Ask a question"
        />
        <button type="submit" disabled={pending}>Send</button>
      </form>
    </div>
  );
}

function visibleCitations(turn) {
  const citations = turn.citations || [];
  const companyChart = (turn.artifacts || []).some((artifact) =>
    String(artifact.title || "").startsWith("Quarterly")
  );
  const forecast = /forecast/i.test(turn.content || "");
  if (forecast || ((turn.artifacts || []).length && !companyChart)) {
    return citations.filter((citation) => citation.kind !== "knowledge_item");
  }
  return citations;
}

function rememberSuggestions(serverTurns, previous, incoming) {
  const kept = new Map();
  for (const turn of previous) {
    if (turn.id && turn.id !== "pending-user" && turn.suggested_questions?.length) {
      kept.set(turn.id, turn.suggested_questions);
    }
  }
  const turns = serverTurns.map((turn) => {
    const fromServer = Array.isArray(turn.suggested_questions) ? turn.suggested_questions : [];
    return {
      ...turn,
      suggested_questions: fromServer.length ? fromServer : kept.get(turn.id) || [],
    };
  });
  if (incoming?.length) {
    for (let index = turns.length - 1; index >= 0; index -= 1) {
      if (turns[index].role === "assistant" && !turns[index].suggested_questions.length) {
        turns[index] = { ...turns[index], suggested_questions: incoming };
        break;
      }
    }
  }
  return turns;
}

function Assistant({ turn, pending, onAsk }) {
  const suggestions = turn.suggested_questions || [];
  return (
    <div>
      <Answer text={turn.content} suggestions={suggestions} />
      <FollowUps questions={suggestions} pending={pending} onAsk={onAsk} />
      {turn.telemetry ? (
        <p className="telemetry">
          {turn.telemetry.router} · {turn.telemetry.model} · {turn.telemetry.latency_ms} ms · in {turn.telemetry.input_tokens} · out {turn.telemetry.output_tokens} · ${turn.telemetry.estimated_cost_usd}
        </p>
      ) : null}
      {visibleCitations(turn).length ? (
        <div className="references">
          <p className="citation-label">References</p>
          <ul className="citations">
            {visibleCitations(turn).map((citation) => (
              <li key={`${citation.kind}-${citation.id}-${citation.quote.slice(0, 24)}`}>
                <q>{citation.quote}</q>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {(turn.artifacts || []).map((artifact) => (
        <Chart key={artifact.id} artifact={artifact} />
      ))}
    </div>
  );
}

function sameQuestion(left, right) {
  const fold = (value) => String(value || "").trim().replace(/\s+/g, " ").toLowerCase();
  return fold(left) === fold(right);
}

function withoutTrailingSuggestion(text, suggestions) {
  const lines = String(text || "").replace(/\r\n/g, "\n").split("\n");
  let end = lines.length;
  while (end > 0 && lines[end - 1].trim() === "") end -= 1;
  if (!end || !suggestions?.length) return String(text || "");
  const last = lines[end - 1].trim();
  const onlyQuestion = last.endsWith("?") && !last.startsWith("- ") && !last.startsWith("* ");
  if (!onlyQuestion || !suggestions.some((question) => sameQuestion(question, last))) {
    return String(text || "");
  }
  return lines.slice(0, end - 1).join("\n").trim();
}

function answerBlocks(text) {
  const blocks = [];
  let paragraph = [];
  let list = [];

  function flushParagraph() {
    const value = paragraph.join(" ").replace(/\s+/g, " ").trim();
    paragraph = [];
    if (value) blocks.push({ type: "p", text: value });
  }

  function flushList() {
    if (!list.length) return;
    blocks.push({ type: "ul", items: list });
    list = [];
  }

  for (const line of String(text || "").replace(/\r\n/g, "\n").split("\n")) {
    const bullet = line.match(/^\s*[-*]\s+(.*)$/);
    if (bullet && bullet[1].trim()) {
      flushParagraph();
      list.push(bullet[1].trim());
      continue;
    }
    if (line.trim() === "") {
      flushParagraph();
      continue;
    }
    flushList();
    paragraph.push(line.trim());
  }
  flushParagraph();
  flushList();
  return blocks;
}

function RichText({ text }) {
  const parts = String(text || "").split(/(\[[^\]]+\]\(\/investigations\/[^)]+\))/g);
  return parts.map((part, index) => {
    const match = part.match(/^\[([^\]]+)\]\((\/investigations\/[^)]+)\)$/);
    if (!match) return <span key={index}>{part}</span>;
    return <Link key={index} to={match[2]}>{match[1]}</Link>;
  });
}

function Answer({ text, suggestions }) {
  const blocks = answerBlocks(withoutTrailingSuggestion(text, suggestions));
  if (!blocks.length) return null;
  return (
    <div className="answer">
      {blocks.map((block, index) => {
        if (block.type === "ul") {
          return (
            <ul key={index}>
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex}><RichText text={item} /></li>
              ))}
            </ul>
          );
        }
        return <p key={index}><RichText text={block.text} /></p>;
      })}
    </div>
  );
}

function FollowUps({ questions, pending, onAsk }) {
  if (!questions.length) return null;
  return (
    <div className="follow-ups" role="group" aria-label="Suggested questions">
      {questions.map((question) => (
        <button
          key={question}
          type="button"
          className="follow-up"
          disabled={pending}
          onClick={() => onAsk(question)}
        >
          {question}
        </button>
      ))}
    </div>
  );
}

function Chart({ artifact }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let view;
    let cancelled = false;
    const node = document.getElementById(`chart-${artifact.id}`);
    import("vega-embed")
      .then(({ default: embed }) => {
        if (cancelled || !node) return;
        return embed(node, artifact.spec, { actions: false });
      })
      .then((result) => {
        view = result;
      })
      .catch(() => setFailed(true));
    return () => {
      cancelled = true;
      if (view) view.finalize();
    };
  }, [artifact]);

  if (failed) {
    return <img className="chart-fallback" alt={artifact.title} src={artifact.image_uri} />;
  }
  return <div id={`chart-${artifact.id}`} className="chart" />;
}
