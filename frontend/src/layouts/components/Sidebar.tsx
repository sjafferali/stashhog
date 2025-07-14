import React from 'react'
import { Layout, Menu } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  DashboardOutlined,
  VideoCameraOutlined,
  BulbOutlined,
  UnorderedListOutlined,
  RobotOutlined,
  SyncOutlined,
  SettingOutlined,
  CalendarOutlined,
} from '@ant-design/icons'

const { Sider } = Layout

interface SidebarProps {
  collapsed: boolean
}

const Sidebar: React.FC<SidebarProps> = ({ collapsed }) => {
  const navigate = useNavigate()
  const location = useLocation()

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
      key: '/analysis',
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
      key: '/jobs',
      icon: <UnorderedListOutlined />,
      label: 'Jobs',
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
  ]

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
  }

  // Find the active menu key based on current path
  const getSelectedKeys = () => {
    const path = location.pathname
    if (path === '/') return ['/']
    
    // Check for exact match first
    const exactMatch = menuItems.find(item => item.key === path)
    if (exactMatch) return [path]
    
    // Check for parent match
    const parentMatch = menuItems.find(item => 
      item.children?.some(child => child.key === path)
    )
    if (parentMatch) return [path]
    
    // Check for prefix match
    const prefixMatch = menuItems.find(item => 
      path.startsWith(item.key) && item.key !== '/'
    )
    if (prefixMatch) return [prefixMatch.key]
    
    return []
  }

  return (
    <Sider 
      trigger={null} 
      collapsible 
      collapsed={collapsed}
      theme="dark"
    >
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
  )
}

export default Sidebar