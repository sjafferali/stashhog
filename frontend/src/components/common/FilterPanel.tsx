import React, { useState } from 'react';
import { 
  Card, 
  Form, 
  Input, 
  Select, 
  DatePicker, 
  InputNumber, 
  Switch, 
  Button, 
  Space,
  Collapse,
  Row,
  Col
} from 'antd';
import { FilterOutlined, ClearOutlined } from '@ant-design/icons';
import styles from './FilterPanel.module.scss';

const { RangePicker } = DatePicker;
const { Panel } = Collapse;

export type FilterType = 'text' | 'select' | 'multiselect' | 'date' | 'daterange' | 'number' | 'boolean';

export interface FilterConfig {
  name: string;
  label: string;
  type: FilterType;
  placeholder?: string;
  options?: { label: string; value: any }[];
  defaultValue?: any;
  span?: number; // Grid column span (1-24)
  section?: string; // Group filters into collapsible sections
}

export interface FilterPanelProps {
  filters: FilterConfig[];
  values: Record<string, any>;
  onChange: (values: Record<string, any>) => void;
  onReset: () => void;
  loading?: boolean;
  collapsible?: boolean;
}

export const FilterPanel: React.FC<FilterPanelProps> = ({
  filters,
  values,
  onChange,
  onReset,
  loading = false,
  collapsible = true,
}) => {
  const [form] = Form.useForm();
  const [activeKeys, setActiveKeys] = useState<string[]>(['filters']);

  const handleValuesChange = (changedValues: any, allValues: any) => {
    onChange(allValues);
  };

  const handleReset = () => {
    form.resetFields();
    onReset();
  };

  const renderFilter = (filter: FilterConfig) => {
    const { name, label, type, placeholder, options, defaultValue } = filter;

    switch (type) {
      case 'text':
        return (
          <Input 
            placeholder={placeholder || `Search ${label}`} 
            allowClear
          />
        );
      
      case 'select':
        return (
          <Select
            placeholder={placeholder || `Select ${label}`}
            options={options}
            allowClear
          />
        );
      
      case 'multiselect':
        return (
          <Select
            mode="multiple"
            placeholder={placeholder || `Select ${label}`}
            options={options}
            allowClear
          />
        );
      
      case 'date':
        return (
          <DatePicker 
            style={{ width: '100%' }}
            placeholder={placeholder || `Select ${label}`}
          />
        );
      
      case 'daterange':
        return (
          <RangePicker 
            style={{ width: '100%' }}
            placeholder={placeholder ? [placeholder, placeholder] : [`Start ${label}`, `End ${label}`]}
          />
        );
      
      case 'number':
        return (
          <InputNumber 
            style={{ width: '100%' }}
            placeholder={placeholder || `Enter ${label}`}
          />
        );
      
      case 'boolean':
        return <Switch />;
      
      default:
        return null;
    }
  };

  const groupedFilters = filters.reduce((acc, filter) => {
    const section = filter.section || 'Filters';
    if (!acc[section]) {
      acc[section] = [];
    }
    acc[section].push(filter);
    return acc;
  }, {} as Record<string, FilterConfig[]>);

  const content = (
    <Form
      form={form}
      layout="vertical"
      initialValues={values}
      onValuesChange={handleValuesChange}
    >
      {Object.entries(groupedFilters).map(([section, sectionFilters]) => (
        <div key={section} className={styles.filterSection}>
          {Object.keys(groupedFilters).length > 1 && (
            <h4 className={styles.sectionTitle}>{section}</h4>
          )}
          <Row gutter={[16, 16]}>
            {sectionFilters.map((filter) => (
              <Col key={filter.name} span={filter.span || 24}>
                <Form.Item
                  name={filter.name}
                  label={filter.label}
                  initialValue={filter.defaultValue}
                >
                  {renderFilter(filter)}
                </Form.Item>
              </Col>
            ))}
          </Row>
        </div>
      ))}
      <div className={styles.actions}>
        <Space>
          <Button 
            icon={<ClearOutlined />} 
            onClick={handleReset}
            disabled={loading}
          >
            Reset
          </Button>
          <Button 
            type="primary" 
            icon={<FilterOutlined />}
            loading={loading}
          >
            Apply Filters
          </Button>
        </Space>
      </div>
    </Form>
  );

  if (collapsible) {
    return (
      <Collapse
        activeKey={activeKeys}
        onChange={setActiveKeys}
        className={styles.filterPanel}
      >
        <Panel 
          header="Filters" 
          key="filters"
          extra={<FilterOutlined />}
        >
          {content}
        </Panel>
      </Collapse>
    );
  }

  return (
    <Card className={styles.filterPanel} title="Filters">
      {content}
    </Card>
  );
};