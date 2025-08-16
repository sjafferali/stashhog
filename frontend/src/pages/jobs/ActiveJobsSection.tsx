import React, { useState, useEffect } from 'react';
import { Table, Card, Badge, Space } from 'antd';
import {
  PlayCircleOutlined,
  SyncOutlined,
  UpOutlined,
  DownOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

interface Job {
  id: string;
  type: string;
  status: string;
  progress?: number;
}

interface ActiveJobsSectionProps {
  onCancel: (jobId: string) => Promise<void>;
  onRetry: (jobId: string) => Promise<void>;
  onRefresh: () => void;
  className?: string;
}

const ActiveJobsSection: React.FC<ActiveJobsSectionProps> = ({ className }) => {
  // TEST 3: Adding useEffect to test if lifecycle hooks break navigation
  const [activeJobs, setActiveJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [mountTime, setMountTime] = useState<string>('');

  // Test useEffect on mount
  useEffect(() => {
    console.log('ActiveJobsSection mounted');
    setMountTime(new Date().toLocaleTimeString());

    // Cleanup function
    return () => {
      console.log('ActiveJobsSection unmounting');
    };
  }, []);

  // Test useEffect that depends on state
  useEffect(() => {
    console.log('Active jobs changed:', activeJobs.length);
  }, [activeJobs]);

  // Test useEffect that runs on every render
  useEffect(() => {
    console.log('Component rendered');
  });

  // Define table columns for testing
  const columns: ColumnsType<Job> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
    },
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
    },
    {
      title: 'Progress',
      dataIndex: 'progress',
      key: 'progress',
      render: (progress: number) => `${progress || 0}%`,
    },
  ];

  const runningCount = activeJobs.filter(
    (job) => job.status === 'running'
  ).length;
  const pendingCount = activeJobs.filter(
    (job) => job.status === 'pending'
  ).length;

  return (
    <Card
      className={className}
      title={
        <Space>
          <PlayCircleOutlined />
          <span>Test 5: With useState + useEffect + Table + Card</span>
          <Badge count={runningCount} showZero={false} color="blue" />
          <Badge count={pendingCount} showZero={false} color="orange" />
        </Space>
      }
      extra={
        <Space>
          <button onClick={() => setCollapsed(!collapsed)}>
            {collapsed ? <DownOutlined /> : <UpOutlined />}
            {collapsed ? 'Show' : 'Hide'}
          </button>
          <button onClick={() => setLoading(!loading)}>
            <SyncOutlined spin={loading} />
            Refresh
          </button>
        </Space>
      }
      size="small"
      style={{ marginBottom: 16 }}
    >
      <div style={{ marginBottom: 16 }}>
        <p>
          <strong>Mounted at:</strong> {mountTime}
        </p>
        <p>
          <strong>Active Jobs:</strong> {activeJobs.length}
        </p>
        <p>
          <strong>Loading:</strong> {loading ? 'Yes' : 'No'}
        </p>
        <p>
          <strong>Collapsed:</strong> {collapsed ? 'Yes' : 'No'}
        </p>
      </div>

      <div style={{ marginBottom: 16 }}>
        <button
          onClick={() =>
            setActiveJobs([
              { id: '1', type: 'test', status: 'running', progress: 50 },
              { id: '2', type: 'sync', status: 'pending', progress: 0 },
              { id: '3', type: 'analysis', status: 'running', progress: 75 },
            ])
          }
          style={{ marginRight: 8 }}
        >
          Add Test Jobs
        </button>
        <button onClick={() => setActiveJobs([])} style={{ marginRight: 8 }}>
          Clear Jobs
        </button>
      </div>

      {!collapsed && (
        <Table
          columns={columns}
          dataSource={activeJobs.map((job) => ({ ...job, key: job.id }))}
          pagination={false}
          size="small"
          loading={loading}
        />
      )}
    </Card>
  );
};

export default ActiveJobsSection;
