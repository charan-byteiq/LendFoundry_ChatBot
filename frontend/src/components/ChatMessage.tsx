import { cn } from '@/lib/utils';
import { Message } from '@/types/chat';
import { BotMessage } from './BotMessage';
import { Bot, User } from 'lucide-react';

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
          "max-w-[85%] rounded-2xl",
          isUser
            ? "bg-primary text-primary-foreground px-4 py-3 rounded-tr-sm"
            : "bg-card/60 border border-border/50 px-4 py-3 rounded-tl-sm"
        )}
      >
        {isUser ? (
          <p className="text-sm leading-relaxed">{message.content}</p>
        ) : (
          <BotMessage message={message} />
        )}
      </div>
    </div>
  );
}
