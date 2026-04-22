import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';
import { CodeBlock } from './CodeBlock';

interface FormattedTextProps {
  content: string;
  className?: string;
}

export function FormattedText({ content, className }: FormattedTextProps) {
  return (
    <div className={cn("prose prose-sm dark:prose-invert max-w-none break-words w-full", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code(props) {
            const { children, className, node, ...rest } = props;
            const match = /language-(\w+)/.exec(className || '');
            const inline = !match && !String(children).includes('\n');
            const language = match ? match[1] : '';
            const codeString = String(children).replace(/\n$/, '');
            
            if (!inline && typeof children === 'string' && codeString.includes('\n') || match) {
              return (
                <div className="not-prose my-4">
                  <CodeBlock code={codeString} language={language || 'text'} title={language || 'Code'} />
                </div>
              );
            }
            return (
              <code className="px-1.5 py-0.5 mx-0.5 rounded-md bg-muted text-foreground font-mono text-[0.875em] before:content-[''] after:content-['']" {...rest}>
                {children}
              </code>
            );
          },
          table(props) {
            const { children, ...rest } = props;
            return (
              <div className="not-prose my-6 w-full overflow-x-auto rounded-lg border border-border/60 shadow-sm bg-card">
                <table className="w-full text-sm text-left" {...rest}>
                  {children}
                </table>
              </div>
            );
          },
          thead(props) {
            const { children, ...rest } = props;
            return <thead className="bg-muted/30 border-b border-border/60" {...rest}>{children}</thead>;
          },
          tbody(props) {
            const { children, ...rest } = props;
            return <tbody className="divide-y divide-border/40" {...rest}>{children}</tbody>;
          },
          tr(props) {
            const { children, ...rest } = props;
            return <tr className="transition-colors hover:bg-muted/40 even:bg-muted/10" {...rest}>{children}</tr>;
          },
          th(props) {
            const { children, ...rest } = props;
            return <th className="px-4 py-3 font-medium text-foreground whitespace-nowrap" {...rest}>{children}</th>;
          },
          td(props) {
            const { children, ...rest } = props;
            return <td className="px-4 py-2.5 text-muted-foreground align-top" {...rest}>{children}</td>;
          },
          p(props) {
            const { children, ...rest } = props;
            return <p className="leading-relaxed mb-4 last:mb-0 text-foreground" {...rest}>{children}</p>;
          },
          a(props) {
            const { children, href, ...rest } = props;
            return (
              <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary hover:text-primary/80 transition-colors underline font-medium" {...rest}>
                {children}
              </a>
            );
          },
          ul(props) {
            const { children, ...rest } = props;
            return <ul className="list-disc list-outside ml-5 mb-4 space-y-1.5 text-foreground marker:text-muted-foreground" {...rest}>{children}</ul>;
          },
          ol(props) {
            const { children, ...rest } = props;
            return <ol className="list-decimal list-outside ml-5 mb-4 space-y-1.5 text-foreground marker:text-muted-foreground" {...rest}>{children}</ol>;
          },
          li(props) {
            const { children, ...rest } = props;
            return <li className="leading-relaxed" {...rest}>{children}</li>;
          },
          h1(props) {
            const { children, ...rest } = props;
            return <h1 className="text-xl font-semibold mt-6 mb-4 text-foreground tracking-tight" {...rest}>{children}</h1>;
          },
          h2(props) {
            const { children, ...rest } = props;
            return <h2 className="text-lg font-semibold mt-5 mb-3 text-foreground tracking-tight" {...rest}>{children}</h2>;
          },
          h3(props) {
            const { children, ...rest } = props;
            return <h3 className="text-base font-medium mt-4 mb-2 text-foreground tracking-tight" {...rest}>{children}</h3>;
          },
          blockquote(props) {
            const { children, ...rest } = props;
            return <blockquote className="border-l-2 border-primary/40 pl-4 py-1 italic text-muted-foreground my-4 bg-muted/20 rounded-r-lg" {...rest}>{children}</blockquote>;
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
