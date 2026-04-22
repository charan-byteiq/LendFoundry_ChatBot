import { cn } from '@/lib/utils';
import { Message } from '@/types/chat';
import { BotMessage } from './BotMessage';
import { Bot, User, FileText } from 'lucide-react';

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div
      className={cn(
        "flex gap-3 message-appear",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center",
          isUser 
            ? "bg-primary/20 text-primary" 
            : "bg-chart-2/20 text-chart-2"
        )}
      >
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>

      {/* Message Content */}
      <div
        className={cn(
          "max-w-[85%] rounded-2xl flex flex-col gap-2",
          isUser
            ? "bg-primary text-primary-foreground px-4 py-3 rounded-tr-sm"
            : "bg-card/60 border border-border/50 px-4 py-3 rounded-tl-sm"
        )}
      >
        {isUser && message.file && (
          <div className="flex items-center gap-2 p-2 rounded-lg bg-primary-foreground/10 border border-primary-foreground/20">
            <FileText size={16} className="text-primary-foreground" />
            <span className="text-sm text-primary-foreground flex-1 truncate font-medium">{message.file.name}</span>
          </div>
        )}
        
        {isUser ? (
          <p className="text-sm leading-relaxed">{message.content}</p>
        ) : (
          <BotMessage message={message} />
        )}
      </div>
    </div>
  );
}
