import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  message,
  Card,
  Tabs,
  Typography,
  Button,
  Spin,
  Input,
  Tag,
  Table,
  Select,
  Space,
  Row,
  Col,
} from 'antd';
import {
  ArrowLeftOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  ClearOutlined,
  DownloadOutlined,
  PauseOutlined,
} from '@ant-design/icons';
import { format } from 'date-fns';
import daemonService from '@/services/daemonService';
import {
  Daemon,
  DaemonLog,
  DaemonJobHistory,
  LogLevel,
  DaemonStatus,
  DaemonWebSocketMessage,
} from '@/types/daemon';
import { useWebSocket } from '@/hooks/useWebSocket';

const { Title, Text } = Typography;
const { TextArea } = Input;

const DaemonDetail: React.FC = () => {
  const { daemonId } = useParams<{ daemonId: string }>();
  const navigate = useNavigate();
  const [daemon, setDaemon] = useState<Daemon | null>(null);
  const [logs, setLogs] = useState<DaemonLog[]>([]);
  const [jobHistory, setJobHistory] = useState<DaemonJobHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('1');
  const [configJson, setConfigJson] = useState('');
  const [logLevel, setLogLevel] = useState<LogLevel | 'ALL'>('ALL');
  const [autoScroll, setAutoScroll] = useState(true);
  const [paused, setPaused] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Load functions wrapped in useCallback
  const loadDaemon = useCallback(async () => {
    if (!daemonId) return;
    try {
      const data = await daemonService.getDaemon(daemonId);
      setDaemon(data);
      setConfigJson(JSON.stringify(data.configuration, null, 2));
    } catch (error) {
      void message.error('Failed to load daemon');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [daemonId]);

  const loadLogs = useCallback(async () => {
    if (!daemonId) return;
    try {
      const data = await daemonService.getDaemonLogs(daemonId, { limit: 100 });
      setLogs(data.reverse()); // Reverse to show oldest first
    } catch (error) {
      console.error('Failed to load logs', error);
    }
  }, [daemonId]);

  const loadJobHistory = useCallback(async () => {
    if (!daemonId) return;
    try {
      const data = await daemonService.getDaemonJobHistory(daemonId, {
        limit: 100,
      });
      setJobHistory(data);
    } catch (error) {
      console.error('Failed to load job history', error);
    }
  }, [daemonId]);

  // WebSocket message handler - memoized to prevent reconnections
  const handleWebSocketMessage = useCallback(
    (data: unknown) => {
      console.log('WebSocket message received:', data);

      if (paused) return;

      const message = data as DaemonWebSocketMessage;

      if (message.type === 'subscription_confirmed') {
        console.log('Subscription confirmed for daemon:', message.daemon_id);
      } else if (
        message.type === 'daemon_update' &&
        message.daemon.id === daemonId
      ) {
        console.log('Daemon update received');
        setDaemon(message.daemon);
      } else if (
        message.type === 'daemon_log' &&
        message.daemon_id === daemonId
      ) {
        console.log('Daemon log received:', message.log);
        setLogs((prev) => {
          const newLogs = [...prev, message.log];
          // Keep only last 1000 logs
          if (newLogs.length > 1000) {
            return newLogs.slice(-1000);
          }
          return newLogs;
        });
      } else if (
        message.type === 'daemon_job_action' &&
        message.daemon_id === daemonId
      ) {
        console.log('Daemon job action received:', message.action);
        setJobHistory((prev) => [message.action, ...prev]);
      }
    },
    [daemonId, paused]
  );

  // WebSocket connection for real-time updates
  const { sendMessage } = useWebSocket('/api/daemons/ws', {
    onMessage: handleWebSocketMessage,
  });

  // Subscribe to daemon updates when component mounts or daemonId changes
  useEffect(() => {
    if (daemonId) {
      // Delay subscription to ensure WebSocket is connected
      const timeoutId = setTimeout(() => {
        console.log('Subscribing to daemon:', daemonId);
        sendMessage({ command: 'subscribe', daemon_id: daemonId });
      }, 500);

      // Cleanup: unsubscribe when component unmounts or daemonId changes
      return () => {
        clearTimeout(timeoutId);
        console.log('Unsubscribing from daemon:', daemonId);
        sendMessage({ command: 'unsubscribe', daemon_id: daemonId });
      };
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [daemonId]); // Remove sendMessage from dependencies to prevent re-subscriptions

  useEffect(() => {
    if (daemonId) {
      void loadDaemon();
      void loadLogs();
      void loadJobHistory();
    }
  }, [daemonId, loadDaemon, loadLogs, loadJobHistory]);

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const handleStart = useCallback(async () => {
    if (!daemonId) return;
    try {
      await daemonService.startDaemon(daemonId);
      void message.success('Daemon started successfully');
      await loadDaemon();
    } catch (error) {
      void message.error('Failed to start daemon');
      console.error(error);
    }
  }, [daemonId, loadDaemon]);

  const handleStop = useCallback(async () => {
    if (!daemonId) return;
    try {
      await daemonService.stopDaemon(daemonId);
      void message.success('Daemon stopped successfully');
      await loadDaemon();
    } catch (error) {
      void message.error('Failed to stop daemon');
      console.error(error);
    }
  }, [daemonId, loadDaemon]);

  const handleRestart = useCallback(async () => {
    if (!daemonId) return;
    try {
      await daemonService.restartDaemon(daemonId);
      void message.success('Daemon restarted successfully');
      await loadDaemon();
    } catch (error) {
      void message.error('Failed to restart daemon');
      console.error(error);
    }
  }, [daemonId, loadDaemon]);

  const handleUpdateConfig = useCallback(async () => {
    if (!daemonId || !daemon) return;
    try {
      const config = JSON.parse(configJson);
      await daemonService.updateDaemon(daemonId, { configuration: config });
      void message.success('Configuration updated successfully');
      await loadDaemon();
    } catch (error) {
      if (error instanceof SyntaxError) {
        void message.error('Invalid JSON configuration');
      } else {
        void message.error('Failed to update configuration');
      }
      console.error(error);
    }
  }, [daemonId, daemon, configJson, loadDaemon]);

  const handleClearLogs = () => {
    setLogs([]);
  };

  const handleExportLogs = () => {
    const logText = logs
      .map(
        (log) =>
          `[${format(new Date(log.created_at), 'yyyy-MM-dd HH:mm:ss')}] [${log.level}] ${log.message}`
      )
      .join('\n');

    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `daemon-${daemonId}-logs-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getLogLevelColor = (level: LogLevel) => {
    switch (level) {
      case LogLevel.DEBUG:
        return '#8c8c8c';
      case LogLevel.INFO:
        return '#1890ff';
      case LogLevel.WARNING:
        return '#faad14';
      case LogLevel.ERROR:
        return '#ff4d4f';
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

  const filteredLogs =
    logLevel === 'ALL' ? logs : logs.filter((log) => log.level === logLevel);

  if (loading) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!daemon) {
    return (
      <div style={{ padding: '24px' }}>
        <Title level={4}>Daemon not found</Title>
      </div>
    );
  }

  const jobHistoryColumns = [
    {
      title: 'Time',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: unknown) =>
        format(new Date(text as string), 'yyyy-MM-dd HH:mm:ss'),
    },
    {
      title: 'Action',
      dataIndex: 'action',
      key: 'action',
      render: (text: unknown) => <Tag>{text as string}</Tag>,
    },
    {
      title: 'Job ID',
      dataIndex: 'job_id',
      key: 'job_id',
      render: (text: unknown) => <Text code>{text as string}</Text>,
    },
    {
      title: 'Reason',
      dataIndex: 'reason',
      key: 'reason',
      render: (text: unknown) => (text as string) || '-',
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <Row align="middle" gutter={16}>
          <Col>
            <Button
              icon={<ArrowLeftOutlined />}
              // eslint-disable-next-line @typescript-eslint/no-misused-promises
              onClick={() => navigate('/daemons')}
              type="text"
            />
          </Col>
          <Col>
            <Title level={3} style={{ margin: 0 }}>
              {daemon.name}
            </Title>
          </Col>
          <Col>
            <Tag color={getStatusColor(daemon.status)}>{daemon.status}</Tag>
          </Col>
        </Row>

        <Space style={{ marginTop: '16px' }}>
          {daemon.status === DaemonStatus.STOPPED ? (
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={() => void handleStart()}
            >
              Start
            </Button>
          ) : (
            <Button
              danger
              icon={<PauseCircleOutlined />}
              onClick={() => void handleStop()}
            >
              Stop
            </Button>
          )}
          <Button
            icon={<ReloadOutlined />}
            onClick={() => void handleRestart()}
            disabled={daemon.status === DaemonStatus.STOPPED}
          >
            Restart
          </Button>
        </Space>
      </div>

      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <Tabs.TabPane tab="Logs" key="1">
            <Space
              style={{
                marginBottom: '16px',
                width: '100%',
                justifyContent: 'space-between',
              }}
            >
              <Space>
                <Select
                  value={logLevel}
                  onChange={setLogLevel}
                  style={{ width: 120 }}
                  options={[
                    { value: 'ALL', label: 'All' },
                    { value: LogLevel.DEBUG, label: 'Debug' },
                    { value: LogLevel.INFO, label: 'Info' },
                    { value: LogLevel.WARNING, label: 'Warning' },
                    { value: LogLevel.ERROR, label: 'Error' },
                  ]}
                />

                <Button
                  onClick={() => setAutoScroll(!autoScroll)}
                  type={autoScroll ? 'primary' : 'default'}
                >
                  Auto-scroll: {autoScroll ? 'ON' : 'OFF'}
                </Button>

                <Button
                  icon={<PauseOutlined />}
                  onClick={() => setPaused(!paused)}
                  danger={paused}
                  // @ts-expect-error - title prop exists but not in types
                  title={paused ? 'Resume' : 'Pause'}
                />
              </Space>

              <Space>
                <Button
                  icon={<ClearOutlined />}
                  onClick={handleClearLogs}
                  // @ts-expect-error - title prop exists but not in types
                  title="Clear logs"
                />
                <Button
                  icon={<DownloadOutlined />}
                  onClick={handleExportLogs}
                  // @ts-expect-error - title prop exists but not in types
                  title="Export logs"
                />
              </Space>
            </Space>

            <div
              style={{
                padding: '16px',
                height: '500px',
                overflow: 'auto',
                backgroundColor: '#1f1f1f',
                borderRadius: '4px',
                fontFamily: 'monospace',
              }}
            >
              {filteredLogs.map((log, index) => (
                <div key={index} style={{ marginBottom: '4px' }}>
                  <Text
                    style={{
                      color: getLogLevelColor(log.level),
                      fontFamily: 'monospace',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                    }}
                  >
                    [{format(new Date(log.created_at), 'HH:mm:ss.SSS')}] [
                    {log.level}] {log.message}
                  </Text>
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          </Tabs.TabPane>

          <Tabs.TabPane tab="Configuration" key="2">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Title level={5}>Configuration</Title>
              <TextArea
                value={configJson}
                onChange={(e) => setConfigJson(e.target.value)}
                rows={10}
                // @ts-expect-error - style prop exists but not in types
                style={{ fontFamily: 'monospace' }}
              />
              <div>
                <Button
                  type="primary"
                  onClick={() => void handleUpdateConfig()}
                >
                  Update Configuration
                </Button>
                <Text
                  type="secondary"
                  style={{ display: 'block', marginTop: '8px' }}
                >
                  Note: Configuration changes will take effect on next restart
                </Text>
              </div>
            </Space>
          </Tabs.TabPane>

          <Tabs.TabPane tab="Job History" key="3">
            <Title level={5}>Job History</Title>
            <Table
              dataSource={jobHistory}
              columns={jobHistoryColumns}
              rowKey="id"
              pagination={{
                pageSize: 10,
              }}
            />
          </Tabs.TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default DaemonDetail;
