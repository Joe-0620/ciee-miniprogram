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

export default function ProfessorHeatPage() {
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [filters, setFilters] = useState({ department_id: undefined, heat_level: undefined });
  const [departments, setDepartments] = useState([]);
  const [data, setData] = useState({ count: 0, results: [] });
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });
  const [globalVisible, setGlobalVisible] = useState(true);
  const [editingRecord, setEditingRecord] = useState(null);
  const [editOpen, setEditOpen] = useState(false);
  const [form] = Form.useForm();

  const loadOptions = async () => {
    try {
      const [payload, settingPayload] = await Promise.all([get('/departments/'), get('/professor-heat/settings/')]);
      setDepartments(Array.isArray(payload) ? payload : []);
      setGlobalVisible(Boolean(settingPayload?.show_professor_heat));
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
        items={[{ title: '招生业务' }, { title: '导师热度分析' }]}
        title="导师热度分析"
        subtitle="根据待处理申请和当前可用名额，快速判断导师当前的竞争程度。"
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
        </div>

        <div className="page-actions">
          <Button onClick={() => fetchData(1, pagination.pageSize, keyword, filters)}>刷新</Button>
          <Space size={8}>
            <Typography.Text>前端显示热度</Typography.Text>
            <Switch checked={globalVisible} onChange={handleToggleGlobalVisible} />
          </Space>
        </div>
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
    </Card>
  );
}
