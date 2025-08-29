import React, { useCallback, useEffect, useState } from 'react';
import {
  Col,
  Row,
  Typography,
  Button,
  Space,
  Spin,
  message,
  Drawer,
  Modal,
  Descriptions,
  Tooltip,
} from 'antd';
import {
  ReloadOutlined,
  FundOutlined,
  CodeOutlined,
  CopyOutlined,
  StopOutlined,
} from '@ant-design/icons';
import daemonService from '@/services/daemonService';
import { Daemon, DaemonStatistics, DaemonStatus } from '@/types/daemon';
import { useWebSocket } from '@/hooks/useWebSocket';
import DaemonCard from '@/components/DaemonCard';
import ActivityFeed from '@/components/ActivityFeed';

const { Title, Text } = Typography;

const Daemons: React.FC = () => {
  const [daemons, setDaemons] = useState<Daemon[]>([]);
  const [statistics, setStatistics] = useState<Map<string, DaemonStatistics>>(
    new Map()
  );
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [activityDrawerVisible, setActivityDrawerVisible] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [rawDataModalVisible, setRawDataModalVisible] = useState(false);
  const [selectedRawDataDaemon, setSelectedRawDataDaemon] =
    useState<Daemon | null>(null);
  const [stoppingAll, setStoppingAll] = useState(false);

  // WebSocket message handler - memoized to prevent reconnections
  const handleWebSocketMessage = useCallback((data: unknown) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const message = data as any;
    if (message.type === 'daemon_update') {
      // Update daemon in the list
      setDaemons((prev) =>
        prev.map((d) => (d.id === message.daemon?.id ? message.daemon : d))
      );
    } else if (message.type === 'daemon_status') {
      // Update daemon's current status fields
      setDaemons((prev) =>
        prev.map((d) =>
          d.id === message.daemon_id
            ? {
                ...d,
                current_status: message.status?.current_status,
                current_job_id: message.status?.current_job_id,
                current_job_type: message.status?.current_job_type,
                status_updated_at: message.status?.status_updated_at,
              }
            : d
        )
      );
    } else if (message.type === 'pong') {
      console.log('Daemons WebSocket connected');
    }
  }, []);

  const handleWebSocketOpen = useCallback(() => {
    console.log('Daemons WebSocket opened');
  }, []);

  // WebSocket connection for real-time updates
  const { sendMessage } = useWebSocket('/api/daemons/ws', {
    onOpen: handleWebSocketOpen,
    onMessage: handleWebSocketMessage,
  });

  // Send initial ping when component mounts
  useEffect(() => {
    const timer = setTimeout(() => {
      sendMessage({ type: 'ping' });
    }, 100);
    return () => clearTimeout(timer);
  }, [sendMessage]);

  useEffect(() => {
    const loadData = async () => {
      await loadDaemons();
    };
    void loadData();
  }, []);

  useEffect(() => {
    if (daemons.length > 0) {
      void loadStatistics(daemons);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [daemons]);

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

  const loadStatistics = async (daemonList?: Daemon[]) => {
    try {
      const daemonsToLoad = daemonList || daemons;
      if (daemonsToLoad.length === 0) return;

      const statsMap = new Map<string, DaemonStatistics>();

      // Load statistics for each daemon in parallel
      const statsPromises = daemonsToLoad.map(async (daemon) => {
        try {
          const stats = await daemonService.getDaemonStatistics(daemon.id);
          return { id: daemon.id, stats };
        } catch (error) {
          console.error(
            `Failed to load statistics for daemon ${daemon.id}:`,
            error
          );
          // Return a default statistics object on error
          return {
            id: daemon.id,
            stats: {
              id: '',
              daemon_id: daemon.id,
              items_processed: 0,
              items_pending: 0,
              error_count_24h: 0,
              warning_count_24h: 0,
              jobs_launched_24h: 0,
              jobs_completed_24h: 0,
              jobs_failed_24h: 0,
              health_score: 100,
              uptime_percentage: 100,
              updated_at: new Date().toISOString(),
            } as DaemonStatistics,
          };
        }
      });

      const results = await Promise.all(statsPromises);
      results.forEach((result) => {
        if (result) {
          statsMap.set(result.id, result.stats);
        }
      });

      setStatistics(statsMap);
    } catch (error) {
      console.error('Failed to load daemon statistics', error);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([loadDaemons(), loadStatistics()]);
    setRefreshing(false);
  };

  const handleStart = async (daemonId: string) => {
    setActionLoading(daemonId);
    try {
      await daemonService.startDaemon(daemonId);
      void message.success('Daemon started successfully');
      await Promise.all([loadDaemons(), loadStatistics()]);
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
      await Promise.all([loadDaemons(), loadStatistics()]);
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
      await Promise.all([loadDaemons(), loadStatistics()]);
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
      await Promise.all([loadDaemons(), loadStatistics()]);
    } catch (error) {
      void message.error('Failed to update auto-start setting');
      console.error(error);
    }
  };

  const showRawDaemonData = (daemon: Daemon) => {
    setSelectedRawDataDaemon(daemon);
    setRawDataModalVisible(true);
  };

  const handleStopAll = async () => {
    // Check if any daemons are running
    const runningDaemons = daemons.filter(
      (d) => d.status === DaemonStatus.RUNNING
    );

    if (runningDaemons.length === 0) {
      void message.info('No daemons are currently running');
      return;
    }

    // Show confirmation modal
    Modal.confirm({
      title: 'Stop All Daemons',
      content: `Are you sure you want to stop all ${runningDaemons.length} running daemon(s)?`,
      icon: <StopOutlined />,
      okText: 'Stop All',
      okType: 'danger',
      cancelText: 'Cancel',
      onOk: async () => {
        setStoppingAll(true);
        try {
          const result = await daemonService.stopAllDaemons();

          if (result.errors && result.errors.length > 0) {
            void message.warning(
              `Stopped ${result.stopped_count} daemon(s) with some errors`
            );
            console.error('Errors stopping daemons:', result.errors);
          } else {
            void message.success(result.message);
          }

          // Reload daemons to update their status
          await Promise.all([loadDaemons(), loadStatistics()]);
        } catch (error) {
          void message.error('Failed to stop all daemons');
          console.error(error);
        } finally {
          setStoppingAll(false);
        }
      },
    });
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
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={2}>Daemons</Title>
            <Text type="secondary">Manage continuous background processes</Text>
          </Col>
          <Col>
            <Space>
              <Button
                danger
                icon={<StopOutlined />}
                onClick={() => void handleStopAll()}
                loading={stoppingAll}
                disabled={
                  stoppingAll ||
                  daemons.every((d) => d.status !== DaemonStatus.RUNNING)
                }
              >
                Stop All
              </Button>
              <Button
                icon={<FundOutlined />}
                onClick={() => setActivityDrawerVisible(true)}
              >
                Activity Feed
              </Button>
              <Button
                icon={refreshing ? <ReloadOutlined spin /> : <ReloadOutlined />}
                onClick={() => void handleRefresh()}
                loading={refreshing}
              >
                Refresh
              </Button>
            </Space>
          </Col>
        </Row>
      </div>

      <Row gutter={[16, 16]}>
        {daemons.map((daemon) => {
          const isLoading = actionLoading === daemon.id;
          const daemonStats = statistics.get(daemon.id);

          return (
            <Col xs={24} sm={24} md={12} lg={8} xl={6} key={daemon.id}>
              <DaemonCard
                daemon={daemon}
                statistics={daemonStats}
                onStart={(id) => void handleStart(id)}
                onStop={(id) => void handleStop(id)}
                onRestart={(id) => void handleRestart(id)}
                onToggleAutoStart={(daemon) =>
                  void handleToggleAutoStart(daemon)
                }
                onViewRawData={() => showRawDaemonData(daemon)}
                isLoading={isLoading}
              />
            </Col>
          );
        })}
      </Row>

      {daemons.length === 0 && (
        <div style={{ textAlign: 'center', marginTop: '48px' }}>
          <Text type="secondary">No daemons configured</Text>
        </div>
      )}

      <Drawer
        title="Activity Feed"
        placement="right"
        width={600}
        onClose={() => setActivityDrawerVisible(false)}
        open={activityDrawerVisible}
      >
        <ActivityFeed limit={100} />
      </Drawer>

      {/* Raw Data Modal */}
      <Modal
        title={
          <Space>
            <CodeOutlined />
            Raw Daemon Data
          </Space>
        }
        open={rawDataModalVisible}
        onCancel={() => {
          setRawDataModalVisible(false);
          setSelectedRawDataDaemon(null);
        }}
        footer={[
          <Button
            key="close"
            onClick={() => {
              setRawDataModalVisible(false);
              setSelectedRawDataDaemon(null);
            }}
          >
            Close
          </Button>,
        ]}
        width={800}
        bodyStyle={{
          maxHeight: 'calc(80vh - 108px)',
          overflowY: 'auto',
        }}
      >
        {selectedRawDataDaemon && (
          <div>
            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="Daemon ID">
                <Space>
                  <Text>{selectedRawDataDaemon.id}</Text>
                  <Tooltip title="Copy Daemon ID">
                    <Button
                      type="link"
                      icon={<CopyOutlined />}
                      size="small"
                      onClick={() => {
                        void navigator.clipboard.writeText(
                          selectedRawDataDaemon.id
                        );
                        void message.success('Daemon ID copied to clipboard');
                      }}
                    />
                  </Tooltip>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="Name">
                {selectedRawDataDaemon.name}
              </Descriptions.Item>
              <Descriptions.Item label="Status">
                {selectedRawDataDaemon.status}
              </Descriptions.Item>
              <Descriptions.Item label="Auto Start">
                {selectedRawDataDaemon.auto_start ? 'Yes' : 'No'}
              </Descriptions.Item>
              <Descriptions.Item label="Created At">
                {new Date(selectedRawDataDaemon.created_at).toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="Updated At">
                {new Date(selectedRawDataDaemon.updated_at).toLocaleString()}
              </Descriptions.Item>
            </Descriptions>

            <Title level={5} style={{ marginTop: 16 }}>
              Full JSON Data
            </Title>
            <pre
              style={{
                background: '#f5f5f5',
                padding: '12px',
                borderRadius: '4px',
                overflow: 'auto',
                fontSize: '12px',
                fontFamily: 'monospace',
              }}
            >
              {JSON.stringify(selectedRawDataDaemon, null, 2)}
            </pre>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default Daemons;
