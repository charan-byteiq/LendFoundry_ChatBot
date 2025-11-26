import React, { useState, useEffect, useRef } from 'react';
import './Chatbot.css';

function Chatbot() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const chatEndRef = useRef(null); // 👈 add ref to scroll to bottom

  // Scroll to bottom when messages update
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Initial welcome message
  useEffect(() => {
    setMessages([{ type: 'bot', text: 'Hi! Ask me anything about LMS.' }]);
  }, []);

  // Send user message and get response from backend
  const sendMessage = async () => {
    if (!input.trim()) return;

    const newMessages = [...messages, { type: 'user', text: input }];
    setMessages(newMessages);
    setInput('');

    try {
      const res = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: input }),
      });

      const data = await res.json();
      setMessages([...newMessages, { type: 'bot', text: data.answer }]);
    } catch (error) {
      setMessages([
        ...newMessages,
        { type: 'bot', text: 'Sorry, something went wrong. Please try again.' },
      ]);
    }
  };

  return (
    <div className="chatbot-container">
      <div className="chat-window">
        {messages.map((msg, index) => (
          <div key={index} className={`chat-message ${msg.type}`}>
            <div className="message-bubble" style={{ whiteSpace: 'pre-line' }}>
              {msg.text}
            </div>
          </div>
        ))}
        {/* 👇 This will scroll into view whenever messages update */}
        <div ref={chatEndRef} />
      </div>

      <div className="input-area">
        <input
          type="text"
          value={input}
          placeholder="Type your question..."
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
        />
        <button onClick={sendMessage}>Send</button>
      </div>
    </div>
  );
}

export default Chatbot;
