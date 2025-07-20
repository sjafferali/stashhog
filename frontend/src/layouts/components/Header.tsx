import React from 'react';
import { Layout, Button, Badge, Space, Tooltip, theme } from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  BellOutlined,
  SyncOutlined,
  SettingOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import useAppStore from '@/store';
import { useRunningJobs } from '@/hooks/useRunningJobs';

const { Header: AntHeader } = Layout;

interface HeaderProps {
  collapsed: boolean;
  onToggle: () => void;
}

const Header: React.FC<HeaderProps> = ({ collapsed, onToggle }) => {
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const { isLoading } = useAppStore();
  const { runningCount } = useRunningJobs();

  return (
    <AntHeader
      style={{
        padding: 0,
        background: token.colorBgContainer,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        boxShadow: '0 1px 4px rgba(0, 0, 0, 0.08)',
      }}
    >
      <Button
        type="text"
        icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
        onClick={onToggle}
        style={{
          fontSize: '16px',
          width: 64,
          height: 64,
        }}
      />

      <Space style={{ marginRight: 24 }}>
        <Tooltip title="Sync Status">
          <Button
            type="text"
            icon={<SyncOutlined spin={isLoading} />}
            onClick={() => {
              void navigate('/sync');
            }}
          />
        </Tooltip>

        <Tooltip
          title={
            runningCount > 0
              ? `${runningCount} running job${runningCount > 1 ? 's' : ''}`
              : 'Jobs'
          }
        >
          <Badge count={runningCount} showZero={false}>
            <Button
              type="text"
              icon={
                runningCount > 0 ? <LoadingOutlined spin /> : <BellOutlined />
              }
              onClick={() => {
                void navigate('/jobs');
              }}
              style={{
                color: runningCount > 0 ? token.colorPrimary : undefined,
              }}
            />
          </Badge>
        </Tooltip>

        <Tooltip title="Settings">
          <Button
            type="text"
            icon={<SettingOutlined />}
            onClick={() => {
              void navigate('/settings');
            }}
          />
        </Tooltip>
      </Space>
    </AntHeader>
  );
};

export default Header;
