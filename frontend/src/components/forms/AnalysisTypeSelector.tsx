import React from 'react';
import { Checkbox, Space, Typography } from 'antd';
import {
  UserOutlined,
  ShopOutlined,
  TagsOutlined,
  FileTextOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

export interface AnalysisTypeOptions {
  detectPerformers: boolean;
  detectStudios: boolean;
  detectTags: boolean;
  detectDetails: boolean;
  useAi: boolean;
}

interface AnalysisTypeSelectorProps {
  value?: AnalysisTypeOptions;
  onChange?: (value: AnalysisTypeOptions) => void;
  showAiOption?: boolean;
}

const defaultOptions: AnalysisTypeOptions = {
  detectPerformers: true,
  detectStudios: true,
  detectTags: true,
  detectDetails: false,
  useAi: true,
};

export const AnalysisTypeSelector: React.FC<AnalysisTypeSelectorProps> = ({
  value = defaultOptions,
  onChange,
  showAiOption = true,
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
          <span>Title</span>
        </Space>
      </Checkbox>

      {showAiOption && (
        <>
          <div
            style={{
              marginTop: 12,
              paddingTop: 12,
              borderTop: '1px solid #f0f0f0',
            }}
          >
            <Checkbox
              checked={value.useAi}
              onChange={(e) => handleChange('useAi', e.target.checked)}
            >
              <Text type="secondary">Use AI for detection</Text>
            </Checkbox>
          </div>
        </>
      )}
    </Space>
  );
};
