import React, { useEffect, useState } from 'react';
import { Button, Card, Form, Input, InputNumber, Modal, Select, Space, Switch, Table, Tag, message } from 'antd';
import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';

import { del, get, patch, post } from '../api/client';
import PageHeader from '../components/PageHeader';
import { loadPageState, savePageState } from '../utils/pageState';

const scopeOptions = [
  { label: '硕士共享池', value: 'master' },
  { label: '博士共享池', value: 'doctor' },
];

const campusOptions = [
  { label: '北京', value: 'beijing' },
  { label: '烟台', value: 'yantai' },
];

function formatSubjectOption(item) {
  const parts = [];
  if (item.subject_type_display) parts.push(item.subject_type_display);
  if (item.subject_code) parts.push(item.subject_code);
  return `${item.subject_name}（${parts.join(' / ')}）`;
}

async function fetchAllPaginated(endpoint, pageSize = 100) {
  const items = [];
  let page = 1;
  let total = 0;

  do {
    const payload = await get(`${endpoint}?page=${page}&page_size=${pageSize}`);
    const pageResults = Array.isArray(payload?.results) ? payload.results : [];
    total = Number(payload?.count || 0);
    items.push(...pageResults);
    page += 1;
  } while (items.length < total);

  return items;
}

export default function SharedQuotaPoolsPage() {
  const initialPageState = loadPageState('shared-quota-pools-page', {
    keyword: '',
    filters: {
      department_id: undefined,
      professor_id: undefined,
      quota_scope: undefined,
      campus: undefined,
    },
    sorter: { order_by: 'teacher_identity_id', order_direction: 'asc' },
    pagination: { current: 1, pageSize: 10 },
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [keyword, setKeyword] = useState(initialPageState.keyword);
  const [filters, setFilters] = useState(initialPageState.filters);
  const [sorter, setSorter] = useState(initialPageState.sorter);
  const [data, setData] = useState({ count: 0, results: [] });
  const [pagination, setPagination] = useState(initialPageState.pagination);
  const [departments, setDepartments] = useState([]);
  const [professors, setProfessors] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [editOpen, setEditOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState(null);
  const [scopeValue, setScopeValue] = useState('master');
  const [form] = Form.useForm();

  const loadOptions = async () => {
    try {
      const [departmentPayload, professorPayload, subjectPayload] = await Promise.all([
        get('/departments/'),
        fetchAllPaginated('/professors'),
        fetchAllPaginated('/subjects'),
      ]);
      setDepartments(Array.isArray(departmentPayload) ? departmentPayload : []);
      setProfessors(professorPayload);
      setSubjects(subjectPayload);
    } catch (err) {
      message.error(err.message);
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
      if (search.trim()) params.set('search', search.trim());
      Object.entries(nextFilters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') params.set(key, String(value));
      });
      const payload = await get(`/shared-quota-pools/?${params.toString()}`);
      setData(payload);
      setPagination({ current: payload.page, pageSize: payload.page_size });
    } catch (err) {
      message.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOptions();
    fetchData(
      initialPageState.pagination.current,
      initialPageState.pagination.pageSize,
      initialPageState.keyword,
      initialPageState.filters,
      initialPageState.sorter,
    );
  }, []);

  useEffect(() => {
    savePageState('shared-quota-pools-page', { keyword, filters, sorter, pagination });
  }, [keyword, filters, sorter, pagination]);

  const updateFilter = (key, value) => {
    const next = { ...filters, [key]: value };
    setFilters(next);
    fetchData(1, pagination.pageSize, keyword, next, sorter);
  };

  const openCreateModal = () => {
    setEditingRecord(null);
    setScopeValue('master');
    form.resetFields();
    form.setFieldsValue({
      quota_scope: 'master',
      campus: 'beijing',
      total_quota: 0,
      used_quota: 0,
      remaining_quota: 0,
      is_active: true,
    });
    setEditOpen(true);
  };

  const openEditModal = (record) => {
    setEditingRecord(record);
    setScopeValue(record.quota_scope);
    form.setFieldsValue({
      professor_id: record.professor_id,
      pool_name: record.pool_name,
      quota_scope: record.quota_scope,
      campus: record.campus,
      subject_ids: record.subject_ids,
      total_quota: record.total_quota,
      used_quota: record.used_quota,
      remaining_quota: record.remaining_quota,
      is_active: record.is_active,
      notes: record.notes,
    });
    setEditOpen(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const payload = editingRecord
        ? await patch(`/shared-quota-pools/${editingRecord.id}/`, values)
        : await post('/shared-quota-pools/', values);
      message.success(payload.detail || '保存成功');
      setEditOpen(false);
      form.resetFields();
      fetchData();
    } catch (err) {
      if (!err?.errorFields) message.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = (record) => {
    Modal.confirm({
      title: `确认删除共享名额池“${record.pool_name}”吗？`,
      centered: true,
      okText: '删除',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          const payload = await del(`/shared-quota-pools/${record.id}/`);
          message.success(payload.detail || '删除成功');
          fetchData();
        } catch (err) {
          message.error(err.message);
        }
      },
    });
  };

  const handleClearAll = () => {
    Modal.confirm({
      centered: true,
      title: '确认一键删除全部共享名额池记录吗？',
      content: '若存在已用名额的共享池，会阻止本次操作。此操作不可恢复。',
      okText: '删除全部',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          const payload = await post('/shared-quota-pools/actions/clear-all/', {});
          message.success(payload.detail || '删除成功');
          fetchData(1, pagination.pageSize, keyword, filters, sorter);
        } catch (err) {
          message.error(err.message);
        }
      },
    });
  };

  const filteredSubjects = subjects.filter((item) => {
    if (scopeValue === 'doctor') return item.subject_type === 2;
    return item.subject_type !== 2;
  });

  const columns = [
    { title: '共享池名称', dataIndex: 'pool_name', key: 'pool_name', sorter: true, width: 220, ellipsis: true, fixed: 'left' },
    { title: '导师', dataIndex: 'professor_name', key: 'professor_name', sorter: true, width: 120, ellipsis: true, fixed: 'left' },
    { title: '工号', dataIndex: 'teacher_identity_id', key: 'teacher_identity_id', sorter: true, width: 110, ellipsis: true },
    { title: '方向', dataIndex: 'department_name', key: 'department_name', width: 140, ellipsis: true, responsive: ['lg'] },
    { title: '类型', dataIndex: 'quota_scope_display', key: 'quota_scope', sorter: true, width: 110, ellipsis: true },
    {
      title: '校区',
      key: 'campus_display',
      width: 100,
      render: (_, record) => (record.quota_scope === 'doctor' ? '不区分' : record.campus_display),
    },
    {
      title: '覆盖专业',
      key: 'subject_labels',
      width: 320,
      ellipsis: true,
      render: (_, record) => (
        <Space size={[4, 4]} wrap>
          {(record.subject_labels || []).map((subject) => (
            <Tag key={subject.id}>{formatSubjectOption(subject)}</Tag>
          ))}
        </Space>
      ),
    },
    { title: '总名额', dataIndex: 'total_quota', key: 'total_quota', sorter: true, width: 90 },
    { title: '已用', dataIndex: 'used_quota', key: 'used_quota', sorter: true, width: 80 },
    { title: '剩余', dataIndex: 'remaining_quota', key: 'remaining_quota', sorter: true, width: 80 },
    {
      title: '状态',
      key: 'is_active',
      width: 90,
      render: (_, record) => (record.is_active ? <Tag color="green">启用</Tag> : <Tag>停用</Tag>),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      fixed: 'right',
      render: (_, record) => (
        <Space wrap className="compact-action-buttons">
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
        <PageHeader
          items={[{ title: '名额与配置' }, { title: '共享名额池' }]}
          title="共享名额池"
          subtitle="配置某位导师在多个专业之间共享使用的招生名额。"
        />

        <div className="page-toolbar">
          <div className="page-filters">
            <Input.Search
              placeholder="按共享池名称、导师、工号或专业搜索"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onSearch={(value) => fetchData(1, pagination.pageSize, value, filters, sorter)}
              allowClear
              style={{ width: 320 }}
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
              showSearch
              optionFilterProp="label"
              placeholder="按导师筛选"
              style={{ width: 220 }}
              value={filters.professor_id}
              options={professors.map((item) => ({ label: `${item.name} (${item.teacher_identity_id})`, value: item.id }))}
              onChange={(value) => updateFilter('professor_id', value)}
            />
            <Select
              allowClear
              placeholder="按类型筛选"
              style={{ width: 160 }}
              value={filters.quota_scope}
              options={scopeOptions}
              onChange={(value) => updateFilter('quota_scope', value)}
            />
            <Select
              allowClear
              placeholder="按校区筛选"
              style={{ width: 160 }}
              value={filters.campus}
              options={campusOptions}
              onChange={(value) => updateFilter('campus', value)}
            />
          </div>
          <div className="page-actions">
            <Button onClick={() => fetchData(1, pagination.pageSize, keyword, filters, sorter)}>刷新</Button>
            <Button danger onClick={handleClearAll}>
              一键删除全部记录
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
              新建共享名额池
            </Button>
          </div>
        </div>

        <Table
          className="dashboard-table"
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={data.results}
          scroll={{ x: 1500 }}
          sticky={{ offsetHeader: 64, offsetScroll: 12 }}
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
        title={editingRecord ? '编辑共享名额池' : '新建共享名额池'}
        open={editOpen}
        onCancel={() => setEditOpen(false)}
        onOk={handleSave}
        confirmLoading={saving}
        destroyOnClose
        width={760}
      >
        <Form
          form={form}
          layout="vertical"
          onValuesChange={(changedValues) => {
            if (!Object.prototype.hasOwnProperty.call(changedValues, 'total_quota')) return;

            const totalQuota = changedValues.total_quota;
            if (editingRecord) {
              const originalTotal = Number(editingRecord.total_quota || 0);
              const originalRemaining = Number(editingRecord.remaining_quota || 0);
              const nextTotal = Number(totalQuota || 0);
              const nextRemaining = Math.max(0, originalRemaining + (nextTotal - originalTotal));
              form.setFieldValue('remaining_quota', nextRemaining);
              return;
            }

            form.setFieldValue('remaining_quota', totalQuota);
          }}
        >
          <Form.Item name="professor_id" label="导师" rules={[{ required: true, message: '请选择导师' }]}>
            <Select
              showSearch
              optionFilterProp="label"
              options={professors.map((item) => ({ label: `${item.name} (${item.teacher_identity_id})`, value: item.id }))}
              placeholder="输入导师姓名或工号搜索"
            />
          </Form.Item>
          <Form.Item name="pool_name" label="共享池名称" rules={[{ required: true, message: '请输入共享池名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="quota_scope" label="名额类型" rules={[{ required: true, message: '请选择名额类型' }]}>
            <Select
              options={scopeOptions}
              onChange={(value) => {
                setScopeValue(value);
                if (value === 'doctor') {
                  form.setFieldValue('campus', undefined);
                } else if (!form.getFieldValue('campus')) {
                  form.setFieldValue('campus', 'beijing');
                }
                form.setFieldValue('subject_ids', []);
              }}
            />
          </Form.Item>
          {scopeValue === 'master' ? (
            <Form.Item name="campus" label="适用校区" rules={[{ required: true, message: '请选择适用校区' }]}>
              <Select options={campusOptions} />
            </Form.Item>
          ) : null}
          <Form.Item name="subject_ids" label="覆盖专业" rules={[{ required: true, message: '请至少选择一个专业' }]}>
            <Select mode="multiple" showSearch options={filteredSubjects.map((item) => ({ label: formatSubjectOption(item), value: item.id }))} />
          </Form.Item>
          <Form.Item name="total_quota" label="总名额" rules={[{ required: true, message: '请输入总名额' }]}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="used_quota" label="已用名额" rules={[{ required: true, message: '请输入已用名额' }]}>
            <InputNumber min={0} style={{ width: '100%' }} disabled />
          </Form.Item>
          <Form.Item name="remaining_quota" label="剩余名额">
            <InputNumber min={0} style={{ width: '100%' }} disabled />
          </Form.Item>
          <Form.Item name="is_active" label="启用状态" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="停用" />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
