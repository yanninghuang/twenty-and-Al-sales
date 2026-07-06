import { PageContainer } from '@/ui/layout/page/components/PageContainer';
import { AiSalesAssistantDashboard } from '@/ai-sales/components/AiSalesAssistantDashboard';
import { currentWorkspaceState } from '@/auth/states/currentWorkspaceState';
import { useAtomStateValue } from '@/ui/utilities/state/jotai/hooks/useAtomStateValue';

export const AiSalesPage = () => {
  const workspace = useAtomStateValue(currentWorkspaceState);
  const workspaceId = workspace?.id || 'demo';

  return (
    <PageContainer>
      <AiSalesAssistantDashboard workspaceId={workspaceId} />
    </PageContainer>
  );
};
