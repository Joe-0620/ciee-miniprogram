# 开发模式说明

## 1. 后端热更新

在后端目录执行：

```powershell
cd D:\Desktop\微信小程序前后端\ciee-miniprogram
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

说明：

- `docker-compose.yml` 保留原有数据库和端口配置
- `docker-compose.dev.yml` 会把当前项目目录挂载到容器内
- Django 运行在 `runserver 0.0.0.0:80`
- 修改 Python 代码后，容器内的 Django 会自动重载

如果新增了模型或迁移文件，仍然需要手动执行：

```powershell
docker compose exec app python manage.py migrate
```

## 2. 管理后台前端热更新

另开一个终端执行：

```powershell
cd D:\Desktop\微信小程序前后端\ciee-miniprogram\admin-frontend
npm install
npm run dev
```

访问地址：

- React 管理端开发环境：http://localhost:5173
- Django API：http://localhost:27081

说明：

- Vite 已代理 `/dashboard-api` 到本地 Django 容器
- 开发模式下 React 路由基址是 `/`
- 生产构建时仍然会输出到 Django 的 `/static/admin/`

## 3. 生产式构建

只有在你要验证正式部署效果或准备上线时，才需要使用：

```powershell
docker compose build
docker compose up -d
```
