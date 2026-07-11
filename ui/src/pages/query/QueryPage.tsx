import "./query.css";
import { IconSend } from "../../shared/icons/IconSend";

type ChatMessage = {
  id: string;
  role: "assistant" | "user";
  text: string;
  meta?: string;
};

const sampleMessages: ChatMessage[] = [
  {
    id: "msg-1",
    role: "assistant",
    text: "可以先告诉我你要检索的 case 范围，我会按分区和类型整理结果。",
    meta: "Knowbase · 09:42 · 0.8s",
  },
  {
    id: "msg-2",
    role: "user",
    text: "帮我查 Claims 分区近 24 小时的 review 状态案例。",
    meta: "You · 09:43",
  },
  {
    id: "msg-3",
    role: "assistant",
    text: "收到。你也可以继续补充筛选条件，比如 facet、run id 或 backlog batch。",
    meta: "Knowbase · 09:43 · 1.1s",
  },
];

export function QueryPage() {
  return (
    <section className="query-page">
      <header className="query-page-header">
        <div className="query-page-copy">
          <h2>Query</h2>
          <p>Ask questions and review responses in one conversation flow.</p>
        </div>
      </header>

      <section className="query-layout">
        <div className="query-chat-panel">
          <div className="query-chat-scroll">
            {sampleMessages.map((message) => (
              <div key={message.id} className={`query-message is-${message.role}`}>
                <div className="query-message-bubble">
                  <p>{message.text}</p>
                </div>
                <span>{message.meta}</span>
              </div>
            ))}
          </div>

          <form className="query-input-form" onSubmit={(event) => event.preventDefault()}>
            <label htmlFor="query-input" className="query-input-wrap">
              <textarea
                id="query-input"
                placeholder="Ask anything about cases, partitions, runs, or backlog..."
                rows={1}
              />
              <button type="submit" className="query-send-icon-button" aria-label="Send message">
                <IconSend />
              </button>
            </label>
          </form>
        </div>
      </section>
    </section>
  );
}
