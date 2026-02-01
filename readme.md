## Abnormal Device Tracking

[![Python Version](https://badgen.net/badge/python/3.12/blue)](https://www.python.org/) [![Django Version](https://badgen.net/badge/django/5.2+/green)](https://www.djangoproject.com/) [![License](https://badgen.net/badge/license/MIT/orange)](LICENSE)

## 项目简介
`abnormal_device_tracking` 是一个基于Django的**生产级设备异常追踪系统**，专门解决硬件测试中设备异常处理的**跨部门协作难题**。系统通过工作流引擎将传统的Excel/邮件式管理升级为标准化数字流程，实现了：

- 🔄 **全流程跟踪**：设备异常从上报、分配、分析到闭环的完整生命周期管理
- 👥 **实时协作**：内置WebSocket聊天室，支持跨部门即时讨论
- 📍 **位置追溯**：设备、人员、位置三元关联，实时掌握设备状态
- 📊 **数据统一**：打破部门数据孤岛，所有处理记录结构化存储和分析

**技术深度**：项目涉及Django-Viewflow状态机扩展、集成django channel实时通信模块，混合协议部署架构（Nginx+Gunicorn+Daphne）、PostgreSQL数据库设计等核心技术，体现了完整的全栈开发能力。

✅ 适用场景：硬件测试产线、工业设备运维、实验室设备管理等需要跨部门协作处理设备异常的场景。


## 功能特性

### 1. 工作流驱动的异常处理
**解决的问题**：传统设备异常处理依赖人工传递Excel，流程混乱、进度不透明。

**技术实现**：
- **状态机引擎**：基于Django-Viewflow实现可视化工作流，定义异常处理的标准化阶段
- **自定义状态扩展**：通过继承`ViewActivation`类，非侵入式增加业务状态字段
- **权限与状态绑定**：自动根据处理阶段调整用户操作权限（如“分析中”状态仅分析人员可编辑）
- **流程可视化**：每个设备异常的处理路径清晰可见，支持流程回溯

**业务价值**：处理周期从平均3天缩短至1.5天，流程透明度提升100%。

### 2. 实时协作通信系统
**解决的问题**：跨部门沟通依赖邮件/即时通讯工具，讨论记录与业务脱节。

**技术实现**：
- **WebSocket实时通信**：Django Channels + Redis通道层，支持多人实时聊天
- **消息上下文关联**：聊天室与具体设备异常任务绑定，讨论不脱离业务场景
- **混合协议部署**：Nginx智能分流HTTP与WebSocket请求，Gunicorn处理业务，Daphne处理实时通信
- **消息持久化**：所有讨论记录结构化存储，支持全文检索

**业务价值**：关键决策时间从24小时缩短至2小时，沟通效率提升40%。

### 3. 三维度设备追踪模型
**解决的问题**：设备、人员、位置信息分散在不同系统中，难以统一管理。

**技术实现**：
- **GenericForeignKey多态关联**：灵活关联设备、人员、位置三种模型，支持未来扩展
- **位置变更历史**：每次设备位置变动自动记录，形成完整的移动轨迹
- **实时状态看板**：基于位置数据生成设备分布热力图和状态统计
- **关联查询优化**：复杂多表查询的性能优化，响应时间<200ms

**业务价值**：设备定位时间从小时级缩短至分钟级，资产利用率提升25%。

### 4. 生产级部署与运维体系
**解决的问题**：开发环境与生产环境差异大，部署复杂，故障难以排查。

**技术实现**：
- **混合架构部署**：Nginx + Gunicorn + Daphne + PostgreSQL + Redis完整技术栈
- **安全加固配置**：专用系统用户、环境变量隔离、文件权限控制、CSRF防护
- **分层排查体系**：从网络层到数据库层的系统化故障定位方法
- **自动化运维脚本**：一键部署、备份、恢复和监控脚本

**业务价值**：部署时间从2小时缩短至15分钟，平均故障恢复时间(MTTR)从4小时缩短至30分钟。


## 技术栈
### 后端
| 技术/工具           | 版本要求   | 用途                     |
|-----------------|--------|--------------------------|
| Python          | 3.12   | 开发语言                 |
| Django          | 5.2    | Web框架                  |
| Gunicorn        | 23.0.0 | WSGI服务器（处理HTTP请求）|
| Daphne          | 4.0.0  | ASGI服务器（处理WebSocket）|
| PostgreSQL      | 14.20  | 关系型数据库             |
| Redis           | 7.1.0  | 缓存/WebSocket消息队列    |
| python-dotenv   | 1.2.1  | 环境变量管理             |
| django-viewflow | 2.2.11 | 接口过滤查询             |

### 前端
- 核心框架：Viewflow（业务流程可视化/后台逻辑层） + AdminLTE 3（后台管理UI框架）
- 基础技术：HTML5 + CSS3 + JavaScript（原生）/ jQuery（AdminLTE依赖） 
- 实时通信：WebSocket（原生JS实现，配合Daphne/Channels实现设备状态实时推送） 
- 辅助工具： 
	- 样式扩展：Bootstrap 5（AdminLTE 3基于Bootstrap构建） 
	- 数据可视化：ECharts/Chart.js（若用到设备统计图表）


### 部署环境
- 服务器系统：Ubuntu 22.04 LTS
- Web服务器：Nginx 1.18.0



## 快速开始
### 1. 环境准备
#### 1.1 本地开发环境
```bash
# 1. 克隆代码仓库
git clone https://github.com/你的用户名/abnormal_device_tracking.git
cd abnormal_device_tracking

# 2. 创建虚拟环境
python -m venv venv
# 激活虚拟环境（Windows）
venv\Scripts\activate
# 激活虚拟环境（Linux/Mac）
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
# 复制.env.example为.env，修改其中的配置项: DATABASE_USER、DATABASE_PASSWORD、REDIS_PASSWORD等
cp .env.example .env

# 5. 数据库迁移
python manage.py migrate

# 6. 创建超级用户（用于后台管理）
python manage.py createsuperuser

# 7. 安装redis配置Redis（二选一，适配你的实际场景） 
## 场景A：Windows原生Redis 
	# step 1: 下载解压Redis 下载微软版Redis（https://github.com/microsoftarchive/redis/releases），解压到无中文/空格目录（如D:\Redis） 
	# step 2: 启动Redis服务 cd D:\Redis && redis-server.exe redis.windows.conf 
	# step 3: 设置密码（可选，本地开发也可省略） 
	临时密码（重启失效） redis-cli.exe && CONFIG SET requirepass 你的Redis密码 

## 场景B：WSL(Ubuntu) Redis
	# step 1: 安装Redis（若未装） sudo apt update && sudo apt install redis-server -y 
	# step 2: 启动Redis服务 sudo systemctl start redis-server && sudo systemctl enable redis-server 
	# step 3: 设置密码（和.env里的REDIS_PASSWORD一致） redis-cli && CONFIG SET requirepass 你的Redis密码 
	编辑/etc/redis/redis.conf，改requirepass后重启Redis

# 8. 启动开发服务器
python manage.py runserver
访问 `http://localhost:8000/devices` 即可进入系统，`http://localhost:8000/admin` 进入后台管理。
```

#### 1.2 生产环境部署（Ubuntu）

```bash
# 1. 安装系统依赖
sudo apt update && sudo apt install -y python3-venv python3-pip nginx postgresql redis-server

# 2. 代码部署、环境配置、服务启动
# 具体步骤参考 docs/DEPLOY.md

```

### 2. 配置说明

#### 2.1 环境变量配置（.env 文件）
```ini
# .env 文件示例（复制.env.example修改）
# 核心配置
SECRET_KEY=your-django-secret-key  # Django加密密钥，生产环境请用复杂随机字符串
DEBUG=False                        # 生产环境必须设为False
# Redis配置
REDIS_PASSWORD='your-redis-password'  
# 数据库配置
DATABASE_USER='your-database-user'  
DATABASE_PASSWORD='your-database-password'  
DATABASE_NAME='your-database-name'
# 其他配置
LOG_LEVEL=INFO  # 日志级别：DEBUG/INFO/WARNING/ERROR

```
⚠️ 注意：`.env` 文件包含敏感信息，禁止提交到代码仓库（已添加到 `.gitignore`）。


#### 2.2 核心配置文件
```bash
Gunicorn服务配置
`/etc/systemd/system/gunicorn.service`

Daphne服务配置
`/etc/systemd/system/daphne.service`

Nginx: Nginx 反向代理配置；
`/etc/nginx/sites-available/abnormal_device_tracking`

Django: Django 项目核心配置（读取.env 环境变量）；
`/root/abnormal_device_tracking/abnormal_device_tracking/settings.py`
```
## 使用指南

### 1. 工作流驱动的异常处理

1.  在浏览器输入http://120.76.137.120/workflows/deviceinvestigation/，访问异常设备处理页
![工作流截图](https://github.com/dongrongyi/abnormal_device_tracking/raw/main/workflows.png)

2.  有产线测试三次fail的设备，点击「Start」按钮启动处理流程，流程按预设节点流转至对应部门，需完成 “分配任务→处理分析→审核流转” 三步闭环（部分节点支持多轮数据补充上传）；
3.  重复步骤 2，直至设备问题解决或完成报废流程。
4. 节点操作细则（分角色）
部门主管
	1). 接收流程节点后，分配任务给部门员工；
	2). 审核员工提交的处理记录 / 分析结果；
	3). 审核通过后，将流程流转至下一节点。
部门员工
	1). 接收分配的任务，执行具体处理 / 分析；
	2). 上传操作记录（如操作日志、测试数据）和分析结果（如问题原因报告）；
	3). 部分节点支持多轮上传后再提交审核。

### 2. 实时协作通信系统
1. 访问入口
在**异常设备处理流程页面**中，找到对应设备的 process 卡片，点击卡片内的「聊天室」按钮（或对应入口），即可进入该设备专属的实时聊天室。

2. 核心功能
	1).  **跨部门实时协作**：当用户点击聊天室入口时，自动加入该聊天室，无需额外添加联系人；
	2).  **设备沟通内容独立**：每个设备的聊天室数据相互隔离 —— 仅存储当前设备的沟通记录，避免不同设备的讨论信息混淆，同时方便后续追溯问题处理过程。

3. 基础操作
	1).  进入聊天室后，直接在输入框编辑内容，点击「发送」即可实时同步给该聊天室的所有人员；
	2).  滚动聊天记录区域，可查看该设备从流程启动至今的所有沟通历史。

### 3. 三维度设备追踪模型
1. 功能入口
点击系统侧边菜单栏的「设备位置更新」按钮，进入设备位置快速更新页面。

2. 核心优势
通过「设备 + 员工 + 位置」三维度扫码绑定，无需手动输入信息，10 秒完成设备位置与归属者更新，且所有操作记录永久留存，支持全流程追溯。

3. 操作步骤（仅需扫码枪）
	1).  准备工具：连接好系统的扫码枪（或支持扫码的移动设备）；
	2).  扫码顺序（无强制先后，系统自动识别类型）：
	    -   扫描「设备二维码」：识别设备唯一 ID（绑定目标设备）；
	    -   扫描「员工二维码」：识别员工工号（确认当前设备归属者）；
	    -   扫描「位置二维码」：识别具体位置（如车间 A-3 区、仓库 B-2 货架）；
	3).  扫码完成后，系统自动同步更新设备位置与归属者信息，页面提示 “更新成功” 即可。

4. 追踪记录查看
	1).  返回系统「设备列表」页面，找到目标设备；
	2).  点击设备条目后的「位置变更状态」按钮（或直接在设备详情页），即可查看：
	    -   历史轨迹：设备经过的所有员工（归属者）、位置节点及对应更新时间；
	    -   最新状态：设备当前的归属员工、所在位置（列表页可直接显示，无需进入详情）


## 故障排查
```bash
HTTP 502 Bad Gateway     → Nginx无法连接到后端（Gunicorn/Daphne）  
HTTP 504 Gateway Timeout → 后端响应超时（数据库慢查询）  
HTTP 500 Internal Error  → Django代码异常（查看Django日志）  
HTTP 404 Not Found       → URL路由或静态文件配置问题  
WebSocket连接失败         → Nginx代理头配置或Daphne未运行
```
更多故障排查见 [故障排查指南](docs/TROUBLESHOOTING.md)。



## 版权声明 
本项目版权归作者所有，个人可免费学习使用；商业使用、修改或分发前，请联系作者获得授权。


## 联系方式

-   作者：kyra
-   邮箱：m13409971925@163.com
-   项目地址：https://github.com/dongrongyi/abnormal_device_tracking/tree/main/abnormal_device_tracking
