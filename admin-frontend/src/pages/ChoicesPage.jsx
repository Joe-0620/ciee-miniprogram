import React, { useEffect, useState } from 'react';
import { Button, Card, Form, Input, Modal, Select, Space, Table, message } from 'antd';

import { download, get, post } from '../api/client';
import PageHeader from '../components/PageHeader';
import StatusTag from '../components/StatusTag';
import { confirmDanger } from '../utils/confirm';


function formatSubjectOption(item) {
  const parts = [item.subject_type_display].filter(Boolean);
  if (item.subject_code) parts.push(item.subject_code);
  return `${item.subject_name}（${parts.join(' / ')}）`;
}

const statusMap = {
  1: { tone: 'success', text: '已同意' },
  2: { tone: 'error', text: '已拒绝' },
  3: { tone: 'processing', text: '待处理' },
  4: { tone: 'default', text: '已取消' },
  5: { tone: 'default', text: '已撤销' },
};

const studentTypeOptions = [
  { label: '硕士推免生', value: 1 },
  { label: '硕士统考生', value: 2 },
  { label: '博士统考生', value: 3 },
];

const postgraduateTypeOptions = [
  { label: '专业型（北京）', value: 1 },
  { label: '学术型', value: 2 },
  { label: '博士', value: 3 },
  { label: '专业型（烟台）', value: 4 },
];

function buildChoiceExportFilename(values) {
  const statusLabel = values.status ? statusMap[values.status]?.text || `状态${values.status}` : '全部状态';
  const yearLabel = values.admission_year ? `${values.admission_year}届` : '全部届别';
  const studentTypeLabel = values.student_type
    ? studentTypeOptions.find((item) => item.value === values.student_type)?.label || `学生类型${values.student_type}`
    : '全部学生类型';
  const postgraduateLabels = Array.isArray(values.postgraduate_type) && values.postgraduate_type.length
    ? values.postgraduate_type
        .map((value) => postgraduateTypeOptions.find((item) => item.value === value)?.label || `研究生类型${value}`)
        .join('、')
    : '全部研究生类型';
  return `双选记录_${statusLabel}_${yearLabel}_${studentTypeLabel}_${postgraduateLabels}.xlsx`;
}

export default function ChoicesPage() {
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [filters, setFilters] = useState({ status: undefined, subject_id: undefined, department_id: undefined, admission_year: undefined });
  const [sorter, setSorter] = useState({ order_by: 'submit_date', order_direction: 'desc' });
  const [subjects, setSubjects] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [admissionYears, setAdmissionYears] = useState([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [data, setData] = useState({ count: 0, results: [] });
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });
  const [exportOpen, setExportOpen] = useState(false);
  const [exportSubmitting, setExportSubmitting] = useState(false);
  const [exportForm] = Form.useForm();

  const loadOptions = async () => {
    try {
      const [subjectPayload, departmentPayload] = await Promise.all([get('/subjects/'), get('/departments/')]);
      setSubjects(subjectPayload.results || subjectPayload || []);
      setDepartments(departmentPayload || []);
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
      const payload = await get(`/choices/?${params.toString()}`);
      setData(payload);
      setAdmissionYears(payload.available_admission_years || []);
      setPagination({ current: payload.page, pageSize: payload.page_size });
    } catch (err) {
      message.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOptions();
    fetchData(1, 10);
  }, []);

  const runAction = async (handler) => {
    setActionLoading(true);
    try {
      const payload = await handler();
      if (payload?.detail) message.success(payload.detail);
      setSelectedRowKeys([]);
      await fetchData();
    } catch (err) {
      message.error(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const deleteChoices = (ids, deleteAllFiltered = false) => {
    const params = new URLSearchParams();
    if (keyword.trim()) params.set('search', keyword.trim());
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') params.set(key, String(value));
    });
    return runAction(() => post(`/choices/actions/batch-delete/?${params.toString()}`, { ids, delete_all_filtered: deleteAllFiltered }));
  };

  const updateFilter = (key, value) => {
    const next = { ...filters, [key]: value };
    setFilters(next);
    fetchData(1, pagination.pageSize, keyword, next, sorter);
  };

  const columns = [
    { title: '学生', dataIndex: 'student_name', key: 'student_name', sorter: true },
    { title: '考生编号', dataIndex: 'candidate_number', key: 'candidate_number', sorter: true },
    { title: '届别', dataIndex: 'admission_year', key: 'admission_year', sorter: true, render: (value) => (value ? `${value}届` : '-') },
    { title: '导师', dataIndex: 'professor_name', key: 'professor_name', sorter: true },
    { title: '导师工号', dataIndex: 'professor_teacher_identity_id', key: 'professor_teacher_identity_id', sorter: true },
    { title: '方向', dataIndex: 'department_name', key: 'department_name', sorter: true },
    { title: '专业', dataIndex: 'subject_name', key: 'subject_name', sorter: true },
    { title: '研究生类型', dataIndex: 'postgraduate_type_display', key: 'postgraduate_type_display', render: (value) => value || '-' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      sorter: true,
      render: (value) => {
        const config = statusMap[value] || { tone: 'default', text: '未知' };
        return <StatusTag tone={config.tone}>{config.text}</StatusTag>;
      },
    },
    {
      title: '提交时间',
      dataIndex: 'submit_date',
      key: 'submit_date',
      sorter: true,
      render: (value) => (value ? new Date(value).toLocaleString() : '-'),
    },
    {
      title: '处理时间',
      dataIndex: 'finish_time',
      key: 'finish_time',
      sorter: true,
      render: (value) => (value ? new Date(value).toLocaleString() : '-'),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Button
          size="small"
          danger
          onClick={() =>
            confirmDanger({
              title: '确认删除这条双选记录吗？',
              content: `${record.student_name} - ${record.professor_name}`,
              onOk: () => deleteChoices([record.id]),
            })
          }
        >
          删除
        </Button>
      ),
    },
  ];

  const exportPostgraduateTypeOptions = Form.useWatch('student_type', exportForm) === 3
    ? postgraduateTypeOptions.filter((item) => item.value === 3)
    : postgraduateTypeOptions.filter((item) => item.value !== 3);

  const handleExport = async () => {
    try {
      const values = await exportForm.validateFields();
      const params = new URLSearchParams();
      if (values.status !== undefined && values.status !== null && values.status !== '') {
        params.set('status', String(values.status));
      }
      if (values.admission_year !== undefined && values.admission_year !== null && values.admission_year !== '') {
        params.set('admission_year', String(values.admission_year));
      }
      if (values.student_type !== undefined && values.student_type !== null && values.student_type !== '') {
        params.set('student_type', String(values.student_type));
      }
      if (Array.isArray(values.postgraduate_type)) {
        values.postgraduate_type.forEach((value) => {
          if (value !== undefined && value !== null && value !== '') {
            params.append('postgraduate_type', String(value));
          }
        });
      }
      setExportSubmitting(true);
      await download(
        `/choices/export-selected/${params.toString() ? `?${params.toString()}` : ''}`,
        buildChoiceExportFilename(values),
      );
      message.success('导出成功');
      setExportOpen(false);
      exportForm.resetFields();
    } catch (err) {
      if (!err?.errorFields) {
        message.error(err.message);
      }
    } finally {
      setExportSubmitting(false);
    }
  };

  return (
    <>
      <Card className="page-card" bordered={false}>
        <PageHeader
          items={[{ title: '招生业务' }, { title: '双选记录' }]}
          title="双选记录"
          subtitle="统一查看学生申请、导师处理和最终状态，适合做整体追踪与异常排查。"
        />

      <div className="page-toolbar">
        <div className="page-filters">
          <Input.Search
            placeholder="按学生、考生编号、导师或工号搜索"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onSearch={(value) => fetchData(1, pagination.pageSize, value)}
            allowClear
            style={{ width: 320 }}
          />
          <Select
            allowClear
            placeholder="按状态筛选"
            style={{ width: 160 }}
            value={filters.status}
            options={Object.entries(statusMap).map(([value, config]) => ({ label: config.text, value }))}
            onChange={(value) => updateFilter('status', value)}
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
            placeholder="按届别筛选"
            style={{ width: 150 }}
            value={filters.admission_year}
            options={admissionYears.map((year) => ({ label: `${year}届`, value: year }))}
            onChange={(value) => updateFilter('admission_year', value)}
          />
          <Select
            allowClear
            placeholder="按专业筛选"
            style={{ width: 180 }}
            value={filters.subject_id}
            options={subjects.map((item) => ({ label: formatSubjectOption(item), value: item.id }))}
            onChange={(value) => updateFilter('subject_id', value)}
          />
        </div>

        <div className="page-actions">
          <Button onClick={() => fetchData(1, pagination.pageSize, keyword, filters, sorter)}>刷新</Button>
          <Button onClick={() => setExportOpen(true)}>导出记录</Button>
          <Button
            danger
            disabled={!selectedRowKeys.length}
            onClick={() =>
              confirmDanger({
                title: '确认删除选中的双选记录吗？',
                content: `共 ${selectedRowKeys.length} 条记录。`,
                onOk: () => deleteChoices(selectedRowKeys),
              })
            }
          >
            删除选中
          </Button>
          <Button
            danger
            onClick={() =>
              confirmDanger({
                title: '确认删除当前筛选结果中的所有双选记录吗？',
                content: '这个操作会删除当前筛选条件下的全部双选记录。',
                onOk: () => deleteChoices([], true),
              })
            }
          >
            删除当前筛选结果
          </Button>
          <Button
            danger
            loading={actionLoading}
            disabled={!selectedRowKeys.length}
            onClick={() =>
              confirmDanger({
                title: '确认撤销选中的已同意双选记录吗？',
                content: `共 ${selectedRowKeys.length} 条记录，撤销后会回补对应名额。`,
                okText: '确认',
                onOk: () => runAction(() => post('/choices/actions/cancel-approved/', { ids: selectedRowKeys })),
              })
            }
          >
            撤销已同意
          </Button>
          <Button loading={actionLoading} onClick={() => runAction(() => post('/choices/actions/reject-waiting-no-quota/', {}))}>
            无名额自动拒绝
          </Button>
          <Button loading={actionLoading} onClick={() => runAction(() => post('/choices/actions/cancel-waiting-giveup/', {}))}>
            放弃后取消等待
          </Button>
        </div>
      </div>

        <Table
          rowKey="id"
          loading={loading}
          rowSelection={{ selectedRowKeys, onChange: setSelectedRowKeys }}
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
        open={exportOpen}
        title="导出记录"
        onCancel={() => {
          if (exportSubmitting) return;
          setExportOpen(false);
          exportForm.resetFields();
        }}
        onOk={handleExport}
        confirmLoading={exportSubmitting}
        okText="开始导出"
        destroyOnClose
      >
        <Form form={exportForm} layout="vertical">
          <Form.Item label="状态" name="status">
            <Select
              allowClear
              placeholder="选择要导出的状态"
              options={Object.entries(statusMap).map(([value, config]) => ({ label: config.text, value }))}
            />
          </Form.Item>
          <Form.Item label="届别" name="admission_year">
            <Select
              allowClear
              placeholder="选择要导出的届别"
              options={admissionYears.map((year) => ({ label: `${year}届`, value: year }))}
            />
          </Form.Item>
          <Form.Item label="学生类型" name="student_type">
            <Select
              allowClear
              placeholder="选择要导出的学生类型"
              options={studentTypeOptions}
              onChange={() => {
                exportForm.setFieldValue('postgraduate_type', undefined);
              }}
            />
          </Form.Item>
          <Form.Item label="研究生类型" name="postgraduate_type">
            <Select
              mode="multiple"
              allowClear
              placeholder="选择要导出的研究生类型"
              options={exportPostgraduateTypeOptions}
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
