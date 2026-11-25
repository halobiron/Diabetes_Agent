import clsx from "clsx";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Render generated prose without executing embedded HTML or unsafe link protocols. */
export function Markdown({ children, className }: { children: string; className?: string }) {
  return (
    <div className={clsx("markdown min-w-0 [overflow-wrap:anywhere]", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        skipHtml
        components={{
          a: ({ href, children }) => href ? (
            <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>
          ) : <span>{children}</span>,
          img: ({ alt }) => <span>{alt}</span>,
          table: ({ children }) => (
            <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Bảng nội dung">
              <table>{children}</table>
            </div>
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
