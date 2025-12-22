import { useState, useRef, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { Database, Zap } from 'lucide-react';
import { Message } from '@/types/chat';
import { sendChatMessage } from '@/services/api';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { TypingIndicator } from './TypingIndicator';
import { useToast } from '@/hooks/use-toast';

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSendMessage = async (content: string, file?: File) => {
    const userMessage: Message = {
      id: uuidv4(),
      role: 'user',
      content,
      timestamp: new Date(),
      file,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await sendChatMessage(content, sessionId, file);

      // Update session ID from response
      if (response.session_id) {
        setSessionId(response.session_id);
      }

      const assistantMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: response.answer || 'Here are the results:',
        timestamp: new Date(),
        response,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      
      toast({
        title: "Connection Error",
        description: "Could not connect to the server. Please ensure the backend is running on localhost:8000",
        variant: "destructive",
      });

      const errorMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: 'Failed to connect to the server.',
        timestamp: new Date(),
        response: {
          backend: 'scope_guard',
          answer: 'Failed to connect to the server.',
          session_id: sessionId || '',
          error: 'Could not connect to the server. Please ensure the backend is running on localhost:8000',
        },
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-background">
      {/* Header */}
      <header className="flex-shrink-0 border-b border-border bg-card/80 backdrop-blur-xl">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img 
              src="/lendfoundry.png" 
              alt="Lendfoundry" 
              className="h-12 object-contain"
            />
            {/* <div>
              <h1 className="text-lg font-semibold text-foreground">Lendfoundry Assistant</h1>
              <p className="text-xs text-muted-foreground">AI-powered data & document assistant</p>
            </div> */}
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10 border border-primary/20">
            <Zap size={14} className="text-primary" />
            <span className="text-xs font-medium text-primary">AI Powered</span>
          </div>
        </div>
      </header>

      {/* Messages Area */}
      <main className="flex-1 overflow-y-auto scrollbar-thin">
        <div className="max-w-4xl mx-auto px-4 py-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
              <div className="w-20 h-20 rounded-2xl bg-primary/10 flex items-center justify-center mb-6 shadow-glow">
                <Database className="w-10 h-10 text-primary" />
              </div>
              <h2 className="text-2xl font-semibold text-foreground mb-2">
                Ask anything about your data
              </h2>
              <p className="text-muted-foreground max-w-md mb-8">
                I can help you with company policies, query your database, analyze documents, 
                and create visualizations from your data.
              </p>
              <div className="flex flex-wrap justify-center gap-2 max-w-2xl">
                {[
                  "Show total funded amount by loan product",
                  "Top 10 delinquent loans",
                  "Loan onboarding trend by month",
                  "Compare Q1 vs Q2 performance",
                ].map((example, index) => (
                  <button
                    key={index}
                    onClick={() => handleSendMessage(example)}
                    className="px-4 py-2 text-sm rounded-full bg-card border border-border/50 
                               hover:bg-primary/10 hover:border-primary/30 hover:text-primary
                               transition-all text-muted-foreground"
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
              {isLoading && <TypingIndicator />}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </main>

      {/* Input Area */}
      <ChatInput onSend={handleSendMessage} isLoading={isLoading} />
    </div>
  );
}
