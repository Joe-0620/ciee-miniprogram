import React, { useEffect, useState } from 'react';
import { Button, Modal, Space, Spin, Typography } from 'antd';
import { CloseOutlined, DownloadOutlined } from '@ant-design/icons';

import { getFilePreviewUrl } from '../utils/files';


export default function PdfPreviewModal({ open, title, fileId, onClose }) {
  const [loading, setLoading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (!open || !fileId) {
      return undefined;
    }

    let active = true;
    setLoading(true);
    setPreviewUrl('');
    setErrorMessage('');

    getFilePreviewUrl(fileId)
      .then((url) => {
        if (active) {
          setPreviewUrl(url);
        }
      })
      .catch((error) => {
        if (active) {
          setPreviewUrl('');
          setErrorMessage(error?.message || '获取预览地址失败');
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [open, fileId]);

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width="88vw"
      style={{ top: 24 }}
      destroyOnClose
      closable={false}
      className="pdf-preview-modal"
    >
      <div className="pdf-preview-shell simple">
        <div className="pdf-preview-topbar">
          <div>
            <Typography.Title level={4} style={{ margin: 0, color: '#f8fafc' }}>
              {title || 'PDF 预览'}
            </Typography.Title>
            <Typography.Text style={{ color: 'rgba(248,250,252,0.78)' }}>
              使用浏览器自带的 PDF 缩放能力进行查看
            </Typography.Text>
          </div>
          <Space wrap>
            <Button
              icon={<DownloadOutlined />}
              onClick={() => previewUrl && window.open(previewUrl, '_blank', 'noopener,noreferrer')}
              disabled={loading || !previewUrl}
            >
              新窗口打开
            </Button>
            <Button icon={<CloseOutlined />} onClick={onClose}>
              关闭
            </Button>
          </Space>
        </div>

        <div className="pdf-simple-stage">
          {loading ? (
            <div className="pdf-preview-loading">
              <Spin size="large" />
            </div>
          ) : null}

          {!loading && previewUrl ? (
            <iframe
              title={title || 'PDF 预览'}
              src={previewUrl}
              className="pdf-simple-frame"
            />
          ) : null}

          {!loading && !previewUrl ? (
            <div className="pdf-preview-empty">
              <Typography.Title level={4} style={{ marginBottom: 8 }}>
                暂时无法预览这份材料
              </Typography.Title>
              <Typography.Text type="secondary">
                {errorMessage || '可以关闭后重试，或检查文件是否已上传成功。'}
              </Typography.Text>
            </div>
          ) : null}
        </div>
      </div>
    </Modal>
  );
}
