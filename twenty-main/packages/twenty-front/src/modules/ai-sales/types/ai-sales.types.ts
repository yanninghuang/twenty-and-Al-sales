import type { ComponentType } from 'react';

export type AiSalesAssistantPageId =
  | 'dashboard'
  | 'knowledge-base'
  | 'customer-profile'
  | 'document-qa'
  | 'risk-alerts';

export type WorkspaceId = string;
export type RecordId = string;

// ── Knowledge Base ───────────────────────────────────────────

export type KnowledgeDocumentSourceType =
  | 'manual'
  | 'note'
  | 'attachment'
  | 'web';

export interface KnowledgeDocument {
  id: string;
  workspace_id: string;
  title: string;
  content: string;
  source_type: KnowledgeDocumentSourceType;
  source_record_type: string | null;
  source_record_id: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeQuerySource {
  chunk_id: string;
  document_title: string;
  excerpt: string;
  score: number;
}

export interface KnowledgeQueryResponse {
  answer: string;
  sources: KnowledgeQuerySource[];
  conversation_id: string | null;
}

export interface KnowledgeDocumentCreate {
  title: string;
  content: string;
  sourceType?: KnowledgeDocumentSourceType;
  sourceRecordType?: string | null;
  sourceRecordId?: string | null;
  metadata?: Record<string, unknown>;
}

// ── Customer Profile ─────────────────────────────────────────

export interface ProfileInsight {
  id: string;
  category: 'behavior' | 'finance' | 'communication' | 'risk' | 'opportunity';
  title: string;
  description: string;
  confidence: number;
  evidence?: Array<{ sourceType: string; sourceId: string; excerpt: string }>;
}

export interface CustomerProfile {
  id: string;
  workspace_id: string;
  company_id: string | null;
  person_id: string | null;
  profile_type: 'company' | 'person';
  summary: string | null;
  tags: string[];
  sentiment_score: number | null;
  engagement_level: 'high' | 'medium' | 'low' | 'none' | null;
  churn_risk_score: number | null;
  upsell_potential_score: number | null;
  key_contacts: Array<{
    personId: string;
    name: string;
    role: string;
    influenceLevel: string;
  }>;
  recent_activities_summary: string | null;
  generated_at: string;
  expires_at: string | null;
  insights: ProfileInsight[];
}

// ── Sales Suggestions ────────────────────────────────────────

export type SuggestionType =
  | 'next_action'
  | 'cross_sell'
  | 'upsell'
  | 'follow_up'
  | 'meeting_prep';

export type SuggestionPriority = 'high' | 'medium' | 'low';

export type SuggestionStatus =
  | 'pending'
  | 'accepted'
  | 'dismissed'
  | 'completed';

export interface SuggestedAction {
  action_type: string;
  description: string;
  relatedRecordId?: string;
}

export interface SuggestionFeedback {
  id: string;
  user_id: string;
  rating: number | null;
  helpful: boolean | null;
  comment: string | null;
  created_at: string;
}

export interface SalesSuggestion {
  id: string;
  workspace_id: string;
  target_type: 'company' | 'opportunity' | 'person';
  target_id: string;
  suggestion_type: SuggestionType;
  priority: SuggestionPriority;
  title: string;
  description: string;
  rationale: string | null;
  suggested_actions: SuggestedAction[];
  status: SuggestionStatus;
  dismissed_reason: string | null;
  generated_at: string;
  expires_at: string | null;
  accepted_at: string | null;
  completed_at: string | null;
  created_by: string | null;
  feedbacks: SuggestionFeedback[];
}

export interface DailyBrief {
  user_id: string;
  generated_at: string;
  suggestions: SalesSuggestion[];
  summary: string;
}

// ── Document QA ──────────────────────────────────────────────

export interface QADocument {
  id: string;
  workspace_id: string;
  title: string;
  file_name: string | null;
  file_type: string | null;
  file_size_bytes: number | null;
  source_type: string;
  created_at: string;
}

export interface QAMessage {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  citations: Array<{
    chunk_id: string;
    document_title?: string;
    excerpt: string;
    pageNumber?: number;
  }>;
  created_at: string;
}

export interface QAConversation {
  id: string;
  workspace_id: string;
  document_ids: string[];
  title: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  messages: QAMessage[];
}

// ── Risk Alerts ──────────────────────────────────────────────

export type AlertSeverity = 'critical' | 'high' | 'medium' | 'low';

export type AlertStatus =
  | 'open'
  | 'acknowledged'
  | 'resolved'
  | 'dismissed';

export type RuleType =
  | 'payment_overdue'
  | 'opportunity_stagnant'
  | 'deal_slipping'
  | 'customer_churn'
  | 'custom';

export interface RiskAlertRule {
  id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  rule_type: RuleType;
  target_type: string;
  conditions: Array<{
    field: string;
    operator: string;
    value: unknown;
  }>;
  severity: AlertSeverity;
  is_active: boolean;
  notification_channels: string[];
  cooldown_hours: number;
  created_at: string;
  updated_at: string;
}

export interface RiskAlert {
  id: string;
  workspace_id: string;
  rule_id: string | null;
  alert_type: string;
  target_type: string;
  target_id: string;
  target_name: string | null;
  severity: AlertSeverity;
  title: string;
  description: string;
  ai_analysis: string | null;
  suggested_actions: Array<{
    action_type: string;
    description: string;
  }>;
  related_data: Record<string, unknown>;
  status: AlertStatus;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  resolved_by: string | null;
  resolved_at: string | null;
  dismissed_reason: string | null;
  created_at: string;
  logs: RiskAlertLog[];
}

export interface RiskAlertLog {
  id: string;
  alert_id: string;
  action: string;
  performed_by: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface RiskAlertSummary {
  total_open: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  recently_resolved: number;
  workspace_id: string;
}
