import React from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { LayoutDashboard, FileText, MessageSquare } from 'lucide-react';

import Analytics from './pages/Analytics';
import DocumentManagement from './pages/DocumentManagement';
import Assistant from './pages/Assistant';
import './index.css';

function Sidebar() {
  return (
    <div className="sidebar">
      <h1>Tech AI Assistant</h1>
      <nav className="nav-links">
        <NavLink to="/" className={({isActive}) => isActive ? "nav-link active" : "nav-link"} end>
          <LayoutDashboard size={20} />
          <span>Analytics</span>
        </NavLink>
        <NavLink to="/documents" className={({isActive}) => isActive ? "nav-link active" : "nav-link"}>
          <FileText size={20} />
          <span>Documents</span>
        </NavLink>
        <NavLink to="/assistant" className={({isActive}) => isActive ? "nav-link active" : "nav-link"}>
          <MessageSquare size={20} />
          <span>AI Assistant</span>
        </NavLink>
      </nav>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="app-container">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Analytics />} />
            <Route path="/documents" element={<DocumentManagement />} />
            <Route path="/assistant" element={<Assistant />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
