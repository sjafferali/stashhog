import React, { useState, useEffect } from 'react';
import { Form, Switch, Select, InputNumber, Input, Space, Typography, Divider, Slider } from 'antd';
import { TaskConfig } from '../types';

const { Text, Title } = Typography;
const { Option } = Select;

interface TaskConfiguratorProps {
  taskType: 'sync' | 'analysis' | 'cleanup';
  value?: TaskConfig;
  onChange?: (config: TaskConfig) => void;
}

const TaskConfigurator: React.FC<TaskConfiguratorProps> = ({ taskType, value, onChange }) => {
  const [config, setConfig] = useState<TaskConfig>(value || {});

  useEffect(() => {
    setConfig(value || {});
  }, [value]);

  const handleChange = (field: string, fieldValue: any) => {
    const newConfig = { ...config, [field]: fieldValue };
    setConfig(newConfig);
    onChange?.(newConfig);
  };

  const renderSyncConfig = () => (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <div>
        <Title level={5}>Sync Configuration</Title>
        <Text type="secondary">Configure how data should be synchronized from Stash</Text>
      </div>

      <div>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text>Sync Mode</Text>
          <Form.Item>
            <Switch
              checked={config.full_sync}
              onChange={(checked) => handleChange('full_sync', checked)}
              checkedChildren="Full Sync"
              unCheckedChildren="Incremental"
            />
          </Form.Item>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Full sync retrieves all data, incremental only gets changes since last sync
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
            value={config.entity_types || ['scenes', 'performers', 'tags', 'studios']}
            onChange={(value) => handleChange('entity_types', value)}
          >
            <Option value="scenes">Scenes</Option>
            <Option value="performers">Performers</Option>
            <Option value="tags">Tags</Option>
            <Option value="studios">Studios</Option>
            <Option value="galleries">Galleries</Option>
            <Option value="movies">Movies</Option>
          </Select>
        </Space>
      </div>

      <div>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text>Force Update</Text>
          <Form.Item>
            <Switch
              checked={config.force_update}
              onChange={(checked) => handleChange('force_update', checked)}
            />
          </Form.Item>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Force update even if data hasn't changed
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
            onChange={(value) => handleChange('scene_filters', {
              ...config.scene_filters,
              min_duration: value,
            })}
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
            onChange={(value) => handleChange('scene_filters', {
              ...config.scene_filters,
              tags: value,
            })}
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
            onChange={(value) => handleChange('scene_filters', {
              ...config.scene_filters,
              performers: value,
            })}
          />
        </Space>
      </div>

      <Divider orientation="left">Analysis Options</Divider>

      <div>
        <Space direction="vertical">
          <Form.Item>
            <Switch
              checked={config.analysis_options?.enable_deduplication !== false}
              onChange={(checked) => handleChange('analysis_options', {
                ...config.analysis_options,
                enable_deduplication: checked,
              })}
            />
            <Text style={{ marginLeft: 8 }}>Enable Deduplication</Text>
          </Form.Item>
          
          <Form.Item>
            <Switch
              checked={config.analysis_options?.enable_quality_check !== false}
              onChange={(checked) => handleChange('analysis_options', {
                ...config.analysis_options,
                enable_quality_check: checked,
              })}
            />
            <Text style={{ marginLeft: 8 }}>Enable Quality Check</Text>
          </Form.Item>
          
          <Form.Item>
            <Switch
              checked={config.analysis_options?.enable_tagging !== false}
              onChange={(checked) => handleChange('analysis_options', {
                ...config.analysis_options,
                enable_tagging: checked,
              })}
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
            onChange={(e) => handleChange('plan_name_template', e.target.value)}
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
            onChange={(value) => handleChange('auto_apply_threshold', value)}
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
            onChange={(value) => handleChange('older_than_days', value)}
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
            onChange={(value) => handleChange('cleanup_types', value)}
          >
            <Option value="logs">Application Logs</Option>
            <Option value="temp_files">Temporary Files</Option>
            <Option value="old_analysis">Old Analysis Results</Option>
            <Option value="orphaned_data">Orphaned Database Records</Option>
            <Option value="cache">Cache Files</Option>
          </Select>
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