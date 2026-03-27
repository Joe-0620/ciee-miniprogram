import React, { useEffect, useMemo, useState } from 'react';
import { PlusOutlined } from '@ant-design/icons';
import { Button, Card, Form, Input, InputNumber, Modal, Select, Space, Table, Tabs, Typography, message } from 'antd';

import { get, patch, post } from '../api/client';
import PageHeader from '../components/PageHeader';
import { confirmDanger } from '../utils/confirm';

const subjectTypeOptions = [
  { label: '专业硕士', value: 0 },
  { label: '学术硕士', value: 1 },
  { label: '博士', value: 2 },
];

function buildSubjectQuery(page, pageSize, search, filters, sorter) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    order_by: sorter.order_by,
    order_direction: sorter.order_direction,
  });

  if (search.trim()) {
    params.set('search', search.trim());
  }

  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, String(value));
    }
  });

  return params;
}

function sumBy(rows, key) {
  return rows.reduce((total, item) => total + (Number(item[key]) || 0), 0);
}

function buildSharedPoolMap(rows, quotaScope) {
  const map = new Map();
  rows
    .filter((item) => item.quota_scope === quotaScope)
    .forEach((pool) => {
      (pool.subject_labels || []).forEach((subject) => {
        if (!map.has(subject.id)) {
          map.set(subject.id, []);
        }
        map.get(subject.id).push(pool);
      });
    });
  return map;
}

function buildMasterSubjectGroups(rows, sharedPoolMap) {
  const groups = new Map();

  rows.forEach((item) => {
    if (!groups.has(item.subject_id)) {
      groups.set(item.subject_id, {
        key: `master-${item.subject_id}`,
        subject_id: item.subject_id,
        subject_name: item.subject_name,
        subject_code: item.subject_code,
        subject_type_display: item.subject_type_display,
        allocations: [],
      });
    }
    groups.get(item.subject_id).allocations.push(item);
  });

  return Array.from(groups.values()).map((group) => {
    const beijingTotal = sumBy(group.allocations, 'beijing_quota');
    const beijingRemaining = sumBy(group.allocations, 'beijing_remaining_quota');
    const yantaiTotal = sumBy(group.allocations, 'yantai_quota');
    const yantaiRemaining = sumBy(group.allocations, 'yantai_remaining_quota');
    const sharedPools = sharedPoolMap.get(group.subject_id) || [];

    return {
      ...group,
      professor_count: group.allocations.length,
      beijing_total: beijingTotal,
      beijing_used: Math.max(0, beijingTotal - beijingRemaining),
      beijing_remaining: beijingRemaining,
      yantai_total: yantaiTotal,
      yantai_used: Math.max(0, yantaiTotal - yantaiRemaining),
      yantai_remaining: yantaiRemaining,
      total_quota: sumBy(group.allocations, 'total_quota'),
      shared_pools: sharedPools,
      shared_pool_count: sharedPools.length,
    };
  });
}

function buildDoctorSubjectGroups(rows, sharedPoolMap) {
  const groups = new Map();

  rows.forEach((item) => {
    if (!groups.has(item.subject_id)) {
      groups.set(item.subject_id, {
        key: `doctor-${item.subject_id}`,
        subject_id: item.subject_id,
        subject_name: item.subject_name,
        subject_code: item.subject_code,
        allocations: [],
      });
    }
    groups.get(item.subject_id).allocations.push(item);
  });

  return Array.from(groups.values()).map((group) => {
    const sharedPools = sharedPoolMap.get(group.subject_id) || [];
    return {
      ...group,
      professor_count: group.allocations.length,
      total_quota: sumBy(group.allocations, 'total_quota'),
      used_quota: sumBy(group.allocations, 'used_quota'),
      remaining_quota: sumBy(group.allocations, 'remaining_quota'),
      shared_pools: sharedPools,
      shared_pool_count: sharedPools.length,
    };
  });
}

function SharedPoolTable({ pools }) {
  if (!pools?.length) {
    return <Typography.Text type="secondary">当前专业未被共享名额池覆盖。</Typography.Text>;
  }

  return (
    <Table
      rowKey="id"
      size="small"
      pagination={false}
      dataSource={pools}
      columns={[
        { title: '共享池名称', dataIndex: 'pool_name', key: 'pool_name' },
        { title: '导师', dataIndex: 'professor_name', key: 'professor_name' },
        { title: '工号', dataIndex: 'teacher_identity_id', key: 'teacher_identity_id' },
        { title: '类型', dataIndex: 'quota_scope_display', key: 'quota_scope_display' },
        { title: '校区', dataIndex: 'campus_display', key: 'campus_display' },
        {
          title: '剩余 / 总名额',
          key: 'quota',
          render: (_, record) => `${record.remaining_quota}/${record.total_quota}`,
        },
      ]}
    />
  );
}

export default function EnrollmentPage() {
  const [departmentRows, setDepartmentRows] = useState([]);
  const [departmentSelectedRowKeys, setDepartmentSelectedRowKeys] = useState([]);
  const [subjectSelectedRowKeys, setSubjectSelectedRowKeys] = useState([]);
  const [subjectData, setSubjectData] = useState({ count: 0, results: [], page: 1, page_size: 10 });
  const [masterQuotaRows, setMasterQuotaRows] = useState([]);
  const [doctorQuotaRows, setDoctorQuotaRows] = useState([]);
  const [sharedPoolRows, setSharedPoolRows] = useState([]);
  const [departmentLoading, setDepartmentLoading] = useState(false);
  const [subjectLoading, setSubjectLoading] = useState(false);
  const [quotaLoading, setQuotaLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [subjectFilters, setSubjectFilters] = useState({ subject_type: undefined, department_id: undefined });
  const [subjectSorter, setSubjectSorter] = useState({ order_by: 'subject_code', order_direction: 'asc' });
  const [departmentSorter, setDepartmentSorter] = useState({ order_by: 'department_name', order_direction: 'asc' });
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });
  const [editingDepartment, setEditingDepartment] = useState(null);
  const [editingSubject, setEditingSubject] = useState(null);
  const [departmentCreateOpen, setDepartmentCreateOpen] = useState(false);
  const [subjectCreateOpen, setSubjectCreateOpen] = useState(false);
  const [departmentForm] = Form.useForm();
  const [subjectForm] = Form.useForm();
  const [departmentCreateForm] = Form.useForm();
  const [subjectCreateForm] = Form.useForm();

  const masterSharedPoolMap = useMemo(() => buildSharedPoolMap(sharedPoolRows, 'master'), [sharedPoolRows]);
  const doctorSharedPoolMap = useMemo(() => buildSharedPoolMap(sharedPoolRows, 'doctor'), [sharedPoolRows]);
  const masterSubjectGroups = useMemo(() => buildMasterSubjectGroups(masterQuotaRows, masterSharedPoolMap), [masterQuotaRows, masterSharedPoolMap]);
  const doctorSubjectGroups = useMemo(() => buildDoctorSubjectGroups(doctorQuotaRows, doctorSharedPoolMap), [doctorQuotaRows, doctorSharedPoolMap]);

  const fetchDepartments = async (nextSorter = departmentSorter) => {
    setDepartmentLoading(true);
    try {
      const params = new URLSearchParams({
        order_by: nextSorter.order_by,
        order_direction: nextSorter.order_direction,
      });
      const payload = await get(`/departments/?${params.toString()}`);
      setDepartmentRows(Array.isArray(payload) ? payload : []);
    } catch (err) {
      message.error(err.message);
    } finally {
      setDepartmentLoading(false);
    }
  };

  const fetchQuotaAssignments = async (search = keyword, filters = subjectFilters) => {
    setQuotaLoading(true);
    try {
      const allSubjectsParams = buildSubjectQuery(1, 500, search, filters, {
        order_by: 'subject_code',
        order_direction: 'asc',
      });

      const [allSubjectsPayload, masterPayload, doctorPayload, sharedPayload] = await Promise.all([
        get(`/subjects/?${allSubjectsParams.toString()}`),
        get('/master-quotas/?page=1&page_size=500'),
        get('/doctor-quotas/?page=1&page_size=500'),
        get('/shared-quota-pools/?page=1&page_size=500'),
      ]);

      const subjectIds = new Set((allSubjectsPayload.results || []).map((item) => item.id));
      setMasterQuotaRows((masterPayload.results || []).filter((item) => subjectIds.has(item.subject_id)));
      setDoctorQuotaRows((doctorPayload.results || []).filter((item) => subjectIds.has(item.subject_id)));
      setSharedPoolRows((sharedPayload.results || []).filter((item) => (item.subject_ids || []).some((subjectId) => subjectIds.has(subjectId))));
    } catch (err) {
      message.error(err.message);
    } finally {
      setQuotaLoading(false);
    }
  };

  const fetchSubjects = async (page = pagination.current, pageSize = pagination.pageSize, search = keyword, filters = subjectFilters, sorter = subjectSorter) => {
    setSubjectLoading(true);
    try {
      const params = buildSubjectQuery(page, pageSize, search, filters, sorter);
      const payload = await get(`/subjects/?${params.toString()}`);
      setSubjectData(payload);
      setPagination({ current: payload.page, pageSize: payload.page_size });
      await fetchQuotaAssignments(search, filters);
    } catch (err) {
      message.error(err.message);
    } finally {
      setSubjectLoading(false);
    }
  };

  useEffect(() => {
    fetchDepartments();
    fetchSubjects(1, 10, '', subjectFilters, subjectSorter);
  }, []);

  const saveDepartment = async (values, isCreate = false) => {
    setSaving(true);
    try {
      const payload = isCreate ? await post('/departments/', values) : await patch(`/departments/${editingDepartment.id}/quota/`, values);
      message.success(payload.detail || '保存成功');
      setEditingDepartment(null);
      setDepartmentCreateOpen(false);
      departmentForm.resetFields();
      departmentCreateForm.resetFields();
      await fetchDepartments();
    } catch (err) {
      message.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  const saveSubject = async (values, isCreate = false) => {
    setSaving(true);
    try {
      const payload = isCreate ? await post('/subjects/', values) : await patch(`/subjects/${editingSubject.id}/quota/`, values);
      const detail = payload.detail ? `${payload.detail}${payload.alternate_updates !== undefined ? `，候补同步 ${payload.alternate_updates} 人` : ''}` : '保存成功';
      message.success(detail);
      setEditingSubject(null);
      setSubjectCreateOpen(false);
      subjectForm.resetFields();
      subjectCreateForm.resetFields();
      await fetchSubjects();
    } catch (err) {
      message.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  const deleteDepartments = async (ids, deleteAllFiltered = false) => {
    await post('/departments/actions/batch-delete/', { ids, delete_all_filtered: deleteAllFiltered });
    message.success('删除成功');
    setDepartmentSelectedRowKeys([]);
    await fetchDepartments();
  };

  const deleteSubjects = async (ids, deleteAllFiltered = false) => {
    const params = new URLSearchParams();
    if (keyword.trim()) params.set('search', keyword.trim());
    Object.entries(subjectFilters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') params.set(key, String(value));
    });
    await post(`/subjects/actions/batch-delete/?${params.toString()}`, { ids, delete_all_filtered: deleteAllFiltered });
    message.success('删除成功');
    setSubjectSelectedRowKeys([]);
    await fetchSubjects(1, pagination.pageSize, keyword, subjectFilters, subjectSorter);
  };

  const updateSubjectFilter = (key, value) => {
    const nextFilters = { ...subjectFilters, [key]: value };
    setSubjectFilters(nextFilters);
    fetchSubjects(1, pagination.pageSize, keyword, nextFilters, subjectSorter);
  };

  const departmentColumns = [
    { title: '方向', dataIndex: 'department_name', key: 'department_name', sorter: true },
    { title: '专业数量', dataIndex: 'subject_count', key: 'subject_count', sorter: true },
    { title: '审核人', dataIndex: 'reviewer_names', key: 'reviewer_names', render: (value) => (Array.isArray(value) && value.length ? value.join('、') : '-') },
    { title: '学硕总名额', dataIndex: 'total_academic_quota', key: 'total_academic_quota', sorter: true },
    { title: '专硕北京', dataIndex: 'total_professional_quota', key: 'total_professional_quota', sorter: true },
    { title: '专硕烟台', dataIndex: 'total_professional_yt_quota', key: 'total_professional_yt_quota', sorter: true },
    { title: '博士总名额', dataIndex: 'total_doctor_quota', key: 'total_doctor_quota', sorter: true },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            onClick={() => {
              setEditingDepartment(record);
              departmentForm.setFieldsValue({
                department_name: record.department_name,
                total_academic_quota: record.total_academic_quota,
                total_professional_quota: record.total_professional_quota,
                total_professional_yt_quota: record.total_professional_yt_quota,
                total_doctor_quota: record.total_doctor_quota,
              });
            }}
          >
            编辑
          </Button>
          <Button
            size="small"
            danger
            onClick={() =>
              confirmDanger({
                title: '确认删除这个方向吗？',
                content: record.department_name,
                onOk: () => deleteDepartments([record.id]),
              })
            }
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const subjectColumns = [
    { title: '专业代码', dataIndex: 'subject_code', key: 'subject_code', sorter: true },
    { title: '专业名称', dataIndex: 'subject_name', key: 'subject_name', sorter: true },
    { title: '专业类型', dataIndex: 'subject_type_display', key: 'subject_type', sorter: true },
    { title: '总招生名额', dataIndex: 'total_admission_quota', key: 'total_admission_quota', sorter: true },
    { title: '已分配导师名额', dataIndex: 'assigned_quota_total', key: 'assigned_quota_total' },
    { title: '共享池覆盖', dataIndex: 'shared_quota_pool_count', key: 'shared_quota_pool_count', render: (value) => (value ? `${value} 个共享池` : '-') },
    { title: '学生总数', dataIndex: 'student_count', key: 'student_count', sorter: true },
    { title: '已录取', dataIndex: 'selected_student_count', key: 'selected_student_count', sorter: true },
    { title: '候补', dataIndex: 'alternate_student_count', key: 'alternate_student_count', sorter: true },
    { title: '放弃', dataIndex: 'giveup_student_count', key: 'giveup_student_count', sorter: true },
    { title: '所属方向', dataIndex: 'departments', key: 'departments', render: (value) => (value?.length ? value.map((item) => item.department_name).join('、') : '-') },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            onClick={() => {
              setEditingSubject(record);
              subjectForm.setFieldsValue({
                subject_name: record.subject_name,
                subject_code: record.subject_code,
                subject_type: record.subject_type,
                total_admission_quota: record.total_admission_quota,
                department_ids: record.departments?.map((item) => item.id) || [],
              });
            }}
          >
            编辑
          </Button>
          <Button
            size="small"
            danger
            onClick={() =>
              confirmDanger({
                title: '确认删除这个专业吗？',
                content: `${record.subject_name}（${record.subject_code}）`,
                onOk: () => deleteSubjects([record.id]),
              })
            }
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const masterSummaryColumns = [
    { title: '专业', key: 'subject', render: (_, record) => `${record.subject_name}（${record.subject_type_display} / ${record.subject_code}）` },
    { title: '分配导师数', dataIndex: 'professor_count', key: 'professor_count' },
    { title: '北京总名额', dataIndex: 'beijing_total', key: 'beijing_total' },
    { title: '北京已用', dataIndex: 'beijing_used', key: 'beijing_used' },
    { title: '北京剩余', dataIndex: 'beijing_remaining', key: 'beijing_remaining' },
    { title: '烟台总名额', dataIndex: 'yantai_total', key: 'yantai_total' },
    { title: '烟台已用', dataIndex: 'yantai_used', key: 'yantai_used' },
    { title: '烟台剩余', dataIndex: 'yantai_remaining', key: 'yantai_remaining' },
    { title: '共享池数量', dataIndex: 'shared_pool_count', key: 'shared_pool_count' },
  ];

  const masterDetailColumns = [
    { title: '导师', dataIndex: 'professor_name', key: 'professor_name' },
    { title: '工号', dataIndex: 'teacher_identity_id', key: 'teacher_identity_id' },
    { title: '北京总名额', dataIndex: 'beijing_quota', key: 'beijing_quota' },
    { title: '北京已用', key: 'beijing_used_quota', render: (_, record) => Math.max(0, (record.beijing_quota || 0) - (record.beijing_remaining_quota || 0)) },
    { title: '北京剩余', dataIndex: 'beijing_remaining_quota', key: 'beijing_remaining_quota' },
    { title: '烟台总名额', dataIndex: 'yantai_quota', key: 'yantai_quota' },
    { title: '烟台已用', key: 'yantai_used_quota', render: (_, record) => Math.max(0, (record.yantai_quota || 0) - (record.yantai_remaining_quota || 0)) },
    { title: '烟台剩余', dataIndex: 'yantai_remaining_quota', key: 'yantai_remaining_quota' },
    { title: '总名额', dataIndex: 'total_quota', key: 'total_quota' },
    { title: '名额来源', key: 'quota_source', render: () => '固定专业名额' },
  ];

  const doctorSummaryColumns = [
    { title: '专业', key: 'subject', render: (_, record) => `${record.subject_name}（博士 / ${record.subject_code}）` },
    { title: '分配导师数', dataIndex: 'professor_count', key: 'professor_count' },
    { title: '总名额', dataIndex: 'total_quota', key: 'total_quota' },
    { title: '已用', dataIndex: 'used_quota', key: 'used_quota' },
    { title: '剩余', dataIndex: 'remaining_quota', key: 'remaining_quota' },
    { title: '共享池数量', dataIndex: 'shared_pool_count', key: 'shared_pool_count' },
  ];

  const doctorDetailColumns = [
    { title: '导师', dataIndex: 'professor_name', key: 'professor_name' },
    { title: '工号', dataIndex: 'teacher_identity_id', key: 'teacher_identity_id' },
    { title: '总名额', dataIndex: 'total_quota', key: 'total_quota' },
    { title: '已用', dataIndex: 'used_quota', key: 'used_quota' },
    { title: '剩余', dataIndex: 'remaining_quota', key: 'remaining_quota' },
    { title: '名额来源', key: 'quota_source', render: () => '固定专业名额' },
  ];

  return (
    <>
      <Card className="page-card" bordered={false}>
        <PageHeader
          items={[{ title: '名额与配置' }, { title: '专业 / 方向' }]}
          title="专业 / 方向"
          subtitle="维护方向、专业和招生总名额，并查看固定专业名额与共享名额池在各专业上的覆盖关系。"
        />

        <Tabs
          items={[
            {
              key: 'departments',
              label: '方向概览',
              children: (
                <>
                  <div className="page-toolbar">
                    <div className="page-filters" />
                    <div className="page-actions">
                      <Button type="primary" icon={<PlusOutlined />} onClick={() => setDepartmentCreateOpen(true)}>新建方向</Button>
                      <Button onClick={() => fetchDepartments()}>刷新</Button>
                      <Button danger disabled={!departmentSelectedRowKeys.length} onClick={() => confirmDanger({ title: '确认删除选中的方向吗？', content: `共 ${departmentSelectedRowKeys.length} 条记录。`, onOk: () => deleteDepartments(departmentSelectedRowKeys) })}>删除选中</Button>
                      <Button danger onClick={() => confirmDanger({ title: '确认删除当前方向列表中的全部记录吗？', content: '这个操作会删除当前方向列表中的所有记录。', onOk: () => deleteDepartments([], true) })}>删除当前列表</Button>
                    </div>
                  </div>

                  <Table
                    rowKey="id"
                    loading={departmentLoading}
                    rowSelection={{ selectedRowKeys: departmentSelectedRowKeys, onChange: setDepartmentSelectedRowKeys }}
                    columns={departmentColumns}
                    dataSource={departmentRows}
                    pagination={false}
                    onChange={(_pager, _filters, tableSorter) => {
                      const nextSorter = tableSorter?.field ? { order_by: tableSorter.field, order_direction: tableSorter.order === 'descend' ? 'desc' : 'asc' } : departmentSorter;
                      setDepartmentSorter(nextSorter);
                      fetchDepartments(nextSorter);
                    }}
                  />
                </>
              ),
            },
            {
              key: 'subjects',
              label: '专业概览',
              children: (
                <>
                  <div className="page-toolbar">
                    <div className="page-filters">
                      <Input.Search placeholder="按专业名称或代码搜索" value={keyword} onChange={(e) => setKeyword(e.target.value)} onSearch={(value) => fetchSubjects(1, pagination.pageSize, value, subjectFilters, subjectSorter)} allowClear style={{ width: 320 }} />
                      <Select allowClear placeholder="按专业类型筛选" style={{ width: 180 }} value={subjectFilters.subject_type} options={subjectTypeOptions} onChange={(value) => updateSubjectFilter('subject_type', value)} />
                      <Select allowClear placeholder="按方向筛选" style={{ width: 200 }} value={subjectFilters.department_id} options={departmentRows.map((item) => ({ label: item.department_name, value: item.id }))} onChange={(value) => updateSubjectFilter('department_id', value)} />
                    </div>
                    <div className="page-actions">
                      <Button type="primary" icon={<PlusOutlined />} onClick={() => setSubjectCreateOpen(true)}>新建专业</Button>
                      <Button onClick={() => fetchSubjects(1, pagination.pageSize, keyword, subjectFilters, subjectSorter)}>刷新</Button>
                      <Button danger disabled={!subjectSelectedRowKeys.length} onClick={() => confirmDanger({ title: '确认删除选中的专业吗？', content: `共 ${subjectSelectedRowKeys.length} 条记录。`, onOk: () => deleteSubjects(subjectSelectedRowKeys) })}>删除选中</Button>
                      <Button danger onClick={() => confirmDanger({ title: '确认删除当前筛选结果中的全部专业吗？', content: '这个操作会删除当前筛选条件下的全部专业。', onOk: () => deleteSubjects([], true) })}>删除当前筛选结果</Button>
                    </div>
                  </div>

                  <Table
                    rowKey="id"
                    loading={subjectLoading}
                    rowSelection={{ selectedRowKeys: subjectSelectedRowKeys, onChange: setSubjectSelectedRowKeys }}
                    columns={subjectColumns}
                    dataSource={subjectData.results}
                    pagination={{ current: pagination.current, pageSize: pagination.pageSize, total: subjectData.count, showSizeChanger: true }}
                    onChange={(pager, _filters, tableSorter) => {
                      const nextSorter = tableSorter?.field ? { order_by: tableSorter.field, order_direction: tableSorter.order === 'descend' ? 'desc' : 'asc' } : subjectSorter;
                      setSubjectSorter(nextSorter);
                      fetchSubjects(pager.current, pager.pageSize, keyword, subjectFilters, nextSorter);
                    }}
                  />

                  <div style={{ marginTop: 24 }}>
                    <Card title="硕士专业导师名额分配" bordered={false} bodyStyle={{ padding: 0 }} extra={<span style={{ color: '#6b7280' }}>展开后可同时查看固定专业名额和共享名额池覆盖情况</span>}>
                      <Table
                        rowKey="key"
                        loading={quotaLoading}
                        columns={masterSummaryColumns}
                        dataSource={masterSubjectGroups}
                        pagination={{ pageSize: 8, showSizeChanger: true }}
                        expandable={{
                          rowExpandable: (record) => record.allocations.length > 0 || record.shared_pools.length > 0,
                          expandedRowRender: (record) => (
                            <Space direction="vertical" size={16} style={{ width: '100%' }}>
                              <Table rowKey="id" columns={masterDetailColumns} dataSource={record.allocations} pagination={false} size="small" />
                              <Card size="small" title="共享名额池覆盖关系">
                                <SharedPoolTable pools={record.shared_pools} />
                              </Card>
                            </Space>
                          ),
                        }}
                      />
                    </Card>
                  </div>

                  <div style={{ marginTop: 24 }}>
                    <Card title="博士专业导师名额分配" bordered={false} bodyStyle={{ padding: 0 }} extra={<span style={{ color: '#6b7280' }}>展开后可同时查看固定专业名额和共享名额池覆盖情况</span>}>
                      <Table
                        rowKey="key"
                        loading={quotaLoading}
                        columns={doctorSummaryColumns}
                        dataSource={doctorSubjectGroups}
                        pagination={{ pageSize: 8, showSizeChanger: true }}
                        expandable={{
                          rowExpandable: (record) => record.allocations.length > 0 || record.shared_pools.length > 0,
                          expandedRowRender: (record) => (
                            <Space direction="vertical" size={16} style={{ width: '100%' }}>
                              <Table rowKey="id" columns={doctorDetailColumns} dataSource={record.allocations} pagination={false} size="small" />
                              <Card size="small" title="共享名额池覆盖关系">
                                <SharedPoolTable pools={record.shared_pools} />
                              </Card>
                            </Space>
                          ),
                        }}
                      />
                    </Card>
                  </div>
                </>
              ),
            },
          ]}
        />
      </Card>

      <Modal title="新建方向" open={departmentCreateOpen} onCancel={() => setDepartmentCreateOpen(false)} onOk={() => departmentCreateForm.submit()} confirmLoading={saving} destroyOnClose>
        <Form form={departmentCreateForm} layout="vertical" onFinish={(values) => saveDepartment(values, true)}>
          <Form.Item name="department_name" label="方向名称" rules={[{ required: true, message: '请输入方向名称' }]}><Input /></Form.Item>
          <Form.Item name="total_academic_quota" label="学硕总名额" initialValue={0}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="total_professional_quota" label="专硕北京名额" initialValue={0}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="total_professional_yt_quota" label="专硕烟台名额" initialValue={0}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="total_doctor_quota" label="博士总名额" initialValue={0}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
        </Form>
      </Modal>

      <Modal title="编辑方向" open={!!editingDepartment} onCancel={() => { setEditingDepartment(null); departmentForm.resetFields(); }} onOk={() => departmentForm.submit()} confirmLoading={saving} destroyOnClose>
        <Form form={departmentForm} layout="vertical" onFinish={(values) => saveDepartment(values, false)}>
          <Form.Item name="department_name" label="方向名称" rules={[{ required: true, message: '请输入方向名称' }]}><Input /></Form.Item>
          <Form.Item name="total_academic_quota" label="学硕总名额"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="total_professional_quota" label="专硕北京名额"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="total_professional_yt_quota" label="专硕烟台名额"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="total_doctor_quota" label="博士总名额"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
        </Form>
      </Modal>

      <Modal title="新建专业" open={subjectCreateOpen} onCancel={() => setSubjectCreateOpen(false)} onOk={() => subjectCreateForm.submit()} confirmLoading={saving} destroyOnClose>
        <Form form={subjectCreateForm} layout="vertical" onFinish={(values) => saveSubject(values, true)}>
          <Form.Item name="subject_name" label="专业名称" rules={[{ required: true, message: '请输入专业名称' }]}><Input /></Form.Item>
          <Form.Item name="subject_code" label="专业代码" rules={[{ required: true, message: '请输入专业代码' }]}><Input /></Form.Item>
          <Form.Item name="subject_type" label="专业类型" rules={[{ required: true, message: '请选择专业类型' }]}><Select options={subjectTypeOptions} /></Form.Item>
          <Form.Item name="total_admission_quota" label="总招生名额" initialValue={0}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="department_ids" label="所属方向" rules={[{ required: true, message: '请选择所属方向' }]}><Select mode="multiple" options={departmentRows.map((item) => ({ label: item.department_name, value: item.id }))} /></Form.Item>
        </Form>
      </Modal>

      <Modal title="编辑专业" open={!!editingSubject} onCancel={() => { setEditingSubject(null); subjectForm.resetFields(); }} onOk={() => subjectForm.submit()} confirmLoading={saving} destroyOnClose>
        <Form form={subjectForm} layout="vertical" onFinish={(values) => saveSubject(values, false)}>
          <Form.Item name="subject_name" label="专业名称" rules={[{ required: true, message: '请输入专业名称' }]}><Input /></Form.Item>
          <Form.Item name="subject_code" label="专业代码" rules={[{ required: true, message: '请输入专业代码' }]}><Input /></Form.Item>
          <Form.Item name="subject_type" label="专业类型" rules={[{ required: true, message: '请选择专业类型' }]}><Select options={subjectTypeOptions} /></Form.Item>
          <Form.Item name="total_admission_quota" label="总招生名额"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="department_ids" label="所属方向" rules={[{ required: true, message: '请选择所属方向' }]}><Select mode="multiple" options={departmentRows.map((item) => ({ label: item.department_name, value: item.id }))} /></Form.Item>
        </Form>
      </Modal>
    </>
  );
}
