import React from 'react';
import { PageHeader as AntPageHeader } from '@ant-design/pro-layout';
import { Breadcrumb } from 'antd';
import { Link } from 'react-router-dom';
import styles from './PageHeader.module.scss';

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
      <AntPageHeader
        title={title}
        subTitle={subtitle}
        extra={actions}
        breadcrumb={breadcrumbItems && breadcrumbItems.length > 0 ? 
          <Breadcrumb items={breadcrumbItems} /> : 
          undefined
        }
      />
    </div>
  );
};