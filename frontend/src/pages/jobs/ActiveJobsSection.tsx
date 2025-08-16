import React, { useState, useEffect } from 'react';
import { Table, Card, Badge, Space } from 'antd';
import {
  PlayCircleOutlined,
  SyncOutlined,
  UpOutlined,
  DownOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useWebSocket } from '@/hooks/useWebSocket';

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
  // TEST 6: Adding WebSocket to test if WebSocket breaks navigation
  const [activeJobs, setActiveJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [mountTime, setMountTime] = useState<string>('');
  const [wsMessages, setWsMessages] = useState<number>(0);

  // This is the critical test - adding WebSocket connection
  const { lastMessage } = useWebSocket('/api/jobs/ws');

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

  // Handle WebSocket messages - this is where the problem likely occurs
  useEffect(() => {
    if (lastMessage) {
      console.log('WebSocket message received:', lastMessage);
      setWsMessages((prev) => prev + 1);

      // Simulate processing WebSocket messages like the original component
      if (typeof lastMessage === 'object') {
        const update = lastMessage as { type: string; job: Job };
        if (update.type === 'job_update' && update.job) {
          const job = update.job;
          const isActiveJob = ['pending', 'running', 'cancelling'].includes(
            job.status
          );

          setActiveJobs((prevJobs) => {
            const jobIndex = prevJobs.findIndex((j) => j.id === job.id);
            if (isActiveJob) {
              if (jobIndex >= 0) {
                const newJobs = [...prevJobs];
                newJobs[jobIndex] = job;
                return newJobs;
              } else {
                return [...prevJobs, job];
              }
            } else {
              if (jobIndex >= 0) {
                return prevJobs.filter((j) => j.id !== job.id);
              }
            }
            return prevJobs;
          });
        }
      }
    }
  }, [lastMessage]);

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
          <span>
            Test 6: With useState + useEffect + Table + Card + WebSocket
          </span>
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
        <p>
          <strong>WebSocket Messages:</strong> {wsMessages}
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
