import React from 'react';
import { Card, Skeleton, Tooltip } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import styles from './StatCard.module.scss';

export interface StatCardProps {
  title: string;
  value: string | number;
  icon?: React.ReactNode;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  loading?: boolean;
  suffix?: string;
  precision?: number;
  tooltip?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon,
  trend,
  loading = false,
  suffix,
  precision = 0,
  tooltip,
}) => {
  const formatValue = () => {
    if (typeof value === 'number') {
      return value.toLocaleString(undefined, {
        minimumFractionDigits: precision,
        maximumFractionDigits: precision,
      });
    }
    return value;
  };

  const content = (
    <Card className={styles.statCard} bordered={false}>
      {loading ? (
        <>
          <Skeleton.Input
            active
            size="small"
            className={styles.titleSkeleton}
          />
          <Skeleton.Input
            active
            size="large"
            className={styles.valueSkeleton}
          />
          <Skeleton.Input
            active
            size="small"
            className={styles.trendSkeleton}
          />
        </>
      ) : (
        <>
          <div className={styles.header}>
            <span className={styles.title}>{title}</span>
            {icon && <div className={styles.icon}>{icon}</div>}
          </div>
          <div className={styles.value}>
            {formatValue()}
            {suffix && <span className={styles.suffix}>{suffix}</span>}
          </div>
          {trend && (
            <div
              className={`${styles.trend} ${trend.isPositive ? styles.positive : styles.negative}`}
            >
              {trend.isPositive ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
              <span className={styles.trendValue}>
                {Math.abs(trend.value).toFixed(1)}%
              </span>
              <span className={styles.trendLabel}>
                {trend.isPositive ? 'increase' : 'decrease'}
              </span>
            </div>
          )}
        </>
      )}
    </Card>
  );

  if (tooltip) {
    return <Tooltip title={tooltip}>{content}</Tooltip>;
  }

  return content;
};
