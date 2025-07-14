import React from 'react'
import { Card, Row, Col, Statistic } from 'antd'
import {
  VideoCameraOutlined,
  UserOutlined,
  TagsOutlined,
  HomeOutlined,
} from '@ant-design/icons'

const Dashboard: React.FC = () => {
  return (
    <div>
      <h1>Dashboard</h1>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Scenes"
              value={0}
              prefix={<VideoCameraOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Performers"
              value={0}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Tags"
              value={0}
              prefix={<TagsOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Studios"
              value={0}
              prefix={<HomeOutlined />}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard