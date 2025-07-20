import React from 'react';
import { Radio, Badge, RadioChangeEvent } from 'antd';
import styles from './StatusFilter.module.scss';

interface StatusCounts {
  draft: number;
  reviewing: number;
  applied: number;
  cancelled: number;
}

interface StatusFilterProps {
  value: string | null;
  onChange: (value: string | null) => void;
  counts: StatusCounts;
}

export const StatusFilter: React.FC<StatusFilterProps> = ({
  value,
  onChange,
  counts,
}) => {
  const statusOptions = [
    {
      label: 'All',
      value: null,
      count: Object.values(counts).reduce((a, b) => a + b, 0),
    },
    {
      label: 'Draft',
      value: 'draft',
      count: counts.draft,
      color: '#1890ff',
    },
    {
      label: 'Reviewing',
      value: 'reviewing',
      count: counts.reviewing,
      color: '#fa8c16',
    },
    {
      label: 'Applied',
      value: 'applied',
      count: counts.applied,
      color: '#52c41a',
    },
    {
      label: 'Cancelled',
      value: 'cancelled',
      count: counts.cancelled,
      color: '#f5222d',
    },
  ];

  return (
    <div className={styles.statusFilter}>
      <Radio.Group
        value={value}
        onChange={(e: RadioChangeEvent) => onChange(e.target.value)}
        buttonStyle="solid"
        size="middle"
      >
        {statusOptions.map((option) => (
          <Radio.Button key={option.value || 'all'} value={option.value}>
            <span className={styles.optionLabel}>
              {option.label}
              <Badge
                count={option.count}
                showZero
                style={{
                  marginLeft: 8,
                  backgroundColor: option.color || '#d9d9d9',
                }}
              />
            </span>
          </Radio.Button>
        ))}
      </Radio.Group>
    </div>
  );
};
