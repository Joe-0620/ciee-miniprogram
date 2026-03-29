import { getDashboardToken, removeDashboardToken } from '../utils/auth';


const API_BASE = '/dashboard-api';

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set('Content-Type', 'application/json');

  const token = getDashboardToken();
  if (token) {
    headers.set('Authorization', `Token ${token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    removeDashboardToken();
  }

  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json') ? await response.json() : null;

  if (!response.ok) {
    const error = new Error(payload?.detail || payload?.message || 'Request failed');
    error.status = response.status;
    error.payload = payload;
    throw error;
  }

  return payload;
}

function buildHeaders(options = {}) {
  const headers = new Headers(options.headers || {});
  const token = getDashboardToken();
  if (token) {
    headers.set('Authorization', `Token ${token}`);
  }
  return headers;
}

export function get(path) {
  return request(path, { method: 'GET' });
}

export function post(path, body) {
  return request(path, { method: 'POST', body: JSON.stringify(body) });
}

export function patch(path, body) {
  return request(path, { method: 'PATCH', body: JSON.stringify(body) });
}

export function del(path) {
  return request(path, { method: 'DELETE' });
}

export async function upload(path, formData) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: buildHeaders(),
    body: formData,
  });

  if (response.status === 401) {
    removeDashboardToken();
  }

  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json') ? await response.json() : null;
  if (!response.ok) {
    const error = new Error(payload?.detail || payload?.message || '上传失败');
    error.status = response.status;
    error.payload = payload;
    throw error;
  }
  return payload;
}

export function uploadWithProgress(path, formData, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE}${path}`);

    const headers = buildHeaders();
    headers.forEach((value, key) => {
      xhr.setRequestHeader(key, value);
    });

    xhr.upload.onprogress = (event) => {
      if (!onProgress || !event.lengthComputable) return;
      const percent = Math.min(100, Math.round((event.loaded / event.total) * 100));
      onProgress(percent);
    };

    xhr.onload = () => {
      if (xhr.status === 401) {
        removeDashboardToken();
      }
      const contentType = xhr.getResponseHeader('content-type') || '';
      const payload = contentType.includes('application/json') && xhr.responseText ? JSON.parse(xhr.responseText) : null;
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(payload);
        return;
      }
      const error = new Error(payload?.detail || payload?.message || '上传失败');
      error.status = xhr.status;
      error.payload = payload;
      reject(error);
    };

    xhr.onerror = () => reject(new Error('上传失败'));
    xhr.send(formData);
  });
}

export async function download(path, filename) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'GET',
    headers: buildHeaders(),
  });

  if (response.status === 401) {
    removeDashboardToken();
  }

  if (!response.ok) {
    throw new Error('下载失败');
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export async function postDownload(path, body, filename) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: (() => {
      const headers = buildHeaders();
      headers.set('Content-Type', 'application/json');
      return headers;
    })(),
    body: JSON.stringify(body),
  });

  if (response.status === 401) {
    removeDashboardToken();
  }

  if (!response.ok) {
    let errorMessage = '下载失败';
    try {
      const payload = await response.json();
      errorMessage = payload?.detail || errorMessage;
    } catch {}
    throw new Error(errorMessage);
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
