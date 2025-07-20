import React from 'react';
import { Card, Statistic, Row, Col } from 'antd';
import {
  FileTextOutlined,
  FileSearchOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import styles from './StatusSummary.module.scss';

interface StatusSummaryProps {
  draft: number;
  reviewing: number;
  applied: number;
  cancelled: number;
  totalChangesReviewing: number;
}

export const StatusSummary: React.FC<StatusSummaryProps> = ({
  draft,
  reviewing,
  applied,
  cancelled,
  totalChangesReviewing,
}) => {
  const summaryCards = [
    {
      title: 'Draft',
      value: draft,
      icon: <FileTextOutlined />,
      color: '#1890ff',
      description: 'Plans in draft',
    },
    {
      title: 'Reviewing',
      value: reviewing,
      icon: <FileSearchOutlined />,
      color: '#fa8c16',
      description: `${totalChangesReviewing} changes to review`,
      highlight: true,
    },
    {
      title: 'Applied',
      value: applied,
      icon: <CheckCircleOutlined />,
      color: '#52c41a',
      description: 'Successfully applied',
    },
    {
      title: 'Cancelled',
      value: cancelled,
      icon: <CloseCircleOutlined />,
      color: '#f5222d',
      description: 'Plans cancelled',
    },
  ];

  return (
    <Row gutter={16} className={styles.statusSummary}>
      {summaryCards.map((card) => (
        <Col xs={24} sm={12} md={6} key={card.title}>
          <Card
            className={`${styles.summaryCard} ${card.highlight ? styles.highlight : ''}`}
            bordered={false}
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
              valueStyle={{ color: card.color }}
              suffix={
                <span className={styles.description}>{card.description}</span>
              }
            />
          </Card>
        </Col>
      ))}
    </Row>
  );
};
