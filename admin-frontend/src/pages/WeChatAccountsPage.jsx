import React, { useEffect, useState } from 'react';
import { Button, Card, Form, Input, Modal, Space, Table, Typography, message } from 'antd';
import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';

import { del, get, patch, post } from '../api/client';


export default function WeChatAccountsPage() {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [sorter, setSorter] = useState({ order_by: 'username', order_direction: 'asc' });
  const [data, setData] = useState({ count: 0, results: [] });
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });
  const [editingRecord, setEditingRecord] = useState(null);
  const [editOpen, setEditOpen] = useState(false);
  const [form] = Form.useForm();

  const fetchData = async (
    page = pagination.current,
    pageSize = pagination.pageSize,
    search = keyword,
    nextSorter = sorter,
  ) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
        order_by: nextSorter.order_by,
        order_direction: nextSorter.order_direction,
      });
      if (search.trim()) params.set('search', search.trim());
      const payload = await get(`/wechat-accounts/?${params.toString()}`);
      setData(payload);
      setPagination({ current: payload.page, pageSize: payload.page_size });
    } catch (err) {
      message.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(1, 10);
  }, []);

  const openCreateModal = () => {
    setEditingRecord(null);
    form.resetFields();
    setEditOpen(true);
  };

  const openEditModal = (record) => {
    setEditingRecord(record);
    form.setFieldsValue({
      username: record.username,
      openid: record.openid,
      session_key: record.session_key,
    });
    setEditOpen(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const payload = editingRecord
        ? await patch(`/wechat-accounts/${editingRecord.id}/`, values)
        : await post('/wechat-accounts/', values);
      message.success(payload.detail || '保存成功');
      setEditOpen(false);
      form.resetFields();
      fetchData();
    } catch (err) {
      if (!err?.errorFields) {
        message.error(err.message);
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = (record) => {
    Modal.confirm({
      title: `确认删除 ${record.username} 的微信绑定吗？`,
      okText: '删除',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          const payload = await del(`/wechat-accounts/${record.id}/`);
          message.success(payload.detail || '删除成功');
          fetchData();
        } catch (err) {
          message.error(err.message);
        }
      },
    });
  };

  const columns = [
    { title: '用户名', dataIndex: 'username', key: 'username', sorter: true },
    { title: '显示名称', dataIndex: 'user_display_name', key: 'user_display_name' },
    { title: 'openid', dataIndex: 'openid', key: 'openid', sorter: true, ellipsis: true },
    { title: 'session_key', dataIndex: 'session_key', key: 'session_key', ellipsis: true },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEditModal(record)}>编辑</Button>
          <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record)}>删除</Button>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Card className="page-card" bordered={false}>
        <Typography.Title level={3}>微信账号绑定</Typography.Title>
        <div className="toolbar" style={{ gap: 12, flexWrap: 'wrap' }}>
          <Input.Search
            placeholder="按用户名或 openid 搜索"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onSearch={(value) => fetchData(1, pagination.pageSize, value)}
            allowClear
            style={{ maxWidth: 320 }}
          />
          <Space wrap>
            <Button onClick={() => fetchData(1, pagination.pageSize, keyword, sorter)}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>新建微信绑定</Button>
          </Space>
        </div>
        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={data.results}
          pagination={{ current: pagination.current, pageSize: pagination.pageSize, total: data.count, showSizeChanger: true }}
          onChange={(pager, _filters, tableSorter) => {
            const nextSorter = tableSorter?.field
              ? { order_by: tableSorter.field, order_direction: tableSorter.order === 'descend' ? 'desc' : 'asc' }
              : sorter;
            setSorter(nextSorter);
            fetchData(pager.current, pager.pageSize, keyword, nextSorter);
          }}
        />
      </Card>

      <Modal
        title={editingRecord ? '编辑微信账号绑定' : '新建微信账号绑定'}
        open={editOpen}
        onCancel={() => setEditOpen(false)}
        onOk={handleSave}
        confirmLoading={saving}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input placeholder="请输入 Django 用户名" />
          </Form.Item>
          <Form.Item name="openid" label="openid" rules={[{ required: true, message: '请输入 openid' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="session_key" label="session_key" rules={[{ required: true, message: '请输入 session_key' }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
