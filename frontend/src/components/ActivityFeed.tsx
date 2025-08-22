import React, { useEffect, useState } from 'react';
import {
  Card,
  Timeline,
  Typography,
  Tag,
  Space,
  Button,
  Select,
  Empty,
  Spin,
} from 'antd';
import {
  CloseCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
  SyncOutlined,
  FilterOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { formatDistanceToNow, format } from 'date-fns';
import { DaemonActivity } from '@/types/daemon';
import daemonService from '@/services/daemonService';

const { Text, Title } = Typography;

interface ActivityFeedProps {
  limit?: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

const ActivityFeed: React.FC<ActivityFeedProps> = ({
  limit = 50,
  autoRefresh = true,
  refreshInterval = 30000, // 30 seconds
}) => {
  const [activities, setActivities] = useState<DaemonActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState<string | undefined>(
    undefined
  );
  const [isRefreshing, setIsRefreshing] = useState(false);

  const loadActivities = async (showLoading = true) => {
    if (showLoading) setLoading(true);
    else setIsRefreshing(true);

    try {
      const data = await daemonService.getAllDaemonActivities({
        limit,
        severity: severityFilter,
      });
      setActivities(data);
    } catch (error) {
      console.error('Failed to load activities:', error);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    void loadActivities();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [severityFilter]);

  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      void loadActivities(false);
    }, refreshInterval);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefresh, refreshInterval, severityFilter]);

  const getActivityIcon = (activity: DaemonActivity) => {
    const { activity_type, severity } = activity;

    if (severity === 'error' || activity_type.includes('ERROR')) {
      return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
    }
    if (severity === 'warning' || activity_type.includes('WARNING')) {
      return <WarningOutlined style={{ color: '#faad14' }} />;
    }
    if (activity_type.includes('JOB')) {
      return <ThunderboltOutlined style={{ color: '#1890ff' }} />;
    }
    if (activity_type.includes('STATUS')) {
      return <SyncOutlined style={{ color: '#722ed1' }} />;
    }
    return <InfoCircleOutlined style={{ color: '#52c41a' }} />;
  };

  const getActivityColor = (severity: string) => {
    switch (severity) {
      case 'error':
        return 'red';
      case 'warning':
        return 'orange';
      default:
        return 'gray';
    }
  };

  const getSeverityTag = (severity: string) => {
    let color = 'default';
    switch (severity) {
      case 'error':
        color = 'error';
        break;
      case 'warning':
        color = 'warning';
        break;
      case 'info':
        color = 'success';
        break;
    }
    return <Tag color={color}>{severity.toUpperCase()}</Tag>;
  };

  const formatActivityType = (type: string) => {
    return type
      .replace(/_/g, ' ')
      .toLowerCase()
      .replace(/\b\w/g, (l) => l.toUpperCase());
  };

  const getActivityTypeColor = (type: string, message: string) => {
    // Check for job-related activities
    if (
      type.includes('JOB') ||
      message.toLowerCase().includes('job launched')
    ) {
      return 'success'; // green
    }
    if (
      message.toLowerCase().includes('job completed') ||
      message.toLowerCase().includes('job finished')
    ) {
      return 'blue';
    }
    if (
      message.toLowerCase().includes('job cancelled') ||
      message.toLowerCase().includes('job failed')
    ) {
      return 'error'; // red
    }
    // Check for status-related activities
    if (type.includes('STATUS')) {
      if (
        message.toLowerCase().includes('started') ||
        message.toLowerCase().includes('running')
      ) {
        return 'success';
      }
      if (message.toLowerCase().includes('stopped')) {
        return 'orange';
      }
    }
    // Default based on severity or activity type
    if (type.includes('ERROR')) {
      return 'error';
    }
    if (type.includes('WARNING')) {
      return 'warning';
    }
    return 'default';
  };

  if (loading) {
    return (
      <Card title="Activity Feed" style={{ height: '100%' }}>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin size="large" />
        </div>
      </Card>
    );
  }

  return (
    <Card
      title={
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Title level={5} style={{ margin: 0 }}>
            Activity Feed
          </Title>
          <Space>
            <Select
              style={{ width: 120 }}
              placeholder="Filter"
              allowClear
              value={severityFilter}
              onChange={setSeverityFilter}
              suffixIcon={<FilterOutlined />}
              options={[
                { label: 'Info', value: 'info' },
                { label: 'Warning', value: 'warning' },
                { label: 'Error', value: 'error' },
              ]}
            />
            <Button
              icon={isRefreshing ? <SyncOutlined spin /> : <ReloadOutlined />}
              onClick={() => void loadActivities(false)}
              disabled={isRefreshing}
            />
          </Space>
        </Space>
      }
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
      bodyStyle={{ flex: 1, overflowY: 'auto', padding: '16px' }}
    >
      {activities.length === 0 ? (
        <Empty
          description="No activities to display"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      ) : (
        <Timeline>
          {activities.map((activity) => (
            <Timeline.Item
              key={activity.id}
              dot={getActivityIcon(activity)}
              color={getActivityColor(activity.severity)}
            >
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <Space>
                  <Text strong>{activity.daemon_name || 'Unknown Daemon'}</Text>
                  {getSeverityTag(activity.severity)}
                  <Tag
                    color={getActivityTypeColor(
                      activity.activity_type,
                      activity.message
                    )}
                  >
                    {formatActivityType(activity.activity_type)}
                  </Tag>
                </Space>
                <Text>{activity.message}</Text>
                <Space>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {formatDistanceToNow(new Date(activity.created_at), {
                      addSuffix: true,
                    })}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    •
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {format(new Date(activity.created_at), 'HH:mm:ss')}
                  </Text>
                </Space>
                {activity.details && (
                  <details style={{ marginTop: 4 }}>
                    <summary style={{ cursor: 'pointer', fontSize: 12 }}>
                      <Text type="secondary">Details</Text>
                    </summary>
                    <pre style={{ fontSize: 11, marginTop: 4 }}>
                      {JSON.stringify(activity.details, null, 2)}
                    </pre>
                  </details>
                )}
              </Space>
            </Timeline.Item>
          ))}
        </Timeline>
      )}
    </Card>
  );
};

export default ActivityFeed;
