import React, { useState, useEffect } from 'react';
import { Input, Select, Space, Typography, Tabs, Row, Col, Alert, Tag } from 'antd';
import { ClockCircleOutlined, CalendarOutlined } from '@ant-design/icons';
import { SCHEDULE_PRESETS } from '../types';
import { useNextRuns } from '../hooks/useSchedules';
import CronHelper from './CronHelper';
import { parseNaturalLanguage } from '../utils/naturalLanguage';
import cronstrue from 'cronstrue';

const { Text, Title } = Typography;
const { TabPane } = Tabs;
const { Option } = Select;

interface ScheduleBuilderProps {
  value?: string;
  onChange?: (value: string) => void;
}

const ScheduleBuilder: React.FC<ScheduleBuilderProps> = ({ value = '', onChange }) => {
  const [mode, setMode] = useState<'preset' | 'builder' | 'natural' | 'advanced'>('preset');
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
      >
        {SCHEDULE_PRESETS.map((preset) => (
          <Option key={preset.expression} value={preset.expression}>
            <Space direction="vertical" size={0}>
              <Text strong>{preset.name}</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {preset.description}
              </Text>
            </Space>
          </Option>
        ))}
      </Select>
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
            onChange={(val) => {
              setMinute(val);
              handleBuilderChange();
            }}
          >
            <Option value="*">Every minute</Option>
            <Option value="0">At minute 0</Option>
            <Option value="*/5">Every 5 minutes</Option>
            <Option value="*/10">Every 10 minutes</Option>
            <Option value="*/15">Every 15 minutes</Option>
            <Option value="*/30">Every 30 minutes</Option>
            {Array.from({ length: 60 }, (_, i) => (
              <Option key={i} value={i.toString()}>
                At minute {i}
              </Option>
            ))}
          </Select>
        </Col>
        
        <Col xs={24} sm={12}>
          <Text type="secondary">Hour (0-23)</Text>
          <Select
            style={{ width: '100%' }}
            value={hour}
            onChange={(val) => {
              setHour(val);
              handleBuilderChange();
            }}
          >
            <Option value="*">Every hour</Option>
            <Option value="*/2">Every 2 hours</Option>
            <Option value="*/3">Every 3 hours</Option>
            <Option value="*/6">Every 6 hours</Option>
            <Option value="*/12">Every 12 hours</Option>
            {Array.from({ length: 24 }, (_, i) => (
              <Option key={i} value={i.toString()}>
                At {i}:00 ({i < 12 ? 'AM' : 'PM'})
              </Option>
            ))}
          </Select>
        </Col>
        
        <Col xs={24} sm={8}>
          <Text type="secondary">Day of Month</Text>
          <Select
            style={{ width: '100%' }}
            value={dayOfMonth}
            onChange={(val) => {
              setDayOfMonth(val);
              handleBuilderChange();
            }}
          >
            <Option value="*">Every day</Option>
            <Option value="1">1st</Option>
            <Option value="15">15th</Option>
            <Option value="L">Last day</Option>
            {Array.from({ length: 31 }, (_, i) => (
              <Option key={i + 1} value={(i + 1).toString()}>
                {i + 1}{['st', 'nd', 'rd'][i] || 'th'}
              </Option>
            ))}
          </Select>
        </Col>
        
        <Col xs={24} sm={8}>
          <Text type="secondary">Month</Text>
          <Select
            style={{ width: '100%' }}
            value={month}
            onChange={(val) => {
              setMonth(val);
              handleBuilderChange();
            }}
          >
            <Option value="*">Every month</Option>
            <Option value="1">January</Option>
            <Option value="2">February</Option>
            <Option value="3">March</Option>
            <Option value="4">April</Option>
            <Option value="5">May</Option>
            <Option value="6">June</Option>
            <Option value="7">July</Option>
            <Option value="8">August</Option>
            <Option value="9">September</Option>
            <Option value="10">October</Option>
            <Option value="11">November</Option>
            <Option value="12">December</Option>
          </Select>
        </Col>
        
        <Col xs={24} sm={8}>
          <Text type="secondary">Day of Week</Text>
          <Select
            style={{ width: '100%' }}
            value={dayOfWeek}
            onChange={(val) => {
              setDayOfWeek(val);
              handleBuilderChange();
            }}
          >
            <Option value="*">Every day</Option>
            <Option value="1">Monday</Option>
            <Option value="2">Tuesday</Option>
            <Option value="3">Wednesday</Option>
            <Option value="4">Thursday</Option>
            <Option value="5">Friday</Option>
            <Option value="6">Saturday</Option>
            <Option value="0">Sunday</Option>
            <Option value="1-5">Weekdays</Option>
            <Option value="0,6">Weekends</Option>
          </Select>
        </Col>
      </Row>
    </Space>
  );

  const renderNaturalTab = () => (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Title level={5}>Describe your schedule in plain English</Title>
      <Text type="secondary">
        Examples: "every day at 3am", "every Monday at noon", "twice a day"
      </Text>
      <Input.Search
        placeholder="Type your schedule..."
        value={naturalInput}
        onChange={(e) => setNaturalInput(e.target.value)}
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
        onChange={(e) => handleExpressionChange(e.target.value)}
        prefix={<ClockCircleOutlined />}
        size="large"
      />
      <CronHelper expression={expression} />
    </Space>
  );

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Tabs activeKey={mode} onChange={(key: any) => setMode(key)}>
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
                  <Tag key={index} icon={<ClockCircleOutlined />}>
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