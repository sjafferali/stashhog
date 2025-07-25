import React from 'react';
import {
  Form,
  Input,
  Select,
  DatePicker,
  Button,
  Space,
  Row,
  Col,
  Card,
  Tag,
  InputNumber,
  Switch,
  Collapse,
} from 'antd';
import {
  SearchOutlined,
  ClearOutlined,
  FilterOutlined,
  UserOutlined,
  TagsOutlined,
  HomeOutlined,
} from '@ant-design/icons';
import { Performer, Tag as TagModel, Studio } from '@/types/models';
import styles from './SceneFilters.module.scss';

const { RangePicker } = DatePicker;
const { Panel } = Collapse;

export interface SceneFilterValues {
  search?: string;
  sceneIds?: string;
  performers?: string[];
  tags?: string[];
  studios?: string[];
  dateRange?: [Date, Date];
  minDuration?: number;
  maxDuration?: number;
  minRating?: number;
  hasDetails?: boolean;
  isAnalyzed?: boolean;
  isOrganized?: boolean;
}

export interface SceneFiltersProps {
  filters: SceneFilterValues;
  onChange: (filters: SceneFilterValues) => void;
  performers: Performer[];
  tags: TagModel[];
  studios: Studio[];
  loading?: boolean;
  showAdvanced?: boolean;
}

export const SceneFilters: React.FC<SceneFiltersProps> = ({
  filters,
  onChange,
  performers,
  tags,
  studios,
  loading = false,
  showAdvanced = true,
}) => {
  const [form] = Form.useForm();

  const handleValuesChange = (
    _: unknown,
    allValues: Record<string, unknown>
  ) => {
    const processedValues: SceneFilterValues = {
      ...allValues,
      dateRange:
        allValues.dateRange &&
        Array.isArray(allValues.dateRange) &&
        allValues.dateRange.length === 2
          ? [allValues.dateRange[0].toDate(), allValues.dateRange[1].toDate()]
          : undefined,
    };
    onChange(processedValues);
  };

  const handleReset = () => {
    form.resetFields();
    onChange({});
  };

  const handleQuickFilter = (type: string, _value: unknown) => {
    const updates: SceneFilterValues = { ...filters };

    switch (type) {
      case 'analyzed':
        updates.isAnalyzed = true;
        break;
      case 'notAnalyzed':
        updates.isAnalyzed = false;
        break;
      case 'highRating':
        updates.minRating = 4;
        break;
      case 'hasDetails':
        updates.hasDetails = true;
        break;
      case 'recent': {
        const lastWeek = new Date();
        lastWeek.setDate(lastWeek.getDate() - 7);
        updates.dateRange = [lastWeek, new Date()];
        break;
      }
    }

    void form.setFieldsValue(updates);
    onChange(updates);
  };

  const quickFilters = [
    { label: 'Analyzed', value: 'analyzed', color: 'green' },
    { label: 'Not Analyzed', value: 'notAnalyzed', color: 'red' },
    { label: 'High Rating', value: 'highRating', color: 'gold' },
    { label: 'Has Details', value: 'hasDetails', color: 'blue' },
    { label: 'Recent', value: 'recent', color: 'purple' },
  ];

  return (
    <Card className={styles.sceneFilters}>
      <Form
        form={form}
        layout="vertical"
        initialValues={filters}
        onValuesChange={handleValuesChange}
      >
        <div className={styles.quickFilters}>
          <span className={styles.label}>Quick Filters:</span>
          <Space>
            {quickFilters.map((filter) => (
              <Tag
                key={filter.value}
                color={filter.color}
                className={styles.quickFilter}
                onClick={() => handleQuickFilter(filter.value, true)}
              >
                {filter.label}
              </Tag>
            ))}
          </Space>
        </div>

        <Row gutter={16}>
          <Col xs={24} md={12} lg={8}>
            <Form.Item name="search" label="Search">
              <Input
                prefix={<SearchOutlined />}
                placeholder="Search scenes..."
                allowClear
              />
            </Form.Item>
          </Col>

          <Col xs={24} md={12} lg={8}>
            <Form.Item
              name="sceneIds"
              label="Scene IDs"
              tooltip="Enter comma-separated scene IDs (e.g., 123,456,789)"
            >
              <Input placeholder="e.g., 123,456,789" allowClear />
            </Form.Item>
          </Col>

          <Col xs={24} md={12} lg={8}>
            <Form.Item name="performers" label="Performers">
              <Select
                mode="multiple"
                placeholder="Select performers"
                showSearch
                filterOption={(input: string, option) =>
                  !!(
                    option?.label &&
                    typeof option.label === 'string' &&
                    option.label.toLowerCase().includes(input.toLowerCase())
                  )
                }
                options={performers.map((p) => ({
                  label: p.name,
                  value: String(p.id),
                }))}
                suffixIcon={<UserOutlined />}
              />
            </Form.Item>
          </Col>

          <Col xs={24} md={12} lg={8}>
            <Form.Item name="tags" label="Tags">
              <Select
                mode="multiple"
                placeholder="Select tags"
                showSearch
                filterOption={(input: string, option) =>
                  !!(
                    option?.label &&
                    typeof option.label === 'string' &&
                    option.label.toLowerCase().includes(input.toLowerCase())
                  )
                }
                options={tags.map((t) => ({
                  label: t.name,
                  value: String(t.id),
                }))}
                suffixIcon={<TagsOutlined />}
              />
            </Form.Item>
          </Col>

          <Col xs={24} md={12} lg={8}>
            <Form.Item name="studios" label="Studios">
              <Select
                mode="multiple"
                placeholder="Select studios"
                showSearch
                filterOption={(input: string, option) =>
                  !!(
                    option?.label &&
                    typeof option.label === 'string' &&
                    option.label.toLowerCase().includes(input.toLowerCase())
                  )
                }
                options={studios.map((s) => ({
                  label: s.name,
                  value: String(s.id),
                }))}
                suffixIcon={<HomeOutlined />}
              />
            </Form.Item>
          </Col>

          <Col xs={24} md={12} lg={8}>
            <Form.Item name="dateRange" label="Date Range">
              <RangePicker style={{ width: '100%' }} />
            </Form.Item>
          </Col>

          <Col xs={24} md={12} lg={8}>
            <Form.Item name="minRating" label="Minimum Rating">
              <InputNumber
                min={0}
                max={5}
                step={0.5}
                style={{ width: '100%' }}
                placeholder="0"
              />
            </Form.Item>
          </Col>
        </Row>

        {showAdvanced && (
          <Collapse ghost>
            <Panel header="Advanced Filters" key="advanced">
              <Row gutter={16}>
                <Col xs={12} md={8} lg={6}>
                  <Form.Item name="minDuration" label="Min Duration (minutes)">
                    <InputNumber
                      min={0}
                      style={{ width: '100%' }}
                      placeholder="0"
                    />
                  </Form.Item>
                </Col>

                <Col xs={12} md={8} lg={6}>
                  <Form.Item name="maxDuration" label="Max Duration (minutes)">
                    <InputNumber
                      min={0}
                      style={{ width: '100%' }}
                      placeholder="999"
                    />
                  </Form.Item>
                </Col>

                <Col xs={8} md={8} lg={4}>
                  <Form.Item
                    name="hasDetails"
                    label="Has Details"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Col>

                <Col xs={8} md={8} lg={4}>
                  <Form.Item
                    name="isAnalyzed"
                    label="Analyzed"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Col>

                <Col xs={8} md={8} lg={4}>
                  <Form.Item
                    name="isOrganized"
                    label="Organized"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
              </Row>
            </Panel>
          </Collapse>
        )}

        <div className={styles.actions}>
          <Space>
            <Button onClick={handleReset} icon={<ClearOutlined />}>
              Clear Filters
            </Button>
            <Button type="primary" icon={<FilterOutlined />} loading={loading}>
              Apply Filters
            </Button>
          </Space>
        </div>
      </Form>
    </Card>
  );
};
