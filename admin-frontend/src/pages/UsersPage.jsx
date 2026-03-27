import React, { useEffect, useState } from 'react';
import { Button, Card, Form, Input, Modal, Select, Space, Switch, Table, Tag, Typography, message } from 'antd';
import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';

import { del, get, patch, post } from '../api/client';


const userTypeOptions = [
  { label: '导师', value: 'professor' },
  { label: '学生', value: 'student' },
  { label: '管理员', value: 'staff' },
  { label: '普通用户', value: 'normal' },
];

const userTypeColor = {
  导师: 'blue',
  学生: 'green',
  管理员: 'gold',
  超级管理员: 'red',
  普通用户: 'default',
};


export default function UsersPage() {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [filters, setFilters] = useState({ user_type: undefined, is_active: undefined });
  const [sorter, setSorter] = useState({ order_by: 'date_joined', order_direction: 'desc' });
  const [data, setData] = useState({ count: 0, results: [] });
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });
  const [editingRecord, setEditingRecord] = useState(null);
  const [editOpen, setEditOpen] = useState(false);
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
      Object.entries(nextFilters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.set(key, String(value));
        }
      });
      const payload = await get(`/users/?${params.toString()}`);
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
    form.setFieldsValue({
      is_active: true,
      is_staff: false,
      is_superuser: false,
    });
    setEditOpen(true);
  };

  const openEditModal = async (record) => {
    try {
      const detail = await get(`/users/${record.id}/`);
      setEditingRecord(record);
      form.setFieldsValue({
        username: detail.username,
        first_name: detail.first_name,
        last_name: detail.last_name,
        email: detail.email,
        is_active: detail.is_active,
        is_staff: detail.is_staff,
        is_superuser: detail.is_superuser,
      });
      setEditOpen(true);
    } catch (err) {
      message.error(err.message);
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const payload = editingRecord
        ? await patch(`/users/${editingRecord.id}/`, values)
        : await post('/users/', values);
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
      title: `确认删除用户 ${record.username} 吗？`,
      okText: '删除',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          const payload = await del(`/users/${record.id}/`);
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
    { title: '显示名称', dataIndex: 'display_name', key: 'display_name' },
    { title: '关联对象', dataIndex: 'linked_name', key: 'linked_name', render: (value) => value || '-' },
    {
      title: '用户类型',
      dataIndex: 'user_type',
      key: 'user_type',
      render: (value) => <Tag color={userTypeColor[value] || 'default'}>{value}</Tag>,
    },
    { title: '邮箱', dataIndex: 'email', key: 'email', sorter: true, render: (value) => value || '-' },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      sorter: true,
      render: (value) => <Tag color={value ? 'green' : 'default'}>{value ? '启用' : '停用'}</Tag>,
    },
    {
      title: '后台权限',
      dataIndex: 'is_staff',
      key: 'is_staff',
      sorter: true,
      render: (value) => <Tag color={value ? 'gold' : 'default'}>{value ? '是' : '否'}</Tag>,
    },
    { title: '创建时间', dataIndex: 'date_joined', key: 'date_joined', sorter: true, render: (value) => (value ? new Date(value).toLocaleString() : '-') },
    { title: '最近登录', dataIndex: 'last_login', key: 'last_login', sorter: true, render: (value) => (value ? new Date(value).toLocaleString() : '-') },
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
        <Typography.Title level={3}>用户管理</Typography.Title>
        <div className="toolbar" style={{ gap: 12, flexWrap: 'wrap' }}>
          <Input.Search
            placeholder="按用户名、姓名或邮箱搜索"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onSearch={(value) => fetchData(1, pagination.pageSize, value)}
            allowClear
            style={{ maxWidth: 320 }}
          />
          <Select
            allowClear
            placeholder="按用户类型筛选"
            style={{ width: 170 }}
            value={filters.user_type}
            options={userTypeOptions}
            onChange={(value) => {
              const next = { ...filters, user_type: value };
              setFilters(next);
              fetchData(1, pagination.pageSize, keyword, next, sorter);
            }}
          />
          <Select
            allowClear
            placeholder="按启用状态筛选"
            style={{ width: 170 }}
            value={filters.is_active}
            options={[
              { label: '启用', value: 'true' },
              { label: '停用', value: 'false' },
            ]}
            onChange={(value) => {
              const next = { ...filters, is_active: value };
              setFilters(next);
              fetchData(1, pagination.pageSize, keyword, next, sorter);
            }}
          />
          <Space wrap>
            <Button onClick={() => fetchData(1, pagination.pageSize, keyword, filters, sorter)}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>新建用户</Button>
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
            fetchData(pager.current, pager.pageSize, keyword, filters, nextSorter);
          }}
        />
      </Card>

      <Modal
        title={editingRecord ? '编辑用户' : '新建用户'}
        open={editOpen}
        onCancel={() => setEditOpen(false)}
        onOk={handleSave}
        confirmLoading={saving}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="password" label="密码">
            <Input.Password placeholder={editingRecord ? '留空则不修改密码' : '留空则默认与用户名一致'} />
          </Form.Item>
          <Form.Item name="first_name" label="名">
            <Input />
          </Form.Item>
          <Form.Item name="last_name" label="姓">
            <Input />
          </Form.Item>
          <Form.Item name="email" label="邮箱">
            <Input />
          </Form.Item>
          <Form.Item name="is_active" label="是否启用" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="停用" />
          </Form.Item>
          <Form.Item name="is_staff" label="是否后台管理员" valuePropName="checked">
            <Switch checkedChildren="是" unCheckedChildren="否" />
          </Form.Item>
          <Form.Item name="is_superuser" label="是否超级管理员" valuePropName="checked">
            <Switch checkedChildren="是" unCheckedChildren="否" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
