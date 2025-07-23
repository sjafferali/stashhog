import React from 'react';
import { Card, Statistic, Row, Col } from 'antd';
import {
  FileTextOutlined,
  FileSearchOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import styles from './StatusSummary.module.scss';

interface StatusSummaryProps {
  pending: number;
  draft: number;
  reviewing: number;
  applied: number;
  cancelled: number;
  totalChangesReviewing: number;
  activeFilter: string | null;
  onFilterChange: (status: string | null) => void;
}

export const StatusSummary: React.FC<StatusSummaryProps> = ({
  pending,
  draft,
  reviewing,
  applied,
  cancelled,
  totalChangesReviewing,
  activeFilter,
  onFilterChange,
}) => {
  const totalPlans = pending + draft + reviewing + applied + cancelled;

  const summaryCards = [
    {
      title: 'All',
      value: totalPlans,
      icon: <FileTextOutlined />,
      color: '#8c8c8c',
      description: 'Total plans',
      status: null,
    },
    {
      title: 'Pending',
      value: pending,
      icon: <ClockCircleOutlined />,
      color: '#722ed1',
      description: 'Plans being created',
      status: 'pending',
    },
    {
      title: 'Draft',
      value: draft,
      icon: <FileTextOutlined />,
      color: '#1890ff',
      description: 'Plans in draft',
      status: 'draft',
    },
    {
      title: 'Reviewing',
      value: reviewing,
      icon: <FileSearchOutlined />,
      color: '#fa8c16',
      description: `${totalChangesReviewing} changes to review`,
      highlight: true,
      status: 'reviewing',
    },
    {
      title: 'Applied',
      value: applied,
      icon: <CheckCircleOutlined />,
      color: '#52c41a',
      description: 'Successfully applied',
      status: 'applied',
    },
    {
      title: 'Cancelled',
      value: cancelled,
      icon: <CloseCircleOutlined />,
      color: '#f5222d',
      description: 'Plans cancelled',
      status: 'cancelled',
    },
  ];

  return (
    <Row gutter={16} className={styles.statusSummary}>
      {summaryCards.map((card) => (
        <Col
          xs={24}
          sm={12}
          md={8}
          lg={8}
          xl={4}
          key={card.title}
          className={styles.statusCol}
        >
          <Card
            className={`${styles.summaryCard} ${card.highlight ? styles.highlight : ''} ${activeFilter === card.status ? styles.active : ''}`}
            bordered={false}
            onClick={() => onFilterChange(card.status)}
            style={{ cursor: 'pointer' }}
          >
            <Statistic
              title={
                <span className={styles.cardTitle}>
                  <span className={styles.icon} style={{ color: card.color }}>
                    {card.icon}
                  </span>
                  {card.title}
                </span>
              }
              value={card.value}
              valueStyle={{ color: card.color, fontSize: '28px' }}
            />
            <div className={styles.description}>{card.description}</div>
          </Card>
        </Col>
      ))}
    </Row>
  );
};
