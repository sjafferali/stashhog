import React from 'react'
import { Card, Button, Space, Statistic, Row, Col } from 'antd'
import { useNavigate } from 'react-router-dom'
import { BulbOutlined, FileTextOutlined, RocketOutlined } from '@ant-design/icons'

const Analysis: React.FC = () => {
  const navigate = useNavigate()

  return (
    <div>
      <h1>Analysis Overview</h1>
      
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={8}>
          <Card>
            <Statistic
              title="Scenes Analyzed"
              value={0}
              suffix="/ 0"
              prefix={<BulbOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <Card>
            <Statistic
              title="Analysis Plans"
              value={0}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <Card>
            <Statistic
              title="Pending Analysis"
              value={0}
              prefix={<RocketOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card title="Quick Actions">
        <Space>
          <Button type="primary" onClick={() => navigate('/analysis/plans')}>
            Manage Plans
          </Button>
          <Button>Run Batch Analysis</Button>
          <Button>View Recent Results</Button>
        </Space>
      </Card>
    </div>
  )
}

export default Analysis