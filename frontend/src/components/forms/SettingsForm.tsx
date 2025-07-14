import React, { useState } from 'react';
import { 
  Form, 
  Input, 
  InputNumber, 
  Select, 
  Switch, 
  Button, 
  Space,
  Tabs,
  Card,
  Alert,
  Divider,
  Typography,
  message
} from 'antd';
import { 
  ApiOutlined, 
  KeyOutlined, 
  SettingOutlined,
  SaveOutlined,
  CheckCircleOutlined,
  SyncOutlined
} from '@ant-design/icons';
import { Settings } from '@/types/models';
import styles from './SettingsForm.module.scss';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

export interface SettingsFormProps {
  settings: Settings;
  onSave: (settings: Settings) => Promise<void>;
  onTest?: (type: 'stash' | 'openai') => Promise<boolean>;
  loading?: boolean;
}

export const SettingsForm: React.FC<SettingsFormProps> = ({
  settings,
  onSave,
  onTest,
  loading = false,
}) => {
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [testingStash, setTestingStash] = useState(false);
  const [testingOpenAI, setTestingOpenAI] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      await onSave(values);
      message.success('Settings saved successfully');
      setHasChanges(false);
    } catch (error) {
      console.error('Failed to save settings:', error);
      message.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const handleTestStash = async () => {
    if (!onTest) return;
    
    setTestingStash(true);
    try {
      const success = await onTest('stash');
      if (success) {
        message.success('Successfully connected to Stash');
      } else {
        message.error('Failed to connect to Stash');
      }
    } catch (error) {
      message.error('Connection test failed');
    } finally {
      setTestingStash(false);
    }
  };

  const handleTestOpenAI = async () => {
    if (!onTest) return;
    
    setTestingOpenAI(true);
    try {
      const success = await onTest('openai');
      if (success) {
        message.success('Successfully connected to OpenAI');
      } else {
        message.error('Failed to connect to OpenAI');
      }
    } catch (error) {
      message.error('Connection test failed');
    } finally {
      setTestingOpenAI(false);
    }
  };

  const handleValuesChange = () => {
    setHasChanges(true);
  };

  const openAIModels = [
    { label: 'GPT-4', value: 'gpt-4' },
    { label: 'GPT-4 Turbo', value: 'gpt-4-turbo-preview' },
    { label: 'GPT-3.5 Turbo', value: 'gpt-3.5-turbo' },
    { label: 'GPT-3.5 Turbo 16k', value: 'gpt-3.5-turbo-16k' },
  ];

  const logLevels = [
    { label: 'Debug', value: 'DEBUG' },
    { label: 'Info', value: 'INFO' },
    { label: 'Warning', value: 'WARNING' },
    { label: 'Error', value: 'ERROR' },
  ];

  return (
    <div className={styles.settingsForm}>
      <Form
        form={form}
        layout="vertical"
        initialValues={settings}
        onValuesChange={handleValuesChange}
      >
        <Tabs defaultActiveKey="stash">
          <TabPane 
            tab={
              <span>
                <ApiOutlined />
                Stash Configuration
              </span>
            } 
            key="stash"
          >
            <Card>
              <Title level={4}>Stash API Settings</Title>
              <Text type="secondary">
                Configure the connection to your Stash instance
              </Text>
              
              <Divider />
              
              <Form.Item
                name="stash_url"
                label="Stash URL"
                rules={[
                  { required: true, message: 'Please enter the Stash URL' },
                  { type: 'url', message: 'Please enter a valid URL' }
                ]}
              >
                <Input 
                  placeholder="http://localhost:9999"
                  prefix={<ApiOutlined />}
                />
              </Form.Item>
              
              <Form.Item
                name="stash_api_key"
                label="API Key (Optional)"
                extra="Leave empty if authentication is not required"
              >
                <Input.Password 
                  placeholder="Enter API key if required"
                  prefix={<KeyOutlined />}
                />
              </Form.Item>
              
              <Form.Item>
                <Button
                  icon={<CheckCircleOutlined />}
                  onClick={handleTestStash}
                  loading={testingStash}
                  disabled={loading}
                >
                  Test Connection
                </Button>
              </Form.Item>
              
              <Alert
                message="Connection Info"
                description="Make sure your Stash instance is running and accessible from this application."
                type="info"
                showIcon
              />
            </Card>
          </TabPane>
          
          <TabPane 
            tab={
              <span>
                <KeyOutlined />
                OpenAI Configuration
              </span>
            } 
            key="openai"
          >
            <Card>
              <Title level={4}>OpenAI API Settings</Title>
              <Text type="secondary">
                Configure OpenAI for scene analysis
              </Text>
              
              <Divider />
              
              <Form.Item
                name="openai_api_key"
                label="OpenAI API Key"
                rules={[
                  { required: true, message: 'Please enter your OpenAI API key' }
                ]}
              >
                <Input.Password 
                  placeholder="sk-..."
                  prefix={<KeyOutlined />}
                />
              </Form.Item>
              
              <Form.Item
                name="openai_model"
                label="Model"
                rules={[
                  { required: true, message: 'Please select a model' }
                ]}
              >
                <Select options={openAIModels} />
              </Form.Item>
              
              <Form.Item
                name="openai_temperature"
                label="Temperature"
                extra="Controls randomness. Lower is more focused, higher is more creative."
              >
                <InputNumber
                  min={0}
                  max={2}
                  step={0.1}
                  style={{ width: '100%' }}
                />
              </Form.Item>
              
              <Form.Item
                name="openai_max_tokens"
                label="Max Tokens (Optional)"
                extra="Maximum number of tokens to generate. Leave empty for default."
              >
                <InputNumber
                  min={1}
                  max={4000}
                  style={{ width: '100%' }}
                  placeholder="Default"
                />
              </Form.Item>
              
              <Form.Item>
                <Button
                  icon={<CheckCircleOutlined />}
                  onClick={handleTestOpenAI}
                  loading={testingOpenAI}
                  disabled={loading}
                >
                  Test Connection
                </Button>
              </Form.Item>
              
              <Alert
                message="API Usage"
                description="Using the OpenAI API will incur costs based on token usage. Monitor your usage in the OpenAI dashboard."
                type="warning"
                showIcon
              />
            </Card>
          </TabPane>
          
          <TabPane 
            tab={
              <span>
                <SettingOutlined />
                General Settings
              </span>
            } 
            key="general"
          >
            <Card>
              <Title level={4}>General Application Settings</Title>
              
              <Divider />
              
              <Form.Item
                name="auto_analyze_new_scenes"
                label="Auto-analyze New Scenes"
                valuePropName="checked"
                extra="Automatically analyze new scenes when they are synced"
              >
                <Switch />
              </Form.Item>
              
              <Form.Item
                name="default_analysis_plan_id"
                label="Default Analysis Plan"
                extra="The analysis plan to use for automatic analysis"
              >
                <Select
                  placeholder="Select a default plan"
                  allowClear
                >
                  {/* Options will be populated from API */}
                </Select>
              </Form.Item>
              
              <Form.Item
                name="sync_interval_hours"
                label="Sync Interval (Hours)"
                extra="How often to sync with Stash (0 to disable)"
              >
                <InputNumber
                  min={0}
                  max={24}
                  style={{ width: '100%' }}
                />
              </Form.Item>
              
              <Form.Item
                name="enable_websocket_notifications"
                label="Enable Real-time Notifications"
                valuePropName="checked"
                extra="Show real-time updates for jobs and sync status"
              >
                <Switch />
              </Form.Item>
              
              <Form.Item
                name="log_level"
                label="Log Level"
              >
                <Select options={logLevels} />
              </Form.Item>
            </Card>
          </TabPane>
        </Tabs>
        
        <div className={styles.actions}>
          <Space>
            <Button
              disabled={!hasChanges || loading}
              onClick={() => {
                form.resetFields();
                setHasChanges(false);
              }}
            >
              Reset
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSave}
              loading={saving}
              disabled={!hasChanges || loading}
            >
              Save Settings
            </Button>
          </Space>
          {hasChanges && (
            <Text type="warning">
              <SyncOutlined /> You have unsaved changes
            </Text>
          )}
        </div>
      </Form>
    </div>
  );
};