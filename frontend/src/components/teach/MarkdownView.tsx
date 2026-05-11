"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props {
  content: string;
  className?: string;
}

/**
 * Рендер markdown энциклопедии в стиле INSERVO.
 * Использует prose-классы tailwind (дефолтные), но переопределяет цвета под light/dark theme.
 */
export function MarkdownView({ content, className = "" }: Props) {
  return (
    <div className={`md-content ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ ...props }) => (
            <h1
              className="text-3xl font-display font-bold text-ink-900 dark:text-ink-50 mt-8 mb-4 pb-2 border-b border-ink-200 dark:border-ink-800"
              {...props}
            />
          ),
          h2: ({ ...props }) => (
            <h2
              className="text-2xl font-display font-semibold text-ink-900 dark:text-ink-50 mt-8 mb-3"
              {...props}
            />
          ),
          h3: ({ ...props }) => (
            <h3
              className="text-xl font-display font-semibold text-ink-900 dark:text-ink-100 mt-6 mb-2"
              {...props}
            />
          ),
          h4: ({ ...props }) => (
            <h4 className="text-lg font-display font-medium text-ink-800 dark:text-ink-200 mt-4 mb-2" {...props} />
          ),
          p: ({ ...props }) => (
            <p className="text-ink-700 dark:text-ink-300 leading-relaxed my-3" {...props} />
          ),
          ul: ({ ...props }) => (
            <ul className="list-disc list-outside ml-6 my-3 text-ink-700 dark:text-ink-300 space-y-1" {...props} />
          ),
          ol: ({ ...props }) => (
            <ol className="list-decimal list-outside ml-6 my-3 text-ink-700 dark:text-ink-300 space-y-1" {...props} />
          ),
          li: ({ ...props }) => <li className="leading-relaxed" {...props} />,
          a: ({ ...props }) => (
            <a
              className="text-brand-700 hover:text-brand-800 dark:text-accent-500 dark:hover:text-accent-400 underline underline-offset-2"
              target="_blank"
              rel="noopener noreferrer"
              {...props}
            />
          ),
          strong: ({ ...props }) => (
            <strong className="font-semibold text-ink-900 dark:text-ink-50" {...props} />
          ),
          em: ({ ...props }) => <em className="text-ink-800 dark:text-ink-200 italic" {...props} />,
          code: ({ inline, ...props }: { inline?: boolean } & React.HTMLAttributes<HTMLElement>) =>
            inline ? (
              <code
                className="bg-ink-100 text-brand-700 dark:bg-ink-900 dark:text-accent-300 px-1.5 py-0.5 rounded text-sm font-mono"
                {...props}
              />
            ) : (
              <code
                className="block bg-ink-100 text-ink-900 dark:bg-ink-900 dark:text-ink-100 p-4 rounded-md font-mono text-sm overflow-x-auto"
                {...props}
              />
            ),
          pre: ({ ...props }) => <pre className="my-4" {...props} />,
          table: ({ ...props }) => (
            <div className="overflow-x-auto my-4">
              <table
                className="min-w-full border-collapse border border-ink-200 dark:border-ink-800 text-sm"
                {...props}
              />
            </div>
          ),
          thead: ({ ...props }) => <thead className="bg-ink-100 dark:bg-ink-900" {...props} />,
          th: ({ ...props }) => (
            <th
              className="border border-ink-200 dark:border-ink-800 px-3 py-2 text-left font-semibold text-ink-900 dark:text-ink-100"
              {...props}
            />
          ),
          td: ({ ...props }) => (
            <td className="border border-ink-200 dark:border-ink-800 px-3 py-2 text-ink-700 dark:text-ink-300" {...props} />
          ),
          blockquote: ({ ...props }) => (
            <blockquote
              className="border-l-4 border-brand-400 dark:border-accent-500/50 pl-4 italic text-ink-700 dark:text-ink-300 my-4 bg-brand-50 dark:bg-ink-900/30 py-2 pr-3"
              {...props}
            />
          ),
          hr: ({ ...props }) => <hr className="border-ink-200 dark:border-ink-800 my-6" {...props} />,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
