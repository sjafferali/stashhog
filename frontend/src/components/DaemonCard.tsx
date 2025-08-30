import React, { useState, useEffect } from 'react';
import {
  Card,
  Tag,
  Button,
  Space,
  Switch,
  Tooltip,
  Badge,
  Statistic,
  Row,
  Col,
  Typography,
  Popover,
  List,
  Alert,
  Divider,
} from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  SettingOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  ExclamationCircleOutlined,
  FundOutlined,
  CodeOutlined,
} from '@ant-design/icons';
import { formatDistanceToNow } from 'date-fns';
import { useNavigate } from 'react-router-dom';
import {
  Daemon,
  DaemonStatus,
  DaemonStatistics,
  DaemonError,
  DaemonActivity,
} from '@/types/daemon';
import daemonService from '@/services/daemonService';

const { Text, Title } = Typography;

interface DaemonCardProps {
  daemon: Daemon;
  statistics?: DaemonStatistics;
  onStart: (daemonId: string) => void;
  onStop: (daemonId: string) => void;
  onRestart: (daemonId: string) => void;
  onToggleAutoStart: (daemon: Daemon) => void;
  onViewRawData?: () => void;
  isLoading: boolean;
}

const DaemonCard: React.FC<DaemonCardProps> = ({
  daemon,
  statistics,
  onStart,
  onStop,
  onRestart,
  onToggleAutoStart,
  onViewRawData,
  isLoading,
}) => {
  const navigate = useNavigate();
  const [errors, setErrors] = useState<DaemonError[]>([]);
  const [activities, setActivities] = useState<DaemonActivity[]>([]);
  const [loadingErrors, setLoadingErrors] = useState(false);
  const [loadingActivities, setLoadingActivities] = useState(false);

  // Add CSS animation for pulsing effect
  useEffect(() => {
    const style = document.createElement('style');
    style.textContent = `
      @keyframes pulse {
        0% {
          opacity: 1;
        }
        50% {
          opacity: 0.4;
        }
        100% {
          opacity: 1;
        }
      }
      .daemon-status-text {
        transition: opacity 0.3s ease-in-out;
      }
    `;
    const existing = document.head.querySelector('[data-daemon-card-styles]');
    if (!existing) {
      style.setAttribute('data-daemon-card-styles', 'true');
      document.head.appendChild(style);
    }
    return () => {
      // Cleanup handled by attribute check above
    };
  }, []);

  // Load errors when hovering over error badge
  const loadErrors = async () => {
    if (loadingErrors || errors.length > 0) return;
    setLoadingErrors(true);
    try {
      const data = await daemonService.getDaemonErrors(daemon.id, {
        limit: 5,
        unresolved_only: true,
      });
      setErrors(data);
    } catch (error) {
      console.error('Failed to load errors:', error);
    } finally {
      setLoadingErrors(false);
    }
  };

  // Load activities when hovering over activity indicator
  const loadActivities = async () => {
    if (loadingActivities || activities.length > 0) return;
    setLoadingActivities(true);
    try {
      const data = await daemonService.getDaemonActivities(daemon.id, {
        limit: 5,
      });
      setActivities(data);
    } catch (error) {
      console.error('Failed to load activities:', error);
    } finally {
      setLoadingActivities(false);
    }
  };

  const getStatusIcon = (status: DaemonStatus) => {
    switch (status) {
      case DaemonStatus.RUNNING:
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case DaemonStatus.STOPPED:
        return <PauseCircleOutlined style={{ color: '#8c8c8c' }} />;
      case DaemonStatus.ERROR:
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
    }
  };

  const getStatusColor = (status: DaemonStatus) => {
    switch (status) {
      case DaemonStatus.RUNNING:
        return 'success';
      case DaemonStatus.STOPPED:
        return 'orange';
      case DaemonStatus.ERROR:
        return 'error';
    }
  };

  const getActivityIcon = (type: string) => {
    if (type.includes('ERROR'))
      return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
    if (type.includes('WARNING'))
      return <WarningOutlined style={{ color: '#faad14' }} />;
    if (type.includes('JOB'))
      return <ThunderboltOutlined style={{ color: '#1890ff' }} />;
    return <InfoCircleOutlined style={{ color: '#52c41a' }} />;
  };

  // Error popover content
  const errorContent = (
    <div style={{ maxWidth: 400 }}>
      <Title level={5}>Recent Errors</Title>
      {loadingErrors ? (
        <Text>Loading...</Text>
      ) : errors.length > 0 ? (
        <List
          size="small"
          dataSource={errors}
          renderItem={(error) => (
            <List.Item>
              <Space direction="vertical" size={0} style={{ width: '100%' }}>
                <Text strong style={{ color: '#ff4d4f' }}>
                  {error.error_type}
                </Text>
                <Text ellipsis>{error.error_message}</Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {error.occurrence_count}x • Last:{' '}
                  {formatDistanceToNow(new Date(error.last_seen), {
                    addSuffix: true,
                  })}
                </Text>
              </Space>
            </List.Item>
          )}
        />
      ) : (
        <Text type="secondary">No recent errors</Text>
      )}
    </div>
  );

  // Activity popover content
  const activityContent = (
    <div style={{ maxWidth: 400 }}>
      <Title level={5}>Recent Activity</Title>
      {loadingActivities ? (
        <Text>Loading...</Text>
      ) : activities.length > 0 ? (
        <List
          size="small"
          dataSource={activities}
          renderItem={(activity) => (
            <List.Item>
              <Space>
                {getActivityIcon(activity.activity_type)}
                <Space direction="vertical" size={0}>
                  <Text>{activity.message}</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {formatDistanceToNow(new Date(activity.created_at), {
                      addSuffix: true,
                    })}
                  </Text>
                </Space>
              </Space>
            </List.Item>
          )}
        />
      ) : (
        <Text type="secondary">No recent activity</Text>
      )}
    </div>
  );

  // Calculate if daemon is actively processing
  const isActivelyProcessing =
    statistics?.current_activity &&
    statistics.current_activity !== 'Idle' &&
    daemon.status === DaemonStatus.RUNNING;

  // Check if daemon is sleeping
  const getSleepInfo = (status: string | undefined) => {
    if (!status) return null;

    const match = status.match(/sleeping for (\d+) seconds/i);
    if (match) {
      return {
        duration: parseInt(match[1]),
        isSleeping: true,
      };
    }
    return { isSleeping: false };
  };

  const sleepInfo = getSleepInfo(daemon.current_status);

  const cardElement = (
    <Card
      title={
        <Space>
          {daemon.name}
          {getStatusIcon(daemon.status)}
          {isActivelyProcessing && (
            <SyncOutlined spin style={{ color: '#1890ff' }} />
          )}
        </Space>
      }
      extra={
        statistics && statistics.error_count_24h > 0 ? (
          <Popover
            content={errorContent}
            title={null}
            trigger="hover"
            onOpenChange={(visible: boolean) => visible && loadErrors()}
          >
            <Badge
              count={statistics.error_count_24h}
              style={{ backgroundColor: '#ff4d4f' }}
            >
              <ExclamationCircleOutlined
                style={{ fontSize: 20, color: '#ff4d4f' }}
              />
            </Badge>
          </Popover>
        ) : null
      }
      actions={[
        daemon.status === DaemonStatus.STOPPED ? (
          <Tooltip title="Start" key="start">
            <Button
              type="text"
              icon={<PlayCircleOutlined />}
              onClick={() => onStart(daemon.id)}
              loading={isLoading}
            />
          </Tooltip>
        ) : (
          <Tooltip title="Stop" key="stop">
            <Button
              type="text"
              danger
              icon={<PauseCircleOutlined />}
              onClick={() => void onStop(daemon.id)}
              loading={isLoading}
            />
          </Tooltip>
        ),
        <Tooltip title="Restart" key="restart">
          <Button
            type="text"
            icon={<ReloadOutlined />}
            onClick={() => onRestart(daemon.id)}
            disabled={daemon.status === DaemonStatus.STOPPED}
            loading={isLoading}
          />
        </Tooltip>,
        <Tooltip title="View Details" key="details">
          <Button
            type="text"
            icon={<SettingOutlined />}
            onClick={() => void navigate(`/daemons/${daemon.id}`)}
          />
        </Tooltip>,
        onViewRawData && (
          <Tooltip title="View Raw Data" key="raw">
            <Button
              type="text"
              icon={<CodeOutlined />}
              onClick={onViewRawData}
            />
          </Tooltip>
        ),
      ].filter(Boolean)}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* Status and Type Tags */}
        <Space>
          <Tag color={getStatusColor(daemon.status)}>{daemon.status}</Tag>
          <Tag color="blue">
            {daemon.type
              .replace(/_/g, ' ')
              .toLowerCase()
              .replace(/\b\w/g, (l) => l.toUpperCase())}
          </Tag>
        </Space>

        {/* Processing Stats */}
        {statistics &&
          (statistics.items_processed > 0 || statistics.items_pending > 0) && (
            <Row gutter={16}>
              <Col span={12}>
                <Statistic
                  title="Processed"
                  value={statistics.items_processed}
                  valueStyle={{ fontSize: 14 }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Pending"
                  value={statistics.items_pending}
                  valueStyle={{ fontSize: 14 }}
                />
              </Col>
            </Row>
          )}

        {/* Job Statistics */}
        {statistics && (
          <Space size="large">
            <Tooltip title="Jobs launched in last 24h">
              <Space size={4}>
                <PlayCircleOutlined style={{ color: '#1890ff' }} />
                <Text>{statistics.jobs_launched_24h}</Text>
              </Space>
            </Tooltip>
            <Tooltip title="Jobs completed in last 24h">
              <Space size={4}>
                <CheckCircleOutlined style={{ color: '#52c41a' }} />
                <Text>{statistics.jobs_completed_24h}</Text>
              </Space>
            </Tooltip>
            <Tooltip title="Jobs failed in last 24h">
              <Space size={4}>
                <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                <Text>{statistics.jobs_failed_24h}</Text>
              </Space>
            </Tooltip>
          </Space>
        )}

        {/* Last Error */}
        {statistics && statistics.last_error_message && (
          <Alert
            message={statistics.last_error_message}
            type="error"
            showIcon
            style={{ marginTop: 8 }}
            description={
              <Text type="secondary" style={{ fontSize: 12 }}>
                {formatDistanceToNow(new Date(statistics.last_error_time!), {
                  addSuffix: true,
                })}
              </Text>
            }
          />
        )}

        {/* Heartbeat and Activity Popover */}
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          {daemon.status === DaemonStatus.RUNNING && daemon.last_heartbeat && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              <ClockCircleOutlined /> Last heartbeat:{' '}
              {formatDistanceToNow(new Date(daemon.last_heartbeat), {
                addSuffix: true,
              })}
            </Text>
          )}

          <Popover
            content={activityContent}
            title={null}
            trigger="hover"
            onOpenChange={(visible: boolean) => visible && loadActivities()}
          >
            <Button type="link" size="small" icon={<FundOutlined />}>
              View Activity
            </Button>
          </Popover>
        </Space>

        <Divider style={{ margin: '12px 0' }} />

        {/* Auto-start Toggle */}
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Text>Auto-start</Text>
          <Switch
            size="small"
            checked={daemon.auto_start}
            onChange={() => onToggleAutoStart(daemon)}
            disabled={isLoading}
          />
        </Space>

        {/* Status Section - always rendered for consistent height */}
        <div
          style={{
            marginTop: 12,
            padding: 10,
            backgroundColor: '#fafafa',
            border: '1px solid #f0f0f0',
            borderRadius: 4,
            minHeight: 44,
            overflow: 'hidden',
          }}
        >
          {daemon.status === DaemonStatus.RUNNING && daemon.current_status ? (
            <div>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                }}
              >
                {sleepInfo?.isSleeping ? (
                  <div
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      backgroundColor: '#faad14',
                      animation: 'pulse 2s ease-in-out infinite',
                      flexShrink: 0,
                    }}
                  />
                ) : (
                  <div
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      backgroundColor: '#52c41a',
                      animation: 'pulse 1s ease-in-out infinite',
                      flexShrink: 0,
                    }}
                  />
                )}
                <Text
                  type="secondary"
                  className="daemon-status-text"
                  style={{
                    fontSize: 13,
                    flex: 1,
                  }}
                >
                  {daemon.current_status}
                </Text>
                {daemon.current_job_id && daemon.current_job_type && (
                  <Space size={6}>
                    <Tag
                      color="blue"
                      style={{
                        fontSize: 11,
                        lineHeight: '18px',
                        padding: '0 6px',
                        margin: 0,
                      }}
                    >
                      {daemon.current_job_type}
                    </Tag>
                    <Button
                      type="link"
                      size="small"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        navigate(`/jobs?job_id=${daemon.current_job_id}`);
                      }}
                      style={{
                        padding: 0,
                        height: 'auto',
                        fontSize: 12,
                        color: '#1890ff',
                      }}
                    >
                      View →
                    </Button>
                  </Space>
                )}
              </div>
              {daemon.status_updated_at && (
                <div
                  style={{
                    marginTop: 4,
                    paddingLeft: 16,
                    display: 'flex',
                    alignItems: 'center',
                  }}
                >
                  <Text
                    type="secondary"
                    style={{
                      fontSize: 10,
                      opacity: 0.5,
                      fontStyle: 'italic',
                    }}
                  >
                    Updated{' '}
                    {formatDistanceToNow(new Date(daemon.status_updated_at), {
                      addSuffix: true,
                    })}
                  </Text>
                </div>
              )}
            </div>
          ) : (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              <div
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  backgroundColor: '#d9d9d9',
                  flexShrink: 0,
                }}
              />
              <Text
                type="secondary"
                style={{
                  fontSize: 13,
                  opacity: 0.6,
                }}
              >
                {daemon.status === DaemonStatus.STOPPED
                  ? 'Daemon stopped'
                  : daemon.status === DaemonStatus.ERROR
                    ? 'Daemon error'
                    : 'No activity'}
              </Text>
            </div>
          )}
        </div>
      </Space>
    </Card>
  );

  return cardElement;
};

export default DaemonCard;
