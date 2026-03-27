import React, { useEffect, useMemo, useState } from 'react';
import { Button, Card, Form, Input, InputNumber, Modal, Select, Space, Switch, Table, message } from 'antd';
import { EditOutlined, PlusOutlined } from '@ant-design/icons';

import { del, get, patch, post } from '../api/client';
import PageHeader from '../components/PageHeader';
import StatusTag from '../components/StatusTag';
import { confirmDanger } from '../utils/confirm';


export default function AdmissionBatchesPage() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState([]);
  const [keyword, setKeyword] = useState('');
  const [filters, setFilters] = useState({ admission_year: undefined, is_active: undefined });
  const [sorter, setSorter] = useState({ order_by: 'admission_year', order_direction: 'desc' });
  const [editOpen, setEditOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState(null);
  const [form] = Form.useForm();

  const yearOptions = useMemo(() => {
    const currentYear = new Date().getFullYear();
    return Array.from({ length: 6 }, (_, index) => {
      const year = currentYear - 1 + index;
      return { label: `${year}届`, value: year };
    });
  }, []);

  async function fetchData(nextKeyword = keyword, nextFilters = filters, nextSorter = sorter) {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        order_by: nextSorter.order_by,
        order_direction: nextSorter.order_direction,
      });
      if (nextKeyword.trim()) params.set('search', nextKeyword.trim());
      Object.entries(nextFilters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.set(key, String(value));
        }
      });
      const payload = await get(`/admission-batches/?${params.toString()}`);
      setData(Array.isArray(payload) ? payload : []);
    } catch (error) {
      message.error(error.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchData();
  }, []);

  function updateFilter(key, value) {
    const nextFilters = { ...filters, [key]: value };
    setFilters(nextFilters);
    fetchData(keyword, nextFilters, sorter);
  }

  function resetFilters() {
    const nextFilters = { admission_year: undefined, is_active: undefined };
    setKeyword('');
    setFilters(nextFilters);
    fetchData('', nextFilters, sorter);
  }

  function openCreateModal() {
    setEditingRecord(null);
    form.resetFields();
    form.setFieldsValue({
      admission_year: new Date().getMonth() >= 8 ? new Date().getFullYear() + 1 : new Date().getFullYear(),
      is_active: true,
      sort_order: 0,
    });
    setEditOpen(true);
  }

  function openEditModal(record) {
    setEditingRecord(record);
    form.setFieldsValue({
      name: record.name,
      admission_year: record.admission_year,
      batch_code: record.batch_code,
      sort_order: record.sort_order,
      is_active: record.is_active,
      description: record.description,
    });
    setEditOpen(true);
  }

  async function handleSave() {
    try {
      const values = await form.validateFields();
      const payload = editingRecord
        ? await patch(`/admission-batches/${editingRecord.id}/`, values)
        : await post('/admission-batches/', values);
      message.success(payload?.detail || (editingRecord ? '招生批次已更新' : '招生批次已创建'));
      setEditOpen(false);
      form.resetFields();
      await fetchData();
    } catch (error) {
      if (!error?.errorFields) {
        message.error(error.message);
      }
    }
  }

  async function handleDelete(record) {
    try {
      const payload = await del(`/admission-batches/${record.id}/`);
      message.success(payload?.detail || '招生批次已删除');
      await fetchData();
    } catch (error) {
      message.error(error.message);
    }
  }

  const columns = [
    { title: '批次名称', dataIndex: 'name', key: 'name', sorter: true },
    {
      title: '届别',
      dataIndex: 'admission_year',
      key: 'admission_year',
      sorter: true,
      render: (value) => `${value}届`,
    },
    { title: '批次编码', dataIndex: 'batch_code', key: 'batch_code', sorter: true, render: (value) => value || '-' },
    { title: '排序值', dataIndex: 'sort_order', key: 'sort_order', sorter: true },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      sorter: true,
      render: (value) => <StatusTag tone={value ? 'success' : 'default'}>{value ? '启用中' : '已停用'}</StatusTag>,
    },
    { title: '说明', dataIndex: 'description', key: 'description', render: (value) => value || '-' },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEditModal(record)}>
            编辑
          </Button>
          <Button
            size="small"
            danger
            onClick={() =>
              confirmDanger({
                title: '确认删除这个招生批次吗？',
                content: `${record.admission_year}届 - ${record.name}`,
                onOk: () => handleDelete(record),
              })
            }
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Card className="page-card" bordered={false}>
        <PageHeader
          items={[{ title: '名额与配置' }, { title: '招生批次' }]}
          title="招生批次"
          subtitle="按届别维护不同招生批次，供学生归档和后台筛选使用。"
        />

        <div className="page-toolbar">
          <div className="page-filters">
            <Input.Search
              allowClear
              placeholder="按批次名称或编码搜索"
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
              onSearch={(value) => fetchData(value, filters, sorter)}
              style={{ width: 240 }}
            />
            <Select
              allowClear
              placeholder="按届别筛选"
              style={{ width: 140 }}
              value={filters.admission_year}
              options={yearOptions}
              onChange={(value) => updateFilter('admission_year', value)}
            />
            <Select
              allowClear
              placeholder="按状态筛选"
              style={{ width: 140 }}
              value={filters.is_active}
              options={[
                { label: '启用中', value: 'true' },
                { label: '已停用', value: 'false' },
              ]}
              onChange={(value) => updateFilter('is_active', value)}
            />
          </div>

          <div className="page-actions">
            <Button onClick={() => fetchData()}>刷新</Button>
            <Button onClick={resetFilters}>清空筛选</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
              新建批次
            </Button>
          </div>
        </div>

        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={data}
          pagination={false}
          onChange={(_, __, tableSorter) => {
            const nextSorter = Array.isArray(tableSorter) ? tableSorter[0] : tableSorter;
            const resolvedSorter = nextSorter?.field
              ? {
                  order_by: nextSorter.field,
                  order_direction: nextSorter.order === 'descend' ? 'desc' : 'asc',
                }
              : sorter;
            setSorter(resolvedSorter);
            fetchData(keyword, filters, resolvedSorter);
          }}
        />
      </Card>

      <Modal
        open={editOpen}
        title={editingRecord ? '编辑招生批次' : '新建招生批次'}
        onCancel={() => setEditOpen(false)}
        onOk={handleSave}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item label="批次名称" name="name" rules={[{ required: true, message: '请输入批次名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="届别" name="admission_year" rules={[{ required: true, message: '请选择届别' }]}>
            <Select options={yearOptions} />
          </Form.Item>
          <Form.Item label="批次编码" name="batch_code">
            <Input />
          </Form.Item>
          <Form.Item label="排序值" name="sort_order">
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="是否启用" name="is_active" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="停用" />
          </Form.Item>
          <Form.Item label="批次说明" name="description">
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
