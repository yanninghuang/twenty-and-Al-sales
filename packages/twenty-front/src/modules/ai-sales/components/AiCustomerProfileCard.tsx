import React, { useState, useEffect } from 'react';
import { aiCustomerProfileClient } from '@/ai-sales/services/aiBackendClient';
import type { CustomerProfile } from '@/ai-sales/types/ai-sales.types';

export const AiCustomerProfileCard: React.FC<{
  workspaceId: string;
  companyId?: string | null;
  personId?: string | null;
  profileType: 'company' | 'person';
}> = ({ workspaceId, companyId, personId, profileType }) => {
  const [profile, setProfile] = useState<CustomerProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);

  // Try to load existing profile
  useEffect(() => {
    const loadProfile = async () => {
      setLoading(true);
      try {
        const result = await aiCustomerProfileClient.getByCompany(
          workspaceId,
          companyId || '',
        );
        if (result.profiles.length > 0) {
          setProfile(result.profiles[0]);
        }
      } catch {
        // Profile may not exist yet
      } finally {
        setLoading(false);
      }
    };

    if (companyId) {
      loadProfile();
    }
  }, [workspaceId, companyId]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const newProfile = await aiCustomerProfileClient.generate(
        workspaceId,
        companyId || null,
        personId || null,
        profileType,
      );
      setProfile(newProfile);
    } catch {
      // Handle error
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: 16, border: '1px solid #e0e0e0', borderRadius: 8 }}>
        <p style={{ color: '#888' }}>正在加载客户画像...</p>
      </div>
    );
  }

  if (!profile) {
    return (
      <div style={{ padding: 16, border: '1px solid #e0e0e0', borderRadius: 8 }}>
        <h4>AI 客户画像</h4>
        <p style={{ color: '#666', fontSize: 13 }}>
          生成 AI 驱动的 360 度客户画像，包含情感分析、流失风险评分和可执行洞察。
        </p>
        <button
          onClick={handleGenerate}
          disabled={generating}
          style={{
            padding: '8px 16px',
            background: '#1967d2',
            color: '#fff',
            border: 'none',
            borderRadius: 4,
            cursor: 'pointer',
            marginTop: 8,
          }}
        >
          {generating ? '生成中...' : '生成画像'}
        </button>
      </div>
    );
  }

  const riskColors: Record<string, string> = {
    high: '#e74c3c',
    medium: '#f39c12',
    low: '#27ae60',
    none: '#95a5a6',
  };

  const engagementColor = riskColors[profile.engagement_level || 'none'] || '#95a5a6';

  return (
    <div style={{ padding: 16, border: '1px solid #e0e0e0', borderRadius: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h4 style={{ margin: 0 }}>AI 客户画像</h4>
        <button
          onClick={handleGenerate}
          disabled={generating}
          style={{
            padding: '4px 12px',
            fontSize: 12,
            background: 'transparent',
            border: '1px solid #ccc',
            borderRadius: 4,
            cursor: 'pointer',
          }}
        >
          {generating ? '刷新中...' : '刷新'}
        </button>
      </div>

      {/* Summary */}
      {profile.summary && (
        <p style={{ fontSize: 13, lineHeight: 1.5, color: '#333', marginBottom: 12 }}>
          {profile.summary}
        </p>
      )}

      {/* Scores */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
        <ScoreBadge label="情感倾向" value={profile.sentiment_score} min={-1} max={1} />
        <ScoreBadge label="流失风险" value={profile.churn_risk_score} min={0} max={1} inverted />
        <ScoreBadge label="增销潜力" value={profile.upsell_potential_score} min={0} max={1} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ fontSize: 11, color: '#666' }}>参与度：</span>
          <span style={{ fontSize: 12, fontWeight: 600, color: engagementColor }}>
            {profile.engagement_level || '暂无'}
          </span>
        </div>
      </div>

      {/* Tags */}
      {profile.tags.length > 0 && (
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 12 }}>
          {profile.tags.map((tag, i) => (
            <span
              key={i}
              style={{
                fontSize: 11,
                padding: '2px 8px',
                background: '#e8f0fe',
                color: '#1967d2',
                borderRadius: 12,
              }}
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Insights */}
      {profile.insights.length > 0 && (
        <div>
          <h5 style={{ fontSize: 13, marginBottom: 8 }}>关键洞察</h5>
          {profile.insights.slice(0, 3).map((insight) => (
            <div key={insight.id} style={{ marginBottom: 6, paddingLeft: 8, borderLeft: '2px solid #e0e0e0' }}>
              <div style={{ fontSize: 12, fontWeight: 600 }}>{insight.title}</div>
              <div style={{ fontSize: 11, color: '#666' }}>{insight.description}</div>
              <div style={{ fontSize: 10, color: '#aaa' }}>
                {insight.category} • 置信度： {(insight.confidence * 100).toFixed(0)}%
              </div>
            </div>
          ))}
        </div>
      )}

      <div style={{ fontSize: 10, color: '#aaa', marginTop: 8 }}>
        生成时间： {new Date(profile.generated_at).toLocaleString()}
      </div>
    </div>
  );
};

const ScoreBadge: React.FC<{
  label: string;
  value: number | null;
  min: number;
  max: number;
  inverted?: boolean;
}> = ({ label, value, min, max, inverted }) => {
  if (value === null) return null;
  const normalized = (value - min) / (max - min);
  const displayValue = inverted ? 1 - normalized : normalized;

  const color =
    displayValue > 0.66 ? '#e74c3c' : displayValue > 0.33 ? '#f39c12' : '#27ae60';

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <span style={{ fontSize: 11, color: '#666' }}>{label}:</span>
      <span style={{ fontSize: 13, fontWeight: 600, color }}>
        {inverted ? `${((1 - normalized) * 100).toFixed(0)}%` : `${(normalized * 100).toFixed(0)}%`}
      </span>
    </div>
  );
};
