// Barrel export for AI Sales Assistant module

// Components
export { AiSalesAssistantDashboard } from './components/AiSalesAssistantDashboard';
export { AiCustomerProfileCard } from './components/AiCustomerProfileCard';
export { AiSalesSuggestionsList } from './components/AiSalesSuggestionsList';
export { AiDocumentQAChat } from './components/AiDocumentQAChat';
export { AiRiskAlertList } from './components/AiRiskAlertList';

// Services
export {
  aiKnowledgeBaseClient,
  aiCustomerProfileClient,
  aiSalesSuggestionsClient,
  aiDocumentQAClient,
  aiRiskAlertsClient,
} from './services/aiBackendClient';

// Hooks
export {
  useAiKnowledgeBase,
  useAiCustomerProfile,
  useAiSalesSuggestions,
  useAiDocumentQA,
  useAiRiskAlerts,
} from './hooks';

// Types
export type {
  KnowledgeDocument,
  KnowledgeQuerySource,
  KnowledgeQueryResponse,
  CustomerProfile,
  ProfileInsight,
  SalesSuggestion,
  SuggestionFeedback,
  QADocument,
  QAConversation,
  QAMessage,
  RiskAlertRule,
  RiskAlert,
  RiskAlertLog,
  RiskAlertSummary,
  DailyBrief,
} from './types/ai-sales.types';
