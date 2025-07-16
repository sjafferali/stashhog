import React, { useState } from 'react';
import {
  Form,
  Switch,
  Select,
  InputNumber,
  Input,
  Button,
  Space,
  Collapse,
  Card,
  Tooltip,
  Tag,
  Alert,
  Typography,
  Row,
  Col,
  Divider,
} from 'antd';
import {
  InfoCircleOutlined,
  ThunderboltOutlined,
  SettingOutlined,
  SaveOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import styles from './AnalysisOptionsForm.module.scss';

const { Panel } = Collapse;
const { Text } = Typography;
const { TextArea } = Input;

export interface AnalysisOptions {
  planId?: number;
  detectPerformers: boolean;
  detectStudios: boolean;
  detectTags: boolean;
  detectDetails: boolean;
  useAi: boolean;
  model: string;
  temperature: number;
  maxTokens?: number;
  promptTemplate?: string;
  customFields?: Record<string, string | number | boolean | null>;
  batchSize: number;
  confidenceThreshold: number;
}

export interface AnalysisOptionsFormProps {
  options: AnalysisOptions;
  onChange: (options: AnalysisOptions) => void;
  showAdvanced?: boolean;
  availablePlans?: Array<{ id: number; name: string; description?: string }>;
  onSaveAsPreset?: (name: string, options: AnalysisOptions) => void;
  presets?: Array<{ name: string; options: AnalysisOptions }>;
}

const defaultPromptTemplate = `Analyze this adult video scene and extract the following information:
- Title: A descriptive title for the scene
- Date: When the scene was produced (if identifiable)
- Performers: Names of performers in the scene
- Studio: Production studio or company
- Tags: Relevant content tags
- Details: A brief description of the scene

Scene Information:
{scene_info}

Please provide your analysis in a structured format.`;

export const AnalysisOptionsForm: React.FC<AnalysisOptionsFormProps> = ({
  options,
  onChange,
  showAdvanced = true,
  availablePlans,
  onSaveAsPreset,
  presets = [],
}) => {
  const [form] = Form.useForm();
  const [_showPresetModal, _setShowPresetModal] = useState(false);
  // const [presetName, setPresetName] = useState('');

  const handleValuesChange = (_: unknown, allValues: AnalysisOptions) => {
    onChange(allValues);
  };

  const handlePresetSelect = (presetName: string) => {
    const preset = presets.find((p) => p.name === presetName);
    if (preset) {
      form.setFieldsValue(preset.options);
      onChange(preset.options);
    }
  };

  // const _handleSavePreset = () => {
  //   if (onSaveAsPreset && presetName) {
  //     onSaveAsPreset(presetName, form.getFieldsValue());
  //     _setShowPresetModal(false);
  //     setPresetName('');
  //   }
  // };

  const models = [
    { label: 'GPT-4 (Most Accurate)', value: 'gpt-4' },
    { label: 'GPT-4 Turbo (Fast & Accurate)', value: 'gpt-4-turbo-preview' },
    { label: 'GPT-3.5 Turbo (Fast & Cheap)', value: 'gpt-3.5-turbo' },
  ];

  return (
    <div className={styles.analysisOptionsForm}>
      <Form
        form={form}
        layout="vertical"
        initialValues={options}
        onValuesChange={handleValuesChange}
      >
        {presets.length > 0 && (
          <Card size="small" className={styles.presetsCard}>
            <Space>
              <Text strong>Quick Presets:</Text>
              {presets.map((preset) => (
                <Tag
                  key={preset.name}
                  color="blue"
                  className={styles.presetTag}
                  onClick={() => handlePresetSelect(preset.name)}
                >
                  <ThunderboltOutlined /> {preset.name}
                </Tag>
              ))}
            </Space>
          </Card>
        )}

        <Card title="Detection Options" className={styles.card}>
          <Row gutter={[16, 16]}>
            <Col xs={12} sm={8} md={6}>
              <Form.Item name="detectPerformers" valuePropName="checked">
                <Space>
                  <Switch />
                  <Text>Detect Performers</Text>
                </Space>
              </Form.Item>
            </Col>

            <Col xs={12} sm={8} md={6}>
              <Form.Item name="detectStudios" valuePropName="checked">
                <Space>
                  <Switch />
                  <Text>Detect Studios</Text>
                </Space>
              </Form.Item>
            </Col>

            <Col xs={12} sm={8} md={6}>
              <Form.Item name="detectTags" valuePropName="checked">
                <Space>
                  <Switch />
                  <Text>Detect Tags</Text>
                </Space>
              </Form.Item>
            </Col>

            <Col xs={12} sm={8} md={6}>
              <Form.Item name="detectDetails" valuePropName="checked">
                <Space>
                  <Switch />
                  <Text>Clean Details HTML</Text>
                </Space>
              </Form.Item>
            </Col>

            <Col xs={12} sm={8} md={6}>
              <Form.Item name="useAi" valuePropName="checked">
                <Space>
                  <Switch />
                  <Text>Use AI Analysis</Text>
                </Space>
              </Form.Item>
            </Col>
          </Row>
        </Card>

        <Card title="AI Model Settings" className={styles.card}>
          {availablePlans && availablePlans.length > 0 && (
            <Form.Item
              name="planId"
              label="Analysis Plan"
              extra="Use a predefined analysis plan or configure custom settings below"
            >
              <Select
                placeholder="Select an analysis plan"
                allowClear
                options={availablePlans.map((plan) => ({
                  label: plan.name,
                  value: plan.id,
                  description: plan.description,
                }))}
              />
            </Form.Item>
          )}

          <Form.Item
            name="model"
            label="AI Model"
            rules={[{ required: true, message: 'Please select a model' }]}
          >
            <Select options={models} />
          </Form.Item>

          <Form.Item
            name="temperature"
            label={
              <Space>
                Temperature
                <Tooltip title="Controls randomness. Lower values make the output more focused and deterministic.">
                  <InfoCircleOutlined />
                </Tooltip>
              </Space>
            }
          >
            <InputNumber min={0} max={2} step={0.1} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="maxTokens"
            label={
              <Space>
                Max Tokens
                <Tooltip title="Maximum number of tokens to generate. Leave empty for default.">
                  <InfoCircleOutlined />
                </Tooltip>
              </Space>
            }
          >
            <InputNumber
              min={100}
              max={4000}
              style={{ width: '100%' }}
              placeholder="Default"
            />
          </Form.Item>
        </Card>

        {showAdvanced && (
          <Collapse ghost>
            <Panel
              header={
                <Space>
                  <SettingOutlined />
                  Advanced Settings
                </Space>
              }
              key="advanced"
            >
              <Card>
                <Form.Item
                  name="batchSize"
                  label="Batch Size"
                  extra="Number of scenes to analyze in parallel"
                >
                  <InputNumber min={1} max={10} style={{ width: '100%' }} />
                </Form.Item>

                <Form.Item
                  name="confidenceThreshold"
                  label="Confidence Threshold"
                  extra="Minimum confidence score (0-1) for suggestions"
                >
                  <InputNumber
                    min={0}
                    max={1}
                    step={0.1}
                    style={{ width: '100%' }}
                  />
                </Form.Item>

                <Divider />

                <Form.Item
                  name="promptTemplate"
                  label={
                    <Space>
                      Custom Prompt Template
                      <Tooltip title="Customize the prompt sent to the AI. Use {scene_info} as a placeholder.">
                        <InfoCircleOutlined />
                      </Tooltip>
                    </Space>
                  }
                  extra="Leave empty to use the default prompt"
                >
                  <TextArea
                    autoSize={{ minRows: 6, maxRows: 6 }}
                    placeholder={defaultPromptTemplate}
                  />
                </Form.Item>

                <Alert
                  message="Experimental Features"
                  description="These advanced settings may affect analysis quality and costs. Use with caution."
                  type="warning"
                  showIcon
                  icon={<ExperimentOutlined />}
                />
              </Card>
            </Panel>
          </Collapse>
        )}

        {onSaveAsPreset && (
          <div className={styles.presetActions}>
            <Button
              icon={<SaveOutlined />}
              onClick={() => _setShowPresetModal(true)}
            >
              Save as Preset
            </Button>
          </div>
        )}
      </Form>

      {/* Preset Modal would go here if needed */}
    </div>
  );
};
