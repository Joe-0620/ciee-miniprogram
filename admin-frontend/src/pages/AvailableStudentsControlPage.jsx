import React, { useEffect, useMemo, useState } from 'react';
import { Button, Card, Select, Space, Switch, Typography, message } from 'antd';

import { get, patch } from '../api/client';
import PageHeader from '../components/PageHeader';


const postgraduateTypeOptions = [
  { label: '北京专硕', value: 1 },
  { label: '学硕', value: 2 },
  { label: '博士', value: 3 },
  { label: '烟台专硕', value: 4 },
];


function getYearOptions(batches) {
  const currentYear = new Date().getFullYear();
  const yearSet = new Set();
  for (let year = currentYear - 1; year <= currentYear + 3; year += 1) {
    yearSet.add(year);
  }
  batches.forEach((batch) => {
    if (batch?.admission_year) {
      yearSet.add(batch.admission_year);
    }
  });
  return Array.from(yearSet)
    .sort((left, right) => left - right)
    .map((year) => ({ label: `${year}届`, value: year }));
}


export default function AvailableStudentsControlPage() {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [batches, setBatches] = useState([]);
  const [setting, setSetting] = useState({
    enabled: true,
    require_resume: false,
    allowed_admission_years: [],
    allowed_batch_ids: [],
    allowed_postgraduate_types: [],
  });

  const yearOptions = useMemo(() => getYearOptions(batches), [batches]);
  const batchOptions = useMemo(
    () => batches.map((item) => ({ label: `${item.admission_year}届 - ${item.name}`, value: item.id })),
    [batches],
  );

  async function loadData() {
    setLoading(true);
    try {
      const [settingPayload, batchPayload] = await Promise.all([get('/student-display-settings/'), get('/admission-batches/')]);
      setSetting({
        enabled: Boolean(settingPayload?.enabled),
        require_resume: Boolean(settingPayload?.require_resume),
        allowed_admission_years: settingPayload?.allowed_admission_years || [],
        allowed_batch_ids: settingPayload?.allowed_batch_ids || [],
        allowed_postgraduate_types: settingPayload?.allowed_postgraduate_types || [],
      });
      setBatches(Array.isArray(batchPayload) ? batchPayload : batchPayload?.results || []);
    } catch (error) {
      message.error(error.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function saveSetting(nextSetting) {
    setSaving(true);
    try {
      const payload = await patch('/student-display-settings/', nextSetting);
      setSetting({
        enabled: Boolean(payload?.enabled),
        require_resume: Boolean(payload?.require_resume),
        allowed_admission_years: payload?.allowed_admission_years || [],
        allowed_batch_ids: payload?.allowed_batch_ids || [],
        allowed_postgraduate_types: payload?.allowed_postgraduate_types || [],
      });
      message.success('可选学生展示配置已更新');
    } catch (error) {
      message.error(error.message);
    } finally {
      setSaving(false);
    }
  }

  function updateSetting(key, value) {
    const nextSetting = { ...setting, [key]: value };
    setSetting(nextSetting);
    saveSetting(nextSetting);
  }

  return (
    <Card className="page-card" bordered={false} loading={loading}>
      <PageHeader
        items={[{ title: '招生业务' }, { title: '可选学生展示控制' }]}
        title="可选学生展示控制"
        subtitle="统一控制小程序导师端可选学生池的展示范围，并与学生管理中的单独开关联动。"
      />

      <div className="page-toolbar">
        <div className="page-filters">
          <Typography.Text type="secondary">
            当全局关闭时，导师端“可选学生”列表将不再展示任何学生；单学生隐藏可在“学生管理”页单独设置。
          </Typography.Text>
        </div>
        <div className="page-actions">
          <Button onClick={loadData}>刷新</Button>
        </div>
      </div>

      <div className="modal-form-section">
        <div className="modal-form-section-title">全局规则</div>
        <div className="modal-form-grid">
          <div>
            <Typography.Text strong>开放可选学生展示</Typography.Text>
            <div style={{ marginTop: 8 }}>
              <Switch
                checked={setting.enabled}
                loading={saving}
                checkedChildren="开启"
                unCheckedChildren="关闭"
                onChange={(checked) => updateSetting('enabled', checked)}
              />
            </div>
          </div>
          <div>
            <Typography.Text strong>仅展示已上传简历学生</Typography.Text>
            <div style={{ marginTop: 8 }}>
              <Switch
                checked={setting.require_resume}
                loading={saving}
                checkedChildren="开启"
                unCheckedChildren="关闭"
                onChange={(checked) => updateSetting('require_resume', checked)}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="modal-form-section">
        <div className="modal-form-section-title">展示范围</div>
        <div className="modal-form-grid">
          <div>
            <Typography.Text strong>允许展示届别</Typography.Text>
            <div style={{ marginTop: 8 }}>
              <Select
                mode="multiple"
                allowClear
                style={{ width: '100%' }}
                placeholder="留空表示不限届别"
                options={yearOptions}
                value={setting.allowed_admission_years}
                onChange={(value) => updateSetting('allowed_admission_years', value)}
              />
            </div>
          </div>
          <div>
            <Typography.Text strong>允许展示招生批次</Typography.Text>
            <div style={{ marginTop: 8 }}>
              <Select
                mode="multiple"
                allowClear
                style={{ width: '100%' }}
                placeholder="留空表示不限批次"
                options={batchOptions}
                value={setting.allowed_batch_ids}
                onChange={(value) => updateSetting('allowed_batch_ids', value)}
              />
            </div>
          </div>
          <div>
            <Typography.Text strong>允许展示培养类型</Typography.Text>
            <div style={{ marginTop: 8 }}>
              <Select
                mode="multiple"
                allowClear
                style={{ width: '100%' }}
                placeholder="留空表示不限培养类型"
                options={postgraduateTypeOptions}
                value={setting.allowed_postgraduate_types}
                onChange={(value) => updateSetting('allowed_postgraduate_types', value)}
              />
            </div>
          </div>
        </div>
      </div>

      <Card size="small" style={{ marginTop: 16 }}>
        <Space direction="vertical" size={4}>
          <Typography.Text strong>当前生效规则</Typography.Text>
          <Typography.Text type="secondary">
            {setting.enabled ? '已开放导师端可选学生展示。' : '当前已关闭导师端可选学生展示。'}
          </Typography.Text>
          <Typography.Text type="secondary">
            {setting.require_resume ? '当前仅展示已上传简历的学生。' : '当前不限制学生是否上传简历。'}
          </Typography.Text>
          <Typography.Text type="secondary">
            {setting.allowed_admission_years.length ? `届别限制：${setting.allowed_admission_years.map((year) => `${year}届`).join('、')}` : '届别限制：不限'}
          </Typography.Text>
          <Typography.Text type="secondary">
            {setting.allowed_batch_ids.length
              ? `批次限制：${batchOptions.filter((item) => setting.allowed_batch_ids.includes(item.value)).map((item) => item.label).join('、') || '所选批次'}`
              : '批次限制：不限'}
          </Typography.Text>
          <Typography.Text type="secondary">
            {setting.allowed_postgraduate_types.length
              ? `培养类型限制：${postgraduateTypeOptions.filter((item) => setting.allowed_postgraduate_types.includes(item.value)).map((item) => item.label).join('、')}`
              : '培养类型限制：不限'}
          </Typography.Text>
        </Space>
      </Card>
    </Card>
  );
}
