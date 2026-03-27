import React, { useEffect, useState } from 'react';
import { Button, Card, Descriptions, Drawer, Input, Select, Space, Table, message } from 'antd';

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

const statusMap = {
  1: { tone: 'success', text: '已通过' },
  2: { tone: 'error', text: '已驳回' },
  3: { tone: 'processing', text: '待审核' },
};

export default function ReviewsPage() {
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [filters, setFilters] = useState({ status: undefined, subject_id: undefined });
  const [sorter, setSorter] = useState({ order_by: 'submit_time', order_direction: 'desc' });
  const [subjects, setSubjects] = useState([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detail, setDetail] = useState(null);
  const [data, setData] = useState({ count: 0, results: [] });
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });

  const loadOptions = async () => {
    try {
      const payload = await get('/subjects/');
      setSubjects(payload.results || payload || []);
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
      const payload = await get(`/review-records/?${params.toString()}`);
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
    fetchData(1, 10);
  }, []);

  const showDetail = async (record) => {
    setDetailLoading(true);
    try {
      const payload = await get(`/review-records/${record.id}/`);
      setDetail(payload);
      setDrawerOpen(true);
    } catch (err) {
      message.error(err.message);
    } finally {
      setDetailLoading(false);
    }
  };

  const batchApprove = async () => {
    setActionLoading(true);
    try {
      const payload = await post('/review-records/actions/batch-approve/', { ids: selectedRowKeys });
      message.success(payload.detail);
      setSelectedRowKeys([]);
      await fetchData();
    } catch (err) {
      message.error(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const deleteReviews = (ids, deleteAllFiltered = false) => {
    const params = new URLSearchParams();
    if (keyword.trim()) params.set('search', keyword.trim());
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') params.set(key, String(value));
    });
    return runAction(() => post(`/review-records/actions/batch-delete/?${params.toString()}`, { ids, delete_all_filtered: deleteAllFiltered }));
  };

  const updateFilter = (key, value) => {
    const next = { ...filters, [key]: value };
    setFilters(next);
    fetchData(1, pagination.pageSize, keyword, next, sorter);
  };

  const columns = [
    { title: '学生', dataIndex: 'student_name', key: 'student_name', sorter: true },
    { title: '考生编号', dataIndex: 'candidate_number', key: 'candidate_number', sorter: true },
    { title: '导师', dataIndex: 'professor_name', key: 'professor_name', sorter: true },
    { title: '审核人', dataIndex: 'reviewer_name', key: 'reviewer_name', sorter: true, render: (value) => value || '-' },
    { title: '专业', dataIndex: 'subject_name', key: 'subject_name', sorter: true },
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
    { title: '提交时间', dataIndex: 'submit_time', key: 'submit_time', sorter: true, render: (value) => (value ? new Date(value).toLocaleString() : '-') },
    { title: '审核时间', dataIndex: 'review_time', key: 'review_time', sorter: true, render: (value) => (value ? new Date(value).toLocaleString() : '-') },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button size="small" onClick={() => showDetail(record)} loading={detailLoading && detail?.id === record.id}>
            查看详情
          </Button>
          <Button size="small" onClick={() => openFileById(record.file_id)} disabled={!record.file_id}>
            查看材料
          </Button>
          <Button
            size="small"
            danger
            onClick={() =>
              confirmDanger({
                title: '确认删除这条审核记录吗？',
                content: `${record.student_name} - ${record.professor_name}`,
                onOk: () => deleteReviews([record.id]),
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
          items={[{ title: '招生业务' }, { title: '审核记录' }]}
          title="审核记录"
          subtitle="查看意向表提交、审核人处理和材料详情，适合集中推进待审核记录。"
        />

        <div className="page-toolbar">
          <div className="page-filters">
            <Input.Search
              placeholder="按学生、考生编号或导师搜索"
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
              placeholder="按专业筛选"
              style={{ width: 180 }}
              value={filters.subject_id}
              options={subjects.map((item) => ({ label: formatSubjectOption(item), value: item.id }))}
              onChange={(value) => updateFilter('subject_id', value)}
            />
          </div>

          <div className="page-actions">
            <Button onClick={() => fetchData(1, pagination.pageSize, keyword, filters, sorter)}>刷新</Button>
            <Button type="primary" loading={actionLoading} disabled={!selectedRowKeys.length} onClick={batchApprove}>
              批量通过
            </Button>
            <Button
              danger
              disabled={!selectedRowKeys.length}
              onClick={() =>
                confirmDanger({
                  title: '确认删除选中的审核记录吗？',
                  content: `共 ${selectedRowKeys.length} 条记录。`,
                  onOk: () => deleteReviews(selectedRowKeys),
                })
              }
            >
              删除选中
            </Button>
            <Button
              danger
              onClick={() =>
                confirmDanger({
                  title: '确认删除当前筛选结果中的所有审核记录吗？',
                  content: '这个操作会删除当前筛选条件下的全部审核记录。',
                  onOk: () => deleteReviews([], true),
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
            const nextSorter = tableSorter?.field
              ? { order_by: tableSorter.field, order_direction: tableSorter.order === 'descend' ? 'desc' : 'asc' }
              : sorter;
            setSorter(nextSorter);
            fetchData(pager.current, pager.pageSize, keyword, filters, nextSorter);
          }}
        />
      </Card>

      <Drawer title="审核记录详情" width={760} open={drawerOpen} onClose={() => setDrawerOpen(false)} destroyOnClose>
        {detail ? (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Descriptions title="审核信息" column={2} bordered size="small">
              <Descriptions.Item label="记录 ID">{detail.id}</Descriptions.Item>
              <Descriptions.Item label="审核人">{detail.reviewer_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <StatusTag tone={(statusMap[detail.status] || { tone: 'default' }).tone}>
                  {(statusMap[detail.status] || { text: '未知' }).text}
                </StatusTag>
              </Descriptions.Item>
              <Descriptions.Item label="提交时间">{detail.submit_time ? new Date(detail.submit_time).toLocaleString() : '-'}</Descriptions.Item>
              <Descriptions.Item label="审核时间">{detail.review_time ? new Date(detail.review_time).toLocaleString() : '-'}</Descriptions.Item>
              <Descriptions.Item label="审核材料">
                <Button size="small" onClick={() => openFileById(detail.file_id)} disabled={!detail.file_id}>
                  查看材料
                </Button>
              </Descriptions.Item>
            </Descriptions>
            <Descriptions title="学生信息" column={2} bordered size="small">
              <Descriptions.Item label="姓名">{detail.student?.name || '-'}</Descriptions.Item>
              <Descriptions.Item label="考生编号">{detail.student?.candidate_number || '-'}</Descriptions.Item>
              <Descriptions.Item label="专业">{detail.student?.subject?.subject_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="手机号">{detail.student?.phone_number || '-'}</Descriptions.Item>
            </Descriptions>
            <Descriptions title="导师信息" column={2} bordered size="small">
              <Descriptions.Item label="姓名">{detail.professor?.name || '-'}</Descriptions.Item>
              <Descriptions.Item label="工号">{detail.professor?.teacher_identity_id || '-'}</Descriptions.Item>
              <Descriptions.Item label="方向">{detail.professor?.department?.department_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="联系电话">{detail.professor?.phone_number || '-'}</Descriptions.Item>
            </Descriptions>
          </Space>
        ) : null}
      </Drawer>
    </>
  );
}
