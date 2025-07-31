import React, { useEffect, useState } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  Select,
  Space,
  Divider,
  InputNumber,
  message,
  Spin,
  Alert,
  Tooltip,
} from 'antd';
import {
  SaveOutlined,
  ApiOutlined,
  LoadingOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
// import { apiClient } from '@/services/apiClient';
import api from '@/services/api';
import useAppStore from '@/store';

// Type definitions for settings
interface SettingItem {
  key: string;
  value: string;
  source: 'database' | 'environment';
  env_value?: string;
}

interface ModelInfo {
  name: string;
  input_cost: number;
}

interface SettingsFormValues {
  stash_url?: string;
  stash_api_key?: string;
  stash_preview_preset?: string;
  openai_api_key?: string;
  openai_model?: string;
  openai_base_url?: string;
  analysis_confidence_threshold?: number;
  analysis_detect_performers?: boolean;
  analysis_detect_studios?: boolean;
  analysis_detect_tags?: boolean;
  analysis_detect_details?: boolean;
  analysis_ai_video_server_url?: string;
  analysis_frame_interval?: number;
  analysis_ai_video_threshold?: number;
  analysis_server_timeout?: number;
  analysis_create_markers?: boolean;
  sync_incremental?: boolean;
  sync_batch_size?: number;
  qbittorrent_host?: string;
  qbittorrent_port?: number;
  qbittorrent_username?: string;
  qbittorrent_password?: string;
  [key: string]: string | number | boolean | undefined;
}

const Settings: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testingStash, setTestingStash] = useState(false);
  const [testingOpenAI, setTestingOpenAI] = useState(false);
  const [testingQBittorrent, setTestingQBittorrent] = useState(false);
  const [runningCleanup, setRunningCleanup] = useState(false);
  const [fieldPlaceholders, setFieldPlaceholders] = useState<
    Record<string, string>
  >({});
  const [availableModels, setAvailableModels] = useState<
    Array<{ value: string; label: string }>
  >([]);
  const { loadSettings } = useAppStore();

  // Fetch available models
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await api.get('/analysis/models');
        const { models } = response.data as {
          models: Record<string, ModelInfo>;
        };

        // Transform models into options for Select component
        const modelOptions = Object.entries(models).map(([key, model]) => ({
          value: key,
          label: `${model.name} - $${model.input_cost}/1M tokens`,
        }));

        setAvailableModels(modelOptions);
      } catch (error) {
        console.error('Failed to fetch models:', error);
        // Fallback to basic models if API fails
        setAvailableModels([
          { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
          { value: 'gpt-4o', label: 'GPT-4o' },
          { value: 'gpt-4', label: 'GPT-4' },
          { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
        ]);
      }
    };

    void fetchModels();
  }, []);

  // Fetch current settings
  useEffect(() => {
    const fetchSettings = async () => {
      try {
        setLoading(true);
        const response = await api.get('/settings');
        const settingsArray = response.data;

        // Transform array of settings to object
        const settingsMap: Record<string, string | number | boolean> = {};
        const placeholders: Record<string, string> = {};

        settingsArray.forEach((setting: SettingItem) => {
          const key = setting.key.replace(/\./g, '_');

          // Always use the actual value, regardless of source
          // This ensures video AI settings and other settings are properly displayed
          if (setting.value !== '********') {
            // The backend now returns properly typed values from JSON storage
            settingsMap[key] = setting.value;
          }

          // Set placeholder to show environment default
          if (setting.source === 'environment' && setting.env_value) {
            if (setting.env_value === '********') {
              placeholders[key] = 'Using environment variable (hidden)';
            } else {
              placeholders[key] = `Default: ${setting.env_value}`;
            }
          }
        });

        // Store placeholders for later use
        setFieldPlaceholders(placeholders);

        form.setFieldsValue(settingsMap);
      } catch (error) {
        console.error('Failed to fetch settings:', error);
        void message.error('Failed to load settings');
      } finally {
        setLoading(false);
      }
    };

    void fetchSettings();
  }, [form]);

  const handleSave = async (values: SettingsFormValues) => {
    try {
      setSaving(true);

      // Transform form values to API format
      // For empty strings, we'll send null to clear the database value
      const updates: Record<string, string | number | boolean | null> = {};
      Object.entries(values).forEach(([key, value]) => {
        if (value !== undefined) {
          // Send null for empty strings to clear the database value
          updates[key] = value === '' ? null : value;
        }
      });

      const response = await api.put('/settings', updates);

      if (response.data.requires_restart) {
        void message.warning(
          'Some settings require a server restart to take effect'
        );
      } else {
        void message.success('Settings saved successfully');
      }

      // Reload settings in the store
      await loadSettings();

      // Refetch settings to ensure form is updated
      const updatedResponse = await api.get('/settings');
      const updatedSettingsArray = updatedResponse.data;
      const updatedSettingsMap: Record<string, string | number | boolean> = {};

      updatedSettingsArray.forEach((setting: SettingItem) => {
        const key = setting.key.replace(/\./g, '_');
        // Always use the actual value, regardless of source
        if (setting.value !== '********') {
          // The backend now returns properly typed values from JSON storage
          updatedSettingsMap[key] = setting.value;
        }
      });

      form.setFieldsValue(updatedSettingsMap);
    } catch (error) {
      console.error('Failed to save settings:', error);
      void message.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const handleTestStashConnection = async () => {
    try {
      setTestingStash(true);
      const values = form.getFieldsValue(['stash_url', 'stash_api_key']);

      const response = await api.post('/settings/test-stash', {
        url: values.stash_url,
        api_key: values.stash_api_key,
      });

      if (response.data.success) {
        void message.success(response.data.message);
      } else {
        void message.error(response.data.message);
      }
    } catch (error) {
      console.error('Failed to test Stash connection:', error);
      void message.error('Failed to test Stash connection');
    } finally {
      setTestingStash(false);
    }
  };

  const handleTestOpenAIConnection = async () => {
    try {
      setTestingOpenAI(true);
      const values = form.getFieldsValue([
        'openai_api_key',
        'openai_model',
        'openai_base_url',
      ]);

      const response = await api.post('/settings/test-openai', {
        api_key: values.openai_api_key,
        model: values.openai_model,
        base_url: values.openai_base_url,
      });

      if (response.data.success) {
        void message.success(response.data.message);
      } else {
        void message.error(response.data.message);
      }
    } catch (error) {
      console.error('Failed to test OpenAI connection:', error);
      void message.error('Failed to test OpenAI connection');
    } finally {
      setTestingOpenAI(false);
    }
  };

  const handleTestQBittorrentConnection = async () => {
    try {
      setTestingQBittorrent(true);
      const values = form.getFieldsValue([
        'qbittorrent_host',
        'qbittorrent_port',
        'qbittorrent_username',
        'qbittorrent_password',
      ]);

      const response = await api.post('/settings/test-qbittorrent', {
        host: values.qbittorrent_host,
        port: values.qbittorrent_port,
        username: values.qbittorrent_username,
        password: values.qbittorrent_password,
      });

      if (response.data.success) {
        void message.success(response.data.message);
      } else {
        void message.error(response.data.message);
      }
    } catch (error) {
      console.error('Failed to test qBittorrent connection:', error);
      void message.error('Failed to test qBittorrent connection');
    } finally {
      setTestingQBittorrent(false);
    }
  };

  const handleRunCleanup = async () => {
    try {
      setRunningCleanup(true);
      const response = await api.post('/jobs/cleanup');

      if (response.data.success) {
        void message.success('Cleanup job started successfully');
        // Optionally navigate to jobs page to see progress
        // navigate(`/jobs/${response.data.job_id}`);
      } else {
        void message.error('Failed to start cleanup job');
      }
    } catch (error) {
      console.error('Failed to run cleanup:', error);
      if (error instanceof Error && 'response' in error) {
        const axiosError = error as { response?: { status?: number } };
        if (axiosError.response?.status === 409) {
          void message.warning('A cleanup job is already running');
        } else {
          void message.error('Failed to start cleanup job');
        }
      } else {
        void message.error('Failed to start cleanup job');
      }
    } finally {
      setRunningCleanup(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <h1>Settings</h1>
      <Card>
        <Alert
          message="Settings Behavior"
          description="Settings use environment variables as defaults. Values entered here will override environment variables. Clear a field to use the environment variable default."
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          initialValues={{
            openai_model: 'gpt-4',
            analysis_confidence_threshold: 0.7,
            sync_batch_size: 100,
          }}
        >
          <Divider orientation="left">Stash Configuration</Divider>

          <Form.Item
            label="Stash URL"
            name="stash_url"
            tooltip="Leave empty to use environment variable"
          >
            <Input
              placeholder={
                fieldPlaceholders.stash_url || 'http://localhost:9999'
              }
              allowClear
            />
          </Form.Item>

          <Form.Item
            label="Stash API Key"
            name="stash_api_key"
            tooltip="Optional if Stash doesn't require authentication"
          >
            <Input.Password
              placeholder={
                fieldPlaceholders.stash_api_key || 'Enter API key if required'
              }
              allowClear
            />
          </Form.Item>

          <Form.Item
            label="Preview Preset"
            name="stash_preview_preset"
            tooltip="Video encoding preset for preview generation. Faster presets reduce quality but process quicker."
          >
            <Select
              placeholder={
                fieldPlaceholders.stash_preview_preset || 'ultrafast'
              }
              allowClear
              options={[
                {
                  value: 'ultrafast',
                  label: 'Ultra Fast (lowest quality, fastest processing)',
                },
                { value: 'veryfast', label: 'Very Fast' },
                { value: 'fast', label: 'Fast' },
                { value: 'medium', label: 'Medium (balanced)' },
                { value: 'slow', label: 'Slow (higher quality)' },
                { value: 'slower', label: 'Slower' },
                {
                  value: 'veryslow',
                  label: 'Very Slow (highest quality, slowest processing)',
                },
              ]}
            />
          </Form.Item>

          <Form.Item>
            <Button
              icon={testingStash ? <LoadingOutlined /> : <ApiOutlined />}
              onClick={() => void handleTestStashConnection()}
              loading={testingStash}
            >
              Test Stash Connection
            </Button>
          </Form.Item>

          <Divider orientation="left">OpenAI Configuration</Divider>

          <Form.Item
            label="OpenAI API Key"
            name="openai_api_key"
            tooltip="Leave empty to use environment variable"
          >
            <Input.Password
              placeholder={fieldPlaceholders.openai_api_key || 'sk-...'}
              allowClear
            />
          </Form.Item>

          <Form.Item label="Model" name="openai_model">
            <Select
              placeholder={fieldPlaceholders.openai_model || 'Select a model'}
              options={availableModels}
              showSearch
              filterOption={(input, option) =>
                String(option?.label ?? '')
                  .toLowerCase()
                  .includes(input.toLowerCase())
              }
            />
          </Form.Item>

          <Form.Item
            label="Custom API Endpoint"
            name="openai_base_url"
            tooltip="Optional: Override OpenAI API endpoint for custom/compatible services"
          >
            <Input
              placeholder={
                fieldPlaceholders.openai_base_url || 'https://api.openai.com/v1'
              }
              allowClear
            />
          </Form.Item>

          {/* Temperature and Max Tokens are not in allowed_keys, so removing them */}

          <Form.Item>
            <Button
              icon={testingOpenAI ? <LoadingOutlined /> : <ApiOutlined />}
              onClick={() => void handleTestOpenAIConnection()}
              loading={testingOpenAI}
            >
              Test OpenAI Connection
            </Button>
          </Form.Item>

          <Divider orientation="left">Analysis Settings</Divider>

          <Form.Item
            label="Confidence Threshold"
            name="analysis_confidence_threshold"
            tooltip="Minimum confidence score for accepting AI suggestions"
          >
            <InputNumber
              min={0}
              max={1}
              step={0.1}
              style={{ width: '100%' }}
              formatter={(value?: number) =>
                `${((value || 0) * 100).toFixed(0)}%`
              }
              parser={(value?: string) => Number(value?.replace('%', '')) / 100}
            />
          </Form.Item>

          <Divider orientation="left">Sync Settings</Divider>

          <Form.Item
            label="Sync Batch Size"
            name="sync_batch_size"
            tooltip="Number of items to sync per batch"
          >
            <InputNumber
              min={10}
              max={1000}
              step={10}
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Divider orientation="left">Video AI Settings</Divider>

          <Form.Item
            label="Video AI Server URL"
            name="analysis_ai_video_server_url"
            tooltip="External AI server URL for video processing"
          >
            <Input
              placeholder={
                fieldPlaceholders.analysis_ai_video_server_url ||
                'http://localhost:8084'
              }
              allowClear
            />
          </Form.Item>

          <Form.Item
            label="Frame Extraction Interval (seconds)"
            name="analysis_frame_interval"
            tooltip="How often to extract frames from video for analysis"
          >
            <InputNumber
              min={1}
              max={60}
              step={1}
              style={{ width: '100%' }}
              placeholder={fieldPlaceholders.analysis_frame_interval || '2'}
            />
          </Form.Item>

          <Form.Item
            label="Video AI Confidence Threshold"
            name="analysis_ai_video_threshold"
            tooltip="Minimum confidence score for video AI detections"
          >
            <InputNumber
              min={0}
              max={1}
              step={0.1}
              style={{ width: '100%' }}
              formatter={(value?: number) =>
                `${((value || 0) * 100).toFixed(0)}%`
              }
              parser={(value?: string) => Number(value?.replace('%', '')) / 100}
              placeholder={
                fieldPlaceholders.analysis_ai_video_threshold || '0.3'
              }
            />
          </Form.Item>

          <Form.Item
            label="Video Processing Timeout (seconds)"
            name="analysis_server_timeout"
            tooltip="Maximum time to wait for video processing"
          >
            <InputNumber
              min={60}
              max={7200}
              step={60}
              style={{ width: '100%' }}
              placeholder={fieldPlaceholders.analysis_server_timeout || '3700'}
            />
          </Form.Item>

          <Form.Item
            label="Create Scene Markers"
            name="analysis_create_markers"
            tooltip="Create scene markers from video AI detections"
          >
            <Select
              style={{ width: 120 }}
              options={[
                { value: true, label: 'Yes' },
                { value: false, label: 'No' },
              ]}
            />
          </Form.Item>

          <Divider orientation="left">qBittorrent Settings</Divider>

          <Form.Item
            label="Host"
            name="qbittorrent_host"
            tooltip="qBittorrent server host"
          >
            <Input
              placeholder={fieldPlaceholders.qbittorrent_host || 'localhost'}
              allowClear
            />
          </Form.Item>

          <Form.Item
            label="Port"
            name="qbittorrent_port"
            tooltip="qBittorrent server port"
          >
            <InputNumber
              min={1}
              max={65535}
              style={{ width: '100%' }}
              placeholder={fieldPlaceholders.qbittorrent_port || '8080'}
            />
          </Form.Item>

          <Form.Item
            label="Username"
            name="qbittorrent_username"
            tooltip="qBittorrent username"
          >
            <Input
              placeholder={fieldPlaceholders.qbittorrent_username || 'admin'}
              allowClear
            />
          </Form.Item>

          <Form.Item
            label="Password"
            name="qbittorrent_password"
            tooltip="qBittorrent password"
          >
            <Input.Password
              placeholder={
                fieldPlaceholders.qbittorrent_password || 'Enter password'
              }
              allowClear
            />
          </Form.Item>

          <Form.Item>
            <Button
              icon={testingQBittorrent ? <LoadingOutlined /> : <ApiOutlined />}
              onClick={() => void handleTestQBittorrentConnection()}
              loading={testingQBittorrent}
            >
              Test qBittorrent Connection
            </Button>
          </Form.Item>

          <Divider orientation="left">Maintenance</Divider>

          <Alert
            message="Database Cleanup"
            description={
              <div>
                <p>The cleanup operation will:</p>
                <ul style={{ marginTop: 8, paddingLeft: 20 }}>
                  <li>
                    Find and update stale jobs stuck in RUNNING/PENDING state
                  </li>
                  <li>Delete old completed jobs (older than 30 days)</li>
                  <li>Reset stuck PENDING plans to DRAFT status</li>
                </ul>
              </div>
            }
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />

          <Form.Item>
            <Tooltip title="Run a one-time cleanup job to maintain database health">
              <Button
                icon={runningCleanup ? <LoadingOutlined /> : <DeleteOutlined />}
                onClick={() => void handleRunCleanup()}
                loading={runningCleanup}
                danger
              >
                Run Cleanup Job
              </Button>
            </Tooltip>
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                onClick={() => form.submit()}
                loading={saving}
              >
                Save Settings
              </Button>
              <Button onClick={() => form.resetFields()} disabled={saving}>
                Reset
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default Settings;
