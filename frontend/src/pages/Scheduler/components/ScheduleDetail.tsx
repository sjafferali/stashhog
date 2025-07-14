import React, { useState } from 'react';
import { Modal, Descriptions, Tag, Space, Button, Form, Input, Switch, Typography, Divider, Alert, Statistic, Row, Col } from 'antd';
import { 
  EditOutlined, 
  PlayCircleOutlined, 
  DeleteOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined
} from '@ant-design/icons';
import { Schedule, UpdateScheduleData } from '../types';
import { useSchedules, useScheduleHistory } from '../hooks/useSchedules';
import ScheduleBuilder from './ScheduleBuilder';
import TaskConfigurator from './TaskConfigurator';
import cronstrue from 'cronstrue';
import dayjs from 'dayjs';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface ScheduleDetailProps {
  schedule: Schedule;
  visible: boolean;
  onClose: () => void;
  onUpdate?: () => void;
}

const ScheduleDetail: React.FC<ScheduleDetailProps> = ({ schedule, visible, onClose, onUpdate }) => {
  const [editMode, setEditMode] = useState(false);
  const [form] = Form.useForm();
  const { updateSchedule, deleteSchedule, runScheduleNow } = useSchedules();
  const { stats } = useScheduleHistory(schedule.id);

  const handleEdit = () => {
    form.setFieldsValue({
      name: schedule.name,
      description: schedule.description,
      schedule: schedule.schedule,
      config: schedule.config,
      enabled: schedule.enabled,
    });
    setEditMode(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const updateData: UpdateScheduleData = {
        name: values.name,
        description: values.description,
        schedule: values.schedule,
        config: values.config,
        enabled: values.enabled,
      };
      
      await updateSchedule(schedule.id, updateData);
      setEditMode(false);
      onUpdate?.();
    } catch (error) {
      console.error('Failed to update schedule:', error);
    }
  };

  const handleDelete = async () => {
    Modal.confirm({
      title: 'Delete Schedule',
      content: `Are you sure you want to delete "${schedule.name}"? This action cannot be undone.`,
      okText: 'Delete',
      okType: 'danger',
      onOk: async () => {
        await deleteSchedule(schedule.id);
        onClose();
        onUpdate?.();
      },
    });
  };

  const handleRunNow = async () => {
    await runScheduleNow(schedule.id);
  };

  const getCronDescription = () => {
    try {
      return cronstrue.toString(schedule.schedule);
    } catch {
      return schedule.schedule;
    }
  };

  const getLastRun = () => {
    if (!stats?.last_run) return null;
    const run = stats.last_run;
    return {
      time: dayjs(run.started_at).format('YYYY-MM-DD HH:mm:ss'),
      status: run.status,
      duration: run.duration,
    };
  };

  return (
    <Modal
      title={editMode ? "Edit Schedule" : "Schedule Details"}
      open={visible}
      onCancel={onClose}
      width={800}
      footer={
        editMode ? (
          <Space>
            <Button onClick={() => setEditMode(false)}>Cancel</Button>
            <Button type="primary" onClick={handleSave}>Save Changes</Button>
          </Space>
        ) : (
          <Space>
            <Button onClick={onClose}>Close</Button>
            <Button icon={<EditOutlined />} onClick={handleEdit}>Edit</Button>
            <Button icon={<PlayCircleOutlined />} onClick={handleRunNow} type="primary">
              Run Now
            </Button>
            <Button danger icon={<DeleteOutlined />} onClick={handleDelete}>
              Delete
            </Button>
          </Space>
        )
      }
    >
      {editMode ? (
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="Schedule Name"
            rules={[{ required: true, message: 'Please enter a schedule name' }]}
          >
            <Input size="large" />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <TextArea rows={3} />
          </Form.Item>

          <Form.Item
            name="schedule"
            label="Schedule Expression"
            rules={[{ required: true, message: 'Please set a schedule' }]}
          >
            <ScheduleBuilder />
          </Form.Item>

          <Form.Item label="Task Configuration">
            <TaskConfigurator
              taskType={schedule.task_type}
              value={form.getFieldValue('config')}
              onChange={(config) => form.setFieldValue('config', config)}
            />
          </Form.Item>

          <Form.Item name="enabled" label="Status" valuePropName="checked">
            <Switch checkedChildren="Enabled" unCheckedChildren="Disabled" />
          </Form.Item>
        </Form>
      ) : (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Descriptions column={2}>
            <Descriptions.Item label="Name" span={2}>
              <Text strong>{schedule.name}</Text>
            </Descriptions.Item>
            
            {schedule.description && (
              <Descriptions.Item label="Description" span={2}>
                {schedule.description}
              </Descriptions.Item>
            )}

            <Descriptions.Item label="Task Type">
              <Tag color={
                schedule.task_type === 'sync' ? 'blue' :
                schedule.task_type === 'analysis' ? 'green' : 'orange'
              }>
                {schedule.task_type.toUpperCase()}
              </Tag>
            </Descriptions.Item>

            <Descriptions.Item label="Status">
              <Tag color={schedule.enabled ? 'green' : 'default'}>
                {schedule.enabled ? 'ENABLED' : 'DISABLED'}
              </Tag>
            </Descriptions.Item>

            <Descriptions.Item label="Schedule" span={2}>
              <Space direction="vertical" size={0}>
                <Text code>{schedule.schedule}</Text>
                <Text type="secondary">{getCronDescription()}</Text>
              </Space>
            </Descriptions.Item>

            <Descriptions.Item label="Created">
              {dayjs(schedule.created_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>

            {schedule.updated_at && (
              <Descriptions.Item label="Last Updated">
                {dayjs(schedule.updated_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            )}

            {schedule.next_run && (
              <Descriptions.Item label="Next Run" span={2}>
                <Space>
                  <ClockCircleOutlined />
                  <Text>{dayjs(schedule.next_run).format('YYYY-MM-DD HH:mm:ss')}</Text>
                  <Text type="secondary">({dayjs(schedule.next_run).fromNow()})</Text>
                </Space>
              </Descriptions.Item>
            )}
          </Descriptions>

          <Divider />

          {stats && (
            <>
              <Title level={5}>Statistics</Title>
              <Row gutter={[16, 16]}>
                <Col xs={24} sm={8}>
                  <Statistic
                    title="Total Runs"
                    value={stats.total_runs}
                    prefix={<ClockCircleOutlined />}
                  />
                </Col>
                <Col xs={24} sm={8}>
                  <Statistic
                    title="Success Rate"
                    value={stats.total_runs > 0 
                      ? Math.round((stats.successful_runs / stats.total_runs) * 100)
                      : 0}
                    suffix="%"
                    prefix={stats.successful_runs > stats.failed_runs ? 
                      <CheckCircleOutlined style={{ color: '#52c41a' }} /> :
                      <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                    }
                  />
                </Col>
                <Col xs={24} sm={8}>
                  <Statistic
                    title="Failed Runs"
                    value={stats.failed_runs}
                    valueStyle={{ color: stats.failed_runs > 0 ? '#ff4d4f' : undefined }}
                  />
                </Col>
              </Row>
            </>
          )}

          {getLastRun() && (
            <>
              <Divider />
              <Alert
                message="Last Run"
                description={
                  <Space direction="vertical" size={0}>
                    <div>
                      <Text type="secondary">Time:</Text> {getLastRun()!.time}
                    </div>
                    <div>
                      <Text type="secondary">Status:</Text>{' '}
                      <Tag color={getLastRun()!.status === 'success' ? 'success' : 'error'}>
                        {getLastRun()!.status}
                      </Tag>
                    </div>
                    {getLastRun()?.duration && (
                      <div>
                        <Text type="secondary">Duration:</Text> {Math.round(getLastRun()!.duration / 60)}m
                      </div>
                    )}
                  </Space>
                }
                type={getLastRun()!.status === 'success' ? 'success' : 'error'}
              />
            </>
          )}

          <Divider />

          <Title level={5}>Configuration</Title>
          <pre style={{ 
            background: '#f5f5f5', 
            padding: '12px', 
            borderRadius: '4px',
            overflow: 'auto',
            maxHeight: '200px'
          }}>
            {JSON.stringify(schedule.config, null, 2)}
          </pre>
        </Space>
      )}
    </Modal>
  );
};

export default ScheduleDetail;