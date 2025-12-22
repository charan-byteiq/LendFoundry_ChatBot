import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';

interface CodeBlockProps {
  code: string;
  language?: string;
  title?: string;
  collapsible?: boolean;
  defaultCollapsed?: boolean;
}

export function CodeBlock({ 
  code, 
  language = 'sql', 
  title = 'SQL Query',
  collapsible = true,
  defaultCollapsed = false 
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-lg border border-border overflow-hidden bg-secondary/50">
      <div 
        className={cn(
          "flex items-center justify-between px-4 py-2 bg-secondary/80",
          collapsible && "cursor-pointer hover:bg-secondary transition-colors"
        )}
        onClick={() => collapsible && setCollapsed(!collapsed)}
      >
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <span className="w-3 h-3 rounded-full bg-destructive/60" />
            <span className="w-3 h-3 rounded-full bg-chart-4/60" />
            <span className="w-3 h-3 rounded-full bg-chart-5/60" />
          </div>
          <span className="text-sm font-medium text-muted-foreground ml-2">
            {title}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleCopy();
            }}
            className="p-1.5 rounded-md hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
            title="Copy code"
          >
            {copied ? <Check size={14} className="text-primary" /> : <Copy size={14} />}
          </button>
          {collapsible && (
            collapsed ? <ChevronDown size={16} className="text-muted-foreground" /> : <ChevronUp size={16} className="text-muted-foreground" />
          )}
        </div>
      </div>
      
      <div className={cn(
        "transition-all duration-300 overflow-hidden",
        collapsed ? "max-h-0" : "max-h-[500px]"
      )}>
        <SyntaxHighlighter
          language={language}
          style={vscDarkPlus}
          customStyle={{
            margin: 0,
            padding: '1rem',
            background: 'transparent',
            fontSize: '0.875rem',
          }}
          wrapLongLines
        >
          {code}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}
