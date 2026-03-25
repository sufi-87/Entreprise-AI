import React, { useState, useRef, useEffect } from 'react';
import { Send, Trash2, Bot, User, Loader2, Download, FileSpreadsheet, FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import * as XLSX from 'xlsx';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

export default function Assistant() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [plantScope, setPlantScope] = useState('All plants');
    const [loading, setLoading] = useState(false);
    const endOfMessagesRef = useRef(null);

    const scrollToBottom = () => endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
    useEffect(() => { scrollToBottom(); }, [messages, loading]);

    const handleSend = async () => {
        if (!input.trim() || loading) return;
        const userMsg = input.trim();
        setInput('');
        const newHistory = [...messages, { role: 'user', content: userMsg }];
        setMessages(newHistory);
        setLoading(true);
        try {
            const recentHistory = messages.slice(-6).map(m => ({ role: m.role, content: m.content }));
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: userMsg, history: recentHistory, plant_scope: plantScope })
            });
            if (res.ok) {
                const data = await res.json();
                setMessages(prev => [...prev, { role: 'assistant', content: data.answer, citations: data.citations, source_links: data.source_links || [] }]);
            } else {
                const err = await res.json();
                setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.detail || 'Internal server error'}` }]);
            }
        } catch (e) {
            setMessages(prev => [...prev, { role: 'assistant', content: `Network error: ${e.message}` }]);
        } finally {
            setLoading(false);
        }
    };

    const handleClear = () => {
        if (confirm('Clear current conversational memory?')) setMessages([]);
    };

    const exportToExcel = () => {
        const rows = messages.map((m, idx) => ({
            No: idx + 1,
            Role: m.role,
            Message: m.content,
            Sources: (m.source_links || []).map(s => s.label).join(' | '),
            SourceURLs: (m.source_links || []).map(s => s.url).join(' | '),
        }));
        const ws = XLSX.utils.json_to_sheet(rows);
        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, 'Chat Export');
        XLSX.writeFile(wb, `tech-ai-chat-${new Date().toISOString().slice(0,19).replace(/[:T]/g,'-')}.xlsx`);
    };

    const exportToPdf = () => {
        const doc = new jsPDF();
        doc.setFontSize(14);
        doc.text('Tech.AI Chat Export', 14, 15);
        doc.setFontSize(10);
        doc.text(`Scope: ${plantScope}`, 14, 22);
        autoTable(doc, {
            startY: 28,
            head: [['No', 'Role', 'Message', 'Sources']],
            body: messages.map((m, idx) => [idx + 1, m.role, m.content, (m.source_links || []).map(s => s.label).join(' | ')]),
            styles: { fontSize: 8, cellWidth: 'wrap' },
            columnStyles: { 2: { cellWidth: 90 }, 3: { cellWidth: 50 } }
        });
        doc.save(`tech-ai-chat-${new Date().toISOString().slice(0,19).replace(/[:T]/g,'-')}.pdf`);
    };

    return (
        <div style={{ height: 'calc(100vh - 4rem)', display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 250px', gap: '2rem' }}>
            <div className="card" style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: 0 }}>
                <div style={{ padding: '1rem 1.5rem', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                    <div>
                        <h3 style={{ fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Bot color="var(--primary)" /> QA Assistant</h3>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Using hybrid retrieval with clickable source documents</span>
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <button className="btn-primary" onClick={exportToExcel} disabled={messages.length === 0} style={{ padding: '0.3rem 0.6rem', fontSize: '0.8rem' }}>
                            <FileSpreadsheet size={14} style={{ display: 'inline', marginRight: '4px' }} /> Excel
                        </button>
                        <button className="btn-primary" onClick={exportToPdf} disabled={messages.length === 0} style={{ padding: '0.3rem 0.6rem', fontSize: '0.8rem' }}>
                            <FileText size={14} style={{ display: 'inline', marginRight: '4px' }} /> PDF
                        </button>
                        <button className="btn-danger" onClick={handleClear} disabled={messages.length === 0} style={{ padding: '0.3rem 0.6rem', fontSize: '0.8rem' }}>
                            <Trash2 size={14} style={{ display: 'inline', marginRight: '4px' }} /> Clear Chat
                        </button>
                    </div>
                </div>
                <div className="chat-messages">
                    {messages.length === 0 && (
                        <div style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: '4rem' }}>
                            <MessageSquareIcon />
                            <p style={{ marginTop: '1rem' }}>Ask me anything about the technical manuals!</p>
                            <p style={{ fontSize: '0.85rem', opacity: 0.7 }}>Answers are grounded solely on your uploaded documents.</p>
                        </div>
                    )}
                    {messages.map((msg, i) => (
                        <div key={i} className={`message ${msg.role === 'user' ? 'user' : 'assistant'}`}>
                            <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '0.5rem' }}>
                                {msg.role === 'user' ? <User size={18} /> : <Bot size={18} />}
                                <span style={{ fontWeight: 600, fontSize: '0.85rem', opacity: 0.8 }}>{msg.role === 'user' ? 'You' : 'Assistant'}</span>
                            </div>
                            <div style={{ fontSize: '0.95rem', lineHeight: '1.6' }}><ReactMarkdown>{msg.content}</ReactMarkdown></div>
                            {msg.role === 'assistant' && msg.source_links && msg.source_links.length > 0 && (
                                <div style={{ marginTop: '1rem', paddingTop: '0.5rem', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                                    <p style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.5rem' }}>SOURCES:</p>
                                    <ul style={{ listStyle: 'circle', paddingLeft: '1.5rem', margin: 0 }}>
                                        {msg.source_links.map((src, idx) => (
                                            <li key={idx} style={{ fontSize: '0.8rem', marginBottom: '0.35rem' }}>
                                                <a href={src.url} target="_blank" rel="noreferrer" style={{ color: 'var(--primary)', textDecoration: 'underline' }}>{src.label}</a>
                                                {src.page_num ? <span style={{ color: 'var(--text-muted)' }}> • page {src.page_num}</span> : null}
                                                {src.source_type ? <span style={{ color: 'var(--text-muted)' }}> • {src.source_type}</span> : null}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    ))}
                    {loading && <div className="message assistant" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}><Loader2 className="animate-spin" size={16} /> Thinking...</div>}
                    <div ref={endOfMessagesRef} />
                </div>
                <div className="chat-input-area">
                    <textarea
                        className="form-control"
                        style={{ resize: 'none', height: '50px', flex: 1 }}
                        placeholder="Type your technical question here..."
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                    />
                    <button className="btn-primary" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '60px' }} onClick={handleSend} disabled={loading || !input.trim()}>
                        <Send size={20} />
                    </button>
                </div>
            </div>
            <div className="card" style={{ height: 'fit-content' }}>
                <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem' }}>Knowledge Scope</h3>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '1rem' }}>Select which specific plant manuals you want the AI to retrieve context from.</p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {["All plants", "JEP", "GF1", "M5"].map(scope => (
                        <label key={scope} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', padding: '0.5rem', borderRadius: '4px', backgroundColor: plantScope === scope ? 'rgba(79, 70, 229, 0.1)' : 'transparent', border: plantScope === scope ? '1px solid var(--primary)' : '1px solid transparent' }}>
                            <input type="radio" name="plantScope" value={scope} checked={plantScope === scope} onChange={() => setPlantScope(scope)} style={{ cursor: 'pointer' }} />
                            {scope}
                        </label>
                    ))}
                </div>
            </div>
        </div>
    );
}

function MessageSquareIcon() {
    return <div style={{ margin: '0 auto', width: '64px', height: '64px', backgroundColor: 'rgba(79, 70, 229, 0.1)', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary)' }}><svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg></div>;
}
