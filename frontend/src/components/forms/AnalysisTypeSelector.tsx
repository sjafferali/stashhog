import React from 'react';
import { Checkbox, Space, Typography } from 'antd';
import {
  UserOutlined,
  ShopOutlined,
  TagsOutlined,
  FileTextOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

export interface AnalysisTypeOptions {
  detectPerformers: boolean;
  detectStudios: boolean;
  detectTags: boolean;
  detectDetails: boolean;
  detectVideoTags: boolean;
}

interface AnalysisTypeSelectorProps {
  value?: AnalysisTypeOptions;
  onChange?: (value: AnalysisTypeOptions) => void;
}

const defaultOptions: AnalysisTypeOptions = {
  detectPerformers: true,
  detectStudios: true,
  detectTags: true,
  detectDetails: false,
  detectVideoTags: false,
};

export const hasAtLeastOneAnalysisTypeSelected = (
  options: AnalysisTypeOptions
): boolean => {
  return (
    options.detectPerformers ||
    options.detectStudios ||
    options.detectTags ||
    options.detectDetails ||
    options.detectVideoTags
  );
};

export const AnalysisTypeSelector: React.FC<AnalysisTypeSelectorProps> = ({
  value = defaultOptions,
  onChange,
}) => {
  const handleChange = (field: keyof AnalysisTypeOptions, checked: boolean) => {
    const newValue = { ...value, [field]: checked };
    onChange?.(newValue);
  };

  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Text strong>Select Analysis Types:</Text>

      <Checkbox
        checked={value.detectPerformers}
        onChange={(e) => handleChange('detectPerformers', e.target.checked)}
      >
        <Space>
          <UserOutlined />
          <span>Performers</span>
        </Space>
      </Checkbox>

      <Checkbox
        checked={value.detectStudios}
        onChange={(e) => handleChange('detectStudios', e.target.checked)}
      >
        <Space>
          <ShopOutlined />
          <span>Studios</span>
        </Space>
      </Checkbox>

      <Checkbox
        checked={value.detectTags}
        onChange={(e) => handleChange('detectTags', e.target.checked)}
      >
        <Space>
          <TagsOutlined />
          <span>AI Tags from Metadata</span>
        </Space>
      </Checkbox>

      <Checkbox
        checked={value.detectDetails}
        onChange={(e) => handleChange('detectDetails', e.target.checked)}
      >
        <Space>
          <FileTextOutlined />
          <span>Details</span>
        </Space>
      </Checkbox>

      <Checkbox
        checked={value.detectVideoTags}
        onChange={(e) => handleChange('detectVideoTags', e.target.checked)}
      >
        <Space>
          <VideoCameraOutlined />
          <span>AI Tags/Markers from Video</span>
        </Space>
      </Checkbox>
    </Space>
  );
};
