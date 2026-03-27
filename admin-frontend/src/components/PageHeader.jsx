import React from 'react';
import { Breadcrumb, Space, Typography } from 'antd';


export default function PageHeader({ items = [], title, subtitle, extra = null }) {
  return (
    <div className="page-header">
      <div className="page-header-main">
        {items.length ? <Breadcrumb items={items} className="page-breadcrumb" /> : null}
        <Space direction="vertical" size={4}>
          <Typography.Title level={3} style={{ margin: 0 }}>
            {title}
          </Typography.Title>
          {subtitle ? (
            <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
              {subtitle}
            </Typography.Paragraph>
          ) : null}
        </Space>
      </div>
      {extra ? <div className="page-header-extra">{extra}</div> : null}
    </div>
  );
}
