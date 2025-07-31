import React from 'react';
import { Layout, Menu } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  DashboardOutlined,
  VideoCameraOutlined,
  BulbOutlined,
  UnorderedListOutlined,
  RobotOutlined,
  SyncOutlined,
  SettingOutlined,
  CalendarOutlined,
} from '@ant-design/icons';

const { Sider } = Layout;

interface SidebarProps {
  collapsed: boolean;
}

const Sidebar: React.FC<SidebarProps> = ({ collapsed }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: 'Dashboard',
    },
    {
      key: '/scenes',
      icon: <VideoCameraOutlined />,
      label: 'Scenes',
    },
    {
      key: 'analysis-menu',
      icon: <BulbOutlined />,
      label: 'Analysis',
      children: [
        {
          key: '/analysis',
          label: 'Overview',
        },
        {
          key: '/analysis/plans',
          label: 'Plans',
        },
      ],
    },
    {
      key: 'jobs-menu',
      icon: <UnorderedListOutlined />,
      label: 'Jobs',
      children: [
        {
          key: '/jobs',
          label: 'Job Monitor',
        },
        {
          key: '/jobs/run',
          label: 'Run Job',
        },
        {
          key: '/jobs/v2',
          label: 'Jobs v2',
        },
      ],
    },
    {
      key: '/sync',
      icon: <SyncOutlined />,
      label: 'Sync',
    },
    {
      key: '/scheduler',
      icon: <CalendarOutlined />,
      label: 'Scheduler',
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: 'Settings',
    },
  ];

  const handleMenuClick = ({ key }: { key: string }) => {
    // Only navigate if the key starts with '/' (is a route)
    if (key.startsWith('/')) {
      void navigate(key);
    }
  };

  // Find the active menu key based on current path
  const getSelectedKeys = () => {
    const path = location.pathname;
    if (path === '/') return ['/'];

    // Check for exact match in all items and their children
    for (const item of menuItems) {
      if (item.key === path && !item.children) return [path];

      if (item.children) {
        const childMatch = item.children.find((child) => child.key === path);
        if (childMatch) return [path];
      }
    }

    // Find all prefix matches and select the longest one
    let longestMatch = '';
    let longestMatchKey = '';

    // Check prefix matches in children first (they should have priority)
    for (const item of menuItems) {
      if (item.children) {
        for (const child of item.children) {
          if (
            path.startsWith(child.key) &&
            child.key !== '/' &&
            child.key.length > longestMatch.length
          ) {
            longestMatch = child.key;
            longestMatchKey = child.key;
          }
        }
      }
    }

    // If we found a match in children, return it
    if (longestMatchKey) return [longestMatchKey];

    // Otherwise check for prefix match in top-level items
    const prefixMatch = menuItems.find(
      (item) => !item.children && path.startsWith(item.key) && item.key !== '/'
    );
    if (prefixMatch) return [prefixMatch.key];

    return [];
  };

  return (
    <Sider trigger={null} collapsible collapsed={collapsed} theme="dark">
      <div
        style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontSize: collapsed ? 20 : 24,
          fontWeight: 'bold',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
        }}
      >
        {collapsed ? <RobotOutlined /> : 'StashHog'}
      </div>
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={getSelectedKeys()}
        onClick={handleMenuClick}
        items={menuItems}
      />
    </Sider>
  );
};

export default Sidebar;
