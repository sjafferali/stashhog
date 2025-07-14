import React from 'react'
import { Card, Table, Tag, Progress, Button, Space } from 'antd'
import { SyncOutlined, CloseCircleOutlined, RedoOutlined } from '@ant-design/icons'

const JobMonitor: React.FC = () => {
  const columns = [
    {
      title: 'Job Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => {
        const color = type === 'sync' ? 'blue' : type === 'analysis' ? 'green' : 'purple'
        return <Tag color={color}>{type.toUpperCase()}</Tag>
      },
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const color = 
          status === 'completed' ? 'green' :
          status === 'failed' ? 'red' :
          status === 'running' ? 'blue' :
          'default'
        return <Tag color={color}>{status.toUpperCase()}</Tag>
      },
    },
    {
      title: 'Progress',
      key: 'progress',
      render: (record: any) => (
        <Progress
          percent={record.total > 0 ? Math.round((record.progress / record.total) * 100) : 0}
          status={record.status === 'failed' ? 'exception' : 'active'}
        />
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (record: any) => (
        <Space>
          {record.status === 'running' && (
            <Button
              type="link"
              danger
              icon={<CloseCircleOutlined />}
              size="small"
            >
              Cancel
            </Button>
          )}
          {record.status === 'failed' && (
            <Button
              type="link"
              icon={<RedoOutlined />}
              size="small"
            >
              Retry
            </Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <h1>Job Monitor</h1>
      <Card
        extra={
          <Button icon={<SyncOutlined />}>
            Refresh
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={[]}
          loading={false}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
          }}
        />
      </Card>
    </div>
  )
}

export default JobMonitor