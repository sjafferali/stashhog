import React from 'react';
import { Layout, Button, Badge, Space, Tooltip, theme } from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  BellOutlined,
  SyncOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import useAppStore from '@/store';

const { Header: AntHeader } = Layout;

interface HeaderProps {
  collapsed: boolean;
  onToggle: () => void;
}

const Header: React.FC<HeaderProps> = ({ collapsed, onToggle }) => {
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const { isLoading } = useAppStore();

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
            onClick={() => navigate('/sync')}
          />
        </Tooltip>

        <Tooltip title="Jobs">
          <Badge count={0} showZero={false}>
            <Button
              type="text"
              icon={<BellOutlined />}
              onClick={() => navigate('/jobs')}
            />
          </Badge>
        </Tooltip>

        <Tooltip title="Settings">
          <Button
            type="text"
            icon={<SettingOutlined />}
            onClick={() => navigate('/settings')}
          />
        </Tooltip>
      </Space>
    </AntHeader>
  );
};

export default Header;
