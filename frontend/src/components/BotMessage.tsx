import { useState } from 'react';
import { BarChart3, Table, AlertCircle, ChevronDown, ChevronUp, Database, Tag, BookOpen, MessageSquare, PieChart } from 'lucide-react';
import { Message, BackendType } from '@/types/chat';
import { CodeBlock } from './CodeBlock';
import { DataChart } from './DataChart';
import { DataTable } from './DataTable';
import { cn } from '@/lib/utils';

interface BotMessageProps {
  message: Message;
}

// Backend indicator badge
function BackendBadge({ backend }: { backend: BackendType }) {
  const config: Record<BackendType, { label: string; icon: React.ReactNode; className: string }> = {
    lf_assist: { label: 'Company Knowledge', icon: <BookOpen size={12} />, className: 'bg-blue-500/10 text-blue-500 border-blue-500/20' },
    doc_assist: { label: 'Document Q&A', icon: <BookOpen size={12} />, className: 'bg-purple-500/10 text-purple-500 border-purple-500/20' },
    db_assist: { label: 'Database Query', icon: <Database size={12} />, className: 'bg-green-500/10 text-green-500 border-green-500/20' },
    viz_assist: { label: 'Visualization', icon: <PieChart size={12} />, className: 'bg-orange-500/10 text-orange-500 border-orange-500/20' },
    scope_guard: { label: 'Assistant', icon: <MessageSquare size={12} />, className: 'bg-gray-500/10 text-gray-500 border-gray-500/20' },
  };

  const { label, icon, className } = config[backend] || config.scope_guard;

  return (
    <div className={cn("inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium border", className)}>
      {icon}
      {label}
    </div>
  );
}

// Tags component for lf_assist
function TagsList({ tags }: { tags: string[] }) {
  return (
    <div className="flex flex-wrap gap-1.5 mt-3">
      {tags.map((tag, index) => (
        <span
          key={index}
          className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary border border-primary/20"
        >
          <Tag size={10} />
          {tag}
        </span>
      ))}
    </div>
  );
}

export function BotMessage({ message }: BotMessageProps) {
  const [viewMode, setViewMode] = useState<'chart' | 'table'>('chart');
  const [showReasoning, setShowReasoning] = useState(false);

  if (!message.response) {
    return (
      <div className="text-foreground">
        {message.content}
      </div>
    );
  }

  const { backend, answer, sql_query, data, chart_analysis, tags, error } = message.response;

  // Error state
  if (error) {
    return (
      <div className="space-y-3">
        {backend && <BackendBadge backend={backend} />}
        <div className="flex items-start gap-3 p-4 rounded-lg bg-destructive/10 border border-destructive/30">
          <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-destructive">Error</p>
            <p className="text-sm text-muted-foreground mt-1">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  const hasData = data && data.length > 0;
  const isChartable = chart_analysis?.chartable && chart_analysis?.auto_chart;
  const isVizAssist = backend === 'viz_assist';

  return (
    <div className="space-y-4">
      {/* Backend Badge */}
      {backend && <BackendBadge backend={backend} />}

      {/* Answer Text */}
      {answer && (
        <div className="text-foreground whitespace-pre-wrap">
          {answer}
        </div>
      )}

      {/* Tags for lf_assist */}
      {tags && tags.length > 0 && <TagsList tags={tags} />}

      {/* SQL Query Section (viz_assist only) */}
      {isVizAssist && sql_query && (
        <CodeBlock 
          code={sql_query} 
          language="sql" 
          title="Generated SQL Query"
          defaultCollapsed={true}
        />
      )}

      {/* Chart Analysis Reasoning (viz_assist only) */}
      {isVizAssist && chart_analysis?.reasoning && (
        <>
          <button
            onClick={() => setShowReasoning(!showReasoning)}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <Database size={14} />
            <span>Analysis Reasoning</span>
            {showReasoning ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          
          {showReasoning && (
            <div className="p-3 rounded-lg bg-muted/30 border border-border/50 text-sm text-muted-foreground animate-fade-in">
              {chart_analysis.reasoning}
            </div>
          )}
        </>
      )}

      {/* Data Visualization Section (viz_assist only) */}
      {isVizAssist && hasData && (
        <div className="rounded-lg border border-border bg-card/40 overflow-hidden">
          {/* View Toggle Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-secondary/30">
            <span className="text-sm font-medium text-foreground">
              Results ({data.length} {data.length === 1 ? 'row' : 'rows'})
            </span>
            <div className="flex items-center gap-1 p-1 rounded-lg bg-muted/50">
              {isChartable && (
                <button
                  onClick={() => setViewMode('chart')}
                  className={cn(
                    "flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-all",
                    viewMode === 'chart'
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted"
                  )}
                >
                  <BarChart3 size={14} />
                  Chart
                </button>
              )}
              <button
                onClick={() => setViewMode('table')}
                className={cn(
                  "flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-all",
                  viewMode === 'table' || !isChartable
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                )}
              >
                <Table size={14} />
                Table
              </button>
            </div>
          </div>

          {/* Content Area */}
          <div className="animate-fade-in">
            {viewMode === 'chart' && isChartable ? (
              <DataChart data={data} chartAnalysis={chart_analysis} />
            ) : (
              <div className="p-4">
                <DataTable data={data} />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Empty State for viz_assist */}
      {isVizAssist && !hasData && !error && (
        <div className="flex items-center justify-center py-8 text-muted-foreground">
          No records found for this query
        </div>
      )}
    </div>
  );
}
