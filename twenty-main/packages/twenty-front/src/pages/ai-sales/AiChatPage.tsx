import { useState, useRef, useEffect } from 'react';
import { PageContainer } from '@/ui/layout/page/components/PageContainer';
import { currentWorkspaceState } from '@/auth/states/currentWorkspaceState';
import { useAtomStateValue } from '@/ui/utilities/state/jotai/hooks/useAtomStateValue';

const API_BASE = 'http://localhost:8000/api/v1';
const API_HEADERS = {
  'Content-Type': 'application/json',
  'X-AI-Backend-API-Key': 'dev-internal-key-change-in-production',
};

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
};

export const AiChatPage = () => {
  const workspace = useAtomStateValue(currentWorkspaceState);
  const workspaceId = workspace?.id || 'demo';
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [conversations, setConversations] = useState<Array<{
    conversation_id: string;
    title: string;
    message_count: number;
  }>>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      const r = await fetch(`${API_BASE}/workspaces/${workspaceId}/chat/conversations`, {
        headers: API_HEADERS,
      });
      if (r.ok) setConversations(await r.json());
    } catch { /* ignore */ }
  };

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: ChatMessage = { id: Date.now().toString(), role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const r = await fetch(`${API_BASE}/workspaces/${workspaceId}/chat`, {
        method: 'POST',
        headers: API_HEADERS,
        body: JSON.stringify({ message: text, conversation_id: conversationId }),
      });
      if (!r.ok) throw new Error(await r.text());
      const d = await r.json();
      setConversationId(d.conversation_id);
      const assistantMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: d.message,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      loadConversations();
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { id: (Date.now() + 1).toString(), role: 'assistant', content: `Error: ${(e as Error).message}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const loadConversation = async (convId: string) => {
    setConversationId(convId);
    try {
      const r = await fetch(`${API_BASE}/workspaces/${workspaceId}/chat/conversations/${convId}`, {
        headers: API_HEADERS,
      });
      if (r.ok) setMessages(await r.json());
    } catch { /* ignore */ }
  };

  const newConversation = () => {
    setConversationId(null);
    setMessages([]);
  };

  return (
    <PageContainer>
      <div style={{ display: 'flex', height: 'calc(100vh - 64px)', gap: 0 }}>
        {/* Conversation sidebar */}
        <div style={{ width: 260, borderRight: '1px solid #e0e0e0', padding: 16, overflowY: 'auto' }}>
          <button
            onClick={newConversation}
            style={{
              width: '100%', padding: '8px 16px', marginBottom: 12,
              background: '#1967d2', color: '#fff', border: 'none',
              borderRadius: 6, cursor: 'pointer', fontSize: 14,
            }}
          >
            + 新建对话
          </button>
          {conversations.map((c) => (
            <div
              key={c.conversation_id}
              onClick={() => loadConversation(c.conversation_id)}
              style={{
                padding: '8px 10px', cursor: 'pointer', borderRadius: 6,
                marginBottom: 4, fontSize: 13,
                background: c.conversation_id === conversationId ? '#e8f0fe' : 'transparent',
              }}
            >
              <div style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {c.title}
              </div>
              <div style={{ fontSize: 11, color: '#999' }}>{c.message_count} 条消息</div>
            </div>
          ))}
        </div>

        {/* Chat area */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
            {messages.length === 0 && (
              <div style={{ textAlign: 'center', padding: 80, color: '#999' }}>
                <div style={{ fontSize: 48, marginBottom: 16 }}>🤖</div>
                <h2>AI 销售助手</h2>
                <p>询问关于销售、客户或 CRM 的任何问题</p>
              </div>
            )}
            {messages.map((msg) => (
              <div
                key={msg.id}
                style={{
                  display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  marginBottom: 12,
                }}
              >
                <div
                  style={{
                    maxWidth: '75%', padding: '10px 16px', borderRadius: 12,
                    background: msg.role === 'user' ? '#1967d2' : '#f1f3f4',
                    color: msg.role === 'user' ? '#fff' : '#333',
                    fontSize: 14, lineHeight: 1.5, whiteSpace: 'pre-wrap',
                  }}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {loading && (
              <div style={{ textAlign: 'left', padding: 8, color: '#999' }}>思考中...</div>
            )}
            <div ref={messagesEndRef} />
          </div>
          <div style={{ padding: 16, borderTop: '1px solid #e0e0e0', display: 'flex', gap: 8 }}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="输入消息..."
              disabled={loading}
              style={{
                flex: 1, padding: '10px 14px', border: '1px solid #ddd',
                borderRadius: 8, fontSize: 14, outline: 'none',
              }}
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              style={{
                padding: '10px 24px', background: '#1967d2', color: '#fff',
                border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 14,
              }}
            >
              发送
            </button>
          </div>
        </div>
      </div>
    </PageContainer>
  );
};
