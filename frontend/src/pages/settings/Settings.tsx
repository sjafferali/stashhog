import React from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  Switch,
  Select,
  Space,
  Divider,
  InputNumber,
} from 'antd';
import { SaveOutlined, ApiOutlined } from '@ant-design/icons';

const Settings: React.FC = () => {
  const [form] = Form.useForm();

  const handleSave = (values: Record<string, unknown>) => {
    console.log('Saving settings:', values);
  };

  const handleTestConnection = () => {
    console.log('Testing connection...');
  };

  return (
    <div>
      <h1>Settings</h1>
      <Card>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          initialValues={{
            openai_model: 'gpt-4',
            openai_temperature: 0.7,
            auto_analyze_new_scenes: false,
            enable_websocket_notifications: true,
            log_level: 'info',
          }}
        >
          <Divider orientation="left">Stash Configuration</Divider>

          <Form.Item
            label="Stash URL"
            name="stash_url"
            rules={[{ required: true, message: 'Please enter the Stash URL' }]}
          >
            <Input placeholder="http://localhost:9999" />
          </Form.Item>

          <Form.Item
            label="Stash API Key"
            name="stash_api_key"
            tooltip="Optional if Stash doesn't require authentication"
          >
            <Input.Password placeholder="Enter API key if required" />
          </Form.Item>

          <Form.Item>
            <Button icon={<ApiOutlined />} onClick={handleTestConnection}>
              Test Connection
            </Button>
          </Form.Item>

          <Divider orientation="left">OpenAI Configuration</Divider>

          <Form.Item
            label="OpenAI API Key"
            name="openai_api_key"
            rules={[
              { required: true, message: 'Please enter your OpenAI API key' },
            ]}
          >
            <Input.Password placeholder="sk-..." />
          </Form.Item>

          <Form.Item label="Model" name="openai_model">
            <Select
              options={[
                { value: 'gpt-4', label: 'GPT-4' },
                { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
              ]}
            />
          </Form.Item>

          <Form.Item label="Temperature" name="openai_temperature">
            <InputNumber min={0} max={2} step={0.1} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item label="Max Tokens" name="openai_max_tokens">
            <InputNumber min={1} max={4000} style={{ width: '100%' }} />
          </Form.Item>

          <Divider orientation="left">General Settings</Divider>

          <Form.Item name="auto_analyze_new_scenes" valuePropName="checked">
            <Switch /> Auto-analyze new scenes
          </Form.Item>

          <Form.Item
            name="enable_websocket_notifications"
            valuePropName="checked"
          >
            <Switch /> Enable WebSocket notifications
          </Form.Item>

          <Form.Item label="Log Level" name="log_level">
            <Select
              options={[
                { value: 'debug', label: 'Debug' },
                { value: 'info', label: 'Info' },
                { value: 'warning', label: 'Warning' },
                { value: 'error', label: 'Error' },
              ]}
            />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                onClick={() => form.submit()}
              >
                Save Settings
              </Button>
              <Button onClick={() => form.resetFields()}>Reset</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default Settings;
