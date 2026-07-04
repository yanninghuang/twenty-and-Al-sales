import { useState, useEffect, useRef } from 'react';
import { PageContainer } from '@/ui/layout/page/components/PageContainer';
import { currentWorkspaceState } from '@/auth/states/currentWorkspaceState';
import { useAtomStateValue } from '@/ui/utilities/state/jotai/hooks/useAtomStateValue';

const API_BASE = 'http://localhost:8000/api/v1';
const API_HEADERS = {
  'X-AI-Backend-API-Key': 'dev-internal-key-change-in-production',
};

type KBDocument = {
  id: string;
  title: string;
  source_type: string;
  created_at: string;
};

type QuerySource = {
  chunk_id: string;
  document_title: string;
  excerpt: string;
  score: number;
};

export const AiKnowledgeBasePage = () => {
  const workspace = useAtomStateValue(currentWorkspaceState);
  const workspaceId = workspace?.id || 'demo';
  const [documents, setDocuments] = useState<KBDocument[]>([]);
  const [messages, setMessages] = useState<Array<{ role: string; content: string; sources?: QuerySource[] }>>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => { loadDocuments(); }, []);

  const loadDocuments = async () => {
    try {
      const r = await fetch(`${API_BASE}/workspaces/${workspaceId}/knowledge-base/documents`, {
        headers: API_HEADERS,
      });
      if (r.ok) {
        const d = await r.json();
        setDocuments(d.documents);
      }
    } catch { /* ignore */ }
  };

  const handleFileUpload = async (file: File) => {
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const r = await fetch(`${API_BASE}/workspaces/${workspaceId}/knowledge-base/documents/upload`, {
        method: 'POST',
        headers: { 'X-AI-Backend-API-Key': API_HEADERS['X-AI-Backend-API-Key'] },
        body: fd,
      });
      if (!r.ok) throw new Error(await r.text());
      await loadDocuments();
    } catch (e) {
      alert('上传失败：' + (e as Error).message);
    } finally {
      setUploading(false);
    }
  };

  const deleteDocument = async (id: string) => {
    try {
      await fetch(`${API_BASE}/workspaces/${workspaceId}/knowledge-base/documents/${id}`, {
        method: 'DELETE',
        headers: API_HEADERS,
      });
      await loadDocuments();
    } catch { /* ignore */ }
  };

  const sendQuery = async () => {
    const text = input.trim();
    if (!text || loading) return;

    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setInput('');
    setLoading(true);

    try {
      const r = await fetch(`${API_BASE}/workspaces/${workspaceId}/knowledge-base/query`, {
        method: 'POST',
        headers: { ...API_HEADERS, 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text, top_k: 5 }),
      });
      if (!r.ok) throw new Error(await r.text());
      const d = await r.json();
      setMessages((prev) => [...prev, { role: 'assistant', content: d.answer, sources: d.sources }]);
    } catch (e) {
      setMessages((prev) => [...prev, { role: 'assistant', content: `Error: ${(e as Error).message}` }]);
    } finally {
      setLoading(false);
    }
  };

  const formatSize = (type: string) => type.toUpperCase();

  return (
    <PageContainer>
      <div style={{ display: 'flex', height: 'calc(100vh - 64px)', gap: 0 }}>
        {/* Sidebar */}
        <div style={{ width: 300, borderRight: '1px solid #e0e0e0', padding: 16, overflowY: 'auto' }}>
          <h3 style={{ fontSize: 16, marginBottom: 12 }}>📚 Knowledge Base</h3>

          {/* Upload zone */}
          <div
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: '2px dashed #ccc', borderRadius: 8, padding: 20,
              textAlign: 'center', cursor: 'pointer', marginBottom: 16,
              background: uploading ? '#f0f0f0' : '#fafafa',
            }}
          >
            <div style={{ fontSize: 28, marginBottom: 4 }}>{uploading ? '⏳' : '📤'}</div>
            <div style={{ fontSize: 13, fontWeight: 500 }}>
              {uploading ? '上传中...' : '点击或拖放文件'}
            </div>
            <div style={{ fontSize: 11, color: '#999', marginTop: 4 }}>
              PDF · DOCX · PPTX · XLSX · TXT
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.pptx,.xlsx,.txt,.md,.csv"
              style={{ display: 'none' }}
              onChange={(e) => {
                if (e.target.files?.[0]) handleFileUpload(e.target.files[0]);
                e.target.value = '';
              }}
            />
          </div>

          {/* Document list */}
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
            文档 ({documents.length})
          </div>
          {documents.map((doc) => (
            <div
              key={doc.id}
              style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '6px 8px', border: '1px solid #eee', borderRadius: 4,
                marginBottom: 4, fontSize: 12,
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  <span style={{
                    display: 'inline-block', padding: '0 4px', borderRadius: 3,
                    background: '#e8f0fe', color: '#1967d2', fontSize: 10,
                    fontWeight: 600, marginRight: 4,
                  }}>
                    {formatSize(doc.source_type)}
                  </span>
                  {doc.title}
                </div>
              </div>
              <button
                onClick={() => deleteDocument(doc.id)}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: '#999', fontSize: 14, padding: '2px 6px',
                }}
              >
                🗑
              </button>
            </div>
          ))}
          {documents.length === 0 && (
            <div style={{ textAlign: 'center', color: '#999', fontSize: 12, padding: 20 }}>
              暂无文档
            </div>
          )}
        </div>

        {/* Chat area */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
            {messages.length === 0 && (
              <div style={{ textAlign: 'center', padding: 80, color: '#999' }}>
                <div style={{ fontSize: 48, marginBottom: 16 }}>📚</div>
                <h2>知识库问答</h2>
                <p>上传文档，然后提问</p>
              </div>
            )}
            {messages.map((msg, i) => (
              <div
                key={i}
                style={{
                  display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  marginBottom: 12,
                }}
              >
                <div
                  style={{
                    maxWidth: '80%', padding: '10px 16px', borderRadius: 12,
                    background: msg.role === 'user' ? '#1967d2' : '#f1f3f4',
                    color: msg.role === 'user' ? '#fff' : '#333',
                    fontSize: 14, lineHeight: 1.5, whiteSpace: 'pre-wrap',
                  }}
                >
                  {msg.content}
                  {msg.sources && msg.sources.length > 0 && (
                    <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid rgba(0,0,0,0.1)', fontSize: 11 }}>
                      📎 Sources:
                      {msg.sources.map((s, j) => (
                        <span key={j} style={{ marginLeft: 6 }}>
                          [{j + 1}] {s.document_title}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && <div style={{ textAlign: 'left', padding: 8, color: '#999' }}>正在搜索知识库...</div>}
            <div ref={messagesEndRef} />
          </div>
          <div style={{ padding: 16, borderTop: '1px solid #e0e0e0', display: 'flex', gap: 8 }}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendQuery()}
              placeholder="询问关于文档的问题..."
              disabled={loading}
              style={{
                flex: 1, padding: '10px 14px', border: '1px solid #ddd',
                borderRadius: 8, fontSize: 14, outline: 'none',
              }}
            />
            <button
              onClick={sendQuery}
              disabled={loading || !input.trim()}
              style={{
                padding: '10px 24px', background: '#1967d2', color: '#fff',
                border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 14,
              }}
            >
              Ask
            </button>
          </div>
        </div>
      </div>
    </PageContainer>
  );
};
