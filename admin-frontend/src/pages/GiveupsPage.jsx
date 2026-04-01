import React, { useEffect, useState } from 'react';
import { Button, Card, Input, Select, Space, Table, message } from 'antd';

import { get, post } from '../api/client';
import PageHeader from '../components/PageHeader';
import StatusTag from '../components/StatusTag';
import { openFileById } from '../utils/files';
import { confirmDanger } from '../utils/confirm';


function formatSubjectOption(item) {
  const parts = [item.subject_type_display].filter(Boolean);
  if (item.subject_code) parts.push(item.subject_code);
  return `${item.subject_name}（${parts.join(' / ')}）`;
}

export default function GiveupsPage() {
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [filters, setFilters] = useState({ subject_id: undefined, admission_year: undefined, is_selected: undefined });
  const [sorter, setSorter] = useState({ order_by: 'id', order_direction: 'desc' });
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
      const payload = await get(`/giveups/?${params.toString()}`);
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

  const revokeGiveup = (id) => runAction(() => post(`/students/${id}/revoke-giveup/`, {}));

  const deleteGiveups = (ids, deleteAllFiltered = false) => {
    const params = new URLSearchParams();
    if (keyword.trim()) params.set('search', keyword.trim());
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') params.set(key, String(value));
    });
    return runAction(() => post(`/giveups/actions/batch-delete/?${params.toString()}`, { ids, delete_all_filtered: deleteAllFiltered }));
  };

  const updateFilter = (key, value) => {
    const next = { ...filters, [key]: value };
    setFilters(next);
    fetchData(1, pagination.pageSize, keyword, next, sorter);
  };

  const columns = [
    { title: '学生', dataIndex: 'name', key: 'name', sorter: true, width: 120, ellipsis: true, fixed: 'left' },
    { title: '考生编号', dataIndex: 'candidate_number', key: 'candidate_number', sorter: true, width: 150, ellipsis: true, fixed: 'left' },
    { title: '届别', dataIndex: 'admission_year', key: 'admission_year', sorter: true, width: 90, render: (value) => (value ? `${value}届` : '-') },
    { title: '专业', key: 'subject_name', sorter: true, width: 180, ellipsis: true, render: (_, record) => record.subject?.subject_name || '-' },
    { title: '总排名', dataIndex: 'final_rank', key: 'final_rank', sorter: true, width: 90, render: (value) => value || '-' },
    {
      title: '放弃说明表',
      dataIndex: 'giveup_signature_table',
      key: 'giveup_signature_table',
      width: 110,
      render: (value) => <StatusTag tone={value ? 'success' : 'default'}>{value ? '已生成' : '未生成'}</StatusTag>,
    },
    {
      title: '是否签名',
      dataIndex: 'is_signate_giveup_table',
      key: 'is_signate_giveup_table',
      width: 110,
      responsive: ['lg'],
      render: (value) => <StatusTag tone={value ? 'success' : 'warning'}>{value ? '已签名' : '未签名'}</StatusTag>,
    },
    {
      title: '放弃前是否录取',
      dataIndex: 'is_selected',
      key: 'is_selected',
      sorter: true,
      width: 120,
      responsive: ['lg'],
      render: (value) => <StatusTag tone={value ? 'processing' : 'default'}>{value ? '是' : '否'}</StatusTag>,
    },
    { title: '当前导师', dataIndex: 'current_professor_name', key: 'current_professor_name', width: 140, ellipsis: true, responsive: ['xl'], render: (value) => value || '-' },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space wrap className="compact-action-buttons">
          <Button size="small" onClick={() => openFileById(record.giveup_signature_table)} disabled={!record.giveup_signature_table}>
            查看材料
          </Button>
          <Button size="small" loading={actionLoading} onClick={() => revokeGiveup(record.id)}>
            撤销放弃
          </Button>
          <Button
            size="small"
            danger
            onClick={() =>
              confirmDanger({
                title: '确认删除这条放弃录取记录吗？',
                content: `${record.name}（${record.candidate_number}）`,
                onOk: () => deleteGiveups([record.id]),
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
      <PageHeader items={[{ title: '招生业务' }, { title: '放弃录取' }]} title="放弃录取" subtitle="查看放弃说明表、签名状态与撤销操作，也支持清理无效记录。" />

      <div className="page-toolbar">
        <div className="page-filters">
          <Input.Search placeholder="按学生姓名或考生编号搜索" value={keyword} onChange={(e) => setKeyword(e.target.value)} onSearch={(value) => fetchData(1, pagination.pageSize, value)} allowClear style={{ width: 320 }} />
          <Select allowClear placeholder="按专业筛选" style={{ width: 180 }} value={filters.subject_id} options={subjects.map((item) => ({ label: formatSubjectOption(item), value: item.id }))} onChange={(value) => updateFilter('subject_id', value)} />
          <Select allowClear placeholder="按届别筛选" style={{ width: 150 }} value={filters.admission_year} options={admissionYears.map((year) => ({ label: `${year}届`, value: year }))} onChange={(value) => updateFilter('admission_year', value)} />
          <Select allowClear placeholder="按录取状态筛选" style={{ width: 170 }} value={filters.is_selected} options={[{ label: '放弃前已录取', value: 'true' }, { label: '放弃前未录取', value: 'false' }]} onChange={(value) => updateFilter('is_selected', value)} />
        </div>
        <div className="page-actions">
          <Button onClick={() => fetchData(1, pagination.pageSize, keyword, filters, sorter)}>刷新</Button>
          <Button
            danger
            disabled={!selectedRowKeys.length}
            onClick={() =>
              confirmDanger({
                title: '确认删除选中的放弃录取记录吗？',
                content: `共 ${selectedRowKeys.length} 条记录。`,
                onOk: () => deleteGiveups(selectedRowKeys),
              })
            }
          >
            删除选中
          </Button>
          <Button
            danger
            onClick={() =>
              confirmDanger({
                title: '确认删除当前筛选结果中的所有放弃录取记录吗？',
                content: '这个操作会删除当前筛选条件下的全部放弃录取记录。',
                onOk: () => deleteGiveups([], true),
              })
            }
          >
            删除当前筛选结果
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
        scroll={{ x: 1300 }}
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
