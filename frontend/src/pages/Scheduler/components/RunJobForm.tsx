import React, { useState, useMemo } from 'react';
import {
  Form,
  Select,
  Button,
  InputNumber,
  Switch,
  Alert,
  Space,
  Typography,
  Divider,
  Input,
  Tag,
  Card,
  Tooltip,
} from 'antd';
import {
  InfoCircleOutlined,
  PlayCircleOutlined,
  SyncOutlined,
  DatabaseOutlined,
  DownloadOutlined,
  ExperimentOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import apiClient from '../../../services/apiClient';
import { message } from 'antd';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

interface RunJobFormProps {
  onSuccess?: (jobId: string) => void;
  onClose?: () => void;
}

interface JobParameter {
  name: string;
  type: 'boolean' | 'number' | 'string' | 'array' | 'select';
  required: boolean;
  default?: string | number | boolean;
  description: string;
  options?: { label: string; value: string | number }[];
  placeholder?: string;
}

interface JobDefinition {
  type: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  category: string;
  parameters: JobParameter[];
}

const jobDefinitions: JobDefinition[] = [
  // Sync Jobs
  {
    type: 'sync',
    name: 'Full Sync',
    description:
      'Synchronize all content from Stash including scenes, performers, tags, and studios',
    icon: <SyncOutlined />,
    category: 'Synchronization',
    parameters: [
      {
        name: 'force',
        type: 'boolean',
        required: false,
        default: false,
        description: 'Force re-sync even if items were recently synced',
      },
    ],
  },
  {
    type: 'sync_scenes',
    name: 'Sync Scenes',
    description: 'Synchronize specific scenes from Stash',
    icon: <DatabaseOutlined />,
    category: 'Synchronization',
    parameters: [
      {
        name: 'scene_ids',
        type: 'array',
        required: false,
        description:
          'Comma-separated list of scene IDs to sync. Leave empty to sync all scenes.',
        placeholder: 'e.g., 123,456,789',
      },
      {
        name: 'force',
        type: 'boolean',
        required: false,
        default: false,
        description: 'Force re-sync even if scenes were recently synced',
      },
    ],
  },
  {
    type: 'sync_performers',
    name: 'Sync Performers',
    description: 'Synchronize all performers from Stash',
    icon: <DatabaseOutlined />,
    category: 'Synchronization',
    parameters: [
      {
        name: 'force',
        type: 'boolean',
        required: false,
        default: false,
        description: 'Force re-sync even if performers were recently synced',
      },
    ],
  },
  {
    type: 'sync_tags',
    name: 'Sync Tags',
    description: 'Synchronize all tags from Stash',
    icon: <DatabaseOutlined />,
    category: 'Synchronization',
    parameters: [
      {
        name: 'force',
        type: 'boolean',
        required: false,
        default: false,
        description: 'Force re-sync even if tags were recently synced',
      },
    ],
  },
  {
    type: 'sync_studios',
    name: 'Sync Studios',
    description: 'Synchronize all studios from Stash',
    icon: <DatabaseOutlined />,
    category: 'Synchronization',
    parameters: [
      {
        name: 'force',
        type: 'boolean',
        required: false,
        default: false,
        description: 'Force re-sync even if studios were recently synced',
      },
    ],
  },
  // Analysis Jobs
  {
    type: 'analysis',
    name: 'Scene Analysis',
    description:
      'Analyze scenes using AI to generate tags, performers, and other metadata',
    icon: <ExperimentOutlined />,
    category: 'AI Analysis',
    parameters: [
      {
        name: 'scene_ids',
        type: 'array',
        required: false,
        description:
          'Comma-separated list of scene IDs to analyze. Leave empty to analyze all unanalyzed scenes.',
        placeholder: 'e.g., 123,456,789',
      },
      {
        name: 'plan_name',
        type: 'string',
        required: false,
        description: 'Name for the analysis plan',
        placeholder: 'e.g., Weekend Analysis',
      },
      {
        name: 'detect_performers',
        type: 'boolean',
        required: false,
        default: true,
        description: 'Detect and match performers in scenes',
      },
      {
        name: 'detect_tags',
        type: 'boolean',
        required: false,
        default: true,
        description: 'Generate tags based on scene content',
      },
      {
        name: 'detect_studio',
        type: 'boolean',
        required: false,
        default: true,
        description: 'Detect and set studio based on watermarks',
      },
      {
        name: 'detect_title',
        type: 'boolean',
        required: false,
        default: true,
        description: 'Generate descriptive titles for scenes',
      },
      {
        name: 'detect_details',
        type: 'boolean',
        required: false,
        default: true,
        description: 'Generate detailed descriptions for scenes',
      },
      {
        name: 'detect_markers',
        type: 'boolean',
        required: false,
        default: false,
        description: 'Detect scene markers and timestamps',
      },
    ],
  },
  {
    type: 'apply_plan',
    name: 'Apply Analysis Plan',
    description:
      'Apply an existing analysis plan to update Stash with AI-generated metadata',
    icon: <ExperimentOutlined />,
    category: 'AI Analysis',
    parameters: [
      {
        name: 'plan_id',
        type: 'string',
        required: true,
        description: 'ID of the analysis plan to apply',
        placeholder: 'Enter plan ID',
      },
      {
        name: 'auto_approve',
        type: 'boolean',
        required: false,
        default: false,
        description: 'Automatically approve all changes without review',
      },
      {
        name: 'change_ids',
        type: 'array',
        required: false,
        description:
          'Comma-separated list of specific change IDs to apply. Leave empty to apply all approved changes.',
        placeholder: 'e.g., 1,2,3',
      },
    ],
  },
  {
    type: 'generate_details',
    name: 'Generate Scene Details',
    description: 'Generate detailed descriptions for scenes using AI',
    icon: <ExperimentOutlined />,
    category: 'AI Analysis',
    parameters: [
      {
        name: 'scene_ids',
        type: 'array',
        required: true,
        description:
          'Comma-separated list of scene IDs to generate details for',
        placeholder: 'e.g., 123,456,789',
      },
    ],
  },
  // Maintenance Jobs
  {
    type: 'cleanup',
    name: 'Cleanup Stale Jobs',
    description:
      'Clean up stuck jobs, delete old completed jobs, and reset stuck analysis plans',
    icon: <DeleteOutlined />,
    category: 'Maintenance',
    parameters: [],
  },
  {
    type: 'process_downloads',
    name: 'Process Downloads',
    description:
      'Process completed torrents from qBittorrent and copy them to the media library',
    icon: <DownloadOutlined />,
    category: 'Downloads',
    parameters: [],
  },
  {
    type: 'stash_scan',
    name: 'Stash Metadata Scan',
    description:
      'Scan the Stash library to update metadata, generate covers, previews, and other media assets',
    icon: <DatabaseOutlined />,
    category: 'Maintenance',
    parameters: [
      {
        name: 'paths',
        type: 'array',
        required: false,
        description:
          'Paths to scan (comma-separated). Leave empty to scan default paths.',
        placeholder: 'e.g., /data/videos,/data/images',
      },
      {
        name: 'rescan',
        type: 'boolean',
        required: false,
        default: false,
        description: 'Force rescan even if modification time is unchanged',
      },
      {
        name: 'scanGenerateCovers',
        type: 'boolean',
        required: false,
        default: true,
        description: 'Generate covers during scan',
      },
      {
        name: 'scanGeneratePreviews',
        type: 'boolean',
        required: false,
        default: true,
        description: 'Generate video previews during scan',
      },
      {
        name: 'scanGenerateImagePreviews',
        type: 'boolean',
        required: false,
        default: false,
        description: 'Generate image previews during scan',
      },
      {
        name: 'scanGenerateSprites',
        type: 'boolean',
        required: false,
        default: true,
        description: 'Generate sprites during scan',
      },
      {
        name: 'scanGeneratePhashes',
        type: 'boolean',
        required: false,
        default: true,
        description: 'Generate perceptual hashes during scan',
      },
      {
        name: 'scanGenerateThumbnails',
        type: 'boolean',
        required: false,
        default: false,
        description: 'Generate image thumbnails during scan',
      },
      {
        name: 'scanGenerateClipPreviews',
        type: 'boolean',
        required: false,
        default: false,
        description: 'Generate image clip previews during scan',
      },
    ],
  },
  {
    type: 'stash_generate',
    name: 'Generate Metadata',
    description:
      'Generate preview images, sprites, thumbnails, and other metadata for media files in Stash',
    icon: <ExperimentOutlined />,
    category: 'Maintenance',
    parameters: [
      {
        name: 'sceneIDs',
        type: 'array',
        required: false,
        description:
          'Comma-separated list of scene IDs to generate metadata for. Leave empty for all scenes.',
        placeholder: 'e.g., 123,456,789',
      },
      {
        name: 'markerIDs',
        type: 'array',
        required: false,
        description:
          'Comma-separated list of marker IDs to generate metadata for. Leave empty for all markers.',
        placeholder: 'e.g., 123,456,789',
      },
      {
        name: 'covers',
        type: 'boolean',
        required: false,
        default: true,
        description: 'Generate cover images',
      },
      {
        name: 'sprites',
        type: 'boolean',
        required: false,
        default: true,
        description: 'Generate sprite sheets for video timeline',
      },
      {
        name: 'previews',
        type: 'boolean',
        required: false,
        default: true,
        description: 'Generate video preview clips',
      },
      {
        name: 'imagePreviews',
        type: 'boolean',
        required: false,
        default: false,
        description: 'Generate image previews',
      },
      {
        name: 'markers',
        type: 'boolean',
        required: false,
        default: true,
        description: 'Generate marker-related metadata',
      },
      {
        name: 'markerImagePreviews',
        type: 'boolean',
        required: false,
        default: false,
        description: 'Generate image previews for markers',
      },
      {
        name: 'markerScreenshots',
        type: 'boolean',
        required: false,
        default: true,
        description: 'Generate screenshots for markers',
      },
      {
        name: 'transcodes',
        type: 'boolean',
        required: false,
        default: false,
        description: 'Generate transcoded versions of videos',
      },
      {
        name: 'phashes',
        type: 'boolean',
        required: false,
        default: true,
        description: 'Generate perceptual hashes for duplicate detection',
      },
      {
        name: 'interactiveHeatmapsSpeeds',
        type: 'boolean',
        required: false,
        default: false,
        description: 'Generate interactive heatmap speed data',
      },
      {
        name: 'clipPreviews',
        type: 'boolean',
        required: false,
        default: true,
        description: 'Generate clip previews',
      },
      {
        name: 'imageThumbnails',
        type: 'boolean',
        required: false,
        default: true,
        description: 'Generate image thumbnails',
      },
      {
        name: 'overwrite',
        type: 'boolean',
        required: false,
        default: false,
        description: 'Overwrite existing generated files',
      },
    ],
  },
];

const RunJobForm: React.FC<RunJobFormProps> = ({ onSuccess, onClose }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [selectedJobType, setSelectedJobType] = useState<string>('');

  const selectedJob = useMemo(
    () => jobDefinitions.find((job) => job.type === selectedJobType),
    [selectedJobType]
  );

  const handleJobTypeChange = (value: string) => {
    setSelectedJobType(value);
    form.resetFields();
    form.setFieldsValue({ job_type: value });
  };

  const handleSubmit = async (
    values: Record<string, string | number | boolean>
  ) => {
    try {
      setLoading(true);

      // Process parameters
      const metadata: Record<
        string,
        string | number | boolean | string[] | number[]
      > = {};

      if (selectedJob) {
        selectedJob.parameters.forEach((param) => {
          const value = values[param.name];
          if (value !== undefined) {
            if (param.type === 'array' && typeof value === 'string') {
              // Convert comma-separated string to array
              metadata[param.name] = value
                .split(',')
                .map((v: string) => v.trim())
                .filter(Boolean);
            } else if (param.type === 'number' && typeof value === 'string') {
              // Convert string to number
              metadata[param.name] = parseInt(value, 10);
            } else {
              metadata[param.name] = value;
            }
          } else if (param.default !== undefined) {
            metadata[param.name] = param.default;
          }
        });
      }

      // Create job using the generic run endpoint
      const response = await apiClient.runJob(selectedJobType, metadata);

      message.success('Job started successfully!');
      if (onSuccess && response.job_id) {
        onSuccess(response.job_id);
      }
      if (onClose) {
        onClose();
      }
    } catch (error) {
      console.error('Failed to start job:', error);
      if (error instanceof Error) {
        message.error(error.message || 'Failed to start job');
      } else {
        message.error('Failed to start job');
      }
    } finally {
      setLoading(false);
    }
  };

  const renderParameterInput = (param: JobDefinition['parameters'][0]) => {
    switch (param.type) {
      case 'boolean':
        return (
          <Form.Item
            name={param.name}
            valuePropName="checked"
            initialValue={param.default}
          >
            <Switch />
          </Form.Item>
        );

      case 'number':
        return (
          <Form.Item
            name={param.name}
            initialValue={param.default}
            rules={[
              {
                required: param.required,
                message: `${param.name} is required`,
              },
            ]}
          >
            <InputNumber
              style={{ width: '100%' }}
              placeholder={param.placeholder}
            />
          </Form.Item>
        );

      case 'string':
        return (
          <Form.Item
            name={param.name}
            initialValue={param.default}
            rules={[
              {
                required: param.required,
                message: `${param.name} is required`,
              },
            ]}
          >
            <Input placeholder={param.placeholder} />
          </Form.Item>
        );

      case 'array':
        return (
          <Form.Item
            name={param.name}
            rules={[
              {
                required: param.required,
                message: `${param.name} is required`,
              },
            ]}
          >
            <TextArea rows={2} placeholder={param.placeholder} />
          </Form.Item>
        );

      case 'select':
        return (
          <Form.Item
            name={param.name}
            initialValue={param.default}
            rules={[
              {
                required: param.required,
                message: `${param.name} is required`,
              },
            ]}
          >
            <Select
              placeholder="Select an option"
              options={param.options?.map((option) => ({
                label: option.label,
                value: option.value,
              }))}
            />
          </Form.Item>
        );

      default:
        return null;
    }
  };

  const groupedJobs = jobDefinitions.reduce(
    (acc, job) => {
      if (!acc[job.category]) {
        acc[job.category] = [];
      }
      acc[job.category].push(job);
      return acc;
    },
    {} as Record<string, JobDefinition[]>
  );

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleSubmit}
      style={{ maxWidth: 600 }}
    >
      <Title level={4}>Run Job Immediately</Title>
      <Paragraph type="secondary">
        Select a job type and configure its parameters to run it immediately.
      </Paragraph>

      <Form.Item
        name="job_type"
        label="Job Type"
        rules={[{ required: true, message: 'Please select a job type' }]}
      >
        <Select
          placeholder="Select a job to run"
          onChange={handleJobTypeChange}
          size="large"
          options={Object.entries(groupedJobs).map(([category, jobs]) => ({
            label: category,
            options: jobs.map((job) => ({
              label: (
                <Space>
                  {job.icon}
                  <span>{job.name}</span>
                </Space>
              ),
              value: job.type,
            })),
          }))}
        />
      </Form.Item>

      {selectedJob && (
        <>
          <Card style={{ marginBottom: 16 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Space>
                {selectedJob.icon}
                <Text strong>{selectedJob.name}</Text>
                <Tag>{selectedJob.category}</Tag>
              </Space>
              <Text type="secondary">{selectedJob.description}</Text>
            </Space>
          </Card>

          {selectedJob.parameters.length > 0 ? (
            <>
              <Divider>Parameters</Divider>
              {selectedJob.parameters.map((param) => (
                <div key={param.name} style={{ marginBottom: 16 }}>
                  <Space align="start" style={{ width: '100%' }}>
                    <Text strong>{param.name}</Text>
                    {param.required && <Tag color="red">Required</Tag>}
                    <Tooltip title={param.description}>
                      <InfoCircleOutlined style={{ color: '#1890ff' }} />
                    </Tooltip>
                  </Space>
                  <Text
                    type="secondary"
                    style={{ display: 'block', marginBottom: 8 }}
                  >
                    {param.description}
                  </Text>
                  {renderParameterInput(param)}
                </div>
              ))}
            </>
          ) : (
            <Alert
              message="No parameters required"
              description="This job will run with default settings."
              type="info"
              showIcon
              style={{ marginTop: 16 }}
            />
          )}
        </>
      )}

      <Form.Item style={{ marginTop: 24 }}>
        <Space>
          <Button
            type="primary"
            loading={loading}
            disabled={!selectedJobType}
            icon={<PlayCircleOutlined />}
            size="large"
            onClick={() => form.submit()}
          >
            Run Job
          </Button>
          {onClose && (
            <Button onClick={onClose} size="large">
              Cancel
            </Button>
          )}
        </Space>
      </Form.Item>

      <Alert
        message="Note"
        description="Some job types may require specific API endpoints that are not yet implemented for direct execution. Use the appropriate UI sections for those operations."
        type="warning"
        showIcon
        style={{ marginTop: 16 }}
      />
    </Form>
  );
};

export default RunJobForm;
