import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Col,
  Row,
  Typography,
  Button,
  Tag,
  Switch,
  Tooltip,
  Space,
  Spin,
  message,
} from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  SettingOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import daemonService from '@/services/daemonService';
import { Daemon, DaemonStatus, DaemonHealthResponse } from '@/types/daemon';
import { formatDistanceToNow } from 'date-fns';
import { useWebSocket } from '@/hooks/useWebSocket';

const { Title, Text } = Typography;

const Daemons: React.FC = () => {
  const navigate = useNavigate();
  const [daemons, setDaemons] = useState<Daemon[]>([]);
  const [health, setHealth] = useState<DaemonHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // WebSocket connection for real-time updates
  const { sendMessage } = useWebSocket('/api/daemons/ws', {
    onOpen: () => {
      // Send initial ping to establish connection
      sendMessage({ type: 'ping' });
    },
    onMessage: (data) => {
      const message = data as { type: string; daemon?: Daemon };
      if (message.type === 'daemon_update') {
        // Update daemon in the list
        setDaemons((prev) =>
          prev.map((d) => (d.id === message.daemon?.id ? message.daemon : d))
        );
      } else if (message.type === 'ping') {
        // Respond to ping with pong to keep connection alive
        sendMessage({ type: 'pong' });
      } else if (message.type === 'pong') {
        // Connection established successfully
        console.log('Daemons WebSocket connected');
      }
    },
  });

  useEffect(() => {
    void loadDaemons();
    void loadHealth();
  }, []);

  const loadDaemons = async () => {
    try {
      const data = await daemonService.getAllDaemons();
      setDaemons(data);
    } catch (error) {
      void message.error('Failed to load daemons');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const loadHealth = async () => {
    try {
      const data = await daemonService.checkDaemonHealth();
      setHealth(data);
    } catch (error) {
      console.error('Failed to load health status', error);
    }
  };

  const handleStart = async (daemonId: string) => {
    setActionLoading(daemonId);
    try {
      await daemonService.startDaemon(daemonId);
      void message.success('Daemon started successfully');
      await loadDaemons();
    } catch (error) {
      void message.error('Failed to start daemon');
      console.error(error);
    } finally {
      setActionLoading(null);
    }
  };

  const handleStop = async (daemonId: string) => {
    setActionLoading(daemonId);
    try {
      await daemonService.stopDaemon(daemonId);
      void message.success('Daemon stopped successfully');
      await loadDaemons();
    } catch (error) {
      void message.error('Failed to stop daemon');
      console.error(error);
    } finally {
      setActionLoading(null);
    }
  };

  const handleRestart = async (daemonId: string) => {
    setActionLoading(daemonId);
    try {
      await daemonService.restartDaemon(daemonId);
      void message.success('Daemon restarted successfully');
      await loadDaemons();
    } catch (error) {
      void message.error('Failed to restart daemon');
      console.error(error);
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleAutoStart = async (daemon: Daemon) => {
    try {
      await daemonService.updateDaemon(daemon.id, {
        auto_start: !daemon.auto_start,
      });
      void message.success('Auto-start setting updated');
      await loadDaemons();
    } catch (error) {
      void message.error('Failed to update auto-start setting');
      console.error(error);
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
        return 'default';
      case DaemonStatus.ERROR:
        return 'error';
    }
  };

  const getHealthStatus = (daemonId: string) => {
    if (!health) return null;

    const healthy = health.healthy.find((h) => h.id === daemonId);
    if (healthy) return { status: 'healthy', uptime: healthy.uptime };

    const unhealthy = health.unhealthy.find((h) => h.id === daemonId);
    if (unhealthy) return { status: 'unhealthy', reason: unhealthy.reason };

    return null;
  };

  if (loading) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <Title level={2}>Daemons</Title>
        <Text type="secondary">Manage continuous background processes</Text>
      </div>

      <Row gutter={[16, 16]}>
        {daemons.map((daemon) => {
          const healthStatus = getHealthStatus(daemon.id);
          const isLoading = actionLoading === daemon.id;

          return (
            <Col xs={24} sm={12} lg={8} xl={6} key={daemon.id}>
              <Card
                title={
                  <Space>
                    {daemon.name}
                    {getStatusIcon(daemon.status)}
                  </Space>
                }
                actions={[
                  daemon.status === DaemonStatus.STOPPED ? (
                    <Tooltip title="Start" key="start">
                      <Button
                        type="text"
                        icon={<PlayCircleOutlined />}
                        onClick={() => void handleStart(daemon.id)}
                        loading={isLoading}
                      />
                    </Tooltip>
                  ) : (
                    <Tooltip title="Stop" key="stop">
                      <Button
                        type="text"
                        danger
                        icon={<PauseCircleOutlined />}
                        onClick={() => void handleStop(daemon.id)}
                        loading={isLoading}
                      />
                    </Tooltip>
                  ),
                  <Tooltip title="Restart" key="restart">
                    <Button
                      type="text"
                      icon={<ReloadOutlined />}
                      onClick={() => void handleRestart(daemon.id)}
                      disabled={daemon.status === DaemonStatus.STOPPED}
                      loading={isLoading}
                    />
                  </Tooltip>,
                  <Tooltip title="View Details" key="details">
                    <Button
                      type="text"
                      icon={<SettingOutlined />}
                      // eslint-disable-next-line @typescript-eslint/no-misused-promises
                      onClick={() => navigate(`/daemons/${daemon.id}`)}
                    />
                  </Tooltip>,
                ]}
              >
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Space>
                    <Tag color={getStatusColor(daemon.status)}>
                      {daemon.status}
                    </Tag>
                    <Tag>{daemon.type}</Tag>
                  </Space>

                  {daemon.status === DaemonStatus.RUNNING &&
                    daemon.last_heartbeat && (
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        Last heartbeat:{' '}
                        {formatDistanceToNow(new Date(daemon.last_heartbeat), {
                          addSuffix: true,
                        })}
                      </Text>
                    )}

                  {healthStatus?.status === 'unhealthy' && (
                    <Space>
                      <WarningOutlined style={{ color: '#faad14' }} />
                      <Text type="warning" style={{ fontSize: '12px' }}>
                        {healthStatus.reason}
                      </Text>
                    </Space>
                  )}

                  {healthStatus?.uptime !== undefined && (
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      Uptime: {Math.floor(healthStatus.uptime / 60)} minutes
                    </Text>
                  )}

                  <Space style={{ marginTop: '8px' }}>
                    <Text>Auto-start</Text>
                    <Switch
                      size="small"
                      checked={daemon.auto_start}
                      onChange={() => void handleToggleAutoStart(daemon)}
                      disabled={isLoading}
                    />
                  </Space>
                </Space>
              </Card>
            </Col>
          );
        })}
      </Row>

      {daemons.length === 0 && (
        <div style={{ textAlign: 'center', marginTop: '48px' }}>
          <Text type="secondary">No daemons configured</Text>
        </div>
      )}
    </div>
  );
};

export default Daemons;
