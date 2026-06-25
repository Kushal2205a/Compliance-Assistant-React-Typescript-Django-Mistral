import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

const components: Components = {
  h1: ({ children, ...props }) => {
    const { ref, ...safe } = props as Record<string, unknown>;
    return (
      <h1 className="text-lg font-bold text-amber-700 dark:text-amber-400 border-l-4 border-amber-500 pl-3 my-4" {...safe}>
        {children}
      </h1>
    );
  },
  h2: ({ children, ...props }) => {
    const { ref, ...safe } = props as Record<string, unknown>;
    return (
      <h2 className="text-base font-bold text-amber-700 dark:text-amber-400 border-l-3 border-amber-400 pl-3 my-3" {...safe}>
        {children}
      </h2>
    );
  },
  h3: ({ children, ...props }) => {
    const { ref, ...safe } = props as Record<string, unknown>;
    return (
      <h3 className="text-sm font-bold text-gray-800 dark:text-gray-200 my-2" {...safe}>
        {children}
      </h3>
    );
  },
  p: ({ children, ...props }) => {
    const { ref, ...safe } = props as Record<string, unknown>;
    return (
      <p className="text-sm leading-relaxed my-2 text-gray-700 dark:text-gray-300" {...safe}>
        {children}
      </p>
    );
  },
  ul: ({ children, ...props }) => {
    const { ref, ...safe } = props as Record<string, unknown>;
    return (
      <ul className="list-disc list-inside space-y-1 my-2 text-sm text-gray-700 dark:text-gray-300" {...safe}>
        {children}
      </ul>
    );
  },
  ol: ({ children, ...props }) => {
    const { ref, ...safe } = props as Record<string, unknown>;
    return (
      <ol className="list-decimal list-inside space-y-1 my-2 text-sm text-gray-700 dark:text-gray-300" {...safe}>
        {children}
      </ol>
    );
  },
  li: ({ children, ...props }) => {
    const { ref, ...safe } = props as Record<string, unknown>;
    return (
      <li className="text-sm text-gray-700 dark:text-gray-300" {...safe}>
        {children}
      </li>
    );
  },
  blockquote: ({ children, ...props }) => {
    const { ref, ...safe } = props as Record<string, unknown>;
    return (
      <blockquote className="border-l-2 border-amber-300 pl-4 italic text-gray-600 dark:text-gray-400 my-2 text-sm" {...safe}>
        {children}
      </blockquote>
    );
  },
  code: ({ children, className }) => {
    const isInline = !className;
    if (isInline) {
      return (
        <code className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded text-xs font-mono text-amber-700 dark:text-amber-400">
          {children}
        </code>
      );
    }
    return (
      <pre className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4 overflow-x-auto my-3 text-xs font-mono border">
        <code className={className}>{children}</code>
      </pre>
    );
  },
  table: ({ children, ...props }) => {
    const { ref, ...safe } = props as Record<string, unknown>;
    return (
      <div className="overflow-x-auto my-3">
        <table className="min-w-full text-sm border-collapse" {...safe}>
          {children}
        </table>
      </div>
    );
  },
  thead: ({ children, ...props }) => {
    const { ref, ...safe } = props as Record<string, unknown>;
    return (
      <thead className="bg-amber-50 dark:bg-amber-900/30" {...safe}>
        {children}
      </thead>
    );
  },
  th: ({ children, ...props }) => {
    const { ref, ...safe } = props as Record<string, unknown>;
    return (
      <th className="border border-gray-200 dark:border-gray-700 px-3 py-2 text-left text-xs font-bold text-gray-700 dark:text-gray-300" {...safe}>
        {children}
      </th>
    );
  },
  td: ({ children, ...props }) => {
    const { ref, ...safe } = props as Record<string, unknown>;
    return (
      <td className="border border-gray-200 dark:border-gray-700 px-3 py-2 text-xs text-gray-600 dark:text-gray-400" {...safe}>
        {children}
      </td>
    );
  },
};

export default function MarkdownRenderer({ content }: { content: string }) {
  return (
    <div className="prose-custom">
      <ReactMarkdown components={components} remarkPlugins={[remarkGfm]}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
