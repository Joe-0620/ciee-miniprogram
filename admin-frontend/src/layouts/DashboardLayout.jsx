import React, { useEffect, useMemo, useState } from 'react';
import {
  AuditOutlined,
  DashboardOutlined,
  KeyOutlined,
  LinkOutlined,
  LogoutOutlined,
  ReadOutlined,
  ScheduleOutlined,
  TeamOutlined,
  UserDeleteOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Button, Layout, Menu, Space, Typography, theme } from 'antd';
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom';

import { post } from '../api/client';
import { removeDashboardToken } from '../utils/auth';


const { Header, Content, Sider } = Layout;

const NAV_GROUPS = [
  {
    key: 'overview',
    icon: <DashboardOutlined />,
    label: '总览',
    children: [{ key: '/', icon: <DashboardOutlined />, label: '仪表盘' }],
  },
  {
    key: 'accounts',
    icon: <AuditOutlined />,
    label: '账号与权限',
    children: [
      { key: '/audit-logs', icon: <AuditOutlined />, label: '操作日志' },
      { key: '/users', icon: <UserOutlined />, label: '用户管理' },
      { key: '/wechat-accounts', icon: <LinkOutlined />, label: '微信账号绑定' },
      { key: '/tokens', icon: <KeyOutlined />, label: '认证令牌' },
    ],
  },
  {
    key: 'people',
    icon: <TeamOutlined />,
    label: '人员管理',
    children: [
      { key: '/professors', icon: <TeamOutlined />, label: '导师管理' },
      { key: '/students', icon: <UserOutlined />, label: '学生管理' },
    ],
  },
  {
    key: 'admission',
    icon: <ReadOutlined />,
    label: '招生业务',
    children: [
      { key: '/choices', icon: <AuditOutlined />, label: '双选记录' },
      { key: '/reviews', icon: <ReadOutlined />, label: '审核记录' },
      { key: '/alternates', icon: <ScheduleOutlined />, label: '候补管理' },
      { key: '/giveups', icon: <UserDeleteOutlined />, label: '放弃录取' },
    ],
  },
  {
    key: 'config',
    icon: <ScheduleOutlined />,
    label: '名额与配置',
    children: [
      { key: '/selection-times', icon: <ScheduleOutlined />, label: '学院师生互选时间设置' },
      { key: '/admission-batches', icon: <ScheduleOutlined />, label: '招生批次' },
      { key: '/enrollment', icon: <ScheduleOutlined />, label: '专业 / 方向' },
      { key: '/master-quotas', icon: <ScheduleOutlined />, label: '导师硕士专业名额' },
      { key: '/doctor-quotas', icon: <ScheduleOutlined />, label: '导师博士专业名额' },
      { key: '/shared-quota-pools', icon: <ScheduleOutlined />, label: '共享名额池' },
    ],
  },
];

const menuItems = NAV_GROUPS.map((group) => ({
  key: group.key,
  icon: group.icon,
  label: group.label,
  children: group.children,
}));

const flatItems = NAV_GROUPS.flatMap((group) =>
  group.children.map((item) => ({
    ...item,
    parentKey: group.key,
  })),
);

export default function DashboardLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { token } = theme.useToken();
  const [openKeys, setOpenKeys] = useState(['overview', 'accounts', 'people', 'admission', 'config']);

  const selectedItem = useMemo(
    () => flatItems.find((item) => location.pathname === item.key || location.pathname.startsWith(`${item.key}/`)),
    [location.pathname],
  );
  const selectedKey = selectedItem?.key || '/';

  useEffect(() => {
    if (selectedItem?.parentKey && !openKeys.includes(selectedItem.parentKey)) {
      setOpenKeys((current) => [...current, selectedItem.parentKey]);
    }
  }, [selectedItem, openKeys]);

  async function onLogout() {
    try {
      await post('/auth/logout/', {});
    } catch {}
    removeDashboardToken();
    navigate('/login', { replace: true });
  }

  if (!selectedKey) {
    return <Navigate to="/" replace />;
  }

  return (
    <Layout className="dashboard-shell">
      <Sider
        width={232}
        className="dashboard-sider"
        style={{
          background: `linear-gradient(180deg, ${token.colorPrimaryBg} 0%, #0f172a 100%)`,
          paddingTop: 24,
        }}
      >
        <Space direction="vertical" size={4} className="dashboard-sider-brand">
          <Typography.Title level={3} style={{ color: '#fff', margin: 0 }}>
            CIEE 后台
          </Typography.Title>
          <Typography.Text style={{ color: 'rgba(255,255,255,0.72)' }}>
            管理员工作台
          </Typography.Text>
        </Space>
        <Menu
          mode="inline"
          inlineIndent={14}
          selectedKeys={[selectedKey]}
          openKeys={openKeys}
          items={menuItems}
          onOpenChange={setOpenKeys}
          onClick={({ key }) => navigate(key)}
          className="dashboard-menu"
          style={{ background: 'transparent', color: '#fff', borderInlineEnd: 'none' }}
          theme="dark"
        />
      </Sider>
      <Layout className="dashboard-main">
        <Header className="dashboard-header">
          <Typography.Title level={4} style={{ margin: 0 }}>
            招生管理后台
          </Typography.Title>
          <Button icon={<LogoutOutlined />} onClick={onLogout}>
            退出登录
          </Button>
        </Header>
        <Content className="dashboard-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
