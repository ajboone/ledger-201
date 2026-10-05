import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ReactNode } from "react";

function SectionLabel({ children }: { children?: ReactNode }) {
  return <p className="chatbot-section-label"><strong>{children}</strong></p>;
}

export default function MessageContent({ role, content }: {
  role: "user" | "assistant";
  content: string;
}) {
  if (role === "user") return <p className="chatbot-user-text">{content}</p>;
  return <div className="chatbot-markdown">
    <Markdown skipHtml remarkPlugins={[remarkGfm]} components={{
      table: ({ children }) => (
        <div className="chatbot-table-scroll" role="region" aria-label="Assistant data table" tabIndex={0}>
          <table>{children}</table>
        </div>
      ),
      h1: SectionLabel, h2: SectionLabel, h3: SectionLabel,
      h4: SectionLabel, h5: SectionLabel, h6: SectionLabel,
      a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>,
      img: ({ alt }) => <span>{alt}</span>,
    }}>{content}</Markdown>
  </div>;
}
