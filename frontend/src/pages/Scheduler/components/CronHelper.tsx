import React from 'react';
import { Space, Typography, Table, Tag, Alert, Collapse } from 'antd';
import { InfoCircleOutlined } from '@ant-design/icons';

const { Text } = Typography;
const { Panel } = Collapse;

interface CronHelperProps {
  expression?: string;
}

const CronHelper: React.FC<CronHelperProps> = ({ expression }) => {
  const fields = expression ? expression.split(' ') : ['*', '*', '*', '*', '*'];

  const fieldDescriptions = [
    {
      name: 'Minute',
      value: fields[0] || '*',
      range: '0-59',
      special: '* , - /',
      examples: ['0', '*/15', '0,30', '10-20'],
    },
    {
      name: 'Hour',
      value: fields[1] || '*',
      range: '0-23',
      special: '* , - /',
      examples: ['0', '*/2', '9-17', '0,12'],
    },
    {
      name: 'Day of Month',
      value: fields[2] || '*',
      range: '1-31',
      special: '* , - / L W',
      examples: ['1', '15', 'L', '1-15'],
    },
    {
      name: 'Month',
      value: fields[3] || '*',
      range: '1-12',
      special: '* , - /',
      examples: ['1', '*/3', '1-6', '12'],
    },
    {
      name: 'Day of Week',
      value: fields[4] || '*',
      range: '0-7',
      special: '* , - / L #',
      examples: ['0', '1-5', '0,6', 'MON'],
    },
  ];

  const specialCharacters = [
    { char: '*', description: 'Any value' },
    { char: ',', description: 'Value list separator' },
    { char: '-', description: 'Range of values' },
    { char: '/', description: 'Step values' },
    { char: 'L', description: 'Last day of month/week' },
    { char: 'W', description: 'Weekday nearest to given day' },
    { char: '#', description: 'Nth occurrence of weekday' },
  ];

  const commonExamples = [
    { expression: '0 * * * *', description: 'Every hour' },
    { expression: '0 0 * * *', description: 'Daily at midnight' },
    { expression: '0 0 * * 0', description: 'Weekly on Sunday' },
    { expression: '0 0 1 * *', description: 'Monthly on the 1st' },
    { expression: '*/5 * * * *', description: 'Every 5 minutes' },
    {
      expression: '0 9-17 * * 1-5',
      description: 'Every hour during business hours',
    },
    { expression: '0 0 L * *', description: 'Last day of every month' },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      {expression && fields.length === 5 && (
        <Alert
          message="Expression Breakdown"
          description={
            <Table
              size="small"
              pagination={false}
              dataSource={fieldDescriptions}
              columns={[
                {
                  title: 'Field',
                  dataIndex: 'name',
                  key: 'name',
                  width: 120,
                },
                {
                  title: 'Value',
                  dataIndex: 'value',
                  key: 'value',
                  width: 80,
                  render: (value) => <Tag color="blue">{String(value)}</Tag>,
                },
                {
                  title: 'Range',
                  dataIndex: 'range',
                  key: 'range',
                  width: 80,
                },
                {
                  title: 'Special Chars',
                  dataIndex: 'special',
                  key: 'special',
                },
              ]}
            />
          }
          type="info"
          icon={<InfoCircleOutlined />}
        />
      )}

      <Collapse ghost>
        <Panel header="Special Characters Reference" key="special">
          <Table
            size="small"
            pagination={false}
            dataSource={specialCharacters}
            columns={[
              {
                title: 'Character',
                dataIndex: 'char',
                key: 'char',
                width: 100,
                render: (char) => <Tag>{String(char)}</Tag>,
              },
              {
                title: 'Description',
                dataIndex: 'description',
                key: 'description',
              },
            ]}
          />
        </Panel>

        <Panel header="Common Examples" key="examples">
          <Table
            size="small"
            pagination={false}
            dataSource={commonExamples}
            columns={[
              {
                title: 'Expression',
                dataIndex: 'expression',
                key: 'expression',
                width: 150,
                render: (expr) => <Tag color="green">{String(expr)}</Tag>,
              },
              {
                title: 'Description',
                dataIndex: 'description',
                key: 'description',
              },
            ]}
          />
        </Panel>

        <Panel header="Field Examples" key="field-examples">
          <Space direction="vertical" style={{ width: '100%' }}>
            {fieldDescriptions.map((field) => (
              <div key={field.name}>
                <Text strong>{field.name}:</Text>
                <Space style={{ marginLeft: 16 }}>
                  {field.examples.map((example) => (
                    <Tag key={example}>{example}</Tag>
                  ))}
                </Space>
              </div>
            ))}
          </Space>
        </Panel>
      </Collapse>
    </Space>
  );
};

export default CronHelper;
