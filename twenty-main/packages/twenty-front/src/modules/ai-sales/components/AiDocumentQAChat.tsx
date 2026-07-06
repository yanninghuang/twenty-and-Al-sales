import React, { useState, useEffect, useRef } from 'react';
import {
  aiDocumentQAClient,
  aiKnowledgeBaseClient,
} from '@/ai-sales/services/aiBackendClient';
import type { QAConversation, QAMessage, QADocument } from '@/ai-sales/types/ai-sales.types';
import type { KnowledgeQueryResponse } from '@/ai-sales/types/ai-sales.types';

type QAMode = 'knowledge-base' | 'document-qa';

export const AiDocumentQAChat: React.FC<{ workspaceId: string }> = ({ workspaceId }) => {
  const [mode, setMode] = useState<QAMode>('knowledge-base');
  const [documents, setDocuments] = useState<QADocument[]>([]);
  const [conversation, setConversation] = useState<QAConversation | null>(null);
  const [conversations, setConversations] = useState<QAConversation[]>([]);
  const [messages, setMessages] = useState<QAMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Document QA mode
  const [docText, setDocText] = useState('');
  const [docTitle, setDocTitle] = useState('');

  useEffect(() => {
    if (mode === 'document-qa') {
      aiDocumentQAClient.listDocuments(workspaceId).then((r) => setDocuments(r.documents));
      aiDocumentQAClient.listConversations(workspaceId).then((r) => setConversations(r.conversations));
    }
  }, [workspaceId, mode]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleKnowledgeBaseQuery = async () => {
    if (!input.trim()) return;
    const userMsg: QAMessage = {
      id: `temp-${Date.now()}`,
      conversationId: 'kb',
      role: 'user',
      content: input,
      citations: [],
      createdAt: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const result = await aiKnowledgeBaseClient.query(workspaceId, input);
      const assistantMsg: QAMessage = {
        id: `temp-${Date.now() + 1}`,
        conversationId: 'kb',
        role: 'assistant',
        content: result.answer,
        citations: result.sources.map((s) => ({
          chunkId: s.chunk_id,
          documentTitle: s.document_title,
          excerpt: s.excerpt,
        })),
        createdAt: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `temp-${Date.now() + 1}`,
          conversationId: 'kb',
          role: 'assistant',
          content: '抱歉，搜索知识库时发生错误。',
          citations: [],
          createdAt: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleDocumentUpload = async () => {
    if (!docText.trim() || !docTitle.trim()) return;
    setUploading(true);
    try {
      await aiDocumentQAClient.uploadDocument(workspaceId, {
        title: docTitle,
        contentText: docText,
        fileType: 'txt',
      });
      setDocText('');
      setDocTitle('');
      const r = await aiDocumentQAClient.listDocuments(workspaceId);
      setDocuments(r.documents);
    } finally {
      setUploading(false);
    }
  };

  const handleStartConversation = async (documentIds: string[]) => {
    try {
      const conv = await aiDocumentQAClient.createConversation(workspaceId, documentIds, 'Document Q&A');
      setConversation(conv);
      setMessages(conv.messages || []);
    } catch {
      // Handle error
    }
  };

  const handleSendDocumentMessage = async () => {
    if (!input.trim() || !conversation) return;
    const userMsg: QAMessage = {
      id: `temp-${Date.now()}`,
      conversationId: conversation.id,
      role: 'user',
      content: input,
      citations: [],
      createdAt: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const response = await aiDocumentQAClient.sendMessage(workspaceId, conversation.id, input);
      setMessages((prev) => [...prev, response]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `temp-${Date.now() + 1}`,
          conversationId: conversation.id,
          role: 'assistant',
          content: '抱歉，回答问题时发生错误。',
          citations: [],
          createdAt: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = () => {
    if (mode === 'knowledge-base') {
      handleKnowledgeBaseQuery();
    } else {
      handleSendDocumentMessage();
    }
  };

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 120px)', border: '1px solid #e0e0e0', borderRadius: 8, overflow: 'hidden' }}>
      {/* Sidebar */}
      <div style={{ width: 260, borderRight: '1px solid #e0e0e0', padding: 16, overflowY: 'auto' }}>
        {/* Mode selector */}
        <div style={{ marginBottom: 16 }}>
          <select
            value={mode}
            onChange={(e) => {
              setMode(e.target.value as QAMode);
              setMessages([]);
              setConversation(null);
            }}
            style={{ width: '100%', padding: '6px 8px', borderRadius: 4, border: '1px solid #ccc' }}
          >
            <option value="knowledge-base">知识库</option>
            <option value="document-qa">文档问答</option>
          </select>
        </div>

        {mode === 'knowledge-base' && (
          <div>
            <h5 style={{ fontSize: 13, marginBottom: 8 }}>知识库</h5>
            <p style={{ fontSize: 11, color: '#888' }}>
              向企业知识库提问。上传文档到知识库即可开始使用。
            </p>
          </div>
        )}

        {mode === 'document-qa' && (
          <div>
            <h5 style={{ fontSize: 13, marginBottom: 8 }}>上传文档</h5>
            <input
              type="text"
              placeholder="文档标题"
              value={docTitle}
              onChange={(e) => setDocTitle(e.target.value)}
              style={{ width: '100%', padding: '5px 8px', marginBottom: 6, fontSize: 12, border: '1px solid #ccc', borderRadius: 4 }}
            />
            <textarea
              placeholder="粘贴文档文本..."
              value={docText}
              onChange={(e) => setDocText(e.target.value)}
              rows={5}
              style={{ width: '100%', padding: '6px 8px', marginBottom: 6, fontSize: 12, border: '1px solid #ccc', borderRadius: 4, resize: 'vertical' }}
            />
            <button
              onClick={handleDocumentUpload}
              disabled={uploading}
              style={{
                width: '100%',
                padding: '6px 12px',
                fontSize: 12,
                background: '#1967d2',
                color: '#fff',
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer',
              }}
            >
              {uploading ? '上传中...' : '上传'}
            </button>

            <h5 style={{ fontSize: 13, marginTop: 16, marginBottom: 8 }}>Documents ({documents.length})</h5>
            {documents.slice(0, 10).map((doc) => (
              <div
                key={doc.id}
                onClick={() => handleStartConversation([doc.id])}
                style={{
                  padding: '6px 8px',
                  fontSize: 12,
                  cursor: 'pointer',
                  borderRadius: 4,
                  background: conversation?.document_ids.includes(doc.id) ? '#e8f0fe' : 'transparent',
                  marginBottom: 4,
                }}
              >
                {doc.title}
              </div>
            ))}

            {conversations.length > 0 && (
              <>
                <h5 style={{ fontSize: 13, marginTop: 16, marginBottom: 8 }}>对话记录</h5>
                {conversations.map((c) => (
                  <div
                    key={c.id}
                    onClick={async () => {
                      const full = await aiDocumentQAClient.getConversation(workspaceId, c.id);
                      setConversation(full);
                      setMessages(full.messages);
                    }}
                    style={{
                      padding: '6px 8px',
                      fontSize: 12,
                      cursor: 'pointer',
                      borderRadius: 4,
                      background: conversation?.id === c.id ? '#e8f0fe' : 'transparent',
                      marginBottom: 4,
                    }}
                  >
                    {c.title || `Conversation ${c.id.slice(0, 8)}`}
                  </div>
                ))}
              </>
            )}
          </div>
        )}
      </div>

      {/* Chat area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Messages */}
        <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
          {messages.length === 0 && (
            <div style={{ textAlign: 'center', padding: 40, color: '#888' }}>
              <h3>AI 问答助手</h3>
              <p>
                {mode === 'knowledge-base'
                  ? '提出关于业务知识的问题'
                  : '上传文档后提出相关问题'}
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              style={{
                marginBottom: 12,
                display: 'flex',
                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
              }}
            >
              <div
                style={{
                  maxWidth: '80%',
                  padding: '10px 14px',
                  borderRadius: 8,
                  background: msg.role === 'user' ? '#1967d2' : '#f0f0f0',
                  color: msg.role === 'user' ? '#fff' : '#333',
                  fontSize: 13,
                  lineHeight: 1.5,
                }}
              >
                <div>{msg.content}</div>
                {msg.citations && msg.citations.length > 0 && (
                  <div
                    style={{
                      marginTop: 8,
                      paddingTop: 8,
                      borderTop: '1px solid rgba(0,0,0,0.1)',
                      fontSize: 11,
                    }}
                  >
                    <strong>来源：</strong>
                    {msg.citations.map((c, i) => (
                      <div key={i} style={{ marginTop: 2 }}>
                        [{i + 1}] {c.document_title || '文档'} — "{c.excerpt.slice(0, 100)}..."
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div style={{ padding: 12, borderTop: '1px solid #e0e0e0', display: 'flex', gap: 8 }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder={
              mode === 'knowledge-base'
                ? '向知识库提问...'
                : !conversation
                  ? '请先选择文档以开始对话'
                  : '询问关于文档的问题...'
            }
            disabled={mode === 'document-qa' && !conversation}
            style={{ flex: 1, padding: '8px 12px', border: '1px solid #ccc', borderRadius: 4, fontSize: 13 }}
          />
          <button
            onClick={handleSend}
            disabled={loading || (mode === 'document-qa' && !conversation)}
            style={{
              padding: '8px 20px',
              background: '#1967d2',
              color: '#fff',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              fontSize: 13,
            }}
          >
            {loading ? '...' : '发送'}
          </button>
        </div>
      </div>
    </div>
  );
};
