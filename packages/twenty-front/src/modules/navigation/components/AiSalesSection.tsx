import { IconBook, IconMessage, IconRobot } from 'twenty-ui/icon';

import { NavigationDrawerItem } from '@/ui/navigation/navigation-drawer/components/NavigationDrawerItem';

export const AiSalesSection = () => {
  return (
    <>
      <NavigationDrawerItem
        label="AI 销售助手"
        to="/ai-sales"
        Icon={IconRobot}
        active={false}
      />
      <NavigationDrawerItem
        label="知识库"
        to="/ai-sales/knowledge-base"
        Icon={IconBook}
        active={false}
      />
      <NavigationDrawerItem
        label="AI 对话"
        to="/ai-sales/chat"
        Icon={IconMessage}
        active={false}
      />
    </>
  );
};
