import React, { useEffect, useState } from 'react';
import { Button, Card, Form, Input, Modal, Select, Space, Table, Tag, Typography, message } from 'antd';
import { DeleteOutlined, KeyOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';

import { del, get, post } from '../api/client';


const userTypeOptions = [
  { label: '导师', value: 'professor' },
  { label: '学生', value: 'student' },
  { label: '管理员', value: 'staff' },
];

const userTypeColor = {
  导师: 'blue',
  学生: 'green',
  管理员: 'gold',
  超级管理员: 'red',
  普通用户: 'default',
};


export default function TokensPage() {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [filters, setFilters] = useState({ user_type: undefined });
  const [sorter, setSorter] = useState({ order_by: 'created', order_direction: 'desc' });
  const [data, setData] = useState({ count: 0, results: [] });
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });
  const [createOpen, setCreateOpen] = useState(false);
  const [form] = Form.useForm();

  const fetchData = async (
    page = pagination.current,
    pageSize = pagination.pageSize,
    search = keyword,
    nextFilters = filters,
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
      if (nextFilters.user_type) params.set('user_type', nextFilters.user_type);
      const payload = await get(`/tokens/?${params.toString()}`);
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

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      await post('/tokens/', values);
      message.success('认证令牌已生成');
      setCreateOpen(false);
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
      title: `确认删除 ${record.username} 的认证令牌吗？`,
      okText: '删除',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          const payload = await del(`/tokens/${record.key}/`);
          message.success(payload.detail || '删除成功');
          fetchData();
        } catch (err) {
          message.error(err.message);
        }
      },
    });
  };

  const handleRegenerate = (record) => {
    Modal.confirm({
      title: `确认重新生成 ${record.username} 的认证令牌吗？`,
      okText: '重新生成',
      cancelText: '取消',
      onOk: async () => {
        try {
          await post(`/tokens/${record.key}/regenerate/`, {});
          message.success('认证令牌已重新生成');
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
    {
      title: '用户类型',
      dataIndex: 'user_type',
      key: 'user_type',
      render: (value) => <Tag color={userTypeColor[value] || 'default'}>{value}</Tag>,
    },
    { title: '认证令牌', dataIndex: 'key', key: 'key', sorter: true, ellipsis: true },
    { title: '创建时间', dataIndex: 'created', key: 'created', sorter: true, render: (value) => (value ? new Date(value).toLocaleString() : '-') },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button size="small" icon={<ReloadOutlined />} onClick={() => handleRegenerate(record)}>重新生成</Button>
          <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record)}>删除</Button>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Card className="page-card" bordered={false}>
        <Typography.Title level={3}>认证令牌</Typography.Title>
        <div className="toolbar" style={{ gap: 12, flexWrap: 'wrap' }}>
          <Input.Search
            placeholder="按用户名、显示名称或令牌搜索"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onSearch={(value) => fetchData(1, pagination.pageSize, value)}
            allowClear
            style={{ maxWidth: 320 }}
          />
          <Select
            allowClear
            placeholder="按用户类型筛选"
            style={{ width: 160 }}
            value={filters.user_type}
            options={userTypeOptions}
            onChange={(value) => {
              const next = { ...filters, user_type: value };
              setFilters(next);
              fetchData(1, pagination.pageSize, keyword, next, sorter);
            }}
          />
          <Space wrap>
            <Button onClick={() => fetchData(1, pagination.pageSize, keyword, filters, sorter)}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>新建认证令牌</Button>
          </Space>
        </div>
        <Table
          rowKey="key"
          loading={loading}
          columns={columns}
          dataSource={data.results}
          pagination={{ current: pagination.current, pageSize: pagination.pageSize, total: data.count, showSizeChanger: true }}
          onChange={(pager, _filters, tableSorter) => {
            const nextSorter = tableSorter?.field
              ? { order_by: tableSorter.field, order_direction: tableSorter.order === 'descend' ? 'desc' : 'asc' }
              : sorter;
            setSorter(nextSorter);
            fetchData(pager.current, pager.pageSize, keyword, filters, nextSorter);
          }}
        />
      </Card>

      <Modal
        title="新建认证令牌"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={handleCreate}
        confirmLoading={saving}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input placeholder="请输入 Django 用户名" prefix={<KeyOutlined />} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
