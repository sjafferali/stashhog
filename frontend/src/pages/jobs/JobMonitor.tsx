import React, { useState, useEffect } from 'react';
import { Card, Table, Tag, Progress, Button, Space } from 'antd';
import {
  SyncOutlined,
  CloseCircleOutlined,
  RedoOutlined,
} from '@ant-design/icons';
import { apiClient } from '@/services/apiClient';
import { Job } from '@/types/models';

const JobMonitor: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [_refreshInterval, setRefreshInterval] =
    useState<NodeJS.Timeout | null>(null);

  const fetchJobs = async () => {
    try {
      setLoading(true);
      const jobs = await apiClient.getJobs({ limit: 50 });
      setJobs(jobs);
    } catch (error) {
      console.error('Failed to fetch jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchJobs();

    // Set up auto-refresh every 5 seconds
    const interval = setInterval(() => {
      void fetchJobs();
    }, 5000);
    setRefreshInterval(interval);

    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, []);

  const handleCancel = async (jobId: string) => {
    try {
      await apiClient.cancelJob(jobId);
      await fetchJobs();
    } catch (error) {
      console.error('Failed to cancel job:', error);
    }
  };

  const handleRetry = async (jobId: string) => {
    try {
      await apiClient.retryJob(jobId);
      await fetchJobs();
    } catch (error) {
      console.error('Failed to retry job:', error);
    }
  };

  const columns = [
    {
      title: 'Job Type',
      dataIndex: 'type',
      key: 'type',
      render: (type: unknown) => {
        const typeStr = String(type);
        const typeLabels: Record<string, string> = {
          sync_all: 'Full Sync',
          scene_sync: 'Scene Sync',
          scene_analysis: 'Scene Analysis',
          batch_analysis: 'Batch Analysis',
        };
        const color = typeStr.includes('sync') ? 'blue' : 'green';
        return (
          <Tag color={color}>
            {typeLabels[typeStr] || typeStr.toUpperCase()}
          </Tag>
        );
      },
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: unknown) => {
        const statusStr = String(status);
        const color =
          statusStr === 'completed'
            ? 'green'
            : statusStr === 'failed'
              ? 'red'
              : statusStr === 'running'
                ? 'blue'
                : statusStr === 'cancelled'
                  ? 'orange'
                  : 'default';
        return <Tag color={color}>{statusStr.toUpperCase()}</Tag>;
      },
    },
    {
      title: 'Progress',
      key: 'progress',
      render: (_: unknown, record: Job) => (
        <Progress
          percent={Math.round(record.progress || 0)}
          status={
            record.status === 'failed'
              ? 'exception'
              : record.status === 'completed'
                ? 'success'
                : 'active'
          }
        />
      ),
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: unknown) => new Date(String(date)).toLocaleString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: unknown, record: Job) => (
        <Space>
          {record.status === 'running' && (
            <Button
              type="link"
              danger
              icon={<CloseCircleOutlined />}
              size="small"
              onClick={() => void handleCancel(record.id)}
            >
              Cancel
            </Button>
          )}
          {record.status === 'failed' && (
            <Button
              type="link"
              icon={<RedoOutlined />}
              size="small"
              onClick={() => void handleRetry(record.id)}
            >
              Retry
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <h1>Job Monitor</h1>
      <Card
        extra={
          <Button
            icon={<SyncOutlined />}
            onClick={() => void fetchJobs()}
            loading={loading}
          >
            Refresh
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={jobs}
          loading={loading}
          rowKey="id"
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
          }}
        />
      </Card>
    </div>
  );
};

export default JobMonitor;
