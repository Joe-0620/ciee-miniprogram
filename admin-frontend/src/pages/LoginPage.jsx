import React, { useState } from 'react';
import { Alert, Button, Card, Form, Input, Space, Typography, message } from 'antd';
import { useNavigate } from 'react-router-dom';

import { post } from '../api/client';
import { setDashboardToken } from '../utils/auth';


export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const onFinish = async (values) => {
    setLoading(true);
    setError('');
    try {
      const payload = await post('/auth/login/', values);
      setDashboardToken(payload.token);
      message.success('登录成功');
      navigate('/', { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-shell">
      <div className="login-panel">
        <div className="login-hero">
          <Typography.Title level={2} style={{ color: '#fff', marginTop: 0 }}>
            CIEE 研究生双选管理后台
          </Typography.Title>
          <Typography.Paragraph style={{ color: 'rgba(255,255,255,0.82)', fontSize: 16, lineHeight: 1.8 }}>
            这里集中处理导师、学生、双选记录、审核流程与名额配置，作为管理员的统一工作台使用。
          </Typography.Paragraph>
          <Space direction="vertical" size={18}>
            <Typography.Text style={{ color: '#dcfce7' }}>统一查看学生、导师、双选记录与审核状态</Typography.Text>
            <Typography.Text style={{ color: '#dcfce7' }}>延续现有后端接口与业务规则，减少迁移成本</Typography.Text>
            <Typography.Text style={{ color: '#dcfce7' }}>与当前 Django 后端共用同一个 Docker 镜像部署</Typography.Text>
          </Space>
        </div>
        <div className="login-form-wrap">
          <Card bordered={false}>
            <Typography.Title level={3}>管理员登录</Typography.Title>
            <Typography.Paragraph type="secondary">
              仅限已开通后台权限的管理员账号登录。
            </Typography.Paragraph>
            {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}
            <Form layout="vertical" onFinish={onFinish}>
              <Form.Item label="用户名" name="username" rules={[{ required: true, message: '请输入用户名' }]}>
                <Input placeholder="请输入管理员用户名" />
              </Form.Item>
              <Form.Item label="密码" name="password" rules={[{ required: true, message: '请输入密码' }]}>
                <Input.Password placeholder="请输入密码" />
              </Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} block>
                登录后台
              </Button>
            </Form>
          </Card>
        </div>
      </div>
    </div>
  );
}
