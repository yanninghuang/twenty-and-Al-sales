import type {
  KnowledgeDocument,
  KnowledgeDocumentCreate,
  KnowledgeQueryResponse,
  CustomerProfile,
  SalesSuggestion,
  QADocument,
  QAConversation,
  QAMessage,
  RiskAlertRule,
  RiskAlert,
  RiskAlertSummary,
  DailyBrief,
} from '@/ai-sales/types/ai-sales.types';

const API_BASE = 'http://localhost:8000/api/v1';
const API_KEY_HEADER = 'X-AI-Backend-API-Key';
const API_KEY = 'dev-internal-key-change-in-production';

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    [API_KEY_HEADER]: API_KEY,
    ...(options.headers as Record<string, string> || {}),
  };

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`AI 后端错误 (${response.status}): ${errorBody}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// ── Knowledge Base ───────────────────────────────────────────

export const aiKnowledgeBaseClient = {
  createDocument: (workspaceId: string, data: KnowledgeDocumentCreate) =>
    request<KnowledgeDocument>(
      `/workspaces/${workspaceId}/knowledge-base/documents`,
      { method: 'POST', body: JSON.stringify(data) },
    ),

  listDocuments: (workspaceId: string, offset = 0, limit = 20) =>
    request<{ documents: KnowledgeDocument[]; total: number }>(
      `/workspaces/${workspaceId}/knowledge-base/documents?offset=${offset}&limit=${limit}`,
    ),

  getDocument: (workspaceId: string, documentId: string) =>
    request<KnowledgeDocument>(
      `/workspaces/${workspaceId}/knowledge-base/documents/${documentId}`,
    ),

  deleteDocument: (workspaceId: string, documentId: string) =>
    request<void>(
      `/workspaces/${workspaceId}/knowledge-base/documents/${documentId}`,
      { method: 'DELETE' },
    ),

  query: (workspaceId: string, query: string, topK = 5) =>
    request<KnowledgeQueryResponse>(
      `/workspaces/${workspaceId}/knowledge-base/query`,
      { method: 'POST', body: JSON.stringify({ query, top_k: topK }) },
    ),
};

// ── Customer Profile ─────────────────────────────────────────

export const aiCustomerProfileClient = {
  generate: (
    workspaceId: string,
    companyId: string | null,
    personId: string | null,
    profileType: 'company' | 'person',
  ) =>
    request<CustomerProfile>(
      `/workspaces/${workspaceId}/customer-profiles/generate`,
      {
        method: 'POST',
        body: JSON.stringify({ company_id: companyId, person_id: personId, profile_type: profileType }),
      },
    ),

  getProfile: (workspaceId: string, profileId: string) =>
    request<CustomerProfile>(
      `/workspaces/${workspaceId}/customer-profiles/${profileId}`,
    ),

  getByCompany: (workspaceId: string, companyId: string) =>
    request<{ profiles: CustomerProfile[]; total: number }>(
      `/workspaces/${workspaceId}/customer-profiles?company_id=${companyId}`,
    ),

  search: (workspaceId: string, query: string, topK = 5) =>
    request<{ profiles: CustomerProfile[]; total: number }>(
      `/workspaces/${workspaceId}/customer-profiles/search`,
      { method: 'POST', body: JSON.stringify({ query, top_k: topK }) },
    ),
};

// ── Sales Suggestions ────────────────────────────────────────

export const aiSalesSuggestionsClient = {
  generate: (
    workspaceId: string,
    targetType: string,
    targetId: string,
    limit = 5,
  ) =>
    request<SalesSuggestion[]>(
      `/workspaces/${workspaceId}/sales-suggestions/generate`,
      {
        method: 'POST',
        body: JSON.stringify({ target_type: targetType, target_id: targetId, limit }),
      },
    ),

  list: (
    workspaceId: string,
    filters?: {
      targetType?: string;
      targetId?: string;
      status?: string;
      assignedTo?: string;
    },
  ) => {
    const params = new URLSearchParams();
    if (filters?.target_type) params.set('target_type', filters.target_type);
    if (filters?.target_id) params.set('target_id', filters.target_id);
    if (filters?.status) params.set('status_filter', filters.status);
    if (filters?.assignedTo) params.set('assigned_to', filters.assignedTo);
    return request<{ suggestions: SalesSuggestion[]; total: number }>(
      `/workspaces/${workspaceId}/sales-suggestions?${params.toString()}`,
    );
  },

  updateStatus: (workspaceId: string, suggestionId: string, status: string, reason?: string) =>
    request<SalesSuggestion>(
      `/workspaces/${workspaceId}/sales-suggestions/${suggestionId}/status`,
      {
        method: 'PATCH',
        body: JSON.stringify({ status, dismissed_reason: reason }),
      },
    ),

  submitFeedback: (
    workspaceId: string,
    suggestionId: string,
    rating: number | null,
    helpful: boolean | null,
    comment?: string,
  ) =>
    request<void>(
      `/workspaces/${workspaceId}/sales-suggestions/${suggestionId}/feedback`,
      {
        method: 'POST',
        body: JSON.stringify({ rating, helpful, comment }),
      },
    ),

  dailyBrief: (workspaceId: string, userId: string) =>
    request<DailyBrief>(
      `/workspaces/${workspaceId}/sales-suggestions/daily-brief`,
      { method: 'POST', body: JSON.stringify({ user_id: userId }) },
    ),
};

// ── Document QA ──────────────────────────────────────────────

export const aiDocumentQAClient = {
  uploadDocument: (
    workspaceId: string,
    data: { title: string; contentText: string; fileName?: string; fileType?: string },
  ) =>
    request<QADocument>(
      `/workspaces/${workspaceId}/document-qa/documents`,
      {
        method: 'POST',
        body: JSON.stringify({
          title: data.title,
          content_text: data.contentText,
          file_name: data.file_name,
          file_type: data.file_type,
        }),
      },
    ),

  listDocuments: (workspaceId: string) =>
    request<{ documents: QADocument[]; total: number }>(
      `/workspaces/${workspaceId}/document-qa/documents`,
    ),

  deleteDocument: (workspaceId: string, documentId: string) =>
    request<void>(
      `/workspaces/${workspaceId}/document-qa/documents/${documentId}`,
      { method: 'DELETE' },
    ),

  createConversation: (workspaceId: string, documentIds: string[], title?: string) =>
    request<QAConversation>(
      `/workspaces/${workspaceId}/document-qa/conversations`,
      {
        method: 'POST',
        body: JSON.stringify({ document_ids: documentIds, title }),
      },
    ),

  listConversations: (workspaceId: string) =>
    request<{ conversations: QAConversation[]; total: number }>(
      `/workspaces/${workspaceId}/document-qa/conversations`,
    ),

  getConversation: (workspaceId: string, conversationId: string) =>
    request<QAConversation>(
      `/workspaces/${workspaceId}/document-qa/conversations/${conversationId}`,
    ),

  sendMessage: (workspaceId: string, conversationId: string, content: string) =>
    request<QAMessage>(
      `/workspaces/${workspaceId}/document-qa/conversations/${conversationId}/messages`,
      { method: 'POST', body: JSON.stringify({ content }) },
    ),
};

// ── Risk Alerts ──────────────────────────────────────────────

export const aiRiskAlertsClient = {
  createRule: (
    workspaceId: string,
    data: {
      name: string;
      ruleType: string;
      targetType: string;
      conditions: Array<{ field: string; operator: string; value: unknown }>;
      severity?: string;
      description?: string;
    },
  ) =>
    request<RiskAlertRule>(
      `/workspaces/${workspaceId}/risk-alerts/rules`,
      { method: 'POST', body: JSON.stringify(data) },
    ),

  listRules: (workspaceId: string) =>
    request<RiskAlertRule[]>(
      `/workspaces/${workspaceId}/risk-alerts/rules`,
    ),

  updateRule: (workspaceId: string, ruleId: string, updates: Partial<RiskAlertRule>) =>
    request<RiskAlertRule>(
      `/workspaces/${workspaceId}/risk-alerts/rules/${ruleId}`,
      { method: 'PUT', body: JSON.stringify(updates) },
    ),

  deleteRule: (workspaceId: string, ruleId: string) =>
    request<void>(
      `/workspaces/${workspaceId}/risk-alerts/rules/${ruleId}`,
      { method: 'DELETE' },
    ),

  listAlerts: (
    workspaceId: string,
    filters?: {
      status?: string;
      severity?: string;
      targetType?: string;
      targetId?: string;
    },
  ) => {
    const params = new URLSearchParams();
    if (filters?.status) params.set('status_filter', filters.status);
    if (filters?.severity) params.set('severity', filters.severity);
    if (filters?.target_type) params.set('target_type', filters.target_type);
    if (filters?.target_id) params.set('target_id', filters.target_id);
    return request<{ alerts: RiskAlert[]; total: number }>(
      `/workspaces/${workspaceId}/risk-alerts?${params.toString()}`,
    );
  },

  updateAlertStatus: (
    workspaceId: string,
    alertId: string,
    status: string,
    reason?: string,
  ) =>
    request<RiskAlert>(
      `/workspaces/${workspaceId}/risk-alerts/${alertId}/status`,
      {
        method: 'PATCH',
        body: JSON.stringify({ status, dismissed_reason: reason }),
      },
    ),

  getSummary: (workspaceId: string) =>
    request<RiskAlertSummary>(
      `/workspaces/${workspaceId}/risk-alerts/summary`,
    ),

  evaluate: (
    workspaceId: string,
    targetType: string,
    targetId?: string,
  ) =>
    request<{ status: string; message: string; alertCount?: number }>(
      `/workspaces/${workspaceId}/risk-alerts/evaluate`,
      {
        method: 'POST',
        body: JSON.stringify({ target_type: targetType, target_id: targetId }),
      },
    ),
};
