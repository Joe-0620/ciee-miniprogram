import React, { useEffect, useState } from 'react';
import { Button, Card, Form, Input, InputNumber, Modal, Select, Space, Table, Typography, message } from 'antd';
import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';

import { del, get, patch, post } from '../api/client';

function formatSubjectOption(item) {
  if (!item) return '-';
  const parts = [item.subject_type_display].filter(Boolean);
  if (item.subject_code) {
    parts.push(item.subject_code);
  }
  return `${item.subject_name}${parts.length ? `（${parts.join(' / ')}）` : ''}`;
}

export default function DoctorQuotasPage() {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [filters, setFilters] = useState({
    department_id: undefined,
    professor_id: undefined,
    subject_id: undefined,
  });
  const [sorter, setSorter] = useState({ order_by: 'teacher_identity_id', order_direction: 'asc' });
  const [data, setData] = useState({ count: 0, results: [] });
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });
  const [departments, setDepartments] = useState([]);
  const [professors, setProfessors] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [editingRecord, setEditingRecord] = useState(null);
  const [editOpen, setEditOpen] = useState(false);
  const [form] = Form.useForm();

  const fetchAllProfessors = async () => {
    const pageSize = 100;
    let page = 1;
    let allResults = [];
    let total = 0;

    do {
      const payload = await get(`/professors/?page=${page}&page_size=${pageSize}&order_by=website_order&order_direction=asc`);
      const results = payload?.results || [];
      total = payload?.count || results.length;
      allResults = allResults.concat(results);
      page += 1;
    } while (allResults.length < total);

    return allResults;
  };

  const loadOptions = async () => {
    try {
      const [departmentPayload, professorList, subjectPayload] = await Promise.all([
        get('/departments/'),
        fetchAllProfessors(),
        get('/subjects/?page=1&page_size=500'),
      ]);
      setDepartments(Array.isArray(departmentPayload) ? departmentPayload : []);
      setProfessors(professorList);
      setSubjects((subjectPayload?.results || []).filter((item) => item.subject_type === 2));
    } catch (error) {
      message.error(error.message);
    }
  };

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
      if (search.trim()) {
        params.set('search', search.trim());
      }
      Object.entries(nextFilters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.set(key, String(value));
        }
      });
      const payload = await get(`/doctor-quotas/?${params.toString()}`);
      setData(payload);
      setPagination({ current: payload.page, pageSize: payload.page_size });
    } catch (error) {
      message.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOptions();
    fetchData(1, 10);
  }, []);

  const updateFilter = (key, value) => {
    const nextFilters = { ...filters, [key]: value };
    setFilters(nextFilters);
    fetchData(1, pagination.pageSize, keyword, nextFilters, sorter);
  };

  const openCreateModal = () => {
    setEditingRecord(null);
    form.resetFields();
    form.setFieldsValue({ total_quota: 0, used_quota: 0, remaining_quota: 0 });
    setEditOpen(true);
  };

  const openEditModal = (record) => {
    setEditingRecord(record);
    form.setFieldsValue({
      professor_id: record.professor_id,
      subject_id: record.subject_id,
      total_quota: record.total_quota,
      used_quota: record.used_quota,
      remaining_quota: record.remaining_quota,
    });
    setEditOpen(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const payload = editingRecord
        ? await patch(`/doctor-quotas/${editingRecord.id}/`, values)
        : await post('/doctor-quotas/', values);
      message.success(payload.detail || '保存成功');
      setEditOpen(false);
      form.resetFields();
      fetchData();
    } catch (error) {
      if (!error?.errorFields) {
        message.error(error.message);
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = (record) => {
    Modal.confirm({
      centered: true,
      title: `确认删除 ${record.professor_name} - ${record.subject_name} 吗？`,
      okText: '删除',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          const payload = await del(`/doctor-quotas/${record.id}/`);
          message.success(payload.detail || '删除成功');
          fetchData();
        } catch (error) {
          message.error(error.message);
        }
      },
    });
  };

  const handleClearAll = () => {
    Modal.confirm({
      centered: true,
      title: '确认一键删除全部博士专业名额记录吗？',
      content: '此操作会删除当前所有导师博士专业名额记录，且不可恢复。',
      okText: '删除全部',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          const payload = await post('/doctor-quotas/actions/clear-all/', {});
          message.success(payload.detail || '删除成功');
          fetchData(1, pagination.pageSize, keyword, filters, sorter);
        } catch (error) {
          message.error(error.message);
        }
      },
    });
  };

  const selectSearchProps = {
    showSearch: true,
    optionFilterProp: 'label',
    filterOption: (input, option) => String(option?.label || '').toLowerCase().includes(input.toLowerCase()),
  };

  const columns = [
    { title: '导师', dataIndex: 'professor_name', key: 'professor_name', sorter: true },
    { title: '工号', dataIndex: 'teacher_identity_id', key: 'teacher_identity_id', sorter: true },
    { title: '博士专业', dataIndex: 'subject_name', key: 'subject_name', sorter: true },
    { title: '专业代码', dataIndex: 'subject_code', key: 'subject_code', sorter: true },
    { title: '总名额', dataIndex: 'total_quota', key: 'total_quota', sorter: true },
    { title: '已用名额', dataIndex: 'used_quota', key: 'used_quota', sorter: true },
    { title: '剩余名额', dataIndex: 'remaining_quota', key: 'remaining_quota', sorter: true },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEditModal(record)}>
            编辑
          </Button>
          <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record)}>
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Card className="page-card" bordered={false}>
        <Typography.Title level={3}>导师博士专业名额</Typography.Title>
        <div className="toolbar" style={{ gap: 12, flexWrap: 'wrap' }}>
          <Input.Search
            placeholder="按导师、工号或专业搜索"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            onSearch={(value) => fetchData(1, pagination.pageSize, value)}
            allowClear
            style={{ maxWidth: 280 }}
          />
          <Select
            allowClear
            placeholder="按方向筛选"
            style={{ width: 180 }}
            value={filters.department_id}
            options={departments.map((item) => ({ label: item.department_name, value: item.id }))}
            onChange={(value) => updateFilter('department_id', value)}
          />
          <Select
            allowClear
            {...selectSearchProps}
            placeholder="按导师筛选"
            style={{ width: 220 }}
            value={filters.professor_id}
            options={professors.map((item) => ({ label: `${item.name} (${item.teacher_identity_id})`, value: item.id }))}
            onChange={(value) => updateFilter('professor_id', value)}
          />
          <Select
            allowClear
            {...selectSearchProps}
            placeholder="按博士专业筛选"
            style={{ width: 240 }}
            value={filters.subject_id}
            options={subjects.map((item) => ({ label: formatSubjectOption(item), value: item.id }))}
            onChange={(value) => updateFilter('subject_id', value)}
          />
          <Space wrap>
            <Button onClick={() => fetchData(1, pagination.pageSize, keyword, filters, sorter)}>刷新</Button>
            <Button danger onClick={handleClearAll}>
              一键删除全部记录
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
              新建博士专业名额
            </Button>
          </Space>
        </div>

        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={data.results}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: data.count,
            showSizeChanger: true,
          }}
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
        title={editingRecord ? '编辑导师博士专业名额' : '新建导师博士专业名额'}
        open={editOpen}
        onCancel={() => setEditOpen(false)}
        onOk={handleSave}
        confirmLoading={saving}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="professor_id" label="导师" rules={[{ required: true, message: '请选择导师' }]}>
            <Select
              {...selectSearchProps}
              allowClear
              placeholder="请输入导师姓名或工号搜索"
              options={professors.map((item) => ({ label: `${item.name} (${item.teacher_identity_id})`, value: item.id }))}
            />
          </Form.Item>
          <Form.Item name="subject_id" label="博士专业" rules={[{ required: true, message: '请选择博士专业' }]}>
            <Select
              {...selectSearchProps}
              allowClear
              placeholder="请输入专业名称或代码搜索"
              options={subjects.map((item) => ({ label: formatSubjectOption(item), value: item.id }))}
            />
          </Form.Item>
          <Form.Item name="total_quota" label="总名额" rules={[{ required: true, message: '请输入总名额' }]}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="used_quota" label="已用名额" rules={[{ required: true, message: '请输入已用名额' }]}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="remaining_quota" label="剩余名额">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
