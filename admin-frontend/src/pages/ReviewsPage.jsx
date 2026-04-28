import React, { useEffect, useState } from 'react';
import { Button, Card, Descriptions, Divider, Drawer, Input, Select, Space, Table, Tag, message } from 'antd';

import { get, post } from '../api/client';
import PageHeader from '../components/PageHeader';
import PdfPreviewModal from '../components/PdfPreviewModal';
import StatusTag from '../components/StatusTag';
import { confirmDanger } from '../utils/confirm';
import { loadPageState, savePageState } from '../utils/pageState';


function formatSubjectOption(item) {
  const parts = [item.subject_type_display].filter(Boolean);
  if (item.subject_code) parts.push(item.subject_code);
  return `${item.subject_name}（${parts.join(' / ')}）`;
}

const statusMap = {
  1: { tone: 'success', text: '已通过' },
  2: { tone: 'error', text: '已驳回' },
  3: { tone: 'processing', text: '待审核' },
  4: { tone: 'warning', text: '已撤销' },
};

export default function ReviewsPage() {
  const initialPageState = loadPageState('reviews-page', {
    keyword: '',
    filters: { status: undefined, subject_id: undefined, admission_year: undefined, reviewer_id: undefined },
    sorter: { order_by: 'submit_time', order_direction: 'desc' },
    pagination: { current: 1, pageSize: 10 },
  });
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [keyword, setKeyword] = useState(initialPageState.keyword);
  const [filters, setFilters] = useState(initialPageState.filters);
  const [sorter, setSorter] = useState(initialPageState.sorter);
  const [subjects, setSubjects] = useState([]);
  const [admissionYears, setAdmissionYears] = useState([]);
  const [reviewers, setReviewers] = useState([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detail, setDetail] = useState(null);
  const [reviewerDrawerOpen, setReviewerDrawerOpen] = useState(false);
  const [reviewerStatsLoading, setReviewerStatsLoading] = useState(false);
  const [reviewerStats, setReviewerStats] = useState(null);
  const [previewState, setPreviewState] = useState({ open: false, title: '', fileId: '' });
  const [data, setData] = useState({ count: 0, results: [] });
  const [pagination, setPagination] = useState(initialPageState.pagination);

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
      setAdmissionYears(payload.available_admission_years || []);
      setReviewers(payload.available_reviewers || []);
      setPagination({ current: payload.page, pageSize: payload.page_size });
    } catch (err) {
      message.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOptions();
    fetchData(
      initialPageState.pagination.current,
      initialPageState.pagination.pageSize,
      initialPageState.keyword,
      initialPageState.filters,
      initialPageState.sorter,
    );
  }, []);

  useEffect(() => {
    savePageState('reviews-page', { keyword, filters, sorter, pagination });
  }, [keyword, filters, sorter, pagination]);

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

  const openPreview = (fileId, title) => {
    setPreviewState({
      open: true,
      title: title || '材料预览',
      fileId: fileId || '',
    });
  };

  const showReviewerStats = async (reviewerId, reviewerName, syncFilter = false) => {
    if (!reviewerId) return;
    if (syncFilter) {
      const nextFilters = { ...filters, reviewer_id: reviewerId };
      setFilters(nextFilters);
      fetchData(1, pagination.pageSize, keyword, nextFilters, sorter);
    }
    setReviewerStatsLoading(true);
    try {
      const payload = await get(`/review-records/reviewer-stats/${reviewerId}/`);
      setReviewerStats(payload);
      setReviewerDrawerOpen(true);
    } catch (err) {
      message.error(err.message || `无法加载审核人 ${reviewerName || ''} 的统计信息`);
    } finally {
      setReviewerStatsLoading(false);
    }
  };

  const columns = [
    { title: '学生', dataIndex: 'student_name', key: 'student_name', sorter: true, width: 120, ellipsis: true, fixed: 'left' },
    { title: '考生编号', dataIndex: 'candidate_number', key: 'candidate_number', sorter: true, width: 150, ellipsis: true, fixed: 'left' },
    { title: '届别', dataIndex: 'admission_year', key: 'admission_year', sorter: true, width: 90, render: (value) => (value ? `${value}届` : '-') },
    { title: '导师', dataIndex: 'professor_name', key: 'professor_name', sorter: true, width: 120, ellipsis: true },
    {
      title: '审核人',
      dataIndex: 'reviewer_name',
      key: 'reviewer_name',
      sorter: true,
      width: 140,
      ellipsis: true,
      responsive: ['lg'],
      render: (value, record) =>
        record.reviewer_id ? (
          <Button type="link" size="small" style={{ paddingInline: 0 }} onClick={() => showReviewerStats(record.reviewer_id, value, true)}>
            {value || '-'}
          </Button>
        ) : (
          value || '-'
        ),
    },
    { title: '专业', dataIndex: 'subject_name', key: 'subject_name', sorter: true, width: 180, ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      sorter: true,
      width: 110,
      render: (value) => {
        const config = statusMap[value] || { tone: 'default', text: '未知' };
        return <StatusTag tone={config.tone}>{config.text}</StatusTag>;
      },
    },
    { title: '提交时间', dataIndex: 'submit_time', key: 'submit_time', sorter: true, width: 170, responsive: ['xl'], render: (value) => (value ? new Date(value).toLocaleString() : '-') },
    { title: '审核时间', dataIndex: 'review_time', key: 'review_time', sorter: true, width: 170, responsive: ['xxl'], render: (value) => (value ? new Date(value).toLocaleString() : '-') },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space wrap className="compact-action-buttons">
          <Button size="small" onClick={() => showDetail(record)} loading={detailLoading && detail?.id === record.id}>
            查看详情
          </Button>
          <Button
            size="small"
            onClick={() => openPreview(record.file_id, `${record.student_name} - 审核材料`)}
            disabled={!record.file_id}
          >
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
            <Select
              allowClear
              placeholder="按届别筛选"
              style={{ width: 160 }}
              value={filters.admission_year}
              options={admissionYears.map((year) => ({ label: `${year}届`, value: year }))}
              onChange={(value) => updateFilter('admission_year', value)}
            />
            <Select
              allowClear
              placeholder="按审核人筛选"
              style={{ width: 180 }}
              value={filters.reviewer_id}
              options={reviewers}
              onChange={(value) => updateFilter('reviewer_id', value)}
            />
          </div>

          <div className="page-actions">
            <Button onClick={() => fetchData(1, pagination.pageSize, keyword, filters, sorter)}>刷新</Button>
            <Button
              disabled={!filters.reviewer_id}
              onClick={() => {
                const nextFilters = { ...filters, reviewer_id: undefined };
                setFilters(nextFilters);
                fetchData(1, pagination.pageSize, keyword, nextFilters, sorter);
              }}
            >
              清除审核人筛选
            </Button>
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
          className="dashboard-table"
          rowKey="id"
          loading={loading}
          rowSelection={{ selectedRowKeys, onChange: setSelectedRowKeys }}
          columns={columns}
          dataSource={data.results}
          scroll={{ x: 1350 }}
          sticky={{ offsetHeader: 64, offsetScroll: 12 }}
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
                <Button
                  size="small"
                  onClick={() => openPreview(detail.file_id, `${detail.student?.name || detail.student_name || '学生'} - 审核材料`)}
                  disabled={!detail.file_id}
                >
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

      <Drawer
        title={reviewerStats ? `${reviewerStats.reviewer_name} 的审核概览` : '审核人概览'}
        width={520}
        open={reviewerDrawerOpen}
        onClose={() => setReviewerDrawerOpen(false)}
        destroyOnClose
      >
        {reviewerStats ? (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Descriptions title="基础统计" column={2} bordered size="small">
              <Descriptions.Item label="审核人">{reviewerStats.reviewer_name}</Descriptions.Item>
              <Descriptions.Item label="总审核数">{reviewerStats.total_count}</Descriptions.Item>
              <Descriptions.Item label="待审核">
                <StatusTag tone="processing">{reviewerStats.pending_count}</StatusTag>
              </Descriptions.Item>
              <Descriptions.Item label="已通过">
                <StatusTag tone="success">{reviewerStats.approved_count}</StatusTag>
              </Descriptions.Item>
              <Descriptions.Item label="已驳回">
                <StatusTag tone="error">{reviewerStats.rejected_count}</StatusTag>
              </Descriptions.Item>
              <Descriptions.Item label="已撤销">
                <StatusTag tone="default">{reviewerStats.revoked_count}</StatusTag>
              </Descriptions.Item>
              <Descriptions.Item label="最近提交时间">
                {reviewerStats.latest_submit_time ? new Date(reviewerStats.latest_submit_time).toLocaleString() : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="最近审核时间">
                {reviewerStats.latest_review_time ? new Date(reviewerStats.latest_review_time).toLocaleString() : '-'}
              </Descriptions.Item>
            </Descriptions>

            <div>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>按届别分布</div>
              <Space wrap>
                {reviewerStats.admission_year_summary?.length ? (
                  reviewerStats.admission_year_summary.map((item) => (
                    <Tag key={item.admission_year} color="blue">{`${item.admission_year}届 · ${item.count}`}</Tag>
                  ))
                ) : (
                  <Tag>暂无数据</Tag>
                )}
              </Space>
            </div>

            <Divider style={{ margin: '4px 0' }} />

            <div>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>按学生类型分布</div>
              <Space wrap>
                {reviewerStats.student_type_summary?.length ? (
                  reviewerStats.student_type_summary.map((item) => (
                    <Tag key={item.student_type} color="purple">{`${item.student_type_display} · ${item.count}`}</Tag>
                  ))
                ) : (
                  <Tag>暂无数据</Tag>
                )}
              </Space>
            </div>

            <Button
              type="primary"
              onClick={() => {
                const nextFilters = { ...filters, reviewer_id: reviewerStats.reviewer_id };
                setFilters(nextFilters);
                fetchData(1, pagination.pageSize, keyword, nextFilters, sorter);
                setReviewerDrawerOpen(false);
              }}
            >
              在表格中查看该审核人全部记录
            </Button>
          </Space>
        ) : null}
      </Drawer>

      <PdfPreviewModal
        open={previewState.open}
        title={previewState.title}
        fileId={previewState.fileId}
        onClose={() => setPreviewState({ open: false, title: '', fileId: '' })}
      />
    </>
  );
}
