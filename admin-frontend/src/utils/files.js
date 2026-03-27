import { post } from '../api/client';


export async function getFilePreviewUrl(fileId) {
  if (!fileId) {
    throw new Error('文件不存在');
  }
  const payload = await post('/files/download-url/', { file_id: fileId });
  return payload.download_url;
}


export async function openFileById(fileId) {
  const previewUrl = await getFilePreviewUrl(fileId);
  window.open(previewUrl, '_blank', 'noopener,noreferrer');
}
