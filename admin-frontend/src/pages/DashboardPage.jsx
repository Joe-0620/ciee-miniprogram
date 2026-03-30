import React, { useEffect, useMemo, useState } from 'react';
import { Card, Col, Progress, Row, Select, Skeleton, Space, Table, Typography, message } from 'antd';

import { get } from '../api/client';
import PageHeader from '../components/PageHeader';
import StatusTag from '../components/StatusTag';


const statCards = [
  ['professor_count', '导师总数'],
  ['student_count', '学生总数'],
  ['pending_choice_count', '待处理申请'],
  ['accepted_choice_count', '已录取双选'],
  ['pending_review_count', '待审核意向表'],
  ['approved_review_count', '已通过审核'],
  ['alternate_student_count', '候补学生'],
  ['giveup_student_count', '放弃录取'],
];

const reviewToneMap = {
  待审核: 'processing',
  已通过: 'success',
  已驳回: 'error',
};

const studentToneMap = {
  已录取: 'success',
  候补中: 'warning',
  已放弃: 'error',
  未完成: 'default',
};

function DistributionCard({ title, subtitle, items, toneMap }) {
  const total = items.reduce((sum, item) => sum + (item.value || 0), 0) || 1;

  return (
    <Card className="page-card dashboard-section-card" bordered={false}>
      <Typography.Title level={4}>{title}</Typography.Title>
      <Typography.Paragraph type="secondary">{subtitle}</Typography.Paragraph>
      <div className="dashboard-distribution-list">
        {items.map((item) => {
          const percent = Math.round(((item.value || 0) / total) * 100);
          return (
            <div key={item.label} className="dashboard-distribution-item">
              <div className="dashboard-distribution-row">
                <StatusTag tone={toneMap[item.label] || 'default'}>{item.label}</StatusTag>
                <span>{item.value || 0} 人</span>
              </div>
              <Progress percent={percent} showInfo={false} strokeColor="#0f766e" trailColor="#e2e8f0" />
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function MiniBarTrend({ title, subtitle, items, color }) {
  const maxValue = Math.max(...items.map((item) => item.value || 0), 1);

  return (
    <Card className="page-card dashboard-section-card" bordered={false}>
      <Typography.Title level={4}>{title}</Typography.Title>
      <Typography.Paragraph type="secondary">{subtitle}</Typography.Paragraph>
      <div className="dashboard-trend-chart">
        {items.map((item) => {
          const height = Math.max(16, Math.round(((item.value || 0) / maxValue) * 180));
          return (
            <div key={item.date} className="dashboard-trend-item">
              <span className="dashboard-trend-value">{item.value || 0}</span>
              <div className="dashboard-trend-bar-wrap">
                <div className="dashboard-trend-bar" style={{ height, background: color }} />
              </div>
              <span className="dashboard-trend-label">{item.label}</span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [filters, setFilters] = useState({ admission_year: 2026, student_type: 2 });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams({
      admission_year: String(filters.admission_year),
      student_type: String(filters.student_type),
    });
    get(`/dashboard/stats/?${params.toString()}`)
      .then(setStats)
      .catch((err) => message.error(err.message))
      .finally(() => setLoading(false));
  }, [filters]);

  const doctorQuotaRows = useMemo(
    () =>
      (stats?.subject_quota || []).map((item) => ({
        key: item.subject_id,
        ...item,
        usage_percent: item.total_quota ? Math.round((item.selected_count / item.total_quota) * 100) : 0,
      })),
    [stats],
  );

  const departmentUsageRows = useMemo(
    () =>
      (stats?.department_usage || []).map((item) => ({
        key: item.department_id,
        ...item,
        master_usage_percent: item.master_total ? Math.round((item.master_used / item.master_total) * 100) : 0,
        doctor_usage_percent: item.doctor_total ? Math.round((item.doctor_used / item.doctor_total) * 100) : 0,
      })),
    [stats],
  );

  const topPendingProfessorRows = useMemo(
    () => (stats?.top_pending_professors || []).map((item) => ({ key: item.professor_id, ...item })),
    [stats],
  );

  const lowQuotaProfessorRows = useMemo(
    () => (stats?.low_quota_professors || []).map((item) => ({ key: item.professor_id, ...item })),
    [stats],
  );
  const studentChoiceBehaviorRows = useMemo(
    () => (stats?.student_choice_behavior_top || []).map((item) => ({ key: item.id, ...item })),
    [stats],
  );

  const doctorColumns = [
    { title: '博士专业', dataIndex: 'subject_name', key: 'subject_name' },
    { title: '代码', dataIndex: 'subject_code', key: 'subject_code' },
    { title: '总名额', dataIndex: 'total_quota', key: 'total_quota' },
    { title: '已录取', dataIndex: 'selected_count', key: 'selected_count' },
    { title: '剩余名额', dataIndex: 'remaining_quota', key: 'remaining_quota' },
    { title: '候补人数', dataIndex: 'alternate_count', key: 'alternate_count' },
    {
      title: '使用率',
      dataIndex: 'usage_percent',
      key: 'usage_percent',
      render: (value) => <Progress percent={value} size="small" strokeColor={value >= 80 ? '#dc2626' : '#0f766e'} />,
    },
  ];

  const departmentColumns = [
    { title: '方向', dataIndex: 'department_name', key: 'department_name' },
    { title: '硕士总名额', dataIndex: 'master_total', key: 'master_total' },
    { title: '硕士已用', dataIndex: 'master_used', key: 'master_used' },
    { title: '硕士剩余', dataIndex: 'master_remaining', key: 'master_remaining' },
    {
      title: '硕士使用率',
      dataIndex: 'master_usage_percent',
      key: 'master_usage_percent',
      render: (value) => <Progress percent={value} size="small" strokeColor="#2563eb" />,
    },
    { title: '博士总名额', dataIndex: 'doctor_total', key: 'doctor_total' },
    { title: '博士已用', dataIndex: 'doctor_used', key: 'doctor_used' },
    { title: '博士剩余', dataIndex: 'doctor_remaining', key: 'doctor_remaining' },
    {
      title: '博士使用率',
      dataIndex: 'doctor_usage_percent',
      key: 'doctor_usage_percent',
      render: (value) => <Progress percent={value} size="small" strokeColor="#7c3aed" />,
    },
  ];

  const topPendingProfessorColumns = [
    { title: '导师', dataIndex: 'professor_name', key: 'professor_name' },
    { title: '工号', dataIndex: 'teacher_identity_id', key: 'teacher_identity_id' },
    { title: '方向', dataIndex: 'department_name', key: 'department_name' },
    { title: '待处理申请', dataIndex: 'pending_count', key: 'pending_count' },
    { title: '已录取人数', dataIndex: 'accepted_count', key: 'accepted_count' },
    {
      title: '剩余名额',
      dataIndex: 'remaining_quota',
      key: 'remaining_quota',
      render: (value) => <StatusTag tone={value <= 1 ? 'error' : value <= 3 ? 'warning' : 'success'}>{value}</StatusTag>,
    },
  ];

  const lowQuotaProfessorColumns = [
    { title: '导师', dataIndex: 'professor_name', key: 'professor_name' },
    { title: '工号', dataIndex: 'teacher_identity_id', key: 'teacher_identity_id' },
    { title: '方向', dataIndex: 'department_name', key: 'department_name' },
    {
      title: '剩余名额',
      dataIndex: 'remaining_quota',
      key: 'remaining_quota',
      render: (value) => <StatusTag tone={value <= 1 ? 'error' : value <= 3 ? 'warning' : 'success'}>{value}</StatusTag>,
    },
    {
      title: '开放选择',
      dataIndex: 'proposed_quota_approved',
      key: 'proposed_quota_approved',
      render: (value) => <StatusTag tone={value ? 'processing' : 'default'}>{value ? '已开放' : '未开放'}</StatusTag>,
    },
  ];

  const studentChoiceBehaviorColumns = [
    { title: '学生姓名', dataIndex: 'name', key: 'name' },
    { title: '考生编号', dataIndex: 'candidate_number', key: 'candidate_number' },
    { title: '专业', dataIndex: 'subject_name', key: 'subject_name', render: (value) => value || '-' },
    { title: '学生类型', dataIndex: 'student_type_display', key: 'student_type_display', render: (value) => value || '-' },
    { title: '取消次数', dataIndex: 'cancel_count', key: 'cancel_count' },
    { title: '选过导师数', dataIndex: 'distinct_professor_count', key: 'distinct_professor_count' },
  ];

  if (!stats || loading) {
    return (
      <Card className="page-card" bordered={false}>
        <Skeleton active paragraph={{ rows: 12 }} />
      </Card>
    );
  }

  return (
    <div className="dashboard-page">
      <Card className="page-card dashboard-hero-card" bordered={false}>
        <PageHeader
          items={[{ title: '总览' }, { title: '仪表盘' }]}
          title="仪表盘"
          subtitle="集中查看招生双选、审核、名额和候补的整体态势，帮助管理员快速判断当前工作的优先级。"
        />
        <Space wrap style={{ marginBottom: 20 }}>
          <Select
            style={{ width: 160 }}
            value={filters.admission_year}
            options={(stats?.available_admission_years || []).map((year) => ({ label: `${year}届`, value: year }))}
            onChange={(value) => setFilters((prev) => ({ ...prev, admission_year: value }))}
          />
          <Select
            style={{ width: 180 }}
            value={filters.student_type}
            options={stats?.student_type_options || []}
            onChange={(value) => setFilters((prev) => ({ ...prev, student_type: value }))}
          />
        </Space>
        <div className="stat-grid">
          {statCards.map(([key, label]) => (
            <div key={key} className="stat-card">
              <div className="stat-label">{label}</div>
              <div className="stat-value">{stats[key] ?? 0}</div>
            </div>
          ))}
        </div>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={12}>
          <DistributionCard title="审核状态分布" subtitle="快速识别当前审核积压和通过、驳回的占比。" items={stats.review_distribution || []} toneMap={reviewToneMap} />
        </Col>
        <Col xs={24} xl={12}>
          <DistributionCard title="学生状态分布" subtitle="查看已录取、候补、放弃和未完成的整体结构。" items={stats.student_status_distribution || []} toneMap={studentToneMap} />
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <MiniBarTrend title="最近一周双选提交数" subtitle="观察近 7 天学生提交导师申请的节奏变化。" items={stats.choice_trend || []} color="linear-gradient(180deg, #22c55e 0%, #15803d 100%)" />
        </Col>
        <Col xs={24} lg={8}>
          <MiniBarTrend title="最近一周审核通过数" subtitle="查看意向表审核的推进速度是否稳定。" items={stats.review_trend || []} color="linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%)" />
        </Col>
        <Col xs={24} lg={8}>
          <MiniBarTrend title="最近一周双选录取数" subtitle="关注近 7 天正式录取人数的变化趋势。" items={stats.accepted_choice_trend || []} color="linear-gradient(180deg, #f59e0b 0%, #d97706 100%)" />
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} xxl={13}>
          <Card className="page-card dashboard-section-card" bordered={false}>
            <Typography.Title level={4}>{stats.subject_quota_title || '专业剩余名额'}</Typography.Title>
            <Typography.Paragraph type="secondary">
              基于当前届别和学生类型，优先发现哪些专业已经接近满额，哪些专业开始堆积候补学生。
            </Typography.Paragraph>
            <Table rowKey="key" columns={doctorColumns} dataSource={doctorQuotaRows} pagination={false} size="small" scroll={{ y: 420 }} />
          </Card>
        </Col>
        <Col xs={24} xxl={11}>
          <Card className="page-card dashboard-section-card" bordered={false}>
            <Typography.Title level={4}>方向名额使用情况</Typography.Title>
            <Typography.Paragraph type="secondary">
              同时查看每个方向的硕士和博士名额占用情况，方便快速识别紧张方向。
            </Typography.Paragraph>
            <Table rowKey="key" columns={departmentColumns} dataSource={departmentUsageRows} pagination={false} size="small" scroll={{ y: 420 }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={12}>
          <Card className="page-card dashboard-section-card" bordered={false}>
            <Typography.Title level={4}>待处理申请最多的导师</Typography.Title>
            <Typography.Paragraph type="secondary">
              这块更适合管理员优先关注可能存在积压的导师。
            </Typography.Paragraph>
            <Table rowKey="key" columns={topPendingProfessorColumns} dataSource={topPendingProfessorRows} pagination={false} size="small" />
          </Card>
        </Col>
        <Col xs={24} xl={12}>
          <Card className="page-card dashboard-section-card" bordered={false}>
            <Typography.Title level={4}>剩余名额最少的导师</Typography.Title>
            <Typography.Paragraph type="secondary">
              这块适合提前关注即将满额的导师和后续候补压力。
            </Typography.Paragraph>
            <Table rowKey="key" columns={lowQuotaProfessorColumns} dataSource={lowQuotaProfessorRows} pagination={false} size="small" />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24}>
          <Card className="page-card dashboard-section-card" bordered={false}>
            <Typography.Title level={4}>学生选择行为排行</Typography.Title>
            <Typography.Paragraph type="secondary">
              先看取消次数和选过的不同导师人数最高的 Top 10，快速识别反复操作学生。
            </Typography.Paragraph>
            <Table rowKey="key" columns={studentChoiceBehaviorColumns} dataSource={studentChoiceBehaviorRows} pagination={false} size="small" />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
