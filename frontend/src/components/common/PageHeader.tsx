import React from 'react';
import { Typography, Space, Breadcrumb } from 'antd';
import { Link } from 'react-router-dom';
import styles from './PageHeader.module.scss';

const { Title } = Typography;

export interface BreadcrumbItem {
  path?: string;
  breadcrumbName: string;
}

export interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  breadcrumbs?: BreadcrumbItem[];
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  actions,
  breadcrumbs,
}) => {
  const breadcrumbItems = breadcrumbs?.map((item, index) => ({
    key: index,
    title: item.path ? (
      <Link to={item.path}>{item.breadcrumbName}</Link>
    ) : (
      item.breadcrumbName
    ),
  }));

  return (
    <div className={styles.pageHeader}>
      <div style={{ padding: '16px 24px', background: '#fff' }}>
        {breadcrumbItems && breadcrumbItems.length > 0 && (
          <Breadcrumb items={breadcrumbItems} style={{ marginBottom: 16 }} />
        )}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Space direction="vertical" size={0}>
            <Title level={4} style={{ margin: 0 }}>
              {title}
            </Title>
            {subtitle && (
              <Typography.Text type="secondary">{subtitle}</Typography.Text>
            )}
          </Space>
          {actions && <Space>{actions}</Space>}
        </div>
      </div>
    </div>
  );
};
