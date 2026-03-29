import React, { useEffect, useState } from 'react';
import { Button, Card, Input, Select, Space, Table, message } from 'antd';

import { get, post } from '../api/client';
import PageHeader from '../components/PageHeader';
import StatusTag from '../components/StatusTag';
import { confirmDanger } from '../utils/confirm';


function formatSubjectOption(item) {
  const parts = [item.subject_type_display].filter(Boolean);
  if (item.subject_code) parts.push(item.subject_code);
  return `${item.subject_name}（${parts.join(' / ')}）`;
}

export default function AlternatesPage() {
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [filters, setFilters] = useState({ subject_id: undefined, is_giveup: undefined, admission_year: undefined });
  const [sorter, setSorter] = useState({ order_by: 'alternate_rank', order_direction: 'asc' });
  const [subjects, setSubjects] = useState([]);
  const [admissionYears, setAdmissionYears] = useState([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [data, setData] = useState({ count: 0, results: [] });
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });

  const loadSubjects = async () => {
    try {
      const payload = await get('/subjects/');
      setSubjects(payload.results || payload || []);
    } catch (err) {
      message.error(err.message);
    }
  };

  const admissionYearOptions = (admissionYears || []).map((year) => ({ label: `${year}届`, value: year }));

  const fetchData = async (page = pagination.current, pageSize = pagination.pageSize, search = keyword, nextFilters = filters, nextSorter = sorter) => {
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
      const payload = await get(`/alternates/?${params.toString()}`);
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
    loadSubjects();
    fetchData(1, 10);
  }, []);

  const runAction = async (fn) => {
    setActionLoading(true);
    try {
      const payload = await fn();
      message.success(payload.detail);
      setSelectedRowKeys([]);
      await fetchData();
    } catch (err) {
      message.error(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const deleteAlternates = (ids, deleteAllFiltered = false) => {
    const params = new URLSearchParams();
    if (keyword.trim()) params.set('search', keyword.trim());
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') params.set(key, String(value));
    });
    return runAction(() => post(`/alternates/actions/batch-delete/?${params.toString()}`, { ids, delete_all_filtered: deleteAllFiltered }));
  };

  const updateFilter = (key, value) => {
    const next = { ...filters, [key]: value };
    setFilters(next);
    fetchData(1, pagination.pageSize, keyword, next, sorter);
  };

  const columns = [
    { title: '学生', dataIndex: 'name', key: 'name', sorter: true },
    { title: '考生编号', dataIndex: 'candidate_number', key: 'candidate_number', sorter: true },
    { title: '专业', key: 'subject_name', sorter: true, render: (_, record) => record.subject?.subject_name || '-' },
    { title: '届别', dataIndex: 'admission_year', key: 'admission_year', sorter: true, render: (value) => (value ? `${value}届` : '-') },
    { title: '总排名', dataIndex: 'final_rank', key: 'final_rank', sorter: true, render: (value) => value || '-' },
    { title: '候补顺位', dataIndex: 'alternate_rank', key: 'alternate_rank', sorter: true, render: (value) => value || '-' },
    {
      title: '放弃状态',
      dataIndex: 'is_giveup',
      key: 'is_giveup',
      sorter: true,
      render: (value) => <StatusTag tone={value ? 'error' : 'success'}>{value ? '已放弃' : '未放弃'}</StatusTag>,
    },
    { title: '当前导师', dataIndex: 'current_professor_name', key: 'current_professor_name', render: (value) => value || '-' },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button size="small" loading={actionLoading} onClick={() => runAction(() => post(`/students/${record.id}/promote-alternate/`, {}))}>
            取消候补
          </Button>
          <Button size="small" loading={actionLoading} onClick={() => runAction(() => post('/alternates/promote-next/', { subject_id: record.subject?.id }))} disabled={!record.subject?.id}>
            递补下一位
          </Button>
          <Button
            size="small"
            danger
            onClick={() =>
              confirmDanger({
                title: '确认删除这条候补记录吗？',
                content: `${record.name}（${record.candidate_number}）`,
                onOk: () => deleteAlternates([record.id]),
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
    <Card className="page-card" bordered={false}>
      <PageHeader items={[{ title: '招生业务' }, { title: '候补管理' }]} title="候补管理" subtitle="查看候补学生、递补顺位和递补操作，也支持清理无效候补记录。" />

      <div className="page-toolbar">
        <div className="page-filters">
          <Input.Search placeholder="按学生姓名或考生编号搜索" value={keyword} onChange={(e) => setKeyword(e.target.value)} onSearch={(value) => fetchData(1, pagination.pageSize, value)} allowClear style={{ width: 320 }} />
          <Select allowClear placeholder="按专业筛选" style={{ width: 180 }} value={filters.subject_id} options={subjects.map((item) => ({ label: formatSubjectOption(item), value: item.id }))} onChange={(value) => updateFilter('subject_id', value)} />
          <Select allowClear placeholder="按届别筛选" style={{ width: 150 }} value={filters.admission_year} options={admissionYearOptions} onChange={(value) => updateFilter('admission_year', value)} />
          <Select allowClear placeholder="按放弃状态筛选" style={{ width: 150 }} value={filters.is_giveup} options={[{ label: '已放弃', value: 'true' }, { label: '未放弃', value: 'false' }]} onChange={(value) => updateFilter('is_giveup', value)} />
        </div>
        <div className="page-actions">
          <Button onClick={() => fetchData(1, pagination.pageSize, keyword, filters, sorter)}>刷新</Button>
          <Button
            danger
            disabled={!selectedRowKeys.length}
            onClick={() =>
              confirmDanger({
                title: '确认删除选中的候补记录吗？',
                content: `共 ${selectedRowKeys.length} 条记录。`,
                onOk: () => deleteAlternates(selectedRowKeys),
              })
            }
          >
            删除选中
          </Button>
          <Button
            danger
            onClick={() =>
              confirmDanger({
                title: '确认删除当前筛选结果中的所有候补记录吗？',
                content: '这个操作会删除当前筛选条件下的全部候补记录。',
                onOk: () => deleteAlternates([], true),
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
        rowSelection={{ selectedRowKeys, onChange: setSelectedRowKeys }}
        columns={columns}
        dataSource={data.results}
        pagination={{ current: pagination.current, pageSize: pagination.pageSize, total: data.count, showSizeChanger: true }}
        onChange={(pager, _filters, tableSorter) => {
          const nextSorter = tableSorter?.field ? { order_by: tableSorter.field, order_direction: tableSorter.order === 'descend' ? 'desc' : 'asc' } : sorter;
          setSorter(nextSorter);
          fetchData(pager.current, pager.pageSize, keyword, filters, nextSorter);
        }}
      />
    </Card>
  );
}
