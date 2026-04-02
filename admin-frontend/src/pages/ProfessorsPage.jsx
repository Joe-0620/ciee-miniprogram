import React, { useEffect, useState } from 'react';
import {
  Button,
  Card,
  Col,
  Divider,
  Form,
  Input,
  Modal,
  Row,
  Select,
  Space,
  Switch,
  Table,
  Typography,
  Upload,
  List,
  message,
} from 'antd';
import { EditOutlined, PlusOutlined, UploadOutlined } from '@ant-design/icons';

import { get, patch, post, upload } from '../api/client';
import PageHeader from '../components/PageHeader';
import StatusTag from '../components/StatusTag';
import { confirmDanger } from '../utils/confirm';
import { loadPageState, savePageState } from '../utils/pageState';

const quotaTypeOptions = [
  { label: '学硕名额清零', value: 'academic' },
  { label: '专硕（北京）名额清零', value: 'professional' },
  { label: '专硕（烟台）名额清零', value: 'professionalyt' },
  { label: '博士名额清零', value: 'doctor' },
];

const professorTitleOptions = ['教授', '副教授', '讲师', '研究员', '副研究员'];

const reviewerOptions = [
  { label: '否', value: 0 },
  { label: '方向审核人（北京）', value: 1 },
  { label: '方向审核人（烟台）', value: 2 },
];

export default function ProfessorsPage() {
  const initialPageState = loadPageState('professors-page', {
    keyword: '',
    filters: {
      department_id: undefined,
      have_qualification: undefined,
      reviewer_only: undefined,
    },
    sorter: { order_by: 'id', order_direction: 'desc' },
    pagination: { current: 1, pageSize: 10 },
  });
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [keyword, setKeyword] = useState(initialPageState.keyword);
  const [filters, setFilters] = useState(initialPageState.filters);
  const [sorter, setSorter] = useState(initialPageState.sorter);
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [data, setData] = useState({ count: 0, results: [] });
  const [pagination, setPagination] = useState(initialPageState.pagination);
  const [departments, setDepartments] = useState([]);
  const [editingRecord, setEditingRecord] = useState(null);
  const [editingDetail, setEditingDetail] = useState(null);
  const [editOpen, setEditOpen] = useState(false);
  const [resetQuotaOpen, setResetQuotaOpen] = useState(false);
  const [masterImportOpen, setMasterImportOpen] = useState(false);
  const [doctorImportOpen, setDoctorImportOpen] = useState(false);
  const [editForm] = Form.useForm();
  const [resetQuotaForm] = Form.useForm();
  const [masterImportForm] = Form.useForm();
  const [doctorImportForm] = Form.useForm();

  const loadBaseOptions = async () => {
    try {
      const payload = await get('/departments/');
      setDepartments(Array.isArray(payload) ? payload : []);
    } catch (error) {
      message.error(error.message);
    }
  };

  const fetchData = async (
    page = pagination.current,
    pageSize = pagination.pageSize,
    nextKeyword = keyword,
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
      if (nextKeyword.trim()) {
        params.set('search', nextKeyword.trim());
      }
      Object.entries(nextFilters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.set(key, String(value));
        }
      });
      const payload = await get(`/professors/?${params.toString()}`);
      setData(payload);
      setPagination({ current: payload.page, pageSize: payload.page_size });
    } catch (error) {
      message.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBaseOptions();
    fetchData(
      initialPageState.pagination.current,
      initialPageState.pagination.pageSize,
      initialPageState.keyword,
      initialPageState.filters,
      initialPageState.sorter,
    );
  }, []);

  useEffect(() => {
    savePageState('professors-page', { keyword, filters, sorter, pagination });
  }, [keyword, filters, sorter, pagination]);

  const runAction = async (handler, successText) => {
    setActionLoading(true);
    try {
      const payload = await handler();
      message.success(successText || payload?.detail || '操作成功');
      setSelectedRowKeys([]);
      await fetchData();
      return payload;
    } catch (error) {
      message.error(error.message);
      throw error;
    } finally {
      setActionLoading(false);
    }
  };

  const normalizeUploadEvent = (event) => {
    if (Array.isArray(event)) return event;
    return event?.fileList || [];
  };

  const buildFormData = (values) => {
    const formData = new FormData();
    Object.entries(values).forEach(([key, value]) => {
      if (key === 'fileList') {
        const file = value?.[0]?.originFileObj;
        if (file) {
          formData.append('file', file);
        }
        return;
      }
      if (typeof value === 'boolean') {
        formData.append(key, value ? 'true' : 'false');
        return;
      }
      if (value !== undefined && value !== null && value !== '') {
        formData.append(key, String(value));
      }
    });
    return formData;
  };

  const openCreateModal = () => {
    setEditingRecord(null);
    setEditingDetail(null);
    editForm.resetFields();
    editForm.setFieldsValue({
      have_qualification: true,
      proposed_quota_approved: false,
      department_position: 0,
      website_order: 0,
    });
    setEditOpen(true);
  };

  const openEditModal = async (record) => {
    try {
      const detail = await get(`/professors/${record.id}/`);
      setEditingRecord(record);
      setEditingDetail(detail);
      editForm.setFieldsValue({
        name: detail.name,
        teacher_identity_id: detail.teacher_identity_id,
        password: '',
        professor_title: detail.professor_title,
        department_id: detail.department?.id,
        email: detail.email,
        phone_number: detail.phone_number,
        avatar: detail.avatar,
        contact_details: detail.contact_details,
        research_areas: detail.research_areas,
        personal_page: detail.personal_page,
        have_qualification: detail.have_qualification,
        proposed_quota_approved: detail.proposed_quota_approved,
        department_position: detail.department_position,
        website_order: detail.website_order,
      });
      setEditOpen(true);
    } catch (error) {
      message.error(error.message);
    }
  };

  const handleSaveProfessor = async () => {
    try {
      const values = await editForm.validateFields();
      await runAction(
        () => (editingRecord ? patch(`/professors/${editingRecord.id}/`, values) : post('/professors/', values)),
        editingRecord ? '导师信息已更新' : '导师已创建',
      );
      setEditOpen(false);
      editForm.resetFields();
    } catch (error) {
      if (!error?.errorFields) {
        message.error(error.message);
      }
    }
  };

  const handleResetQuota = async () => {
    try {
      const values = await resetQuotaForm.validateFields();
      await runAction(
        () => post('/professors/actions/reset-quota/', { ids: selectedRowKeys, quota_type: values.quota_type }),
        '导师名额已清零',
      );
      setResetQuotaOpen(false);
      resetQuotaForm.resetFields();
    } catch (error) {
      if (!error?.errorFields) {
        message.error(error.message);
      }
    }
  };

  const handleMasterImport = async () => {
    try {
      const values = await masterImportForm.validateFields();
      const payload = await runAction(() => upload('/professors/import-master-quota/', buildFormData(values)), '硕士名额导入完成');
      setMasterImportOpen(false);
      masterImportForm.resetFields();
      Modal.info({
        title: '硕士名额导入结果',
        width: 560,
        content: (
          <Space direction="vertical" style={{ width: '100%' }} size={12}>
            <Typography.Text>{payload?.detail || '硕士名额导入完成'}</Typography.Text>
            <Typography.Text>更新记录数：{payload?.updated_count ?? 0}</Typography.Text>
            <Typography.Text>跳过行数：{payload?.skipped_rows ?? 0}</Typography.Text>
            <Typography.Text>自动创建导师账号：{payload?.created_professor_count ?? 0}</Typography.Text>
            {(payload?.created_professor_teacher_ids || []).length > 0 ? (
              <>
                <Typography.Text strong>新建导师工号</Typography.Text>
                <List
                  size="small"
                  bordered
                  dataSource={payload.created_professor_teacher_ids}
                  renderItem={(item) => <List.Item>{item}</List.Item>}
                />
              </>
            ) : null}
            {(payload?.subject_quota_summary || []).length > 0 ? (
              <>
                <Typography.Text strong>按专业名额汇总</Typography.Text>
                <List
                  size="small"
                  bordered
                  dataSource={payload.subject_quota_summary}
                  renderItem={(item) => (
                    <List.Item>
                      <Space direction="vertical" style={{ width: '100%' }} size={2}>
                        <Typography.Text strong>
                          {item.subject_name}（{item.subject_code}）
                        </Typography.Text>
                        <Typography.Text type="secondary">
                          固定北京名额：{item.beijing_quota}　固定烟台名额：{item.yantai_quota}　共享北京名额：{item.shared_beijing_quota}　共享烟台名额：{item.shared_yantai_quota}　总名额：{item.total_quota}
                        </Typography.Text>
                      </Space>
                    </List.Item>
                  )}
                />
              </>
            ) : null}
          </Space>
        ),
      });
    } catch (error) {
      if (!error?.errorFields) {
        message.error(error.message);
      }
    }
  };

  const handleDoctorImport = async () => {
    try {
      const values = await doctorImportForm.validateFields();
      await runAction(() => upload('/professors/import-doctor-quota/', buildFormData(values)), '博士名额导入完成');
      setDoctorImportOpen(false);
      doctorImportForm.resetFields();
    } catch (error) {
      if (!error?.errorFields) {
        message.error(error.message);
      }
    }
  };

  const updateFilter = (key, value) => {
    const nextFilters = { ...filters, [key]: value };
    setFilters(nextFilters);
    fetchData(1, pagination.pageSize, keyword, nextFilters, sorter);
  };

  const buildDeleteQuery = () => {
    const params = new URLSearchParams();
    if (keyword.trim()) {
      params.set('search', keyword.trim());
    }
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.set(key, String(value));
      }
    });
    return params.toString();
  };

  const deleteProfessors = (ids, deleteAllFiltered = false) => {
    const query = buildDeleteQuery();
    return runAction(
      () => post(`/professors/actions/batch-delete/${query ? `?${query}` : ''}`, { ids, delete_all_filtered: deleteAllFiltered }),
      '删除成功',
    );
  };

  const columns = [
    { title: '姓名', dataIndex: 'name', key: 'name', sorter: true, width: 140, ellipsis: true, fixed: 'left' },
    { title: '工号', dataIndex: 'teacher_identity_id', key: 'teacher_identity_id', sorter: true, width: 120, ellipsis: true },
    {
      title: '方向',
      key: 'department_name',
      sorter: true,
      width: 140,
      ellipsis: true,
      render: (_, record) => record.department?.department_name || '-',
    },
    {
      title: '硕士招生专业',
      dataIndex: 'master_subjects',
      key: 'master_subjects',
      width: 220,
      ellipsis: true,
      render: (value) => (value?.length ? value.join('、') : '-'),
    },
    {
      title: '博士招生专业',
      dataIndex: 'doctor_subjects',
      key: 'doctor_subjects',
      width: 180,
      ellipsis: true,
      responsive: ['xl'],
      render: (value) => (value?.length ? value.join('、') : '-'),
    },
    {
      title: '共享池覆盖',
      dataIndex: 'shared_quota_summary',
      key: 'shared_quota_summary',
      width: 220,
      responsive: ['xxl'],
      render: (value, record) => {
        if (!value?.length) return '-';
        return (
          <Space direction="vertical" size={4}>
            <Typography.Text>{`${record.shared_quota_pool_count || value.length} 个共享池`}</Typography.Text>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {value.map((item) => item.pool_name).join('、')}
            </Typography.Text>
          </Space>
        );
      },
    },
    {
      title: '招生资格',
      key: 'have_qualification',
      width: 110,
      render: (_, record) => (
        <StatusTag tone={record.have_qualification ? 'success' : 'default'}>
          {record.have_qualification ? '可招生' : '不可招生'}
        </StatusTag>
      ),
    },
    {
      title: '开放选择',
      key: 'proposed_quota_approved',
      width: 110,
      render: (_, record) => (
        <StatusTag tone={record.proposed_quota_approved ? 'processing' : 'default'}>
          {record.proposed_quota_approved ? '已开放' : '未开放'}
        </StatusTag>
      ),
    },
    { title: '剩余总名额', dataIndex: 'remaining_quota', key: 'remaining_quota', sorter: true, width: 110 },
    { title: '待处理申请', dataIndex: 'pending_choice_count', key: 'pending_choice_count', sorter: true, width: 110, responsive: ['lg'] },
    {
      title: '操作',
      key: 'actions',
      width: 160,
      fixed: 'right',
      render: (_, record) => (
        <Space wrap className="compact-action-buttons">
          <Button size="small" icon={<EditOutlined />} onClick={() => openEditModal(record)}>
            编辑
          </Button>
          <Button
            size="small"
            danger
            onClick={() =>
              confirmDanger({
                title: '确认删除这位导师吗？',
                content: `${record.name}（${record.teacher_identity_id}）`,
                onOk: () => deleteProfessors([record.id]),
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
          items={[{ title: '人员管理' }, { title: '导师管理' }]}
          title="导师管理"
          subtitle="集中维护导师资料、审核人身份、开放选择状态以及硕博专业名额。"
        />

        <div className="page-toolbar">
          <div className="page-filters">
            <Input.Search
              placeholder="按姓名、工号或研究方向搜索"
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
              onSearch={(value) => fetchData(1, pagination.pageSize, value, filters, sorter)}
              allowClear
              style={{ width: 320 }}
            />
            <Select
              allowClear
              placeholder="按方向筛选"
              style={{ width: 180 }}
              options={departments.map((item) => ({ label: item.department_name, value: item.id }))}
              value={filters.department_id}
              onChange={(value) => updateFilter('department_id', value)}
            />
            <Select
              allowClear
              placeholder="按招生资格筛选"
              style={{ width: 160 }}
              value={filters.have_qualification}
              options={[
                { label: '可招生', value: 'true' },
                { label: '不可招生', value: 'false' },
              ]}
              onChange={(value) => updateFilter('have_qualification', value)}
            />
            <Select
              allowClear
              placeholder="按审核人筛选"
              style={{ width: 170 }}
              value={filters.reviewer_only}
              options={[{ label: '仅显示审核人', value: 'true' }]}
              onChange={(value) => updateFilter('reviewer_only', value)}
            />
          </div>

          <div className="page-actions">
            <Button onClick={() => fetchData(1, pagination.pageSize, keyword, filters, sorter)}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
              新建导师
            </Button>
            <Button onClick={() => setMasterImportOpen(true)}>导入硕士名额</Button>
            <Button onClick={() => setDoctorImportOpen(true)}>导入博士名额</Button>
            <Button disabled={!selectedRowKeys.length} onClick={() => setResetQuotaOpen(true)}>
              名额清零
            </Button>
            <Button
              danger
              disabled={!selectedRowKeys.length}
              onClick={() =>
                confirmDanger({
                  title: '确认删除选中的导师吗？',
                  content: `共 ${selectedRowKeys.length} 位导师，删除后将同时清理关联登录账号。`,
                  onOk: () => deleteProfessors(selectedRowKeys),
                })
              }
            >
              删除选中
            </Button>
            <Button
              danger
              onClick={() =>
                confirmDanger({
                  title: '确认删除当前筛选结果中的所有导师吗？',
                  content: '这个操作会删除当前筛选条件下的全部导师记录，并同步清理关联登录账号。',
                  onOk: () => deleteProfessors([], true),
                })
              }
            >
              删除当前筛选结果
            </Button>
            <Button
              loading={actionLoading}
              disabled={!selectedRowKeys.length}
              onClick={() => runAction(() => post('/professors/actions/reset-password/', { ids: selectedRowKeys }), '密码已重置为工号')}
            >
              密码重置为工号
            </Button>
            <Button
              loading={actionLoading}
              disabled={!selectedRowKeys.length}
              onClick={() =>
                runAction(() => post('/professors/actions/reset-selection-status/', { ids: selectedRowKeys }), '开放选择状态已重置')
              }
            >
              重置开放选择状态
            </Button>
          </div>
        </div>

        <Table
          className="dashboard-table"
          rowKey="id"
          loading={loading}
          rowSelection={{ selectedRowKeys, onChange: setSelectedRowKeys }}
          columns={columns}
          dataSource={data.results}
          scroll={{ x: 1500 }}
          sticky={{ offsetHeader: 64, offsetScroll: 12 }}
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
        title={editingRecord ? '编辑导师' : '新建导师'}
        open={editOpen}
        onCancel={() => setEditOpen(false)}
        onOk={handleSaveProfessor}
        confirmLoading={actionLoading}
        destroyOnClose
        width={860}
        afterClose={() => setEditingDetail(null)}
      >
        <Form form={editForm} layout="vertical">
          <Divider orientation="left">基础信息</Divider>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="name" label="姓名" rules={[{ required: true, message: '请输入导师姓名' }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="teacher_identity_id" label="工号" rules={[{ required: true, message: '请输入导师工号' }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="password" label="登录密码">
                <Input.Password placeholder={editingRecord ? '留空则不修改密码' : '留空则默认与工号一致'} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="professor_title" label="职称">
                <Select allowClear options={professorTitleOptions.map((item) => ({ label: item, value: item }))} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="department_id" label="招生方向" rules={[{ required: true, message: '请选择招生方向' }]}>
                <Select options={departments.map((item) => ({ label: item.department_name, value: item.id }))} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="department_position" label="审核人身份">
                <Select options={reviewerOptions} />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left">联系与说明</Divider>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="email" label="邮箱">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="phone_number" label="手机号">
                <Input />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item name="avatar" label="头像地址">
                <Input placeholder="请输入导师头像图片地址" />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item name="contact_details" label="联系方式说明">
                <Input />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item name="research_areas" label="研究方向">
                <Input.TextArea rows={3} />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item name="personal_page" label="个人主页">
                <Input.TextArea rows={3} />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left">状态与排序</Divider>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="website_order" label="官网排序">
                <Input type="number" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="have_qualification" label="具备招生资格" valuePropName="checked">
                <Switch checkedChildren="是" unCheckedChildren="否" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="proposed_quota_approved" label="开放选择资格" valuePropName="checked">
                <Switch checkedChildren="已开放" unCheckedChildren="未开放" />
              </Form.Item>
            </Col>
          </Row>

          {editingRecord && (
            <>
              <Divider orientation="left">共享名额池</Divider>
              {(editingDetail?.shared_quota_pools || []).length ? (
                <Space direction="vertical" size={12} style={{ width: '100%' }}>
                  {editingDetail.shared_quota_pools.map((pool) => (
                    <Card key={pool.id} size="small" bordered>
                      <Space direction="vertical" size={4} style={{ width: '100%' }}>
                        <Typography.Text strong>{pool.pool_name}</Typography.Text>
                        <Typography.Text type="secondary">
                          {pool.quota_scope_display} / {pool.campus_display} / 剩余 {pool.remaining_quota}/{pool.total_quota}
                        </Typography.Text>
                        <Typography.Text>
                          覆盖专业：
                          {pool.subject_labels?.length ? pool.subject_labels.map((item) => item.subject_name).join('、') : '-'}
                        </Typography.Text>
                      </Space>
                    </Card>
                  ))}
                </Space>
              ) : (
                <Typography.Text type="secondary">当前未配置共享名额池。</Typography.Text>
              )}
            </>
          )}
        </Form>
      </Modal>

      <Modal
        title="导师名额清零"
        open={resetQuotaOpen}
        onCancel={() => setResetQuotaOpen(false)}
        onOk={handleResetQuota}
        confirmLoading={actionLoading}
        destroyOnClose
      >
        <Form form={resetQuotaForm} layout="vertical">
          <Form.Item name="quota_type" label="清零类型" rules={[{ required: true, message: '请选择要清零的名额类型' }]}>
            <Select options={quotaTypeOptions} placeholder="请选择名额类型" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="导入硕士名额"
        open={masterImportOpen}
        onCancel={() => setMasterImportOpen(false)}
        onOk={handleMasterImport}
        confirmLoading={actionLoading}
        destroyOnClose
      >
        <Form form={masterImportForm} layout="vertical" initialValues={{ sync_quotas: false }}>
          <Form.Item name="sync_quotas" label="同步专业总名额" valuePropName="checked">
            <Switch checkedChildren="同步" unCheckedChildren="不同步" />
          </Form.Item>
          <Form.Item
            name="fileList"
            label="XLSX 文件"
            valuePropName="fileList"
            getValueFromEvent={normalizeUploadEvent}
            rules={[{ required: true, message: '请上传 XLSX 文件' }]}
          >
            <Upload beforeUpload={() => false} maxCount={1} accept=".xlsx">
              <Button icon={<UploadOutlined />}>选择文件</Button>
            </Upload>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="导入博士名额"
        open={doctorImportOpen}
        onCancel={() => setDoctorImportOpen(false)}
        onOk={handleDoctorImport}
        confirmLoading={actionLoading}
        destroyOnClose
      >
        <Form form={doctorImportForm} layout="vertical" initialValues={{ conflict_action: 'replace' }}>
          <Form.Item name="conflict_action" label="冲突处理方式" rules={[{ required: true, message: '请选择冲突处理方式' }]}>
            <Select options={[{ label: '覆盖本次名额', value: 'replace' }, { label: '在现有基础上增加', value: 'add' }]} />
          </Form.Item>
          <Form.Item
            name="fileList"
            label="XLSX 文件"
            valuePropName="fileList"
            getValueFromEvent={normalizeUploadEvent}
            rules={[{ required: true, message: '请上传 XLSX 文件' }]}
          >
            <Upload beforeUpload={() => false} maxCount={1} accept=".xlsx">
              <Button icon={<UploadOutlined />}>选择文件</Button>
            </Upload>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
