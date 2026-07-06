import { useState, useCallback } from 'react';
import type {
  KnowledgeDocument,
  KnowledgeQueryResponse,
  CustomerProfile,
  SalesSuggestion,
  QADocument,
  QAConversation,
  QAMessage,
  RiskAlert,
  RiskAlertSummary,
  RiskAlertRule,
} from '@/ai-sales/types/ai-sales.types';
import {
  aiKnowledgeBaseClient,
  aiCustomerProfileClient,
  aiSalesSuggestionsClient,
  aiDocumentQAClient,
  aiRiskAlertsClient,
} from '@/ai-sales/services/aiBackendClient';

// ── Knowledge Base ───────────────────────────────────────────

export const useAiKnowledgeBase = (workspaceId: string) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const uploadDocument = useCallback(
    async (title: string, content: string) => {
      setLoading(true);
      setError(null);
      try {
        return await aiKnowledgeBaseClient.createDocument(workspaceId, { title, content });
      } catch (e) {
        setError((e as Error).message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [workspaceId],
  );

  const searchKnowledge = useCallback(
    async (query: string, topK?: number) => {
      setLoading(true);
      setError(null);
      try {
        return await aiKnowledgeBaseClient.query(workspaceId, query, topK);
      } catch (e) {
        setError((e as Error).message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [workspaceId],
  );

  const listDocuments = useCallback(
    async (offset?: number, limit?: number) => {
      setLoading(true);
      try {
        return await aiKnowledgeBaseClient.listDocuments(workspaceId, offset, limit);
      } catch (e) {
        setError((e as Error).message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [workspaceId],
  );

  return { uploadDocument, searchKnowledge, listDocuments, loading, error };
};

// ── Customer Profile ─────────────────────────────────────────

export const useAiCustomerProfile = (workspaceId: string) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateProfile = useCallback(
    async (companyId: string | null, personId: string | null, profileType: 'company' | 'person') => {
      setLoading(true);
      setError(null);
      try {
        return await aiCustomerProfileClient.generate(workspaceId, companyId, personId, profileType);
      } catch (e) {
        setError((e as Error).message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [workspaceId],
  );

  const getProfileByCompany = useCallback(
    async (companyId: string) => {
      setLoading(true);
      try {
        return await aiCustomerProfileClient.getByCompany(workspaceId, companyId);
      } catch (e) {
        setError((e as Error).message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [workspaceId],
  );

  return { generateProfile, getProfileByCompany, loading, error };
};

// ── Sales Suggestions ────────────────────────────────────────

export const useAiSalesSuggestions = (workspaceId: string) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateSuggestions = useCallback(
    async (targetType: string, targetId: string, limit?: number) => {
      setLoading(true);
      setError(null);
      try {
        return await aiSalesSuggestionsClient.generate(workspaceId, targetType, targetId, limit);
      } catch (e) {
        setError((e as Error).message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [workspaceId],
  );

  const updateStatus = useCallback(
    async (suggestionId: string, status: string, reason?: string) => {
      try {
        return await aiSalesSuggestionsClient.updateStatus(workspaceId, suggestionId, status, reason);
      } catch (e) {
        setError((e as Error).message);
        return null;
      }
    },
    [workspaceId],
  );

  return { generateSuggestions, updateStatus, loading, error };
};

// ── Document QA ──────────────────────────────────────────────

export const useAiDocumentQA = (workspaceId: string) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const uploadDocument = useCallback(
    async (title: string, contentText: string, fileName?: string, fileType?: string) => {
      setLoading(true);
      setError(null);
      try {
        return await aiDocumentQAClient.uploadDocument(workspaceId, { title, contentText, fileName, fileType });
      } catch (e) {
        setError((e as Error).message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [workspaceId],
  );

  const askQuestion = useCallback(
    async (conversationId: string, question: string) => {
      setLoading(true);
      setError(null);
      try {
        return await aiDocumentQAClient.sendMessage(workspaceId, conversationId, question);
      } catch (e) {
        setError((e as Error).message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [workspaceId],
  );

  const createConversation = useCallback(
    async (documentIds: string[], title?: string) => {
      try {
        return await aiDocumentQAClient.createConversation(workspaceId, documentIds, title);
      } catch (e) {
        setError((e as Error).message);
        return null;
      }
    },
    [workspaceId],
  );

  return { uploadDocument, askQuestion, createConversation, loading, error };
};

// ── Risk Alerts ──────────────────────────────────────────────

export const useAiRiskAlerts = (workspaceId: string) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getSummary = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      return await aiRiskAlertsClient.getSummary(workspaceId);
    } catch (e) {
      setError((e as Error).message);
      return null;
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  const listAlerts = useCallback(
    async (filters?: { status?: string; severity?: string }) => {
      setLoading(true);
      try {
        return await aiRiskAlertsClient.listAlerts(workspaceId, filters);
      } catch (e) {
        setError((e as Error).message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [workspaceId],
  );

  const updateAlertStatus = useCallback(
    async (alertId: string, status: string, reason?: string) => {
      try {
        return await aiRiskAlertsClient.updateAlertStatus(workspaceId, alertId, status, reason);
      } catch (e) {
        setError((e as Error).message);
        return null;
      }
    },
    [workspaceId],
  );

  return { getSummary, listAlerts, updateAlertStatus, loading, error };
};
