import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, Database, FileText, CheckCircle } from 'lucide-react';

export default function Analytics() {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    const fetchStats = async () => {
        try {
            const res = await fetch('/api/stats');
            if (res.ok) {
                const data = await res.json();
                setStats(data);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStats();
        // Refresh every 5 seconds
        const interval = setInterval(fetchStats, 5000);
        return () => clearInterval(interval);
    }, []);

    if (loading || !stats) {
        return <div style={{ padding: '2rem' }}>Loading analytics...</div>;
    }

    const chartData = Object.entries(stats.top_plants || {}).map(([name, count]) => ({
        name,
        count
    }));

    return (
        <div className="fade-in">
            <h2 style={{ marginBottom: '2rem', fontSize: '1.5rem', fontWeight: 600 }}>Analytics Dashboard</h2>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
                <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <div style={{ padding: '1rem', backgroundColor: 'rgba(79, 70, 229, 0.1)', borderRadius: '50%', color: 'var(--primary)' }}>
                        <FileText size={24} />
                    </div>
                    <div>
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Total Documents</p>
                        <h3 style={{ fontSize: '1.5rem' }}>{stats.total_documents}</h3>
                    </div>
                </div>
                <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <div style={{ padding: '1rem', backgroundColor: 'rgba(16, 185, 129, 0.1)', borderRadius: '50%', color: 'var(--success)' }}>
                        <Database size={24} />
                    </div>
                    <div>
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Total Indexed Chunks</p>
                        <h3 style={{ fontSize: '1.5rem' }}>{stats.total_chunks}</h3>
                    </div>
                </div>
                <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <div style={{ padding: '1rem', backgroundColor: 'rgba(239, 68, 68, 0.1)', borderRadius: '50%', color: 'var(--danger)' }}>
                        <Activity size={24} />
                    </div>
                    <div>
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Total Queries Asked</p>
                        <h3 style={{ fontSize: '1.5rem' }}>{stats.total_queries}</h3>
                    </div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 1fr', gap: '2rem', marginBottom: '2rem' }}>
                <div className="card">
                    <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem' }}>Top Plants by Documents</h3>
                    <div style={{ height: '250px' }}>
                        {chartData.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={chartData}>
                                    <XAxis dataKey="name" stroke="var(--text-muted)" />
                                    <YAxis stroke="var(--text-muted)" allowDecimals={false} />
                                    <Tooltip cursor={{ fill: 'rgba(255,255,255,0.05)' }} contentStyle={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px' }} />
                                    <Bar dataKey="count" fill="var(--primary)" radius={[4, 4, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        ) : <p style={{ color: 'var(--text-muted)' }}>No data available.</p>}
                    </div>
                </div>
                <div className="card">
                    <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem' }}>Last 10 Questions</h3>
                    <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        {stats.recent_queries.map((q, i) => (
                            <li key={i} style={{ display: 'flex', gap: '1rem', paddingBottom: '0.75rem', borderBottom: '1px solid var(--border)' }}>
                                <CheckCircle size={18} color="var(--success)" style={{ flexShrink: 0, marginTop: '2px' }} />
                                <div>
                                    <p style={{ fontSize: '0.9rem' }}>{q.filename}</p>
                                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                        {new Date(q.timestamp).toLocaleString()} • Scope: {q.plant}
                                    </span>
                                </div>
                            </li>
                        ))}
                        {stats.recent_queries.length === 0 && <p style={{ color: 'var(--text-muted)' }}>No queries yet.</p>}
                    </ul>
                </div>
            </div>

            <div className="card">
                <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem' }}>Log Viewer</h3>
                <div style={{ overflowX: 'auto' }}>
                    <table>
                        <thead>
                            <tr>
                                <th>Timestamp</th>
                                <th>Plant</th>
                                <th>Filename/Query</th>
                                <th>Action</th>
                                <th>Status</th>
                                <th>Latency (ms)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {stats.logs.map((log, i) => (
                                <tr key={i}>
                                    <td>{new Date(log.timestamp).toLocaleString()}</td>
                                    <td>{log.plant}</td>
                                    <td>{log.filename}</td>
                                    <td>
                                        <span style={{
                                            padding: '0.25rem 0.5rem',
                                            borderRadius: '4px',
                                            fontSize: '0.75rem',
                                            backgroundColor: log.action === 'upload' ? 'rgba(16, 185, 129, 0.1)' : log.action === 'delete' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(79, 70, 229, 0.1)',
                                            color: log.action === 'upload' ? 'var(--success)' : log.action === 'delete' ? 'var(--danger)' : 'var(--primary)'
                                        }}>
                                            {log.action.toUpperCase()}
                                        </span>
                                    </td>
                                    <td>
                                        <span style={{ color: log.status === 'success' ? 'var(--success)' : 'var(--danger)' }}>
                                            {log.status}
                                        </span>
                                    </td>
                                    <td>{log.latency_ms}</td>
                                </tr>
                            ))}
                            {stats.logs.length === 0 && (
                                <tr>
                                    <td colSpan="6" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No logs available.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
