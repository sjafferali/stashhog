import React, { useEffect, useState } from 'react';
import { Card, Table, Button, Space, Tag, message } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import { AnalysisPlan } from '@/types/models';

const PlanList: React.FC = () => {
  const navigate = useNavigate();
  const [plans, setPlans] = useState<AnalysisPlan[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void fetchPlans();
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
          pending: 'orange',
          applied: 'green',
          failed: 'red',
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

  return (
    <div>
      <h1>Analysis Plans</h1>
      <Card
        extra={
          <Button type="primary" icon={<PlusOutlined />}>
            Create Plan
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={plans}
          loading={loading}
          rowKey="id"
          pagination={false}
        />
      </Card>
    </div>
  );
};

export default PlanList;
