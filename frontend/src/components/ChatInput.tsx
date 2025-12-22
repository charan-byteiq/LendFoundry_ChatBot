import { useState, useRef, FormEvent, KeyboardEvent } from 'react';
import { Send, Sparkles, Paperclip, X, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatInputProps {
  onSend: (message: string, file?: File) => void;
  isLoading: boolean;
}

export function ChatInput({ onSend, isLoading }: ChatInputProps) {
  const [input, setInput] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSend(input.trim(), selectedFile || undefined);
      setInput('');
      setSelectedFile(null);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file);
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const suggestions = [
    "What are the top 10 loans by outstanding balance & ID?",
    "Compare loan onboarding by month",
    "Show me a bar chart of loans by state"
  ];

  return (
    <div className="border-t border-border bg-card/80 backdrop-blur-xl">
      <div className="max-w-4xl mx-auto px-4 py-4">
        {/* Quick Suggestions */}
        {input.length === 0 && !selectedFile && (
          <div className="flex flex-wrap gap-2 mb-3">
            {suggestions.map((suggestion, index) => (
              <button
                key={index}
                onClick={() => setInput(suggestion)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-full 
                           bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground 
                           transition-colors border border-border/50"
              >
                <Sparkles size={12} className="text-primary" />
                {suggestion}
              </button>
            ))}
          </div>
        )}

        {/* File Attachment Preview */}
        {selectedFile && (
          <div className="flex items-center gap-2 mb-3 p-2 rounded-lg bg-primary/10 border border-primary/20">
            <FileText size={16} className="text-primary" />
            <span className="text-sm text-foreground flex-1 truncate">{selectedFile.name}</span>
            <button
              onClick={handleRemoveFile}
              className="p-1 rounded-full hover:bg-primary/20 transition-colors"
            >
              <X size={14} className="text-muted-foreground" />
            </button>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex items-end gap-3">
          {/* File Upload Button */}
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            onChange={handleFileSelect}
            className="hidden"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading}
            className={cn(
              "flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center",
              "bg-secondary/50 border border-border",
              "hover:bg-muted transition-colors",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              selectedFile && "bg-primary/10 border-primary/30"
            )}
            title="Attach PDF for Document Q&A"
          >
            <Paperclip size={18} className={selectedFile ? "text-primary" : "text-muted-foreground"} />
          </button>

          <div className="flex-1 relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={selectedFile ? "Ask a question about the document..." : "Ask a question about your data..."}
              disabled={isLoading}
              rows={1}
              className={cn(
                "w-full resize-none rounded-xl border border-border bg-secondary/50 px-4 py-3",
                "text-foreground placeholder:text-muted-foreground",
                "focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50",
                "disabled:opacity-50 disabled:cursor-not-allowed",
                "transition-all duration-200",
                "min-h-[48px] max-h-[120px]"
              )}
              style={{
                height: 'auto',
                minHeight: '48px',
              }}
              onInput={(e) => {
                const target = e.target as HTMLTextAreaElement;
                target.style.height = 'auto';
                target.style.height = Math.min(target.scrollHeight, 120) + 'px';
              }}
            />
          </div>

          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className={cn(
              "flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center",
              "bg-primary text-primary-foreground",
              "hover:bg-primary/90 active:scale-95",
              "disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100",
              "transition-all duration-200",
              "shadow-glow"
            )}
          >
            <Send size={18} />
          </button>
        </form>

        <p className="text-xs text-muted-foreground text-center mt-3">
          Press Enter to send, Shift + Enter for new line. Attach a PDF for document Q&A.
        </p>
      </div>
    </div>
  );
}
