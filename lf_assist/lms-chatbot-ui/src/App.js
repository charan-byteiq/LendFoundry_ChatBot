import React from 'react';
import './App.css';
import Chatbot from './components/Chatbot';

function App() {
  return (
    <div className="app-wrapper">
      <h1 className="chat-title">LMS Chatbot</h1>
      <Chatbot />
    </div>
  );
}

export default App;
