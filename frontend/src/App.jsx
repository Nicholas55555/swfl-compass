import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { DocBuilder, DocumentCard } from "./Docs.jsx";
import { PlacesPanel } from "./Places.jsx";

const PERSONAS = [
  { id: "resident", label: "🏠 I live here" },
  { id: "student", label: "🎓 I study here" },
  { id: "worker", label: "💼 I work here" },
  { id: "visitor", label: "🌴 I'm visiting" },
];

const STARTERS = {
  resident: [
    "What's my hurricane evacuation zone in Lee County and how do I prepare?",
    "Is there red tide at Fort Myers Beach right now?",
    "Where can I get help paying my electric bill in SWFL?",
  ],
  student: [
    "How do I get from FGCU to downtown Fort Myers without a car?",
    "What free mental health resources are available to FGCU students?",
    "Where can students find affordable housing near FGCU?",
  ],
  worker: [
    "What job training programs does CareerSource Southwest Florida offer?",
    "Which industries are hiring most in Lee and Collier County?",
    "Are there childcare assistance programs for working parents in SWFL?",
  ],
  visitor: [
    "What are the best beaches near Naples and Fort Myers?",
    "Where can I see manatees in Southwest Florida?",
    "What should visitors know about hurricane season in SWFL?",
  ],
};

const md = (text) => (
  <ReactMarkdown
    remarkPlugins={[remarkGfm]}
    components={{ a: (p) => <a {...p} target="_blank" rel="noreferrer" /> }}
  >
    {text}
  </ReactMarkdown>
);

function hostOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function ResourceCard({ r, onSummarize, onAsk }) {
  const [state, setState] = useState({ loading: false, summary: null, error: null });
  const [open, setOpen] = useState(false);

  async function summarize() {
    if (state.summary) return setOpen(!open);
    setState({ loading: true, summary: null, error: null });
    setOpen(true);
    try {
      const res = await onSummarize(r.url);
      setState({ loading: false, summary: res.summary, error: null });
    } catch (e) {
      setState({ loading: false, summary: null, error: e.message });
    }
  }

  return (
    <div className="resource">
      <div className="resource-head">
        <img
          className="favicon"
          src={`https://www.google.com/s2/favicons?domain=${hostOf(r.url)}&sz=32`}
          alt=""
        />
        <div className="resource-text">
          <a href={r.url} target="_blank" rel="noreferrer" className="resource-title">
            {r.title}
          </a>
          <div className="resource-host">{hostOf(r.url)}</div>
          {r.why && <div className="resource-why">{r.why}</div>}
        </div>
      </div>
      <div className="resource-actions">
        <button onClick={summarize} disabled={state.loading}>
          {state.loading ? "Summarizing…" : state.summary ? (open ? "Hide summary" : "Show summary") : "✨ Summarize"}
        </button>
        <a className="btn-link" href={r.url} target="_blank" rel="noreferrer">
          Open ↗
        </a>
        <button className="ghost" onClick={() => onAsk(`Tell me more about "${r.title}" (${r.url}) — what can it help me with?`)}>
          Ask about it
        </button>
      </div>
      {open && (state.summary || state.error) && (
        <div className={state.error ? "summary error" : "summary"}>
          {state.error ? state.error : md(state.summary)}
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [persona, setPersona] = useState(null);
  const [messages, setMessages] = useState([]); // {role, content, statuses, resources, suggestions, error}
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID()); // keys this chat's vector store
  const [builder, setBuilder] = useState(null); // "itinerary" | "guide" | null
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function patchLast(fn) {
    setMessages((ms) => {
      const copy = ms.slice();
      copy[copy.length - 1] = fn({ ...copy[copy.length - 1] });
      return copy;
    });
  }

  async function send(text, task = null) {
    text = (text ?? input).trim();
    if (!text || busy) return;
    setInput("");
    setBuilder(null);
    setBusy(true);
    const history = [...messages, { role: "user", content: text }];
    setMessages([...history, { role: "assistant", content: "", statuses: [], pending: true }]);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          persona,
          session_id: sessionId,
          task,
          messages: history
            .filter((m) => m.content)
            .map((m) => ({ role: m.role, content: m.content })),
        }),
      });
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let idx;
        while ((idx = buf.indexOf("\n\n")) >= 0) {
          const chunk = buf.slice(0, idx);
          buf = buf.slice(idx + 2);
          if (!chunk.startsWith("data: ")) continue;
          const ev = JSON.parse(chunk.slice(6));
          if (ev.type === "status") patchLast((m) => ({ ...m, statuses: [...m.statuses, ev.text] }));
          else if (ev.type === "answer") patchLast((m) => ({ ...m, content: ev.text, document: ev.document }));
          else if (ev.type === "places") patchLast((m) => ({ ...m, places: ev.places }));
          else if (ev.type === "extras")
            patchLast((m) => ({ ...m, resources: ev.resources, suggestions: ev.suggested_questions }));
          else if (ev.type === "error") patchLast((m) => ({ ...m, error: ev.text }));
        }
      }
    } catch (e) {
      patchLast((m) => ({ ...m, error: e.message }));
    } finally {
      patchLast((m) => ({ ...m, pending: false }));
      setBusy(false);
    }
  }

  async function summarizeUrl(url) {
    const res = await fetch("/api/summarize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, session_id: sessionId, focus: messages.filter((m) => m.role === "user").at(-1)?.content }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `Error ${res.status}`);
    return data;
  }

  const empty = messages.length === 0;

  return (
    <div className="app">
      <header>
        <div className="brand">
          <span className="logo">🧭</span>
          <div>
            <h1>SWFL Compass</h1>
            <p>Your AI guide to living, studying, working & visiting Southwest Florida</p>
          </div>
        </div>
        {!empty && (
          <button className="ghost" onClick={() => {
              setMessages([]);
              setSessionId(crypto.randomUUID());
              setBuilder(null);
            }} disabled={busy}>
            New chat
          </button>
        )}
      </header>

      <main>
        {empty && (
          <div className="welcome">
            <h2>Hi! What brings you to Southwest Florida?</h2>
            <div className="personas">
              {PERSONAS.map((p) => (
                <button
                  key={p.id}
                  className={persona === p.id ? "chip active" : "chip"}
                  onClick={() => setPersona(persona === p.id ? null : p.id)}
                >
                  {p.label}
                </button>
              ))}
            </div>
            <p className="hint">Try one of these:</p>
            <div className="starters">
              {(STARTERS[persona] || [...STARTERS.resident.slice(0, 2), ...STARTERS.visitor.slice(0, 1), STARTERS.student[0]]).map((q) => (
                <button key={q} className="starter" onClick={() => send(q)}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="msg user">
              {m.content}
            </div>
          ) : (
            <div key={i} className="msg assistant">
              {m.statuses?.length > 0 && (
                <details className="steps" open={m.pending}>
                  <summary>
                    {m.pending ? <span className="spinner" /> : "🧠"}{" "}
                    {m.pending ? m.statuses.at(-1) : `Researched in ${m.statuses.length} steps`}
                  </summary>
                  <ul>
                    {m.statuses.map((s, j) => (
                      <li key={j}>{s}</li>
                    ))}
                  </ul>
                </details>
              )}
              {m.content &&
                (m.document ? (
                  <DocumentCard content={m.content}>{md(m.content)}</DocumentCard>
                ) : (
                  <div className="answer">{md(m.content)}</div>
                ))}
              {m.error && <div className="summary error">⚠️ {m.error}</div>}

              {m.places?.length > 0 && <PlacesPanel places={m.places} />}

              {m.resources?.length > 0 && (
                <div className="resources">
                  <h3>📚 Helpful resources</h3>
                  {m.resources.map((r) => (
                    <ResourceCard key={r.url} r={r} onSummarize={summarizeUrl} onAsk={send} />
                  ))}
                </div>
              )}

              {m.suggestions?.length > 0 && i === messages.length - 1 && (
                <div className="suggestions">
                  <h3>💡 You might also ask</h3>
                  {m.suggestions.map((q) => (
                    <button key={q} className="starter" onClick={() => send(q)} disabled={busy}>
                      {q}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )
        )}
        <div ref={bottomRef} />
      </main>

      <div className="dock">
        {builder && (
          <DocBuilder mode={builder} disabled={busy} onClose={() => setBuilder(null)} onSubmit={(label, task) => send(label, task)} />
        )}
        <div className="tools">
          <button className={builder === "itinerary" ? "tool active" : "tool"} onClick={() => setBuilder(builder === "itinerary" ? null : "itinerary")} disabled={busy}>
            🗺️ Plan an itinerary
          </button>
          <button className={builder === "guide" ? "tool active" : "tool"} onClick={() => setBuilder(builder === "guide" ? null : "guide")} disabled={busy}>
            📄 Make a guide
          </button>
        </div>
      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about hurricanes, beaches, jobs, FGCU, services… or paste a link to summarize"
          disabled={busy}
        />
        <button type="submit" disabled={busy || !input.trim()}>
          {busy ? "…" : "Send"}
        </button>
      </form>
      </div>
    </div>
  );
}
