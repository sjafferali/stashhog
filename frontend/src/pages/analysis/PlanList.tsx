import React, { useEffect, useState, useMemo } from 'react';
import { Card, Table, Button, Space, Tag, message, Badge, Spin } from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import { AnalysisPlan, Job } from '@/types/models';
import { FilterPanel, FilterConfig } from '@/components/common/FilterPanel';

const PlanList: React.FC = () => {
  const navigate = useNavigate();
  const [plans, setPlans] = useState<AnalysisPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [runningJobs, setRunningJobs] = useState<Job[]>([]);
  const [filterValues, setFilterValues] = useState<
    Record<
      string,
      string | number | boolean | string[] | [string, string] | null | undefined
    >
  >({});

  useEffect(() => {
    void fetchPlans();
    void fetchRunningJobs();

    // Poll for running jobs every 5 seconds
    const interval = setInterval(() => {
      void fetchRunningJobs();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const fetchPlans = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getAnalysisPlans();
      setPlans(data);
    } catch (error) {
      console.error('Failed to fetch plans:', error);
      void message.error('Failed to load analysis plans');
    } finally {
      setLoading(false);
    }
  };

  const fetchRunningJobs = async () => {
    try {
      const jobs = await apiClient.getJobs({ status: 'running' });
      setRunningJobs(jobs.filter((job) => job.status === 'running'));
    } catch (error) {
      console.error('Failed to fetch running jobs:', error);
    }
  };

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: unknown) => {
        const statusStr = String(status);
        const colorMap: Record<string, string> = {
          draft: 'blue',
          reviewing: 'orange',
          applied: 'green',
          cancelled: 'red',
        };
        return (
          <Tag color={colorMap[statusStr] || 'default'}>
            {statusStr.charAt(0).toUpperCase() + statusStr.slice(1)}
          </Tag>
        );
      },
    },
    {
      title: 'Total Scenes',
      dataIndex: 'total_scenes',
      key: 'total_scenes',
    },
    {
      title: 'Total Changes',
      dataIndex: 'total_changes',
      key: 'total_changes',
    },
    {
      title: 'Created At',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: unknown) => new Date(String(date)).toLocaleString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: unknown, record: AnalysisPlan) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => {
              void navigate(`/analysis/plans/${record.id}`);
            }}
          >
            View
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => {
              void handleDelete(record.id);
            }}
          >
            Delete
          </Button>
        </Space>
      ),
    },
  ];

  const handleDelete = async (id: number) => {
    try {
      await apiClient.deleteAnalysisPlan(id);
      void message.success('Plan deleted successfully');
      void fetchPlans();
    } catch (error) {
      console.error('Failed to delete plan:', error);
      void message.error('Failed to delete plan');
    }
  };

  const filterConfig: FilterConfig[] = [
    {
      name: 'status',
      label: 'Status',
      type: 'multiselect',
      options: [
        { label: 'Draft', value: 'draft' },
        { label: 'Reviewing', value: 'reviewing' },
        { label: 'Applied', value: 'applied' },
        { label: 'Cancelled', value: 'cancelled' },
      ],
      placeholder: 'Filter by status',
    },
  ];

  const filteredPlans = useMemo(() => {
    let filtered = [...plans];

    // Filter by status
    const statusFilter = filterValues.status as string[] | undefined;
    if (statusFilter && statusFilter.length > 0) {
      filtered = filtered.filter((plan) => statusFilter.includes(plan.status));
    }

    return filtered;
  }, [plans, filterValues]);

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16 }}>
        <h1 style={{ margin: 0, flex: 1 }}>Analysis Plans</h1>
        {runningJobs.length > 0 && (
          <Badge count={runningJobs.length} style={{ marginRight: 20 }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '8px 16px',
                background: '#f0f2f5',
                borderRadius: 4,
                gap: 8,
              }}
            >
              <Spin
                indicator={<LoadingOutlined style={{ fontSize: 16 }} spin />}
              />
              <span>
                {runningJobs.length} job{runningJobs.length > 1 ? 's' : ''}{' '}
                running
              </span>
            </div>
          </Badge>
        )}
      </div>

      <FilterPanel
        filters={filterConfig}
        values={filterValues}
        onChange={setFilterValues}
        onReset={() => setFilterValues({})}
        collapsible={false}
      />

      <Card
        style={{ marginTop: 16 }}
        extra={
          <Button type="primary" icon={<PlusOutlined />}>
            Create Plan
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={filteredPlans}
          loading={loading}
          rowKey="id"
          pagination={false}
        />
      </Card>
    </div>
  );
};

export default PlanList;
