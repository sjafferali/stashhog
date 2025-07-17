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
} from 'antd';
import { SaveOutlined, ApiOutlined, LoadingOutlined } from '@ant-design/icons';
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

interface SettingsFormValues {
  stash_url?: string;
  stash_api_key?: string;
  openai_api_key?: string;
  openai_model?: string;
  openai_base_url?: string;
  analysis_confidence_threshold?: number;
  analysis_detect_performers?: boolean;
  analysis_detect_studios?: boolean;
  analysis_detect_tags?: boolean;
  analysis_detect_details?: boolean;
  analysis_use_ai?: boolean;
  [key: string]: string | number | boolean | undefined;
}

const Settings: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testingStash, setTestingStash] = useState(false);
  const [testingOpenAI, setTestingOpenAI] = useState(false);
  const [fieldPlaceholders, setFieldPlaceholders] = useState<
    Record<string, string>
  >({});
  const { loadSettings } = useAppStore();

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

          // Use actual value if from database, otherwise leave empty
          if (setting.source === 'database' && setting.value !== '********') {
            settingsMap[key] = setting.value;
          } else if (
            setting.key === 'openai_model' &&
            setting.source === 'environment'
          ) {
            // Special case: always show model value
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
              options={[
                { value: 'gpt-4', label: 'GPT-4' },
                { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
              ]}
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
