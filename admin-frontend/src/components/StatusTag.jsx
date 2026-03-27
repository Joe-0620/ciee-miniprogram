import React from 'react';
import { Tag } from 'antd';


const presets = {
  success: 'success',
  error: 'error',
  warning: 'warning',
  processing: 'processing',
  default: 'default',
};

export default function StatusTag({ tone = 'default', children }) {
  return <Tag color={presets[tone] || presets.default}>{children}</Tag>;
}
