import React, { useEffect, useState } from 'react';
import { Button, Card, Descriptions, Drawer, Input, Select, Space, Table, message } from 'antd';

import { get } from '../api/client';
import PageHeader from '../components/PageHeader';
import StatusTag from '../components/StatusTag';


const levelOptions = [
  { label: '信息', value: 'info' },
  { label: '警告', value: 'warning' },
  { label: '错误', value: 'error' },
];

const statusOptions = [
  { label: '成功', value: 'success' },
  { label: '失败', value: 'failed' },
];

const moduleOptions = [
  { label: '认证登录', value: '认证登录' },
  { label: '用户管理', value: '用户管理' },
  { label: '导师管理', value: '导师管理' },
  { label: '学生管理', value: '学生管理' },
  { label: '双选记录', value: '双选记录' },
  { label: '审核记录', value: '审核记录' },
  { label: '候补管理', value: '候补管理' },
  { label: '放弃录取', value: '放弃录取' },
  { label: '专业方向', value: '专业方向' },
  { label: '导师硕士专业名额', value: '导师硕士专业名额' },
  { label: '导师博士专业名额', value: '导师博士专业名额' },
  { label: '微信账号绑定', value: '微信账号绑定' },
  { label: '认证令牌', value: '认证令牌' },
  { label: '互选时间设置', value: '互选时间设置' },
  { label: '材料访问', value: '材料访问' },
];

function formatDateTime(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', { hour12: false });
}

function JsonBlock({ data }) {
  return (
    <pre
      style={{
        margin: 0,
        padding: 16,
        background: '#0f172a',
        color: '#e2e8f0',
        borderRadius: 12,
        overflowX: 'auto',
        maxHeight: 320,
      }}
    >
      {data ? JSON.stringify(data, null, 2) : '无'}
    </pre>
  );
}

export default function AuditLogsPage() {
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [filters, setFilters] = useState({
    module: undefined,
    action: '',
    status: undefined,
    level: undefined,
    date_from: '',
    date_to: '',
  });
  const [sorter, setSorter] = useState({ order_by: 'created_at', order_direction: 'desc' });
  const [data, setData] = useState({ count: 0, results: [] });
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20 });
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState(null);

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
      const payload = await get(`/audit-logs/?${params.toString()}`);
      setData(payload);
      setPagination({ current: payload.page, pageSize: payload.page_size });
    } catch (err) {
      message.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(1, 20);
  }, []);

  const updateFilter = (key, value) => {
    const nextFilters = { ...filters, [key]: value };
    setFilters(nextFilters);
    fetchData(1, pagination.pageSize, keyword, nextFilters, sorter);
  };

  const showDetail = async (record) => {
    setDetailLoading(true);
    try {
      const payload = await get(`/audit-logs/${record.id}/`);
      setDetail(payload);
      setDetailOpen(true);
    } catch (err) {
      message.error(err.message);
    } finally {
      setDetailLoading(false);
    }
  };

  const columns = [
    {
      title: '操作时间',
      dataIndex: 'created_at',
      key: 'created_at',
      sorter: true,
      render: formatDateTime,
    },
    {
      title: '管理员',
      dataIndex: 'operator_display_name',
      key: 'operator_username',
      sorter: true,
      render: (_, record) => record.operator_display_name || record.operator_username || '-',
    },
    {
      title: '模块',
      dataIndex: 'module',
      key: 'module',
      sorter: true,
    },
    {
      title: '动作',
      dataIndex: 'action',
      key: 'action',
      sorter: true,
    },
    {
      title: '对象',
      dataIndex: 'target_display',
      key: 'target_display',
      sorter: true,
      render: (value) => value || '-',
    },
    {
      title: '结果',
      dataIndex: 'status',
      key: 'status',
      sorter: true,
      render: (_, record) => <StatusTag tone={record.status === 'success' ? 'success' : 'error'}>{record.status_display}</StatusTag>,
    },
    {
      title: '风险级别',
      dataIndex: 'level',
      key: 'level',
      sorter: true,
      render: (_, record) => {
        const tone = record.level === 'error' ? 'error' : record.level === 'warning' ? 'warning' : 'processing';
        return <StatusTag tone={tone}>{record.level_display}</StatusTag>;
      },
    },
    {
      title: 'IP 地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
      render: (value) => value || '-',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Button type="link" onClick={() => showDetail(record)}>
          查看详情
        </Button>
      ),
    },
  ];

  return (
    <Space direction="vertical" size={20} style={{ width: '100%' }}>
      <PageHeader
        items={[{ title: '账号与权限' }, { title: '操作日志' }]}
        title="操作日志"
        subtitle="记录管理员登录、退出、增删改、批量操作、材料访问等关键行为，方便追踪与回溯。"
      />
      <Card>
        <Space wrap style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space wrap>
            <Input.Search
              placeholder="搜索管理员、对象、说明、请求路径"
              allowClear
              style={{ width: 260 }}
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
              onSearch={(value) => {
                setKeyword(value);
                fetchData(1, pagination.pageSize, value, filters, sorter);
              }}
            />
            <Select allowClear placeholder="按模块筛选" style={{ width: 180 }} value={filters.module} options={moduleOptions} onChange={(value) => updateFilter('module', value)} />
            <Input allowClear placeholder="按动作筛选，如 student.update" style={{ width: 220 }} value={filters.action} onChange={(event) => updateFilter('action', event.target.value)} />
            <Select allowClear placeholder="按结果筛选" style={{ width: 140 }} value={filters.status} options={statusOptions} onChange={(value) => updateFilter('status', value)} />
            <Select allowClear placeholder="按风险级别筛选" style={{ width: 160 }} value={filters.level} options={levelOptions} onChange={(value) => updateFilter('level', value)} />
            <Input type="date" style={{ width: 150 }} value={filters.date_from} onChange={(event) => updateFilter('date_from', event.target.value)} />
            <Input type="date" style={{ width: 150 }} value={filters.date_to} onChange={(event) => updateFilter('date_to', event.target.value)} />
          </Space>
          <Button
            onClick={() => {
              const nextFilters = { module: undefined, action: '', status: undefined, level: undefined, date_from: '', date_to: '' };
              setKeyword('');
              setFilters(nextFilters);
              fetchData(1, pagination.pageSize, '', nextFilters, sorter);
            }}
          >
            清空筛选
          </Button>
        </Space>
      </Card>
      <Card>
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
            showTotal: (total) => `共 ${total} 条`,
          }}
          onChange={(pager, _, tableSorter) => {
            const nextSorter = tableSorter.order
              ? {
                  order_by: tableSorter.field || 'created_at',
                  order_direction: tableSorter.order === 'descend' ? 'desc' : 'asc',
                }
              : sorter;
            setSorter(nextSorter);
            fetchData(pager.current, pager.pageSize, keyword, filters, nextSorter);
          }}
        />
      </Card>
      <Drawer title="操作日志详情" placement="right" width={760} open={detailOpen} onClose={() => setDetailOpen(false)} destroyOnClose>
        {detailLoading || !detail ? null : (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Card>
              <Descriptions column={2} bordered size="small">
                <Descriptions.Item label="操作时间">{formatDateTime(detail.created_at)}</Descriptions.Item>
                <Descriptions.Item label="管理员">{detail.operator_display_name || detail.operator_username || '-'}</Descriptions.Item>
                <Descriptions.Item label="模块">{detail.module}</Descriptions.Item>
                <Descriptions.Item label="动作">{detail.action}</Descriptions.Item>
                <Descriptions.Item label="执行结果">
                  <StatusTag tone={detail.status === 'success' ? 'success' : 'error'}>{detail.status_display}</StatusTag>
                </Descriptions.Item>
                <Descriptions.Item label="风险级别">
                  <StatusTag tone={detail.level === 'error' ? 'error' : detail.level === 'warning' ? 'warning' : 'processing'}>
                    {detail.level_display}
                  </StatusTag>
                </Descriptions.Item>
                <Descriptions.Item label="操作对象">{detail.target_display || '-'}</Descriptions.Item>
                <Descriptions.Item label="对象类型">{detail.target_type || '-'}</Descriptions.Item>
                <Descriptions.Item label="对象 ID">{detail.target_id || '-'}</Descriptions.Item>
                <Descriptions.Item label="IP 地址">{detail.ip_address || '-'}</Descriptions.Item>
                <Descriptions.Item label="请求方法">{detail.request_method || '-'}</Descriptions.Item>
                <Descriptions.Item label="请求路径">{detail.request_path || '-'}</Descriptions.Item>
                <Descriptions.Item label="说明" span={2}>{detail.detail || '-'}</Descriptions.Item>
                <Descriptions.Item label="客户端信息" span={2}>{detail.user_agent || '-'}</Descriptions.Item>
              </Descriptions>
            </Card>
            <Card title="变更前数据">
              <JsonBlock data={detail.before_data} />
            </Card>
            <Card title="变更后数据">
              <JsonBlock data={detail.after_data} />
            </Card>
          </Space>
        )}
      </Drawer>
    </Space>
  );
}
