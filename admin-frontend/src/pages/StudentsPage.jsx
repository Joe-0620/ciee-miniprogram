import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Modal,
  Progress,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Upload,
  message,
} from 'antd';
import {
  EditOutlined,
  LockOutlined,
  PlusOutlined,
  PoweroffOutlined,
  UnlockOutlined,
  UploadOutlined,
} from '@ant-design/icons';

import { get, patch, post, postDownload, upload, uploadWithProgress } from '../api/client';
import PageHeader from '../components/PageHeader';
import PdfPreviewModal from '../components/PdfPreviewModal';
import StatusTag from '../components/StatusTag';
import { confirmDanger } from '../utils/confirm';

function formatSubjectLabel(subject) {
  if (!subject) return '-';
  return subject.subject_name || '-';
}

function getStudentStatus(record) {
  if (record.is_giveup) return { tone: 'error', text: '已放弃' };
  if (record.is_selected) return { tone: 'success', text: '已录取' };
  if (record.is_alternate) return { tone: 'warning', text: '候补中' };
  if (record.current_choice_status === 'pending') return { tone: 'processing', text: '待处理' };
  return { tone: 'default', text: '未完成' };
}

const reviewStatusMap = {
  1: { tone: 'success', text: '已通过' },
  2: { tone: 'error', text: '已驳回' },
  3: { tone: 'processing', text: '待审核' },
  4: { tone: 'default', text: '未提交' },
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

const reviewStatusOptions = [
  { label: '已通过', value: 1 },
  { label: '已驳回', value: 2 },
  { label: '待审核', value: 3 },
  { label: '未提交', value: 4 },
];

const importTypeOptions = [
  { label: '硕士推免生', value: 'master_recommend' },
  { label: '硕士统考生', value: 'master_exam' },
  { label: '博士统考生', value: 'doctor' },
];

function buildBooleanOptions(trueLabel, falseLabel) {
  return [
    { label: trueLabel, value: 'true' },
    { label: falseLabel, value: 'false' },
  ];
}

function getDefaultAdmissionYear() {
  const now = new Date();
  return now.getMonth() >= 8 ? now.getFullYear() + 1 : now.getFullYear();
}

function normalizeUploadEvent(event) {
  if (Array.isArray(event)) return event;
  return event?.fileList || [];
}

export default function StudentsPage() {
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [data, setData] = useState({ count: 0, page: 1, page_size: 10, results: [] });
  const [subjects, setSubjects] = useState([]);
  const [batches, setBatches] = useState([]);
  const [keyword, setKeyword] = useState('');
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [filters, setFilters] = useState({
    subject_id: undefined,
    admission_year: undefined,
    admission_batch_id: undefined,
    can_login: undefined,
    selection_display_enabled: undefined,
    student_type: undefined,
    postgraduate_type: undefined,
    is_selected: undefined,
    is_alternate: undefined,
    is_giveup: undefined,
    review_status: undefined,
  });
  const [sorter, setSorter] = useState({ order_by: 'final_rank', order_direction: 'asc' });
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });
  const [editOpen, setEditOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [importSubmitting, setImportSubmitting] = useState(false);
  const [importProgress, setImportProgress] = useState(0);
  const [importResult, setImportResult] = useState(null);
  const [editingRecord, setEditingRecord] = useState(null);
  const [previewState, setPreviewState] = useState({ open: false, title: '', fileId: '' });
  const [editForm] = Form.useForm();
  const [importForm] = Form.useForm();

  const yearOptions = useMemo(() => {
    const currentYear = new Date().getFullYear();
    return Array.from({ length: 6 }, (_, index) => {
      const year = currentYear - 1 + index;
      return { label: `${year}届`, value: year };
    });
  }, []);

  async function loadBaseOptions() {
    try {
      const [subjectPayload, batchPayload] = await Promise.all([get('/subjects/'), get('/admission-batches/')]);
      setSubjects(Array.isArray(subjectPayload) ? subjectPayload : subjectPayload?.results || []);
      setBatches(Array.isArray(batchPayload) ? batchPayload : batchPayload?.results || []);
    } catch (error) {
      message.error(error.message);
    }
  }

  async function fetchData(
    page = pagination.current,
    pageSize = pagination.pageSize,
    nextKeyword = keyword,
    nextFilters = filters,
    nextSorter = sorter,
  ) {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
        order_by: nextSorter.order_by,
        order_direction: nextSorter.order_direction,
      });
      if (nextKeyword.trim()) {
        params.set('search', nextKeyword.trim());
      }
      Object.entries(nextFilters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.set(key, String(value));
        }
      });
      const payload = await get(`/students/?${params.toString()}`);
      setData(payload);
      setPagination({ current: payload.page, pageSize: payload.page_size });
    } catch (error) {
      message.error(error.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadBaseOptions();
    fetchData(1, 10);
  }, []);

  async function runAction(handler, successMessage) {
    setActionLoading(true);
    try {
      const payload = await handler();
      message.success(successMessage || payload?.detail || '操作成功');
      setSelectedRowKeys([]);
      await loadBaseOptions();
      await fetchData();
      return payload;
    } catch (error) {
      message.error(error.message);
      throw error;
    } finally {
      setActionLoading(false);
    }
  }

  function updateFilter(key, value) {
    const nextFilters = { ...filters, [key]: value };
    setFilters(nextFilters);
    fetchData(1, pagination.pageSize, keyword, nextFilters, sorter);
  }

  function resetFilters() {
    const nextFilters = {
      subject_id: undefined,
      admission_year: undefined,
      admission_batch_id: undefined,
      can_login: undefined,
      selection_display_enabled: undefined,
      student_type: undefined,
      postgraduate_type: undefined,
      is_selected: undefined,
      is_alternate: undefined,
      is_giveup: undefined,
      review_status: undefined,
    };
    const nextSorter = { order_by: 'final_rank', order_direction: 'asc' };
    setKeyword('');
    setFilters(nextFilters);
    setSorter(nextSorter);
    fetchData(1, pagination.pageSize, '', nextFilters, nextSorter);
  }

  function openCreateModal() {
    setEditingRecord(null);
    editForm.resetFields();
    editForm.setFieldsValue({
      student_type: 2,
      postgraduate_type: 1,
      study_mode: true,
      can_login: true,
      selection_display_enabled: true,
      admission_year: getDefaultAdmissionYear(),
      is_selected: false,
      is_alternate: false,
      is_giveup: false,
    });
    setEditOpen(true);
  }

  async function openEditModal(record) {
    try {
      const detail = await get(`/students/${record.id}/`);
      setEditingRecord(record);
      editForm.setFieldsValue({
        name: detail.name,
        candidate_number: detail.candidate_number,
        identify_number: detail.identify_number,
        subject_id: detail.subject?.id,
        admission_year: detail.admission_year,
        admission_batch_id: detail.admission_batch?.id,
        can_login: detail.can_login,
        selection_display_enabled: detail.selection_display_enabled,
        student_type: detail.student_type,
        postgraduate_type: detail.postgraduate_type,
        study_mode: detail.study_mode,
        phone_number: detail.phone_number,
        initial_exam_score: detail.initial_exam_score,
        secondary_exam_score: detail.secondary_exam_score,
        initial_rank: detail.initial_rank,
        secondary_rank: detail.secondary_rank,
        final_rank: detail.final_rank,
        is_selected: detail.is_selected,
        is_alternate: detail.is_alternate,
        alternate_rank: detail.alternate_rank,
        is_giveup: detail.is_giveup,
      });
      setEditOpen(true);
    } catch (error) {
      message.error(error.message);
    }
  }

  async function handleSaveStudent() {
    try {
      const values = await editForm.validateFields();
      await runAction(
        () => (editingRecord ? patch(`/students/${editingRecord.id}/`, values) : post('/students/', values)),
        editingRecord ? '学生信息已更新' : '学生已创建',
      );
      setEditOpen(false);
      editForm.resetFields();
    } catch (error) {
      if (!error?.errorFields) {
        message.error(error.message);
      }
    }
  }

  async function handleImport() {
    try {
      const values = await importForm.validateFields();
      const formData = new FormData();
      formData.append('import_type', values.import_type);
      formData.append('update_quota', values.update_quota ? 'true' : 'false');
      formData.append('file', values.fileList[0].originFileObj);
      setImportSubmitting(true);
      setImportProgress(0);
      setImportResult(null);
      const payload = await uploadWithProgress('/students/import/', formData, setImportProgress);
      setImportProgress(100);
      setImportResult(payload);
      message.success(payload?.detail || '学生导入完成');
      await fetchData(1, pagination.pageSize, keyword, filters, sorter);
      importForm.resetFields();
    } catch (error) {
      if (!error?.errorFields) {
        message.error(error.message);
      }
    } finally {
      setImportSubmitting(false);
    }
  }

  function buildDeleteQuery() {
    const params = new URLSearchParams();
    if (keyword.trim()) params.set('search', keyword.trim());
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.set(key, String(value));
      }
    });
    return params.toString();
  }

  async function deleteStudents(ids = [], deleteAllFiltered = false) {
    const query = buildDeleteQuery();
    await runAction(
      () => post(`/students/actions/batch-delete/${query ? `?${query}` : ''}`, { ids, delete_all_filtered: deleteAllFiltered }),
      '删除成功',
    );
  }

  async function toggleSelectedStudentsLogin(canLogin) {
    const actionText = canLogin ? '开启' : '关闭';
    const targetCount = selectedRowKeys.length;
    if (!targetCount) {
      message.warning('请先选择学生。');
      return;
    }

    const execute = () =>
      runAction(
        () => post('/students/actions/toggle-login/', { ids: selectedRowKeys, can_login: canLogin }),
        `已${actionText}选中学生的小程序登录权限`,
      );

    if (!canLogin) {
      confirmDanger({
        title: '确认关闭选中学生的小程序登录权限吗？',
        content: `关闭后，已登录的 ${targetCount} 名学生会在下次请求时自动退出登录。`,
        okText: '确认关闭',
        cancelText: '取消',
        onOk: execute,
      });
      return;
    }

    await execute();
  }

  async function toggleSelectedStudentsDisplay(selectionDisplayEnabled) {
    const actionText = selectionDisplayEnabled ? '开启' : '关闭';
    const targetCount = selectedRowKeys.length;
    if (!targetCount) {
      message.warning('请先选择学生。');
      return;
    }

    const execute = () =>
      runAction(
        () => post('/students/actions/toggle-selection-display/', { ids: selectedRowKeys, selection_display_enabled: selectionDisplayEnabled }),
        `已${actionText}选中学生的可选学生池展示`,
      );

    if (!selectionDisplayEnabled) {
      confirmDanger({
        title: '确认关闭选中学生的可选学生池展示吗？',
        content: `关闭后，这 ${targetCount} 名学生将不会出现在小程序导师端的可选学生列表中。`,
        okText: '确认关闭',
        cancelText: '取消',
        onOk: execute,
      });
      return;
    }

    await execute();
  }

  async function batchDownload(fileType, filename) {
    try {
      await postDownload('/students/actions/batch-download/', { ids: selectedRowKeys, file_type: fileType }, filename);
      message.success('下载成功');
    } catch (error) {
      message.error(error.message);
    }
  }

  function openPreview(title, fileId) {
    if (!fileId) {
      message.warning('该材料暂未上传。');
      return;
    }
    setPreviewState({ open: true, title, fileId });
  }

  const columns = [
    { title: '姓名', dataIndex: 'name', key: 'name', sorter: true },
    { title: '考生编号', dataIndex: 'candidate_number', key: 'candidate_number', sorter: true },
    {
      title: '专业',
      dataIndex: 'subject',
      key: 'subject_name',
      sorter: true,
      render: (subject) => formatSubjectLabel(subject),
    },
    {
      title: '届别',
      dataIndex: 'admission_year',
      key: 'admission_year',
      sorter: true,
      render: (value) => (value ? `${value}届` : '-'),
    },
    {
      title: '批次',
      dataIndex: 'admission_batch',
      key: 'admission_batch',
      sorter: true,
      render: (value) => (value ? `${value.admission_year}届 - ${value.name}` : '-'),
    },
    { title: '学生类型', dataIndex: 'student_type_display', key: 'student_type', sorter: true },
    { title: '培养类型', dataIndex: 'postgraduate_type_display', key: 'postgraduate_type', sorter: true },
    { title: '综合排名', dataIndex: 'final_rank', key: 'final_rank', sorter: true },
    {
      title: '登录状态',
      dataIndex: 'can_login',
      key: 'can_login',
      sorter: true,
      render: (value) => (value ? <Tag color="green">允许登录</Tag> : <Tag color="red">禁止登录</Tag>),
    },
    {
      title: '可选学生池显示',
      dataIndex: 'selection_display_enabled',
      key: 'selection_display_enabled',
      sorter: true,
      render: (value) => (value ? <Tag color="blue">显示</Tag> : <Tag color="default">隐藏</Tag>),
    },
    {
      title: '当前状态',
      key: 'status',
      render: (_, record) => {
        const status = getStudentStatus(record);
        return <StatusTag tone={status.tone}>{status.text}</StatusTag>;
      },
    },
    {
      title: '审核状态',
      dataIndex: 'signature_table_review_status',
      key: 'signature_table_review_status',
      sorter: true,
      render: (value) => {
        const config = reviewStatusMap[value] || { tone: 'default', text: '未知' };
        return <StatusTag tone={config.tone}>{config.text}</StatusTag>;
      },
    },
    {
      title: '材料',
      key: 'files',
      render: (_, record) => (
        <Space wrap>
          <Button size="small" onClick={() => openPreview(`${record.name}的简历`, record.resume)} disabled={!record.resume}>
            简历
          </Button>
          <Button
            size="small"
            onClick={() => openPreview(`${record.name}的互选表`, record.signature_table)}
            disabled={!record.signature_table}
          >
            互选表
          </Button>
          <Button
            size="small"
            onClick={() => openPreview(`${record.name}的放弃说明表`, record.giveup_signature_table)}
            disabled={!record.giveup_signature_table}
          >
            放弃表
          </Button>
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space wrap>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEditModal(record)}>
            编辑
          </Button>
          <Button
            size="small"
            onClick={() =>
              post('/students/actions/toggle-login/', { ids: [record.id], can_login: !record.can_login })
                .then((payload) => {
                  message.success(payload?.detail || '操作成功');
                  fetchData();
                })
                .catch((error) => message.error(error.message))
            }
          >
            {record.can_login ? '关闭登录' : '开启登录'}
          </Button>
          <Button
            size="small"
            onClick={() => {
              const checked = !record.selection_display_enabled;
              const execute = () =>
                post('/students/actions/toggle-selection-display/', { ids: [record.id], selection_display_enabled: checked })
                  .then((payload) => {
                    message.success(payload?.detail || '操作成功');
                    fetchData();
                  })
                  .catch((error) => message.error(error.message));

              if (!checked) {
                confirmDanger({
                  title: '确认关闭该学生的可选学生池展示吗？',
                  content: `${record.name}（${record.candidate_number}）将从导师端可选学生列表中隐藏。`,
                  okText: '确认关闭',
                  cancelText: '取消',
                  onOk: execute,
                });
                return;
              }
              execute();
            }}
          >
            {record.selection_display_enabled ? '隐藏展示' : '恢复展示'}
          </Button>
          <Button
            size="small"
            danger
            onClick={() =>
              confirmDanger({
                title: '确认删除这名学生吗？',
                content: `${record.name}（${record.candidate_number}）将被删除。`,
                okText: '确认删除',
                cancelText: '取消',
                onOk: () => deleteStudents([record.id]),
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
          items={[{ title: '人员管理' }, { title: '学生管理' }]}
          title="学生管理"
          subtitle="统一维护学生资料、届别、招生批次、登录权限和材料查看。"
        />

        <div className="page-toolbar students-page-toolbar">
          <div className="page-filters students-page-filters">
            <Input.Search
              allowClear
              placeholder="按姓名或考生编号搜索"
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
              onSearch={(value) => fetchData(1, pagination.pageSize, value, filters, sorter)}
              style={{ width: 240 }}
            />
            <Select
              allowClear
              placeholder="按专业筛选"
              style={{ width: 240 }}
              value={filters.subject_id}
              options={subjects.map((item) => ({ label: formatSubjectLabel(item), value: item.id }))}
              onChange={(value) => updateFilter('subject_id', value)}
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
              placeholder="按批次筛选"
              style={{ width: 240 }}
              value={filters.admission_batch_id}
              options={batches.map((item) => ({ label: `${item.admission_year}届 - ${item.name}`, value: item.id }))}
              onChange={(value) => updateFilter('admission_batch_id', value)}
            />
            <Select
              allowClear
              placeholder="按登录状态筛选"
              style={{ width: 150 }}
              value={filters.can_login}
              options={buildBooleanOptions('允许登录', '禁止登录')}
              onChange={(value) => updateFilter('can_login', value)}
            />
            <Select
              allowClear
              placeholder="按展示状态筛选"
              style={{ width: 160 }}
              value={filters.selection_display_enabled}
              options={buildBooleanOptions('显示', '隐藏')}
              onChange={(value) => updateFilter('selection_display_enabled', value)}
            />
            <Select
              allowClear
              placeholder="按学生类型筛选"
              style={{ width: 160 }}
              value={filters.student_type}
              options={studentTypeOptions}
              onChange={(value) => updateFilter('student_type', value)}
            />
            <Select
              allowClear
              placeholder="按培养类型筛选"
              style={{ width: 170 }}
              value={filters.postgraduate_type}
              options={postgraduateTypeOptions}
              onChange={(value) => updateFilter('postgraduate_type', value)}
            />
            <Select
              allowClear
              placeholder="按录取状态筛选"
              style={{ width: 150 }}
              value={filters.is_selected}
              options={buildBooleanOptions('已录取', '未录取')}
              onChange={(value) => updateFilter('is_selected', value)}
            />
            <Select
              allowClear
              placeholder="按候补状态筛选"
              style={{ width: 150 }}
              value={filters.is_alternate}
              options={buildBooleanOptions('候补中', '非候补')}
              onChange={(value) => updateFilter('is_alternate', value)}
            />
            <Select
              allowClear
              placeholder="按放弃状态筛选"
              style={{ width: 150 }}
              value={filters.is_giveup}
              options={buildBooleanOptions('已放弃', '未放弃')}
              onChange={(value) => updateFilter('is_giveup', value)}
            />
            <Select
              allowClear
              placeholder="按审核状态筛选"
              style={{ width: 150 }}
              value={filters.review_status}
              options={reviewStatusOptions}
              onChange={(value) => updateFilter('review_status', value)}
            />
          </div>

          <div className="page-actions students-page-actions">
            <Button onClick={() => fetchData(1, pagination.pageSize, keyword, filters, sorter)}>刷新</Button>
            <Button onClick={resetFilters}>清空筛选</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
              新建学生
            </Button>
            <Button icon={<UploadOutlined />} onClick={() => setImportOpen(true)}>
              导入学生
            </Button>
            <Button
              icon={<UnlockOutlined />}
              disabled={!selectedRowKeys.length}
              loading={actionLoading}
              onClick={() => toggleSelectedStudentsLogin(true)}
            >
              开启选中学生登录
            </Button>
            <Button
              icon={<PoweroffOutlined />}
              disabled={!selectedRowKeys.length}
              loading={actionLoading}
              onClick={() => toggleSelectedStudentsLogin(false)}
            >
              关闭选中学生登录
            </Button>
            <Button disabled={!selectedRowKeys.length} loading={actionLoading} onClick={() => toggleSelectedStudentsDisplay(true)}>
              开启选中学生展示
            </Button>
            <Button disabled={!selectedRowKeys.length} loading={actionLoading} onClick={() => toggleSelectedStudentsDisplay(false)}>
              关闭选中学生展示
            </Button>
            <Button
              icon={<LockOutlined />}
              disabled={!selectedRowKeys.length}
              loading={actionLoading}
              onClick={() =>
                runAction(
                  () => post('/students/actions/reset-password/', { ids: selectedRowKeys }),
                  '密码已重置为考生编号',
                )
              }
            >
              重置密码
            </Button>
            <Button disabled={!selectedRowKeys.length} onClick={() => batchDownload('signature', '学生互选表.zip')}>
              下载互选表
            </Button>
            <Button disabled={!selectedRowKeys.length} onClick={() => batchDownload('giveup', '学生放弃说明表.zip')}>
              下载放弃表
            </Button>
            <Button
              danger
              disabled={!selectedRowKeys.length}
              onClick={() =>
                confirmDanger({
                  title: '确认删除选中的学生吗？',
                  content: `共 ${selectedRowKeys.length} 名学生将被删除。`,
                  okText: '确认删除',
                  cancelText: '取消',
                  onOk: () => deleteStudents(selectedRowKeys),
                })
              }
            >
              删除选中
            </Button>
            <Button
              danger
              onClick={() =>
                confirmDanger({
                  title: '确认删除当前筛选结果中的全部学生吗？',
                  content: '这会删除当前筛选条件下的全部学生记录。',
                  okText: '确认删除',
                  cancelText: '取消',
                  onOk: () => deleteStudents([], true),
                })
              }
            >
              删除当前筛选结果
            </Button>
          </div>
        </div>

        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={data.results}
          rowSelection={{ selectedRowKeys, onChange: setSelectedRowKeys }}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: data.count,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
          onChange={(nextPagination, _, tableSorter) => {
            const nextSorter = Array.isArray(tableSorter) ? tableSorter[0] : tableSorter;
            const resolvedSorter = nextSorter?.field
              ? {
                  order_by: nextSorter.field,
                  order_direction: nextSorter.order === 'descend' ? 'desc' : 'asc',
                }
              : sorter;
            setSorter(resolvedSorter);
            fetchData(nextPagination.current, nextPagination.pageSize, keyword, filters, resolvedSorter);
          }}
        />
      </Card>

      <Modal
        open={editOpen}
        title={editingRecord ? '编辑学生' : '新建学生'}
        onCancel={() => setEditOpen(false)}
        onOk={handleSaveStudent}
        width={900}
        destroyOnClose
      >
        <Form form={editForm} layout="vertical">
          <div className="modal-form-section">
            <div className="modal-form-section-title">基础信息</div>
            <div className="modal-form-grid">
              <Form.Item label="姓名" name="name" rules={[{ required: true, message: '请输入姓名' }]}>
                <Input />
              </Form.Item>
              <Form.Item label="考生编号" name="candidate_number" rules={[{ required: true, message: '请输入考生编号' }]}>
                <Input />
              </Form.Item>
              <Form.Item label="身份证号" name="identify_number">
                <Input />
              </Form.Item>
              <Form.Item label="手机号" name="phone_number">
                <Input />
              </Form.Item>
              <Form.Item label="报考专业" name="subject_id" rules={[{ required: true, message: '请选择报考专业' }]}>
                <Select options={subjects.map((item) => ({ label: formatSubjectLabel(item), value: item.id }))} />
              </Form.Item>
              <Form.Item label="届别" name="admission_year" rules={[{ required: true, message: '请选择届别' }]}>
                <Select options={yearOptions} />
              </Form.Item>
              <Form.Item label="招生批次" name="admission_batch_id">
                <Select
                  allowClear
                  options={batches.map((item) => ({ label: `${item.admission_year}届 - ${item.name}`, value: item.id }))}
                />
              </Form.Item>
              <Form.Item label="允许登录小程序" name="can_login" valuePropName="checked">
                <Switch checkedChildren="允许" unCheckedChildren="禁止" />
              </Form.Item>
              <Form.Item label="显示在可选学生池" name="selection_display_enabled" valuePropName="checked">
                <Switch checkedChildren="显示" unCheckedChildren="隐藏" />
              </Form.Item>
            </div>
          </div>

          <div className="modal-form-section">
            <div className="modal-form-section-title">培养信息</div>
            <div className="modal-form-grid">
              <Form.Item label="学生类型" name="student_type" rules={[{ required: true, message: '请选择学生类型' }]}>
                <Select options={studentTypeOptions} />
              </Form.Item>
              <Form.Item label="培养类型" name="postgraduate_type" rules={[{ required: true, message: '请选择培养类型' }]}>
                <Select options={postgraduateTypeOptions} />
              </Form.Item>
              <Form.Item label="学习方式" name="study_mode" valuePropName="checked">
                <Switch checkedChildren="全日制" unCheckedChildren="非全日制" />
              </Form.Item>
              <Form.Item label="初试成绩" name="initial_exam_score">
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item label="复试成绩" name="secondary_exam_score">
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item label="初试排名" name="initial_rank">
                <InputNumber style={{ width: '100%' }} min={1} />
              </Form.Item>
              <Form.Item label="复试排名" name="secondary_rank">
                <InputNumber style={{ width: '100%' }} min={1} />
              </Form.Item>
              <Form.Item label="综合排名" name="final_rank">
                <InputNumber style={{ width: '100%' }} min={1} />
              </Form.Item>
            </div>
          </div>

          <div className="modal-form-section">
            <div className="modal-form-section-title">状态信息</div>
            <div className="modal-form-grid">
              <Form.Item label="已录取" name="is_selected" valuePropName="checked">
                <Switch checkedChildren="是" unCheckedChildren="否" />
              </Form.Item>
              <Form.Item label="候补中" name="is_alternate" valuePropName="checked">
                <Switch checkedChildren="是" unCheckedChildren="否" />
              </Form.Item>
              <Form.Item label="候补顺位" name="alternate_rank">
                <InputNumber style={{ width: '100%' }} min={1} />
              </Form.Item>
              <Form.Item label="已放弃录取" name="is_giveup" valuePropName="checked">
                <Switch checkedChildren="是" unCheckedChildren="否" />
              </Form.Item>
              {!editingRecord ? (
                <Form.Item label="初始密码" name="password">
                  <Input.Password placeholder="留空则默认使用考生编号" />
                </Form.Item>
              ) : null}
            </div>
          </div>
        </Form>
      </Modal>

      <Modal
        open={importOpen}
        title="导入学生"
        onCancel={() => {
          if (importSubmitting) return;
          setImportOpen(false);
          setImportProgress(0);
          setImportResult(null);
          importForm.resetFields();
        }}
        onOk={handleImport}
        confirmLoading={importSubmitting}
        okText={importSubmitting ? '导入中...' : '开始导入'}
        destroyOnClose
      >
        <Form form={importForm} layout="vertical">
          <Form.Item label="导入类型" name="import_type" rules={[{ required: true, message: '请选择导入类型' }]}>
            <Select options={importTypeOptions} />
          </Form.Item>
          <Form.Item label="同步覆盖名额" name="update_quota" valuePropName="checked">
            <Switch checkedChildren="同步" unCheckedChildren="不同步" />
          </Form.Item>
          <Form.Item
            label="导入文件"
            name="fileList"
            valuePropName="fileList"
            getValueFromEvent={normalizeUploadEvent}
            rules={[{ required: true, message: '请上传导入文件' }]}
          >
            <Upload beforeUpload={() => false} maxCount={1}>
              <Button icon={<UploadOutlined />}>选择 Excel 或 CSV 文件</Button>
            </Upload>
          </Form.Item>
        </Form>
        {importSubmitting || importProgress > 0 ? (
          <div style={{ marginTop: 16 }}>
            <Progress percent={importProgress} status={importSubmitting ? 'active' : 'success'} />
          </div>
        ) : null}
        {importResult ? (
          <div style={{ marginTop: 16 }}>
            <Alert
              type="success"
              showIcon
              message={importResult.detail || '学生导入完成'}
              description={
                <div>
                  <div>创建人数：{importResult.created_count ?? '-'}</div>
                  <div>跳过人数：{importResult.skipped_rows ?? '-'}</div>
                  {Array.isArray(importResult.summary) && importResult.summary.length ? (
                    <div style={{ marginTop: 8 }}>
                      {importResult.summary.map((item) => (
                        <div key={`${item.subject_code}-${item.subject_name}`} style={{ marginBottom: 6 }}>
                          {item.subject_name}（{item.subject_code}）：创建 {item.created_count}，候补 {item.alternate_count}，正常 {item.normal_count}
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              }
            />
          </div>
        ) : null}
      </Modal>

      <PdfPreviewModal
        open={previewState.open}
        title={previewState.title}
        fileId={previewState.fileId}
        onClose={() => setPreviewState({ open: false, title: '', fileId: '' })}
      />
    </>
  );
}
