import React, { useEffect, useState, useMemo } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  message,
  Badge,
  Spin,
  Modal,
} from 'antd';
import {
  EditOutlined,
  CloseOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import { AnalysisPlan, Job } from '@/types/models';
import { StatusSummary } from '@/components/analysis/StatusSummary';
import styles from './PlanList.module.scss';

const PlanList: React.FC = () => {
  const navigate = useNavigate();
  const [plans, setPlans] = useState<AnalysisPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [runningJobs, setRunningJobs] = useState<Job[]>([]);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

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
      width: 120,
      render: (status: unknown) => {
        const statusStr = String(status).toLowerCase();
        const colorMap: Record<string, string> = {
          draft: 'blue',
          reviewing: 'orange',
          applied: 'green',
          cancelled: 'red',
        };
        return (
          <Tag
            color={colorMap[statusStr] || 'default'}
            style={{ fontWeight: 500 }}
          >
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
            icon={<CloseOutlined />}
            onClick={() => {
              void handleCancel(record.id);
            }}
            disabled={
              record.status.toLowerCase() === 'applied' ||
              record.status.toLowerCase() === 'cancelled'
            }
          >
            Cancel
          </Button>
        </Space>
      ),
    },
  ];

  const handleCancel = async (id: number) => {
    try {
      await apiClient.cancelAnalysisPlan(id);
      void message.success('Plan cancelled successfully');
      void fetchPlans();
    } catch (error) {
      console.error('Failed to cancel plan:', error);
      void message.error('Failed to cancel plan');
    }
  };

  const handleBulkAccept = async () => {
    const selectedPlans = plans.filter((plan) =>
      selectedRowKeys.includes(plan.id)
    );
    const reviewingPlans = selectedPlans.filter(
      (plan) => plan.status.toLowerCase() === 'reviewing'
    );

    if (reviewingPlans.length === 0) {
      void message.warning('Please select plans that are in reviewing status');
      return;
    }

    Modal.confirm({
      title: 'Accept All Changes',
      content: `Are you sure you want to accept all changes for ${reviewingPlans.length} plan(s)?`,
      onOk: async () => {
        let successCount = 0;
        let errorCount = 0;

        for (const plan of reviewingPlans) {
          try {
            await apiClient.bulkUpdateAnalysisPlan(plan.id, 'accept_all');
            successCount++;
          } catch (error) {
            console.error(
              `Failed to accept changes for plan ${plan.id}:`,
              error
            );
            errorCount++;
          }
        }

        if (successCount > 0) {
          void message.success(
            `Successfully accepted changes for ${successCount} plan(s)`
          );
          void fetchPlans();
          setSelectedRowKeys([]);
        }
        if (errorCount > 0) {
          void message.error(
            `Failed to accept changes for ${errorCount} plan(s)`
          );
        }
      },
    });
  };

  const handleBulkReject = async () => {
    const selectedPlans = plans.filter((plan) =>
      selectedRowKeys.includes(plan.id)
    );
    const reviewingPlans = selectedPlans.filter(
      (plan) => plan.status.toLowerCase() === 'reviewing'
    );

    if (reviewingPlans.length === 0) {
      void message.warning('Please select plans that are in reviewing status');
      return;
    }

    Modal.confirm({
      title: 'Reject All Changes',
      content: `Are you sure you want to reject all changes for ${reviewingPlans.length} plan(s)? This will cancel the plans.`,
      onOk: async () => {
        let successCount = 0;
        let errorCount = 0;

        for (const plan of reviewingPlans) {
          try {
            await apiClient.bulkUpdateAnalysisPlan(plan.id, 'reject_all');
            successCount++;
          } catch (error) {
            console.error(
              `Failed to reject changes for plan ${plan.id}:`,
              error
            );
            errorCount++;
          }
        }

        if (successCount > 0) {
          void message.success(
            `Successfully rejected changes for ${successCount} plan(s)`
          );
          void fetchPlans();
          setSelectedRowKeys([]);
        }
        if (errorCount > 0) {
          void message.error(
            `Failed to reject changes for ${errorCount} plan(s)`
          );
        }
      },
    });
  };

  const statusCounts = useMemo(() => {
    const counts = {
      draft: 0,
      reviewing: 0,
      applied: 0,
      cancelled: 0,
    };

    plans.forEach((plan) => {
      const normalizedStatus = plan.status.toLowerCase();
      if (normalizedStatus in counts) {
        counts[normalizedStatus as keyof typeof counts]++;
      }
    });

    return counts;
  }, [plans]);

  const totalChangesReviewing = useMemo(() => {
    return plans
      .filter((plan) => plan.status.toLowerCase() === 'reviewing')
      .reduce((sum, plan) => sum + (plan.total_changes || 0), 0);
  }, [plans]);

  const filteredAndSortedPlans = useMemo(() => {
    let filtered = [...plans];

    // Filter by status
    if (statusFilter) {
      filtered = filtered.filter(
        (plan) => plan.status.toLowerCase() === statusFilter
      );
    }

    // Sort by status priority and then by creation date
    const statusPriority: Record<string, number> = {
      reviewing: 1,
      draft: 2,
      applied: 3,
      cancelled: 4,
    };

    filtered.sort((a, b) => {
      // First sort by status priority
      const priorityDiff =
        statusPriority[a.status.toLowerCase()] -
        statusPriority[b.status.toLowerCase()];
      if (priorityDiff !== 0) {
        return priorityDiff;
      }

      // Then sort by creation date (most recent first)
      return (
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
    });

    return filtered;
  }, [plans, statusFilter]);

  return (
    <div>
      <div className={styles.pageHeader}>
        <h1>Analysis Plans</h1>
        {runningJobs.length > 0 && (
          <Badge count={runningJobs.length} className={styles.runningJobsBadge}>
            <div className={styles.runningJobsIndicator}>
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

      <StatusSummary
        draft={statusCounts.draft}
        reviewing={statusCounts.reviewing}
        applied={statusCounts.applied}
        cancelled={statusCounts.cancelled}
        totalChangesReviewing={totalChangesReviewing}
        activeFilter={statusFilter}
        onFilterChange={setStatusFilter}
      />

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16,
        }}
      >
        <Space>
          {selectedRowKeys.length > 0 && (
            <>
              <span>{selectedRowKeys.length} plan(s) selected</span>
              <Button
                icon={<CheckCircleOutlined />}
                onClick={() => {
                  void handleBulkAccept();
                }}
              >
                Accept All Changes
              </Button>
              <Button
                danger
                icon={<CloseCircleOutlined />}
                onClick={() => {
                  void handleBulkReject();
                }}
              >
                Reject All Changes
              </Button>
            </>
          )}
        </Space>
      </div>

      <Card>
        <div
          style={
            {
              '--reviewing-bg': '#fff7e6',
              '--draft-bg': '#e6f7ff',
              '--applied-bg': '#f6ffed',
              '--cancelled-bg': '#fff1f0',
            } as React.CSSProperties
          }
        >
          <Table<AnalysisPlan>
            columns={columns}
            dataSource={filteredAndSortedPlans}
            loading={loading}
            rowKey="id"
            {...({
              rowSelection: {
                selectedRowKeys,
                onChange: (newSelectedRowKeys: React.Key[]) => {
                  setSelectedRowKeys(newSelectedRowKeys);
                },
              },
            } as any)} // eslint-disable-line @typescript-eslint/no-explicit-any
            pagination={{
              pageSize: 20,
              showSizeChanger: true,
              showTotal: (total, range) =>
                `${range[0]}-${range[1]} of ${total} plans`,
            }}
            rowClassName={(record) =>
              `plan-row plan-${record.status.toLowerCase()}`
            }
            onRow={(record) => ({
              onClick: (e) => {
                // Don't navigate if clicking on action buttons or checkbox
                const target = e.target as HTMLElement;
                if (
                  !target.closest('button') &&
                  !target.closest('a') &&
                  !target.closest('.ant-checkbox-wrapper')
                ) {
                  void navigate(`/analysis/plans/${record.id}`);
                }
              },
            })}
          />
        </div>
      </Card>
    </div>
  );
};

export default PlanList;
