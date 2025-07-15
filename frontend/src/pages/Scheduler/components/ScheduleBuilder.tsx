import React, { useState, useEffect, ChangeEvent } from 'react';
import {
  Input,
  Select,
  Space,
  Typography,
  Tabs,
  Row,
  Col,
  Alert,
  Tag,
} from 'antd';
import { ClockCircleOutlined, CalendarOutlined } from '@ant-design/icons';
import { SCHEDULE_PRESETS } from '../types';
import { useNextRuns } from '../hooks/useSchedules';
import CronHelper from './CronHelper';
import { parseNaturalLanguage } from '../utils/naturalLanguage';
import cronstrue from 'cronstrue';

const { Text, Title } = Typography;
const { TabPane } = Tabs;

interface ScheduleBuilderProps {
  value?: string;
  onChange?: (value: string) => void;
}

const ScheduleBuilder: React.FC<ScheduleBuilderProps> = ({
  value = '',
  onChange,
}) => {
  const [mode, setMode] = useState<
    'preset' | 'builder' | 'natural' | 'advanced'
  >('preset');
  const [expression, setExpression] = useState(value);
  const [naturalInput, setNaturalInput] = useState('');

  // Cron builder state
  const [minute, setMinute] = useState('0');
  const [hour, setHour] = useState('0');
  const [dayOfMonth, setDayOfMonth] = useState('*');
  const [month, setMonth] = useState('*');
  const [dayOfWeek, setDayOfWeek] = useState('*');

  const { nextRuns, error } = useNextRuns(expression);

  useEffect(() => {
    setExpression(value);
    // Parse existing cron expression for builder
    if (value && mode === 'builder') {
      const parts = value.split(' ');
      if (parts.length === 5) {
        setMinute(parts[0]);
        setHour(parts[1]);
        setDayOfMonth(parts[2]);
        setMonth(parts[3]);
        setDayOfWeek(parts[4]);
      }
    }
  }, [value, mode]);

  const handleExpressionChange = (newExpression: string) => {
    setExpression(newExpression);
    onChange?.(newExpression);
  };

  const handleBuilderChange = () => {
    const newExpression = `${minute} ${hour} ${dayOfMonth} ${month} ${dayOfWeek}`;
    handleExpressionChange(newExpression);
  };

  const handleNaturalLanguageSubmit = () => {
    const parsed = parseNaturalLanguage(naturalInput);
    if (parsed) {
      handleExpressionChange(parsed);
      setMode('advanced');
    }
  };

  const getCronDescription = () => {
    if (!expression) return '';
    try {
      return cronstrue.toString(expression);
    } catch {
      return 'Invalid expression';
    }
  };

  const renderPresetTab = () => (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Title level={5}>Choose a preset schedule</Title>
      <Select
        style={{ width: '100%' }}
        placeholder="Select a preset"
        value={expression}
        onChange={handleExpressionChange}
        options={SCHEDULE_PRESETS.map((preset) => ({
          key: preset.expression,
          value: preset.expression,
          label: (
            <Space direction="vertical" size={0}>
              <Text strong>{preset.name}</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {preset.description}
              </Text>
            </Space>
          ),
        }))}
      />
    </Space>
  );

  const renderBuilderTab = () => (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Title level={5}>Build your schedule</Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12}>
          <Text type="secondary">Minute (0-59)</Text>
          <Select
            style={{ width: '100%' }}
            value={minute}
            onChange={(val: string) => {
              setMinute(val);
              handleBuilderChange();
            }}
            options={[
              { value: '*', label: 'Every minute' },
              { value: '0', label: 'At minute 0' },
              { value: '*/5', label: 'Every 5 minutes' },
              { value: '*/10', label: 'Every 10 minutes' },
              { value: '*/15', label: 'Every 15 minutes' },
              { value: '*/30', label: 'Every 30 minutes' },
              ...Array.from({ length: 60 }, (_, i) => ({
                key: i,
                value: i.toString(),
                label: `At minute ${i}`,
              })),
            ]}
          />
        </Col>

        <Col xs={24} sm={12}>
          <Text type="secondary">Hour (0-23)</Text>
          <Select
            style={{ width: '100%' }}
            value={hour}
            onChange={(val: string) => {
              setHour(val);
              handleBuilderChange();
            }}
            options={[
              { value: '*', label: 'Every hour' },
              { value: '*/2', label: 'Every 2 hours' },
              { value: '*/3', label: 'Every 3 hours' },
              { value: '*/6', label: 'Every 6 hours' },
              { value: '*/12', label: 'Every 12 hours' },
              ...Array.from({ length: 24 }, (_, i) => ({
                key: i,
                value: i.toString(),
                label: `At ${i}:00 (${i < 12 ? 'AM' : 'PM'})`,
              })),
            ]}
          />
        </Col>

        <Col xs={24} sm={8}>
          <Text type="secondary">Day of Month</Text>
          <Select
            style={{ width: '100%' }}
            value={dayOfMonth}
            onChange={(val: string) => {
              setDayOfMonth(val);
              handleBuilderChange();
            }}
            options={[
              { value: '*', label: 'Every day' },
              { value: '1', label: '1st' },
              { value: '15', label: '15th' },
              { value: 'L', label: 'Last day' },
              ...Array.from({ length: 31 }, (_, i) => ({
                key: i + 1,
                value: (i + 1).toString(),
                label: `${i + 1}${['st', 'nd', 'rd'][i] || 'th'}`,
              })),
            ]}
          />
        </Col>

        <Col xs={24} sm={8}>
          <Text type="secondary">Month</Text>
          <Select
            style={{ width: '100%' }}
            value={month}
            onChange={(val: string) => {
              setMonth(val);
              handleBuilderChange();
            }}
            options={[
              { value: '*', label: 'Every month' },
              { value: '1', label: 'January' },
              { value: '2', label: 'February' },
              { value: '3', label: 'March' },
              { value: '4', label: 'April' },
              { value: '5', label: 'May' },
              { value: '6', label: 'June' },
              { value: '7', label: 'July' },
              { value: '8', label: 'August' },
              { value: '9', label: 'September' },
              { value: '10', label: 'October' },
              { value: '11', label: 'November' },
              { value: '12', label: 'December' },
            ]}
          />
        </Col>

        <Col xs={24} sm={8}>
          <Text type="secondary">Day of Week</Text>
          <Select
            style={{ width: '100%' }}
            value={dayOfWeek}
            onChange={(val: string) => {
              setDayOfWeek(val);
              handleBuilderChange();
            }}
            options={[
              { value: '*', label: 'Every day' },
              { value: '1', label: 'Monday' },
              { value: '2', label: 'Tuesday' },
              { value: '3', label: 'Wednesday' },
              { value: '4', label: 'Thursday' },
              { value: '5', label: 'Friday' },
              { value: '6', label: 'Saturday' },
              { value: '0', label: 'Sunday' },
              { value: '1-5', label: 'Weekdays' },
              { value: '0,6', label: 'Weekends' },
            ]}
          />
        </Col>
      </Row>
    </Space>
  );

  const renderNaturalTab = () => (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Title level={5}>Describe your schedule in plain English</Title>
      <Text type="secondary">
        Examples: {'"'}every day at 3am{'"'}, {'"'}every Monday at noon{'"'},{' '}
        {'"'}twice a day{'"'}
      </Text>
      <Input.Search
        placeholder="Type your schedule..."
        value={naturalInput}
        onChange={(e: ChangeEvent<HTMLInputElement>) =>
          setNaturalInput(e.target.value)
        }
        onSearch={handleNaturalLanguageSubmit}
        enterButton="Parse"
        size="large"
      />
    </Space>
  );

  const renderAdvancedTab = () => (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Title level={5}>Enter cron expression directly</Title>
      <Input
        placeholder="* * * * *"
        value={expression}
        onChange={(e: ChangeEvent<HTMLInputElement>) =>
          handleExpressionChange(e.target.value)
        }
        prefix={<ClockCircleOutlined />}
        size="large"
      />
      <CronHelper expression={expression} />
    </Space>
  );

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Tabs
        activeKey={mode}
        onChange={(key: string) =>
          setMode(key as 'preset' | 'builder' | 'natural' | 'advanced')
        }
      >
        <TabPane tab="Presets" key="preset">
          {renderPresetTab()}
        </TabPane>
        <TabPane tab="Builder" key="builder">
          {renderBuilderTab()}
        </TabPane>
        <TabPane tab="Natural Language" key="natural">
          {renderNaturalTab()}
        </TabPane>
        <TabPane tab="Advanced" key="advanced">
          {renderAdvancedTab()}
        </TabPane>
      </Tabs>

      {expression && (
        <Space direction="vertical" style={{ width: '100%' }}>
          <Alert
            message={
              <Space>
                <CalendarOutlined />
                <Text strong>{getCronDescription()}</Text>
              </Space>
            }
            type={error ? 'error' : 'info'}
          />

          {!error && nextRuns.length > 0 && (
            <div>
              <Text type="secondary">Next runs:</Text>
              <Space direction="vertical" size={4} style={{ marginTop: 8 }}>
                {nextRuns.map((run, index) => (
                  <Tag key={index}>
                    <ClockCircleOutlined />
                    {run.toLocaleString()}
                  </Tag>
                ))}
              </Space>
            </div>
          )}
        </Space>
      )}
    </Space>
  );
};

export default ScheduleBuilder;
