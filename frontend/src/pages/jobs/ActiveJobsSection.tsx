import React, { useState, useEffect } from 'react';
import { Table } from 'antd';
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

  return (
    <div
      className={className}
      style={{
        padding: 16,
        marginBottom: 16,
        border: '1px solid #d9d9d9',
        borderRadius: 4,
        backgroundColor: '#fff',
      }}
    >
      <h3>Test 4: With useState + useEffect + Table</h3>
      <p>Mounted at: {mountTime}</p>
      <p>Active Jobs: {activeJobs.length}</p>
      <p>Loading: {loading ? 'Yes' : 'No'}</p>
      <p>Collapsed: {collapsed ? 'Yes' : 'No'}</p>

      <div style={{ marginBottom: 16 }}>
        <button
          onClick={() => setCollapsed(!collapsed)}
          style={{ marginRight: 8 }}
        >
          Toggle Collapsed
        </button>
        <button
          onClick={() =>
            setActiveJobs([
              { id: '1', type: 'test', status: 'running', progress: 50 },
              { id: '2', type: 'sync', status: 'pending', progress: 0 },
            ])
          }
          style={{ marginRight: 8 }}
        >
          Add Test Jobs
        </button>
        <button onClick={() => setLoading(!loading)} style={{ marginRight: 8 }}>
          Toggle Loading
        </button>
        <button onClick={() => setActiveJobs([])}>Clear Jobs</button>
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
    </div>
  );
};

export default ActiveJobsSection;
