import React, { useState, useEffect, useCallback } from 'react';
import {
  aiKnowledgeBaseClient,
  aiRiskAlertsClient,
  aiSalesSuggestionsClient,
} from '@/ai-sales/services/aiBackendClient';
import type {
  KnowledgeQueryResponse,
  RiskAlertSummary,
  SalesSuggestion,
} from '@/ai-sales/types/ai-sales.types';

type DashboardTab = 'overview' | 'knowledge' | 'suggestions' | 'alerts';

export const AiSalesAssistantDashboard: React.FC<{ workspaceId: string }> = ({
  workspaceId,
}) => {
  const [activeTab, setActiveTab] = useState<DashboardTab>('overview');
  const [summary, setSummary] = useState<RiskAlertSummary | null>(null);
  const [suggestions, setSuggestions] = useState<SalesSuggestion[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadDashboard = async () => {
      setLoading(true);
      try {
        const [alertsSummary, suggestionsResult] = await Promise.all([
          aiRiskAlertsClient.getSummary(workspaceId),
          aiSalesSuggestionsClient.list(workspaceId, { status: 'pending' }),
        ]);
        setSummary(alertsSummary);
        setSuggestions(suggestionsResult.suggestions.slice(0, 5));
      } catch {
        // Dashboard data is non-critical
      } finally {
        setLoading(false);
      }
    };
    loadDashboard();
  }, [workspaceId]);

  if (loading) {
    return <div style={{ padding: 24 }}>正在加载 AI 销售助手...</div>;
  }

  return (
    <div style={{ padding: 24 }}>
      <h1>AI 销售助手</h1>
      <p style={{ color: '#666', marginBottom: 24 }}>
        AI 驱动的销售洞察、建议与风险监控
      </p>

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 24, borderBottom: '1px solid #e0e0e0', paddingBottom: 12 }}>
        {(['overview', 'knowledge', 'suggestions', 'alerts'] as DashboardTab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '8px 16px',
              border: 'none',
              background: activeTab === tab ? '#1967d2' : 'transparent',
              color: activeTab === tab ? '#fff' : '#333',
              borderRadius: 4,
              cursor: 'pointer',
              fontWeight: activeTab === tab ? 600 : 400,
            }}
          >
            {tab === 'overview' && '概览'}
            {tab === 'knowledge' && '知识库'}
            {tab === 'suggestions' && '建议'}
            {tab === 'alerts' && '风险预警'}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <DashboardOverview summary={summary} suggestions={suggestions} />
      )}
      {activeTab === 'knowledge' && (
        <div>
          <h3>快速知识搜索</h3>
          <KnowledgeSearchWidget workspaceId={workspaceId} />
        </div>
      )}
      {activeTab === 'suggestions' && (
        <SuggestionsWidget workspaceId={workspaceId} />
      )}
      {activeTab === 'alerts' && (
        <AlertsWidget workspaceId={workspaceId} />
      )}
    </div>
  );
};

// ── Sub-components ───────────────────────────────────────────

const DashboardOverview: React.FC<{
  summary: RiskAlertSummary | null;
  suggestions: SalesSuggestion[];
}> = ({ summary, suggestions }) => (
  <div>
    {/* Alert Summary Cards */}
    {summary && (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 16, marginBottom: 24 }}>
        <StatCard label="待处理预警" value={summary.total_open} color="#e74c3c" />
        <StatCard label="严重" value={summary.critical_count} color="#c0392b" />
        <StatCard label="高" value={summary.high_count} color="#e67e22" />
        <StatCard label="中" value={summary.medium_count} color="#f1c40f" />
        <StatCard label="已解决 (7天)" value={summary.recently_resolved} color="#27ae60" />
      </div>
    )}

    {/* Top Suggestions */}
    <h3 style={{ marginBottom: 12 }}>待处理建议 Top</h3>
    {suggestions.length > 0 ? (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {suggestions.map((s) => (
          <SuggestionCard key={s.id} suggestion={s} />
        ))}
      </div>
    ) : (
      <p style={{ color: '#888' }}>暂无待处理建议。请从公司或商机页面生成建议。</p>
    )}
  </div>
);

const StatCard: React.FC<{ label: string; value: number; color: string }> = ({
  label,
  value,
  color,
}) => (
  <div style={{ padding: 16, border: '1px solid #e0e0e0', borderRadius: 8, textAlign: 'center' }}>
    <div style={{ fontSize: 32, fontWeight: 700, color }}>{value}</div>
    <div style={{ fontSize: 13, color: '#666', marginTop: 4 }}>{label}</div>
  </div>
);

const KnowledgeSearchWidget: React.FC<{ workspaceId: string }> = ({ workspaceId }) => {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<KnowledgeQueryResponse | null>(null);
  const [searching, setSearching] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const response = await aiKnowledgeBaseClient.query(workspaceId, query);
      setResult(response);
    } catch {
      setResult(null);
    } finally {
      setSearching(false);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="向知识库提问..."
          style={{ flex: 1, padding: '8px 12px', border: '1px solid #ccc', borderRadius: 4 }}
        />
        <button
          onClick={handleSearch}
          disabled={searching}
          style={{ padding: '8px 16px', background: '#1967d2', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}
        >
          {searching ? '搜索中...' : '搜索'}
        </button>
      </div>

      {result && (
        <div style={{ background: '#f8f9fa', padding: 16, borderRadius: 8 }}>
          <p style={{ lineHeight: 1.6 }}>{result.answer}</p>
          {result.sources.length > 0 && (
            <div style={{ marginTop: 12, fontSize: 12, color: '#888' }}>
              <strong>来源：</strong>
              {result.sources.map((s, i) => (
                <span key={i} style={{ marginLeft: 8 }}>
                  [{i + 1}] {s.document_title}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const SuggestionsWidget: React.FC<{ workspaceId: string }> = ({ workspaceId }) => {
  const [items, setItems] = useState<SalesSuggestion[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    aiSalesSuggestionsClient.list(workspaceId, { status: 'pending' }).then((r) => {
      setItems(r.suggestions);
      setLoading(false);
    });
  }, [workspaceId]);

  if (loading) return <p>正在加载建议...</p>;

  return (
    <div>
      {items.map((s) => (
        <SuggestionCard key={s.id} suggestion={s} />
      ))}
      {items.length === 0 && (
        <p style={{ color: '#888' }}>暂无建议。请前往公司或商机详情页生成建议。</p>
      )}
    </div>
  );
};

const SuggestionCard: React.FC<{ suggestion: SalesSuggestion }> = ({ suggestion }) => {
  const priorityColors: Record<string, string> = {
    high: '#e74c3c',
    medium: '#f39c12',
    low: '#3498db',
  };

  return (
    <div
      style={{
        padding: 12,
        border: '1px solid #e0e0e0',
        borderLeft: `4px solid ${priorityColors[suggestion.priority] || '#ccc'}`,
        borderRadius: 4,
        marginBottom: 8,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <strong>{suggestion.title}</strong>
        <span
          style={{
            fontSize: 11,
            padding: '2px 8px',
            borderRadius: 12,
            background: '#f0f0f0',
            textTransform: 'uppercase',
          }}
        >
          {suggestion.priority}
        </span>
      </div>
      <p style={{ fontSize: 13, color: '#555', margin: '4px 0' }}>{suggestion.description}</p>
      {suggestion.rationale && (
        <p style={{ fontSize: 12, color: '#999', fontStyle: 'italic' }}>原因：{suggestion.rationale}</p>
      )}
      <div style={{ fontSize: 11, color: '#aaa', marginTop: 4 }}>
        {suggestion.suggestion_type.replace(/_/g, ' ')} • {suggestion.status}
      </div>
    </div>
  );
};

const AlertsWidget: React.FC<{ workspaceId: string }> = ({ workspaceId }) => {
  const [alerts, setAlerts] = useState<RiskAlert[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    aiRiskAlertsClient.listAlerts(workspaceId, { status: 'open' }).then((r) => {
      setAlerts(r.alerts);
      setLoading(false);
    });
  }, [workspaceId]);

  if (loading) return <p>正在加载预警...</p>;

  const severityColors: Record<string, string> = {
    critical: '#c0392b',
    high: '#e74c3c',
    medium: '#f39c12',
    low: '#3498db',
  };

  return (
    <div>
      {alerts.map((a) => (
        <div
          key={a.id}
          style={{
            padding: 12,
            border: '1px solid #e0e0e0',
            borderLeft: `4px solid ${severityColors[a.severity] || '#ccc'}`,
            borderRadius: 4,
            marginBottom: 8,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <strong>{a.title}</strong>
            <span
              style={{
                fontSize: 11,
                padding: '2px 8px',
                borderRadius: 12,
                background: severityColors[a.severity] + '20',
                color: severityColors[a.severity],
                fontWeight: 600,
              }}
            >
              {a.severity.toUpperCase()}
            </span>
          </div>
          <p style={{ fontSize: 13, color: '#555', margin: '4px 0' }}>{a.description}</p>
          <div style={{ fontSize: 11, color: '#aaa' }}>
            {a.target_type}: {a.target_name || a.target_id} • {a.status} • {new Date(a.created_at).toLocaleDateString()}
          </div>
        </div>
      ))}
      {alerts.length === 0 && (
        <p style={{ color: '#888' }}>暂无风险预警，CRM 状态良好！</p>
      )}
    </div>
  );
};

import type { RiskAlert } from '@/ai-sales/types/ai-sales.types';
