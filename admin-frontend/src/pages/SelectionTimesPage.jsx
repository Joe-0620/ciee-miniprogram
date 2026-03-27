import React, { useEffect, useState } from 'react';
import { Button, Card, Col, Form, Input, Row, Space, Tag, Typography, message } from 'antd';

import { get, patch } from '../api/client';

function toDatetimeLocal(value) {
  if (!value) {
    return '';
  }
  const date = new Date(value);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function buildTag(status) {
  const colorMap = {
    '未开始': 'default',
    '进行中': 'green',
    '已结束': 'red',
  };
  return <Tag color={colorMap[status] || 'default'}>{status || '未配置'}</Tag>;
}

export default function SelectionTimesPage() {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [meta, setMeta] = useState({
    student: { status_text: '未配置' },
    professor: { status_text: '未配置' },
  });
  const [form] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      const payload = await get('/selection-times/');
      const student = payload?.student || {};
      const professor = payload?.professor || {};
      setMeta({ student, professor });
      form.setFieldsValue({
        student_open_time: toDatetimeLocal(student.open_time),
        student_close_time: toDatetimeLocal(student.close_time),
        professor_open_time: toDatetimeLocal(professor.open_time),
        professor_close_time: toDatetimeLocal(professor.close_time),
      });
    } catch (err) {
      message.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const payload = await patch('/selection-times/', {
        student: {
          open_time: values.student_open_time,
          close_time: values.student_close_time,
        },
        professor: {
          open_time: values.professor_open_time,
          close_time: values.professor_close_time,
        },
      });
      setMeta({
        student: payload?.student || {},
        professor: payload?.professor || {},
      });
      form.setFieldsValue({
        student_open_time: toDatetimeLocal(payload?.student?.open_time),
        student_close_time: toDatetimeLocal(payload?.student?.close_time),
        professor_open_time: toDatetimeLocal(payload?.professor?.open_time),
        professor_close_time: toDatetimeLocal(payload?.professor?.close_time),
      });
      message.success('互选时间已保存');
    } catch (err) {
      if (!err?.errorFields) {
        message.error(err.message);
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card className="page-card" bordered={false} loading={loading}>
      <Typography.Title level={3}>学院师生互选时间设置</Typography.Title>
      <Typography.Paragraph type="secondary">
        系统固定保留两条配置：一条控制学生提交导师申请，一条控制导师处理学生申请。后台不再允许新增或删除多条记录。
      </Typography.Paragraph>

      <Form form={form} layout="vertical">
        <Row gutter={[16, 16]}>
          <Col xs={24} xl={12}>
            <Card bordered={false} className="inner-card">
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <Typography.Title level={4} style={{ margin: 0 }}>
                  学生互选时间
                </Typography.Title>
                <Typography.Text type="secondary">
                  控制学生提交导师选择申请的时间窗口
                </Typography.Text>
                {buildTag(meta.student?.status_text)}
              </Space>
              <Row gutter={12} style={{ marginTop: 20 }}>
                <Col span={24}>
                  <Form.Item
                    name="student_open_time"
                    label="开始时间"
                    rules={[{ required: true, message: '请选择学生端开始时间' }]}
                  >
                    <Input type="datetime-local" />
                  </Form.Item>
                </Col>
                <Col span={24}>
                  <Form.Item
                    name="student_close_time"
                    label="结束时间"
                    rules={[{ required: true, message: '请选择学生端结束时间' }]}
                  >
                    <Input type="datetime-local" />
                  </Form.Item>
                </Col>
              </Row>
            </Card>
          </Col>

          <Col xs={24} xl={12}>
            <Card bordered={false} className="inner-card">
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <Typography.Title level={4} style={{ margin: 0 }}>
                  导师互选时间
                </Typography.Title>
                <Typography.Text type="secondary">
                  控制导师接受或拒绝学生申请的时间窗口
                </Typography.Text>
                {buildTag(meta.professor?.status_text)}
              </Space>
              <Row gutter={12} style={{ marginTop: 20 }}>
                <Col span={24}>
                  <Form.Item
                    name="professor_open_time"
                    label="开始时间"
                    rules={[{ required: true, message: '请选择导师端开始时间' }]}
                  >
                    <Input type="datetime-local" />
                  </Form.Item>
                </Col>
                <Col span={24}>
                  <Form.Item
                    name="professor_close_time"
                    label="结束时间"
                    rules={[{ required: true, message: '请选择导师端结束时间' }]}
                  >
                    <Input type="datetime-local" />
                  </Form.Item>
                </Col>
              </Row>
            </Card>
          </Col>
        </Row>

        <div className="toolbar" style={{ marginTop: 24, gap: 12 }}>
          <Button onClick={fetchData}>刷新</Button>
          <Button type="primary" onClick={handleSave} loading={saving}>
            保存设置
          </Button>
        </div>
      </Form>
    </Card>
  );
}
