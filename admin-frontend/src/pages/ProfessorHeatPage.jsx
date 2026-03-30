import React, { useEffect, useState } from 'react';
import { Button, Card, Form, Input, InputNumber, Modal, Select, Space, Switch, Table, Typography, message } from 'antd';
import { FireFilled } from '@ant-design/icons';

import { get, patch } from '../api/client';
import PageHeader from '../components/PageHeader';


const heatToneMap = {
  低: 'low',
  中: 'medium',
  高: 'high',
  很高: 'very-high',
};

function formatHeatStars(level) {
  if (level === '很高') return 4;
  if (level === '高') return 3;
  if (level === '中') return 2;
  return 1;
}

function inferPostgraduateTypeFromSubject(subject) {
  if (!subject) return undefined;
  if (subject.subject_type === 1) return 2;
  if (subject.subject_type === 2) return 3;
  return undefined;
}

function getSubjectTypeLabel(subject) {
  if (!subject) return '';
  if (subject.subject_type === 2) return '博士';
  if (subject.subject_type === 1) return '学硕';
  return '专硕';
}

export default function ProfessorHeatPage() {
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [filters, setFilters] = useState({ department_id: undefined, heat_level: undefined, subject_id: undefined, postgraduate_type: undefined, student_type: 2 });
  const [departments, setDepartments] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [data, setData] = useState({ count: 0, results: [] });
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });
  const [globalVisible, setGlobalVisible] = useState(true);
  const [editingRecord, setEditingRecord] = useState(null);
  const [editOpen, setEditOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [form] = Form.useForm();
  const [settingsForm] = Form.useForm();

  const loadOptions = async () => {
    try {
      const [payload, subjectPayload, settingPayload] = await Promise.all([
        get('/departments/'),
        get('/subjects/'),
        get('/professor-heat/settings/'),
      ]);
      const nextDepartments = Array.isArray(payload) ? payload : [];
      const nextSubjects = Array.isArray(subjectPayload)
        ? subjectPayload
        : Array.isArray(subjectPayload?.results)
          ? subjectPayload.results
          : [];
      setDepartments(nextDepartments);
      setSubjects(nextSubjects);
      setGlobalVisible(Boolean(settingPayload?.show_professor_heat));
      settingsForm.setFieldsValue({
        calculation_scope: 'subject',
        target_admission_year: Number(settingPayload?.target_admission_year ?? 2026),
        medium_threshold: Number(settingPayload?.medium_threshold ?? 2),
        high_threshold: Number(settingPayload?.high_threshold ?? 4),
        very_high_threshold: Number(settingPayload?.very_high_threshold ?? 6),
        medium_ratio_threshold: Number(settingPayload?.medium_ratio_threshold ?? 1.5),
        high_ratio_threshold: Number(settingPayload?.high_ratio_threshold ?? 2.5),
        very_high_ratio_threshold: Number(settingPayload?.very_high_ratio_threshold ?? 4),
      });

    } catch (error) {
      message.error(error.message);
    }
  };

  const fetchData = async (
    page = pagination.current,
    pageSize = pagination.pageSize,
    search = keyword,
    nextFilters = filters,
  ) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
      });
      if (search.trim()) {
        params.set('search', search.trim());
      }
      Object.entries(nextFilters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.set(key, String(value));
        }
      });
      const payload = await get(`/professor-heat/?${params.toString()}`);
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

  const runAction = async (handler, successText) => {
    setActionLoading(true);
    try {
      const payload = await handler();
      message.success(successText || payload?.detail || '操作成功');
      return payload;
    } catch (error) {
      message.error(error.message);
      throw error;
    } finally {
      setActionLoading(false);
    }
  };

  const handleToggleGlobalVisible = async (checked) => {
    try {
      const payload = await runAction(
        () => patch('/professor-heat/settings/', { show_professor_heat: checked }),
        checked ? '已开启前端热度显示' : '已关闭前端热度显示',
      );
      setGlobalVisible(Boolean(payload?.show_professor_heat));
      await fetchData();
    } catch {}
  };

  const handleSaveSettings = async () => {
    try {
      const values = await settingsForm.validateFields();
      await runAction(
        () =>
          patch('/professor-heat/settings/', {
            calculation_scope: 'subject',
            target_admission_year: values.target_admission_year,
            medium_threshold: values.medium_threshold,
            high_threshold: values.high_threshold,
            very_high_threshold: values.very_high_threshold,
            medium_ratio_threshold: values.medium_ratio_threshold,
            high_ratio_threshold: values.high_ratio_threshold,
            very_high_ratio_threshold: values.very_high_ratio_threshold,
          }),
        '热度计算设置已更新',
      );
      setSettingsOpen(false);
      await loadOptions();
      await fetchData();
    } catch (error) {
      if (!error?.errorFields) {
        message.error(error.message);
      }
    }
  };

  const openEditModal = (record) => {
    setEditingRecord(record);
    form.setFieldsValue({
      heat_display_enabled: record.heat_display_enabled,
      manual_heat_score: record.manual_heat_score ?? null,
      manual_heat_level: record.manual_heat_level || undefined,
    });
    setEditOpen(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      await runAction(
        () =>
          patch(`/professor-heat/${editingRecord.id}/`, {
            heat_display_enabled: values.heat_display_enabled,
            manual_heat_score: values.manual_heat_score ?? '',
            manual_heat_level: values.manual_heat_level ?? '',
          }),
        '导师热度设置已更新',
      );
      setEditOpen(false);
      await fetchData();
    } catch (error) {
      if (!error?.errorFields) {
        message.error(error.message);
      }
    }
  };

  const handleToggleProfessorVisible = (record, checked) => {
    Modal.confirm({
      centered: true,
      title: checked ? '确认开启该导师的热度显示吗？' : '确认关闭该导师的热度显示吗？',
      content: `${record.name}（${record.teacher_identity_id}）`,
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        try {
          await runAction(
            () =>
              patch(`/professor-heat/${record.id}/`, {
                heat_display_enabled: checked,
              }),
            checked ? '已开启该导师的热度显示' : '已关闭该导师的热度显示',
          );
          await fetchData();
        } catch {}
      },
    });
  };

  const updateFilter = (key, value) => {
    const nextFilters = { ...filters, [key]: value };
    setFilters(nextFilters);
    fetchData(1, pagination.pageSize, keyword, nextFilters);
  };

  const handleSubjectChange = (value) => {
    const selectedSubject = subjects.find((item) => item.id === value);
    const inferredPostgraduateType = inferPostgraduateTypeFromSubject(selectedSubject);
    const nextFilters = {
      ...filters,
      subject_id: value,
      postgraduate_type: inferredPostgraduateType,
    };
    setFilters(nextFilters);
    fetchData(1, pagination.pageSize, keyword, nextFilters);
  };

  const columns = [
    { title: '导师姓名', dataIndex: 'name', key: 'name' },
    { title: '工号', dataIndex: 'teacher_identity_id', key: 'teacher_identity_id' },
    {
      title: '方向',
      key: 'department_name',
      render: (_, record) => record.department?.department_name || '-',
    },
    {
      title: '可用名额',
      dataIndex: 'available_quota_total',
      key: 'available_quota_total',
      render: (value) => value ?? 0,
    },
    {
      title: '待处理',
      dataIndex: 'pending_count',
      key: 'pending_count',
      render: (value) => value ?? 0,
    },
    {
      title: '已同意',
      dataIndex: 'accepted_count',
      key: 'accepted_count',
      render: (value) => value ?? 0,
    },
    {
      title: '已拒绝',
      dataIndex: 'rejected_count',
      key: 'rejected_count',
      render: (value) => value ?? 0,
    },
    {
      title: '热度指数',
      dataIndex: 'heat_score',
      key: 'heat_score',
      render: (value) => Number(value || 0).toFixed(2),
    },
    {
      title: '热度等级',
      dataIndex: 'heat_level',
      key: 'heat_level',
      render: (value) => (
        <span className={`heat-pill heat-pill-${heatToneMap[value] || 'low'}`}>
          <span>互选热度</span>
          <span className="heat-pill-icons">
            {Array.from({ length: formatHeatStars(value || '低') }).map((_, index) => (
              <FireFilled key={index} />
            ))}
          </span>
        </span>
      ),
    },
    {
      title: '前端显示',
      dataIndex: 'heat_visible',
      key: 'heat_visible',
      render: (value) => <span className={`heat-pill ${value ? 'heat-pill-low' : 'heat-pill-muted'}`}>{value ? '显示' : '隐藏'}</span>,
    },
    {
      title: '个人开关',
      dataIndex: 'heat_display_enabled',
      key: 'heat_display_enabled',
      render: (value, record) => (
        <Switch
          checked={value}
          checkedChildren="开启"
          unCheckedChildren="关闭"
          loading={actionLoading}
          onChange={(checked) => handleToggleProfessorVisible(record, checked)}
        />
      ),
    },
    {
      title: '手动热度',
      key: 'manual_heat',
      render: (_, record) => {
        if (record.manual_heat_score == null && !record.manual_heat_level) {
          return '-';
        }
        return `${record.manual_heat_score ?? '-'} / ${record.manual_heat_level || '自动'}`;
      },
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Button size="small" onClick={() => openEditModal(record)}>
          编辑热度
        </Button>
      ),
    },
  ];

  return (
    <Card className="page-card" bordered={false}>
      <PageHeader
        items={[{ title: '招生业务' }, { title: '导师热度管理' }]}
        title="导师热度管理"
        subtitle="统一管理前端热度显示、手动热度覆盖和热度计算规则。"
      />

      <div className="page-toolbar">
        <div className="page-filters">
          <Input.Search
            placeholder="按导师姓名或工号搜索"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            onSearch={(value) => fetchData(1, pagination.pageSize, value, filters)}
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
            placeholder="按热度筛选"
            style={{ width: 160 }}
            value={filters.heat_level}
            options={[
              { label: '低', value: '低' },
              { label: '中', value: '中' },
              { label: '高', value: '高' },
              { label: '很高', value: '很高' },
            ]}
            onChange={(value) => updateFilter('heat_level', value)}
          />
          <Select
            allowClear
            placeholder="按专业视角查看"
            style={{ width: 240 }}
            value={filters.subject_id}
            options={subjects.map((item) => ({
              label: `${item.subject_name}（${getSubjectTypeLabel(item)}${item.subject_code ? `，${item.subject_code}` : ''}）`,
              value: item.id,
            }))}
            onChange={handleSubjectChange}
          />
          <Select
            placeholder="按学生类型统计"
            style={{ width: 180 }}
            value={filters.student_type}
            options={[
              { label: '硕士统考生', value: 2 },
              { label: '硕士推荐生', value: 1 },
              { label: '博士统考生', value: 3 },
            ]}
            onChange={(value) => updateFilter('student_type', value)}
          />
          <Select
            allowClear
            placeholder="按培养类型视角"
            style={{ width: 180 }}
            value={filters.postgraduate_type}
            options={[
              { label: '北京专硕', value: 1 },
              { label: '学硕', value: 2 },
              { label: '博士', value: 3 },
              { label: '烟台专硕', value: 4 },
            ]}
            onChange={(value) => updateFilter('postgraduate_type', value)}
          />
        </div>

        <div className="page-actions">
          <Button onClick={() => fetchData(1, pagination.pageSize, keyword, filters)}>刷新</Button>
          <Button onClick={() => setSettingsOpen(true)}>热度计算设置</Button>
          <Space size={8}>
            <Typography.Text>前端显示热度</Typography.Text>
            <Switch checked={globalVisible} onChange={handleToggleGlobalVisible} />
          </Space>
        </div>
      </div>

      <Typography.Paragraph type="secondary" style={{ marginTop: 0 }}>
        {filters.subject_id
          ? '当前表格正在按所选专业视角展示导师热度，并只统计所配置届别、所选学生类型下的待处理人数。若同时指定培养类型，则会进一步按该培养类型下的申请人数和名额计算。'
          : '当前热度仅按专业视角计算。请选择专业查看对应口径下的导师热度。'}
      </Typography.Paragraph>

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
        onChange={(pager) => {
          fetchData(pager.current, pager.pageSize, keyword, filters);
        }}
      />

      <Modal
        title={editingRecord ? `编辑导师热度：${editingRecord.name}` : '编辑导师热度'}
        open={editOpen}
        onCancel={() => setEditOpen(false)}
        onOk={handleSave}
        confirmLoading={actionLoading}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="heat_display_enabled" label="该导师前端显示热度" valuePropName="checked">
            <Switch checkedChildren="显示" unCheckedChildren="隐藏" />
          </Form.Item>
          <Form.Item name="manual_heat_score" label="手动热度指数">
            <InputNumber min={0} step={0.1} precision={2} style={{ width: '100%' }} placeholder="留空则使用系统计算值" />
          </Form.Item>
          <Form.Item name="manual_heat_level" label="手动热度等级">
            <Select
              allowClear
              placeholder="留空则按热度指数自动计算"
              options={[
                { label: '低 1档', value: '低' },
                { label: '中 2档', value: '中' },
                { label: '高 3档', value: '高' },
                { label: '很高 4档', value: '很高' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="热度计算设置"
        open={settingsOpen}
        onCancel={() => setSettingsOpen(false)}
        onOk={handleSaveSettings}
        confirmLoading={actionLoading}
        destroyOnClose
      >
        <Form form={settingsForm} layout="vertical">
          <Form.Item
            name="calculation_scope"
            label="热度计算维度"
            tooltip="热度已统一固定为按当前学生专业计算。"
          >
            <Input value="按当前学生专业计算" disabled />
          </Form.Item>
          <Form.Item
            name="target_admission_year"
            label="统计届别"
            rules={[{ required: true, message: '请输入统计届别' }]}
            extra="默认按 2026 届统计，不考虑往届。明年可在这里改成 2027 届。"
          >
            <InputNumber min={2000} max={9999} precision={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="热度规则说明">
            <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
              热度只统计待处理人数。系统会同时比较“待处理人数超出可用名额的差额”和“待处理/可用名额比例”，只要满足任一档位阈值，就进入对应热度等级。
            </Typography.Paragraph>
          </Form.Item>
          <Space size={12} style={{ display: 'flex' }} align="start">
            <Form.Item
              name="medium_threshold"
              label="2级超出阈值"
              rules={[{ required: true, message: '请输入中热度阈值' }]}
              style={{ flex: 1 }}
            >
              <InputNumber min={0} step={0.1} precision={2} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item
              name="high_threshold"
              label="3级超出阈值"
              rules={[{ required: true, message: '请输入高热度阈值' }]}
              style={{ flex: 1 }}
            >
              <InputNumber min={0} step={0.1} precision={2} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item
              name="very_high_threshold"
              label="4级超出阈值"
              rules={[{ required: true, message: '请输入很高热度阈值' }]}
              style={{ flex: 1 }}
            >
              <InputNumber min={0} step={0.1} precision={2} style={{ width: '100%' }} />
            </Form.Item>
          </Space>
          <Space size={12} style={{ display: 'flex' }} align="start">
            <Form.Item
              name="medium_ratio_threshold"
              label="2级比例阈值"
              rules={[{ required: true, message: '请输入 2 级比例阈值' }]}
              style={{ flex: 1 }}
            >
              <InputNumber min={0} step={0.1} precision={2} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item
              name="high_ratio_threshold"
              label="3级比例阈值"
              rules={[{ required: true, message: '请输入 3 级比例阈值' }]}
              style={{ flex: 1 }}
            >
              <InputNumber min={0} step={0.1} precision={2} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item
              name="very_high_ratio_threshold"
              label="4级比例阈值"
              rules={[{ required: true, message: '请输入 4 级比例阈值' }]}
              style={{ flex: 1 }}
            >
              <InputNumber min={0} step={0.1} precision={2} style={{ width: '100%' }} />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </Card>
  );
}
