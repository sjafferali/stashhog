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
} from 'antd';
import { ReloadOutlined, FundOutlined } from '@ant-design/icons';
import daemonService from '@/services/daemonService';
import { Daemon, DaemonStatistics } from '@/types/daemon';
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
      // Update daemon statistics
      setStatistics((prev) => {
        const newMap = new Map(prev);
        newMap.set(message.daemon_id, message.status);
        return newMap;
      });
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
    </div>
  );
};

export default Daemons;
