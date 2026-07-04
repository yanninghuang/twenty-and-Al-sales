import React, { useState, useEffect } from 'react';
import { aiSalesSuggestionsClient } from '@/ai-sales/services/aiBackendClient';
import type { SalesSuggestion } from '@/ai-sales/types/ai-sales.types';

export const AiSalesSuggestionsList: React.FC<{
  workspaceId: string;
  targetType?: string;
  targetId?: string;
  limit?: number;
}> = ({ workspaceId, targetType, targetId, limit = 10 }) => {
  const [suggestions, setSuggestions] = useState<SalesSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [filter, setFilter] = useState<string>('pending');

  const loadSuggestions = async () => {
    setLoading(true);
    try {
      const result = await aiSalesSuggestionsClient.list(workspaceId, {
        targetType,
        targetId,
        status: filter,
      });
      setSuggestions(result.suggestions);
    } catch {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSuggestions();
  }, [workspaceId, filter]);

  const handleGenerate = async () => {
    if (!targetType || !targetId) return;
    setGenerating(true);
    try {
      await aiSalesSuggestionsClient.generate(workspaceId, targetType, targetId, limit);
      await loadSuggestions();
    } finally {
      setGenerating(false);
    }
  };

  const handleStatusUpdate = async (suggestionId: string, status: string) => {
    await aiSalesSuggestionsClient.updateStatus(workspaceId, suggestionId, status);
    await loadSuggestions();
  };

  if (loading) {
    return <p style={{ color: '#888', padding: 16 }}>正在加载建议...</p>;
  }

  const priorityOrder = { high: 0, medium: 1, low: 2 };

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h4 style={{ margin: 0 }}>AI 销售建议</h4>
        {targetType && targetId && (
          <button
            onClick={handleGenerate}
            disabled={generating}
            style={{
              padding: '6px 12px',
              background: '#1967d2',
              color: '#fff',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              fontSize: 12,
            }}
          >
            {generating ? '生成中...' : '生成新建议'}
          </button>
        )}
      </div>

      {/* Status filter */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 12 }}>
        {['pending', 'accepted', 'completed', 'dismissed'].map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            style={{
              padding: '3px 10px',
              fontSize: 11,
              border: '1px solid #ccc',
              borderRadius: 12,
              background: filter === s ? '#1967d2' : 'transparent',
              color: filter === s ? '#fff' : '#666',
              cursor: 'pointer',
            }}
          >
            {(s === 'pending' && '待处理') || (s === 'accepted' && '已接受') || (s === 'completed' && '已完成') || (s === 'dismissed' && '已忽略') || s}
          </button>
        ))}
      </div>

      {/* Suggestions list */}
      {suggestions
        .sort((a, b) => (priorityOrder[a.priority] || 1) - (priorityOrder[b.priority] || 1))
        .map((suggestion) => (
          <div
            key={suggestion.id}
            style={{
              padding: 12,
              border: '1px solid #e0e0e0',
              borderRadius: 6,
              marginBottom: 8,
              background: suggestion.priority === 'high' ? '#fff5f5' : '#fff',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <strong style={{ fontSize: 14 }}>{suggestion.title}</strong>
              <span
                style={{
                  fontSize: 10,
                  padding: '2px 6px',
                  borderRadius: 10,
                  background: suggestion.priority === 'high' ? '#fde8e8' : '#f0f0f0',
                  color: suggestion.priority === 'high' ? '#c0392b' : '#666',
                }}
              >
                {suggestion.priority.toUpperCase()}
              </span>
            </div>
            <p style={{ fontSize: 13, color: '#555', margin: '4px 0' }}>{suggestion.description}</p>
            {suggestion.rationale && (
              <p style={{ fontSize: 11, color: '#999', fontStyle: 'italic' }}>
                原因：{suggestion.rationale}
              </p>
            )}

            {/* Suggested actions */}
            {suggestion.suggested_actions.length > 0 && (
              <div style={{ margin: '8px 0' }}>
                {suggestion.suggested_actions.map((action, i) => (
                  <div key={i} style={{ fontSize: 12, color: '#444', paddingLeft: 12 }}>
                    • {action.actionType}: {action.description}
                  </div>
                ))}
              </div>
            )}

            {/* Action buttons */}
            {suggestion.status === 'pending' && (
              <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                <ActionButton label="接受" color="#27ae60" onClick={() => handleStatusUpdate(suggestion.id, 'accepted')} />
                <ActionButton label="完成" color="#2980b9" onClick={() => handleStatusUpdate(suggestion.id, 'completed')} />
                <ActionButton label="忽略" color="#95a5a6" onClick={() => handleStatusUpdate(suggestion.id, 'dismissed')} />
              </div>
            )}

            <div style={{ fontSize: 10, color: '#aaa', marginTop: 4 }}>
              {suggestion.suggestion_type.replace(/_/g, ' ')} • {suggestion.status} •{' '}
              {new Date(suggestion.generated_at).toLocaleDateString()}
            </div>
          </div>
        ))}

      {suggestions.length === 0 && (
        <p style={{ color: '#888', fontSize: 13 }}>
          未找到{filter}的建议。
          {targetType && targetId && ' 点击"生成新建议"为此记录创建 AI 驱动的建议。'}
        </p>
      )}
    </div>
  );
};

const ActionButton: React.FC<{
  label: string;
  color: string;
  onClick: () => void;
}> = ({ label, color, onClick }) => (
  <button
    onClick={onClick}
    style={{
      padding: '3px 10px',
      fontSize: 11,
      background: 'transparent',
      border: `1px solid ${color}`,
      color,
      borderRadius: 4,
      cursor: 'pointer',
    }}
  >
    {label}
  </button>
);
