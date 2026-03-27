import { Modal } from 'antd';


export function confirmDanger({ title, content, onOk, okText = '删除', cancelText = '取消' }) {
  Modal.confirm({
    centered: true,
    title,
    content,
    okText,
    cancelText,
    okButtonProps: { danger: true },
    onOk,
  });
}
