import { Bot } from 'lucide-react';

export function TypingIndicator() {
  return (
    <div className="flex gap-3 message-appear">
      <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-chart-2/20 text-chart-2">
        <Bot size={16} />
      </div>
      <div className="bg-card/60 border border-border/50 px-4 py-3 rounded-2xl rounded-tl-sm">
        <div className="typing-indicator flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-primary" />
          <span className="w-2 h-2 rounded-full bg-primary" />
          <span className="w-2 h-2 rounded-full bg-primary" />
          <span className="ml-2 text-sm text-muted-foreground">Analyzing your query...</span>
        </div>
      </div>
    </div>
  );
}
