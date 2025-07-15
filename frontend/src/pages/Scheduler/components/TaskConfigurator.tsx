import React, { useState, useEffect, ChangeEvent } from 'react';
import {
  Form,
  Switch,
  Select,
  InputNumber,
  Input,
  Space,
  Typography,
  Divider,
  Slider,
} from 'antd';
import { TaskConfig } from '../types';

const { Text, Title } = Typography;

interface TaskConfiguratorProps {
  taskType: 'sync' | 'analysis' | 'cleanup';
  value?: TaskConfig;
  onChange?: (config: TaskConfig) => void;
}

const TaskConfigurator: React.FC<TaskConfiguratorProps> = ({
  taskType,
  value,
  onChange,
}) => {
  const [config, setConfig] = useState<TaskConfig>(value || {});

  useEffect(() => {
    setConfig(value || {});
  }, [value]);

  const handleChange = (
    field: string,
    fieldValue: string | number | boolean | string[] | Record<string, unknown>
  ) => {
    const newConfig = { ...config, [field]: fieldValue };
    setConfig(newConfig);
    onChange?.(newConfig);
  };

  const renderSyncConfig = () => (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <div>
        <Title level={5}>Sync Configuration</Title>
        <Text type="secondary">
          Configure how data should be synchronized from Stash
        </Text>
      </div>

      <div>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text>Sync Mode</Text>
          <Form.Item>
            <Switch
              checked={config.full_sync}
              onChange={(checked: boolean) =>
                handleChange('full_sync', checked)
              }
              checkedChildren="Full Sync"
              unCheckedChildren="Incremental"
            />
          </Form.Item>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Full sync retrieves all data, incremental only gets changes since
            last sync
          </Text>
        </Space>
      </div>

      <div>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text>Entity Types</Text>
          <Select
            mode="multiple"
            style={{ width: '100%' }}
            placeholder="Select entities to sync"
            value={
              config.entity_types || ['scenes', 'performers', 'tags', 'studios']
            }
            onChange={(value: string[]) => handleChange('entity_types', value)}
            options={
              [
                { value: 'scenes', label: 'Scenes' },
                { value: 'performers', label: 'Performers' },
                { value: 'tags', label: 'Tags' },
                { value: 'studios', label: 'Studios' },
                { value: 'galleries', label: 'Galleries' },
                { value: 'movies', label: 'Movies' },
              ] as any // eslint-disable-line @typescript-eslint/no-explicit-any
            }
          />
        </Space>
      </div>

      <div>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text>Force Update</Text>
          <Form.Item>
            <Switch
              checked={config.force_update}
              onChange={(checked: boolean) =>
                handleChange('force_update', checked)
              }
            />
          </Form.Item>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Force update even if data hasn{"'"}t changed
          </Text>
        </Space>
      </div>
    </Space>
  );

  const renderAnalysisConfig = () => (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <div>
        <Title level={5}>Analysis Configuration</Title>
        <Text type="secondary">Configure scene analysis parameters</Text>
      </div>

      <Divider orientation="left">Scene Filters</Divider>

      <div>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text>Minimum Duration (seconds)</Text>
          <InputNumber
            style={{ width: '100%' }}
            min={0}
            value={config.scene_filters?.min_duration || 60}
            onChange={(value: number | null) =>
              handleChange('scene_filters', {
                ...config.scene_filters,
                min_duration: value,
              })
            }
            placeholder="60"
          />
        </Space>
      </div>

      <div>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text>Filter by Tags</Text>
          <Select
            mode="tags"
            style={{ width: '100%' }}
            placeholder="Enter tags to filter by"
            value={config.scene_filters?.tags || []}
            onChange={(value: string[]) =>
              handleChange('scene_filters', {
                ...config.scene_filters,
                tags: value,
              })
            }
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            Only analyze scenes with these tags
          </Text>
        </Space>
      </div>

      <div>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text>Filter by Performers</Text>
          <Select
            mode="tags"
            style={{ width: '100%' }}
            placeholder="Enter performer names"
            value={config.scene_filters?.performers || []}
            onChange={(value: string[]) =>
              handleChange('scene_filters', {
                ...config.scene_filters,
                performers: value,
              })
            }
          />
        </Space>
      </div>

      <Divider orientation="left">Analysis Options</Divider>

      <div>
        <Space direction="vertical">
          <Form.Item>
            <Switch
              checked={config.analysis_options?.enable_deduplication !== false}
              onChange={(checked: boolean) =>
                handleChange('analysis_options', {
                  ...config.analysis_options,
                  enable_deduplication: checked,
                })
              }
            />
            <Text style={{ marginLeft: 8 }}>Enable Deduplication</Text>
          </Form.Item>

          <Form.Item>
            <Switch
              checked={config.analysis_options?.enable_quality_check !== false}
              onChange={(checked: boolean) =>
                handleChange('analysis_options', {
                  ...config.analysis_options,
                  enable_quality_check: checked,
                })
              }
            />
            <Text style={{ marginLeft: 8 }}>Enable Quality Check</Text>
          </Form.Item>

          <Form.Item>
            <Switch
              checked={config.analysis_options?.enable_tagging !== false}
              onChange={(checked: boolean) =>
                handleChange('analysis_options', {
                  ...config.analysis_options,
                  enable_tagging: checked,
                })
              }
            />
            <Text style={{ marginLeft: 8 }}>Enable Auto-Tagging</Text>
          </Form.Item>
        </Space>
      </div>

      <div>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text>Plan Name Template</Text>
          <Input
            value={config.plan_name_template || 'Analysis_{date}_{time}'}
            onChange={(e: ChangeEvent<HTMLInputElement>) =>
              handleChange('plan_name_template', e.target.value)
            }
            placeholder="Analysis_{date}_{time}"
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            Available variables: {'{date}'}, {'{time}'}, {'{count}'}
          </Text>
        </Space>
      </div>

      <div>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text>Auto-Apply Threshold (%)</Text>
          <Slider
            min={0}
            max={100}
            value={config.auto_apply_threshold || 0}
            onChange={(value: number) =>
              handleChange('auto_apply_threshold', value || 0)
            }
            marks={{
              0: 'Disabled',
              50: '50%',
              75: '75%',
              90: '90%',
              100: '100%',
            }}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            Automatically apply changes when confidence is above this threshold
          </Text>
        </Space>
      </div>
    </Space>
  );

  const renderCleanupConfig = () => (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <div>
        <Title level={5}>Cleanup Configuration</Title>
        <Text type="secondary">Configure what data to clean up</Text>
      </div>

      <div>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text>Delete data older than (days)</Text>
          <InputNumber
            style={{ width: '100%' }}
            min={1}
            value={config.older_than_days || 30}
            onChange={(value: number | null) =>
              handleChange('older_than_days', value || 30)
            }
            placeholder="30"
          />
        </Space>
      </div>

      <div>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text>Cleanup Types</Text>
          <Select
            mode="multiple"
            style={{ width: '100%' }}
            placeholder="Select what to clean up"
            value={config.cleanup_types || ['logs', 'temp_files']}
            onChange={(value: string[]) => handleChange('cleanup_types', value)}
            options={
              [
                { value: 'logs', label: 'Application Logs' },
                { value: 'temp_files', label: 'Temporary Files' },
                {
                  value: 'old_analysis',
                  label: 'Old Analysis Results',
                },
                {
                  value: 'orphaned_data',
                  label: 'Orphaned Database Records',
                },
                { value: 'cache', label: 'Cache Files' },
              ] as any // eslint-disable-line @typescript-eslint/no-explicit-any
            }
          />
        </Space>
      </div>

      <div>
        <Text type="warning">
          Warning: Cleanup operations are permanent and cannot be undone.
        </Text>
      </div>
    </Space>
  );

  const renderConfig = () => {
    switch (taskType) {
      case 'sync':
        return renderSyncConfig();
      case 'analysis':
        return renderAnalysisConfig();
      case 'cleanup':
        return renderCleanupConfig();
      default:
        return null;
    }
  };

  return (
    <div style={{ maxHeight: 400, overflowY: 'auto', paddingRight: 8 }}>
      {renderConfig()}
    </div>
  );
};

export default TaskConfigurator;
