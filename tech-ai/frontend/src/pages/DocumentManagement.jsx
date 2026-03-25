import React, { useState, useEffect } from 'react';
import { Upload, Trash2, Search, Filter, Loader } from 'lucide-react';

const ALLOWED_PLANTS = ["JEP", "GF1", "M5"];

export default function DocumentManagement() {
    const [documents, setDocuments] = useState([]);
    const [plant, setPlant] = useState("JEP");
    const [filterPlant, setFilterPlant] = useState("All");
    const [searchQuery, setSearchQuery] = useState("");
    const [uploading, setUploading] = useState(false);
    const [toast, setToast] = useState(null);

    const fetchDocuments = async () => {
        try {
            const res = await fetch('/api/documents');
            if (res.ok) setDocuments(await res.json());
        } catch (e) {
            console.error(e);
        }
    };

    useEffect(() => {
        fetchDocuments();
    }, []);

    const showToast = (msg, isError = false) => {
        setToast({ msg, isError });
        setTimeout(() => setToast(null), 4000);
    };

    const handleUpload = async (e) => {
        if (!e.target.files.length) return;
        setUploading(true);

        // Upload sequentially to show reliable individual status but we allow multiple select
        const files = Array.from(e.target.files);

        for (const file of files) {
            const formData = new FormData();
            formData.append("file", file);
            formData.append("plant", plant);

            try {
                const res = await fetch('/api/documents/upload', {
                    method: 'POST',
                    body: formData
                });

                if (res.ok) {
                    showToast(`Successfully uploaded ${file.name}`);
                } else {
                    const err = await res.json();
                    showToast(`Failed defining ${file.name}: ${err.detail || 'Error'}`, true);
                }
            } catch (err) {
                showToast(`Network error on ${file.name}`, true);
            }
        }

        setUploading(false);
        fetchDocuments();
        e.target.value = null; // reset
    };

    const handleDelete = async (docPlant, filename) => {
        if (!confirm(`Are you sure you want to delete ${filename}?`)) return;

        try {
            const res = await fetch(`/api/documents/${docPlant}/${filename}`, {
                method: 'DELETE'
            });
            if (res.ok) {
                showToast(`Deleted ${filename}`);
                fetchDocuments();
            } else {
                showToast(`Failed to delete ${filename}`, true);
            }
        } catch (e) {
            showToast('Network error on delete', true);
        }
    };

    const formatSize = (bytes) => {
        if (bytes === 0) return '0 B';
        const k = 1024, sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const filteredDocs = documents.filter(d => {
        const matchPlant = filterPlant === "All" || d.plant === filterPlant;
        const matchSearch = d.filename.toLowerCase().includes(searchQuery.toLowerCase());
        return matchPlant && matchSearch;
    });

    return (
        <div>
            <h2 style={{ marginBottom: '2rem', fontSize: '1.5rem', fontWeight: 600 }}>Document Management</h2>

            <div className="card" style={{ marginBottom: '2rem' }}>
                <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem' }}>Upload Knowledge</h3>
                <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
                    Select the targeted Plant context, then upload relevant technical manuals or drawings to automatically index.
                </p>

                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <select
                        className="form-control"
                        style={{ width: '150px' }}
                        value={plant}
                        onChange={(e) => setPlant(e.target.value)}
                    >
                        {ALLOWED_PLANTS.map(p => <option key={p} value={p}>{p}</option>)}
                    </select>

                    <label className="btn-primary" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', opacity: uploading ? 0.7 : 1 }}>
                        {uploading ? <Loader className="animate-spin" size={18} /> : <Upload size={18} />}
                        {uploading ? 'Uploading...' : 'Upload Files'}
                        <input type="file" multiple style={{ display: 'none' }} onChange={handleUpload} disabled={uploading} accept=".pdf,.doc,.docx,.xls,.xlsx,.csv,.txt,.ppt,.pptx,.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff,.md,.json,.xml,.html,.htm,.rtf" />
                    </label>
                </div>
            </div>

            <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
                    <h3 style={{ fontSize: '1.1rem' }}>Indexed Documents</h3>
                    <div style={{ display: 'flex', gap: '1rem' }}>
                        <div style={{ position: 'relative' }}>
                            <Filter size={16} style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--text-muted)' }} />
                            <select
                                className="form-control"
                                style={{ paddingLeft: '2.2rem', width: '130px' }}
                                value={filterPlant}
                                onChange={(e) => setFilterPlant(e.target.value)}
                            >
                                <option value="All">All Plants</option>
                                {ALLOWED_PLANTS.map(p => <option key={p} value={p}>{p}</option>)}
                            </select>
                        </div>
                        <div style={{ position: 'relative' }}>
                            <Search size={16} style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--text-muted)' }} />
                            <input
                                type="text"
                                placeholder="Search filename..."
                                className="form-control"
                                style={{ paddingLeft: '2.2rem' }}
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                            />
                        </div>
                    </div>
                </div>

                <div style={{ overflowX: 'auto' }}>
                    <table>
                        <thead>
                            <tr>
                                <th>Plant</th>
                                <th>Filename</th>
                                <th>Type</th>
                                <th>Size</th>
                                <th>Upload Date</th>
                                <th>Status</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredDocs.map((doc, i) => (
                                <tr key={i}>
                                    <td><span style={{ fontWeight: 600, color: 'var(--text-main)' }}>{doc.plant}</span></td>
                                    <td>{doc.filename}</td>
                                    <td>{doc.type}</td>
                                    <td>{formatSize(doc.size_bytes)}</td>
                                    <td>{new Date(doc.upload_date).toLocaleDateString()}</td>
                                    <td><span style={{ color: 'var(--success)', fontSize: '0.85rem' }}>Indexed</span></td>
                                    <td>
                                        <button className="btn-danger" onClick={() => handleDelete(doc.plant, doc.filename)}>
                                            <Trash2 size={16} />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                            {filteredDocs.length === 0 && (
                                <tr>
                                    <td colSpan="7" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No documents found.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {toast && (
                <div className="toast-container">
                    <div className={`toast ${toast.isError ? 'error' : 'success'}`}>
                        {toast.msg}
                    </div>
                </div>
            )}
        </div>
    );
}
