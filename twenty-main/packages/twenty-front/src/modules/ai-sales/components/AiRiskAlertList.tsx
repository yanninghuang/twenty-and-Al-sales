import React, { useState, useEffect } from 'react';
import { aiRiskAlertsClient } from '@/ai-sales/services/aiBackendClient';
import type { RiskAlert, RiskAlertSummary } from '@/ai-sales/types/ai-sales.types';

export const AiRiskAlertList: React.FC<{
  workspaceId: string;
  initialStatus?: string;
  targetType?: string;
  targetId?: string;
}> = ({ workspaceId, initialStatus = 'open', targetType, targetId }) => {
  const [alerts, setAlerts] = useState<RiskAlert[]>([]);
  const [summary, setSummary] = useState<RiskAlertSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState(initialStatus);

  const loadData = async () => {
    setLoading(true);
    try {
      const [alertsResult, summaryResult] = await Promise.all([
        aiRiskAlertsClient.listAlerts(workspaceId, {
          status: statusFilter,
          targetType,
          targetId,
        }),
        aiRiskAlertsClient.getSummary(workspaceId),
      ]);
      setAlerts(alertsResult.alerts);
      setSummary(summaryResult);
    } catch {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [workspaceId, statusFilter]);

  const handleStatusUpdate = async (alertId: string, newStatus: string) => {
    await aiRiskAlertsClient.updateAlertStatus(workspaceId, alertId, newStatus);
    await loadData();
  };

  if (loading) {
    return <p style={{ color: '#888', padding: 16 }}>正在加载风险预警...</p>;
  }

  const severityColors: Record<string, string> = {
    critical: '#c0392b',
    high: '#e74c3c',
    medium: '#f39c12',
    low: '#3498db',
  };

  return (
    <div style={{ padding: 16 }}>
      {/* Summary bar */}
      {summary && (
        <div
          style={{
            display: 'flex',
            gap: 16,
            padding: 12,
            background: '#f8f9fa',
            borderRadius: 8,
            marginBottom: 16,
            flexWrap: 'wrap',
          }}
        >
          <SummaryItem label="待处理" value={summary.total_open} color="#e74c3c" />
          <SummaryItem label="严重" value={summary.critical_count} color="#c0392b" />
          <SummaryItem label="高" value={summary.high_count} color="#e67e22" />
          <SummaryItem label="中" value={summary.medium_count} color="#f1c40f" />
          <SummaryItem label="低" value={summary.low_count} color="#3498db" />
          <SummaryItem label="已解决 (7天)" value={summary.recently_resolved} color="#27ae60" />
        </div>
      )}

      {/* Status filter */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 12 }}>
        {['open', 'acknowledged', 'resolved', 'dismissed'].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            style={{
              padding: '3px 10px',
              fontSize: 11,
              border: '1px solid #ccc',
              borderRadius: 12,
              background: statusFilter === s ? '#1967d2' : 'transparent',
              color: statusFilter === s ? '#fff' : '#666',
              cursor: 'pointer',
            }}
          >
            {(s === 'open' && '待处理') || (s === 'acknowledged' && '已确认') || (s === 'resolved' && '已解决') || (s === 'dismissed' && '已忽略') || s}
          </button>
        ))}
      </div>

      {/* Alert list */}
      {alerts.map((alert) => (
        <div
          key={alert.id}
          style={{
            padding: 12,
            border: '1px solid #e0e0e0',
            borderLeft: `4px solid ${severityColors[alert.severity] || '#ccc'}`,
            borderRadius: 6,
            marginBottom: 8,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <strong style={{ fontSize: 14 }}>{alert.title}</strong>
              <span
                style={{
                  marginLeft: 8,
                  fontSize: 10,
                  padding: '2px 6px',
                  borderRadius: 10,
                  background: severityColors[alert.severity] + '20',
                  color: severityColors[alert.severity],
                  fontWeight: 600,
                }}
              >
                {alert.severity.toUpperCase()}
              </span>
            </div>
          </div>

          <p style={{ fontSize: 13, color: '#555', margin: '4px 0' }}>{alert.description}</p>

          {/* AI Analysis */}
          {alert.ai_analysis && (
            <div
              style={{
                marginTop: 8,
                padding: 8,
                background: '#f8f9fa',
                borderRadius: 4,
                fontSize: 12,
                color: '#555',
                borderLeft: '2px solid #1967d2',
              }}
            >
              <strong style={{ fontSize: 11, color: '#1967d2' }}>AI 分析：</strong>{' '}
              {alert.ai_analysis}
            </div>
          )}

          {/* Suggested actions */}
          {alert.suggested_actions.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <strong style={{ fontSize: 11, color: '#666' }}>建议操作：</strong>
              {alert.suggested_actions.map((action, i) => (
                <div key={i} style={{ fontSize: 12, color: '#444', paddingLeft: 12, marginTop: 2 }}>
                  • {action.description}
                </div>
              ))}
            </div>
          )}

          {/* Action buttons for open alerts */}
          {alert.status === 'open' && (
            <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
              <AlertActionButton
                label="确认"
                color="#f39c12"
                onClick={() => handleStatusUpdate(alert.id, 'acknowledged')}
              />
              <AlertActionButton
                label="解决"
                color="#27ae60"
                onClick={() => handleStatusUpdate(alert.id, 'resolved')}
              />
              <AlertActionButton
                label="忽略"
                color="#95a5a6"
                onClick={() => handleStatusUpdate(alert.id, 'dismissed')}
              />
            </div>
          )}

          <div style={{ fontSize: 10, color: '#aaa', marginTop: 6 }}>
            {alert.alert_type} • {alert.target_type}: {alert.target_name || alert.target_id} •{' '}
            {new Date(alert.created_at).toLocaleString()}
            {alert.acknowledged_at && ` • 确认时间： ${new Date(alert.acknowledged_at).toLocaleString()}`}
            {alert.resolved_at && ` • 解决时间： ${new Date(alert.resolved_at).toLocaleString()}`}
          </div>
        </div>
      ))}

      {alerts.length === 0 && (
        <p style={{ color: '#888', fontSize: 13, textAlign: 'center', padding: 24 }}>
          未找到{statusFilter}的风险预警。
        </p>
      )}
    </div>
  );
};

const SummaryItem: React.FC<{ label: string; value: number; color: string }> = ({
  label,
  value,
  color,
}) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
    <span style={{ fontSize: 11, color: '#888' }}>{label}:</span>
    <span style={{ fontSize: 14, fontWeight: 700, color }}>{value}</span>
  </div>
);

const AlertActionButton: React.FC<{
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
