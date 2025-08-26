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
  Alert,
  Modal,
  Descriptions,
  Tooltip,
} from 'antd';
import {
  ArrowLeftOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  ClearOutlined,
  DownloadOutlined,
  PauseOutlined,
  CheckCircleOutlined,
  SaveOutlined,
  RedoOutlined,
  CodeOutlined,
  CopyOutlined,
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
  const [originalConfigJson, setOriginalConfigJson] = useState('');
  const [savingConfig, setSavingConfig] = useState(false);
  const [configSaved, setConfigSaved] = useState(false);
  const [configError, setConfigError] = useState<string | null>(null);
  const [logLevel, setLogLevel] = useState<LogLevel | 'ALL'>(LogLevel.INFO);
  const [autoScroll, setAutoScroll] = useState(true);
  const [paused, setPaused] = useState(false);
  const [rawDataModalVisible, setRawDataModalVisible] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Load functions wrapped in useCallback
  const loadDaemon = useCallback(
    async (preserveConfigState = false) => {
      if (!daemonId) return;
      try {
        const data = await daemonService.getDaemon(daemonId);
        setDaemon(data);
        const configStr = JSON.stringify(data.configuration, null, 2);
        setConfigJson(configStr);
        setOriginalConfigJson(configStr);
        // Don't reset config state if we're preserving it (e.g., from WebSocket updates)
        if (!preserveConfigState) {
          setConfigSaved(false);
          setConfigError(null);
        }
      } catch (error) {
        void message.error('Failed to load daemon');
        console.error(error);
      } finally {
        setLoading(false);
      }
    },
    [daemonId]
  );

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
        // Update config JSON but preserve the success/error state
        const configStr = JSON.stringify(message.daemon.configuration, null, 2);
        setConfigJson(configStr);
        setOriginalConfigJson(configStr);
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
      void loadDaemon(false);
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
      await loadDaemon(false);
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
      await loadDaemon(false);
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
      await loadDaemon(false);
    } catch (error) {
      void message.error('Failed to restart daemon');
      console.error(error);
    }
  }, [daemonId, loadDaemon]);

  const handleUpdateConfig = useCallback(async () => {
    if (!daemonId || !daemon) return;

    setSavingConfig(true);
    setConfigError(null);
    setConfigSaved(false);

    try {
      // Validate JSON
      let config;
      try {
        config = JSON.parse(configJson);
      } catch {
        setConfigError('Invalid JSON format. Please check your configuration.');
        setSavingConfig(false);
        return;
      }

      // Save configuration
      await daemonService.updateDaemon(daemonId, { configuration: config });

      // Update success state
      setConfigSaved(true);
      setOriginalConfigJson(configJson);
      void message.success({
        content: 'Configuration saved successfully!',
        duration: 5,
        icon: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
      });

      // Clear success message after 10 seconds
      setTimeout(() => {
        setConfigSaved(false);
      }, 10000);

      // Load daemon but preserve config state
      await loadDaemon(true);
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : 'Failed to update configuration';
      setConfigError(errorMessage);
      void message.error({
        content: errorMessage,
        duration: 5,
      });
      console.error(error);
    } finally {
      setSavingConfig(false);
    }
  }, [daemonId, daemon, configJson, loadDaemon]);

  const handleResetToDefault = useCallback(async () => {
    if (!daemonId) return;

    try {
      // Get default configuration
      const defaultConfig =
        await daemonService.getDaemonDefaultConfig(daemonId);

      // Remove the _descriptions key from the default config
      const { _descriptions, ...cleanConfig } = defaultConfig;

      // Set the config JSON
      const configStr = JSON.stringify(cleanConfig, null, 2);
      setConfigJson(configStr);

      // Clear any error
      setConfigError(null);

      void message.info(
        'Configuration reset to defaults. Click "Save Configuration" to apply.'
      );
    } catch (error) {
      void message.error('Failed to load default configuration');
      console.error(error);
    }
  }, [daemonId]);

  // Helper to check if configuration has changed
  const hasConfigChanged = configJson !== originalConfigJson;

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
        return 'orange';
      case DaemonStatus.ERROR:
        return 'error';
    }
  };

  // Define log level hierarchy for filtering
  const logLevelHierarchy = {
    [LogLevel.DEBUG]: 0,
    [LogLevel.INFO]: 1,
    [LogLevel.WARNING]: 2,
    [LogLevel.ERROR]: 3,
  };

  const filteredLogs =
    logLevel === 'ALL'
      ? logs
      : logs.filter((log) => {
          // Show logs at the selected level and above (more severe)
          const selectedLevel = logLevelHierarchy[logLevel as LogLevel];
          const logLevelValue = logLevelHierarchy[log.level];
          return logLevelValue >= selectedLevel;
        });

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

  const getActionColor = (action: string) => {
    switch (action) {
      case 'LAUNCHED':
        return 'success';
      case 'CANCELLED':
        return 'error';
      case 'FINISHED':
        return 'blue';
      default:
        return 'default';
    }
  };

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
      render: (text: unknown) => {
        const action = text as string;
        return (
          <Tag color={getActionColor(action)}>
            {action
              .replace(/_/g, ' ')
              .toLowerCase()
              .replace(/\b\w/g, (l) => l.toUpperCase())}
          </Tag>
        );
      },
    },
    {
      title: 'Job ID',
      dataIndex: 'job_id',
      key: 'job_id',
      render: (text: unknown) => {
        const jobId = text as string;
        return (
          <Text code copyable={{ text: jobId }} style={{ color: '#1890ff' }}>
            {jobId}
          </Text>
        );
      },
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
          <Button
            icon={<CodeOutlined />}
            onClick={() => setRawDataModalVisible(true)}
          >
            View Raw Data
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
                    { value: 'ALL', label: 'All Levels' },
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
                    [
                    {format(
                      new Date(log.created_at),
                      'yyyy-MM-dd HH:mm:ss.SSS'
                    )}
                    ] [{log.level}] {log.message}
                  </Text>
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          </Tabs.TabPane>

          <Tabs.TabPane tab="Configuration" key="2">
            <Space direction="vertical" style={{ width: '100%', gap: '16px' }}>
              <div>
                <Title level={5} style={{ marginBottom: '8px' }}>
                  Configuration
                  {hasConfigChanged && (
                    <Tag color="orange" style={{ marginLeft: '8px' }}>
                      Unsaved Changes
                    </Tag>
                  )}
                </Title>
              </div>

              {/* Success Alert */}
              {configSaved && (
                <Alert
                  message="Configuration saved successfully!"
                  description="Your changes have been saved. Configuration will take effect on next restart."
                  type="success"
                  showIcon
                  icon={<CheckCircleOutlined />}
                  closable
                  onClose={() => setConfigSaved(false)}
                  style={{ marginBottom: '16px' }}
                />
              )}

              {/* Error Alert */}
              {configError && (
                <Alert
                  message="Configuration Error"
                  description={configError}
                  type="error"
                  showIcon
                  closable
                  onClose={() => setConfigError(null)}
                  style={{ marginBottom: '16px' }}
                />
              )}

              <TextArea
                value={configJson}
                onChange={(e) => {
                  setConfigJson(e.target.value);
                  setConfigError(null); // Clear error when user types
                  setConfigSaved(false); // Clear saved status when user types
                }}
                rows={15}
                // @ts-expect-error - style prop exists but not in types
                style={{
                  fontFamily: 'monospace',
                  border: configError ? '1px solid #ff4d4f' : undefined,
                }}
                placeholder="Enter configuration in JSON format..."
              />

              <Space direction="vertical" style={{ width: '100%' }}>
                <Space>
                  <Button
                    type="primary"
                    icon={<SaveOutlined />}
                    onClick={() => void handleUpdateConfig()}
                    loading={savingConfig}
                    disabled={!hasConfigChanged || savingConfig}
                  >
                    {savingConfig ? 'Saving...' : 'Save Configuration'}
                  </Button>

                  {hasConfigChanged && (
                    <Button
                      onClick={() => {
                        setConfigJson(originalConfigJson);
                        setConfigError(null);
                        setConfigSaved(false);
                      }}
                      disabled={savingConfig}
                    >
                      Reset Changes
                    </Button>
                  )}

                  <Button
                    icon={<RedoOutlined />}
                    onClick={() => void handleResetToDefault()}
                    disabled={savingConfig}
                  >
                    Reset to Default
                  </Button>
                </Space>

                <Text type="secondary" style={{ fontSize: '12px' }}>
                  Note: Configuration changes will take effect on next daemon
                  restart
                </Text>
              </Space>
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

      {/* Raw Data Modal */}
      <Modal
        title={
          <Space>
            <CodeOutlined />
            Raw Daemon Data
          </Space>
        }
        open={rawDataModalVisible}
        onCancel={() => setRawDataModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setRawDataModalVisible(false)}>
            Close
          </Button>,
        ]}
        width={800}
        bodyStyle={{
          maxHeight: 'calc(80vh - 108px)',
          overflowY: 'auto',
        }}
      >
        {daemon && (
          <div>
            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="Daemon ID">
                <Space>
                  <Text>{daemon.id}</Text>
                  <Tooltip title="Copy Daemon ID">
                    <Button
                      type="link"
                      icon={<CopyOutlined />}
                      size="small"
                      onClick={() => {
                        void navigator.clipboard.writeText(daemon.id);
                        void message.success('Daemon ID copied to clipboard');
                      }}
                    />
                  </Tooltip>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="Name">{daemon.name}</Descriptions.Item>
              <Descriptions.Item label="Type">{daemon.type}</Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag color={getStatusColor(daemon.status)}>{daemon.status}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Auto Start">
                {daemon.auto_start ? 'Yes' : 'No'}
              </Descriptions.Item>
              <Descriptions.Item label="Created At">
                {new Date(daemon.created_at).toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="Updated At">
                {new Date(daemon.updated_at).toLocaleString()}
              </Descriptions.Item>
            </Descriptions>

            <Title level={5} style={{ marginTop: 16 }}>
              Configuration
            </Title>
            <pre
              style={{
                background: '#f5f5f5',
                padding: '12px',
                borderRadius: '4px',
                overflow: 'auto',
                fontSize: '12px',
                fontFamily: 'monospace',
                maxHeight: '200px',
              }}
            >
              {JSON.stringify(daemon.configuration, null, 2)}
            </pre>

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
              {JSON.stringify(daemon, null, 2)}
            </pre>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default DaemonDetail;
