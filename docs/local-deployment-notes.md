# Onyx 本地部署与前端改动重新部署记录

本文记录一次 Windows 本机部署、调试和重新部署 Onyx 的成功经验，方便后续复用。

## 适用场景

适用于以下情况：

- Windows 本机运行 Onyx。
- 已通过 `onyx_data/deployment` 目录安装或运行过 Onyx。
- 需要重新部署本地 Onyx。
- 需要让 `onyx/web` 中的前端源码改动在本地容器中生效。
- 需要验证 Admin Panel、Image Generation 页面或聊天页功能。

## 环境要点

本次成功运行时的关键环境特征：

- 系统：Windows。
- Docker 命令显式使用 `default` context。
- Onyx 实际运行目录：`e:/Study/AI/claude/onyx_data/deployment`。
- Onyx 源码目录：`e:/Study/AI/claude/onyx`。
- Web 前端源码目录：`e:/Study/AI/claude/onyx/web`。
- 本地部署中的前端容器使用镜像标签：`onyxdotapp/onyx-web-server:edge`。
- 从源码构建 `web_server` 后默认生成的镜像标签可能是：`onyxdotapp/onyx-web-server:latest`。

## 常见问题与经验

如果 Docker Desktop 的 `desktop-linux` context 不可用，可以改用 `default` context：

```bash
docker --context default ps
```

如果 `3000` 端口被其他容器占用，例如 `open-webui`，Onyx 的 nginx 无法绑定 `3000`。需要先停掉占用端口的容器，或改端口配置。本次处理方式是临时停止 `open-webui`：

```bash
docker --context default stop open-webui
```

不要直接用源码目录里的 compose 在错误的 project directory 下拉起一套新项目，否则容易生成临时项目，例如 `onyx1`，并与当前 Onyx 部署抢占端口。

源码 compose 中的 nginx volume 路径可能与实际安装目录不匹配，导致 nginx 启动时报 `/tmp/run-nginx.sh: not found`。恢复实际本地部署时，优先使用 `onyx_data/deployment` 下的 compose 文件。

本次浏览器验证使用 `playwright-cli`。如果普通 Playwright 测试提示浏览器未安装，不要继续安装浏览器；可以用 `playwright-cli` 直接操作当前环境中的浏览器会话。

## 恢复本地部署

实际部署目录使用：

```text
e:/Study/AI/claude/onyx_data/deployment
```

基础 compose 文件：

```text
e:/Study/AI/claude/onyx_data/deployment/docker-compose.yml
e:/Study/AI/claude/onyx_data/deployment/docker-compose.onyx-lite.yml
```

如果需要暴露开发和测试端口，再加载：

```text
e:/Study/AI/claude/onyx_data/deployment/docker-compose.dev.yml
```

恢复核心服务：

```bash
docker --context default compose \
  --project-directory "e:/Study/AI/claude/onyx_data/deployment" \
  -f "e:/Study/AI/claude/onyx_data/deployment/docker-compose.yml" \
  -f "e:/Study/AI/claude/onyx_data/deployment/docker-compose.onyx-lite.yml" \
  -f "e:/Study/AI/claude/onyx_data/deployment/docker-compose.dev.yml" \
  up -d --wait api_server relational_db web_server nginx
```

查看容器状态：

```bash
docker --context default ps --filter "name=onyx" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
```

## 暴露开发端口

如果实际部署目录缺少 `docker-compose.dev.yml`，可以从源码部署目录复制：

```bash
cp "e:/Study/AI/claude/onyx/deployment/docker_compose/docker-compose.dev.yml" \
  "e:/Study/AI/claude/onyx_data/deployment/docker-compose.dev.yml"
```

该文件用于暴露常用开发和测试端口：

- API：`8080`
- Postgres：`5432`
- Redis：`6379`
- Vespa config：`19071`
- Vespa query：`8081`
- OpenSearch：`9200`

## 前端源码改动后重新部署

前端源码改动后，只需要单独构建 `web_server`，不必全量构建后端镜像。

在源码 compose 配置下构建前端镜像：

```bash
docker --context default compose \
  --project-directory "e:/Study/AI/claude/onyx/deployment/docker_compose" \
  -f "e:/Study/AI/claude/onyx/deployment/docker_compose/docker-compose.yml" \
  build web_server
```

构建成功后确认 `latest` 镜像存在：

```bash
docker --context default image inspect onyxdotapp/onyx-web-server:latest --format '{{.Id}} {{.RepoTags}}'
```

实际本地部署使用的是 `edge` 标签，因此需要把新构建的 `latest` 标记为 `edge`：

```bash
docker --context default tag onyxdotapp/onyx-web-server:latest onyxdotapp/onyx-web-server:edge
```

然后使用实际部署目录的 compose 强制重建 `web_server` 和 `nginx`：

```bash
docker --context default compose \
  --project-directory "e:/Study/AI/claude/onyx_data/deployment" \
  -f "e:/Study/AI/claude/onyx_data/deployment/docker-compose.yml" \
  -f "e:/Study/AI/claude/onyx_data/deployment/docker-compose.onyx-lite.yml" \
  -f "e:/Study/AI/claude/onyx_data/deployment/docker-compose.dev.yml" \
  up -d --force-recreate web_server nginx
```

确认运行中的 web 容器使用的是新镜像：

```bash
docker --context default inspect onyx-web_server-1 --format '{{.Image}} {{.Config.Image}}'
```

如果页面没有出现新功能，优先检查这里的镜像 ID 是否仍然是旧的 `edge`。

## 后端集成测试环境经验

Onyx 项目 Python 依赖更适合 Python 3.11。虽然项目声明 `requires-python = ">=3.11"`，但 Python 3.13 下可能因为 `psycopg2-binary==2.9.9` 没有合适 wheel 而触发源码构建，并因缺少 `pg_config` 失败。

可用 `uv` 安装 Python 3.11 并同步后端和开发依赖：

```bash
py -3.13 -m pip install uv
py -3.13 -m uv python install 3.11
UV_PROJECT_ENVIRONMENT="e:/Study/AI/claude/onyx/.venv311" \
  py -3.13 -m uv sync \
  --project "e:/Study/AI/claude/onyx" \
  --python 3.11 \
  --no-default-groups \
  --group backend \
  --group dev
```

后端测试应从 `onyx/backend` 目录运行，因为 Alembic 配置依赖当前工作目录。

Image Generation 相关集成测试会 reset Postgres、Vespa 和 FileStore。lite 模式默认只启动 Postgres 不够，需要额外启动 Redis、Vespa、OpenSearch：

```bash
docker --context default compose \
  --project-directory "e:/Study/AI/claude/onyx_data/deployment" \
  -f "e:/Study/AI/claude/onyx_data/deployment/docker-compose.yml" \
  -f "e:/Study/AI/claude/onyx_data/deployment/docker-compose.onyx-lite.yml" \
  -f "e:/Study/AI/claude/onyx_data/deployment/docker-compose.dev.yml" \
  --profile redis \
  --profile vectordb \
  --profile opensearch \
  up -d --wait cache index indexing_model_server opensearch
```

如果测试 fixture 读取 `OPENAI_API_KEY`，但当前只是验证配置保存逻辑，可以设置假的测试 key：

```bash
OPENAI_API_KEY="sk-test-openai-key"
```

## 浏览器验证经验

使用 `playwright-cli` 打开本地页面：

```bash
playwright-cli open http://localhost:3000/admin/configuration/image-generation
```

如果跳转到登录页，可以用 API 登录管理员账号：

```bash
playwright-cli run-code "async page => { const res = await page.request.post('http://localhost:3000/api/auth/login', { form: { username: 'admin_user@example.com', password: 'TestPassword123!' } }); return { status: res.status(), body: await res.text() }; }"
```

登录后重新进入页面：

```bash
playwright-cli goto http://localhost:3000/admin/configuration/image-generation
```

检查页面是否出现 `OpenAI Compatible`：

```bash
playwright-cli --raw eval "document.body.innerText.includes('OpenAI Compatible')"
```

可以用快照定位元素：

```bash
playwright-cli snapshot --depth=6
```

验证 `OpenAI Compatible` 编辑弹窗字段：

```bash
playwright-cli run-code "async page => ({ modelName: await page.getByLabel('Model Name').inputValue(), baseUrl: await page.getByLabel('Base URL').inputValue(), hasApiKeyField: await page.getByLabel('API Key').count(), connectEnabled: await page.getByRole('button', { name: 'Connect', exact: true }).isEnabled() })"
```

## Image Generation 与 sub2api 经验

Onyx 的聊天模型和图片生成模型是两套配置。

聊天框底部显示的模型，例如 `gpt-5.5`，是文本聊天模型。它负责理解用户请求、决定是否调用工具、组织文字回复。

真正生图使用的是 Admin Panel → Image Generation 中配置的默认图片模型。

新增的 `OpenAI Compatible` 会把以下字段传给兼容接口：

- `model_name`
- `api_base`
- `api_key`

如果兼容接口是 sub2api，`gpt-image-2` 请求可能被调度到 ChatGPT/Codex OAuth 通道，而不是 OpenAI API Key 的 Images API 通道。此时上游可能报错：

```text
The 'gpt-image-2' model is not supported when using Codex with a ChatGPT account.
```

这表示 Onyx 已经正确传递模型和 base URL，但 sub2api 选中的上游账号不支持该图片模型。

生图能否成功取决于：

- sub2api 选中的账号类型。
- 该账号是否支持对应图片模型。
- 请求是否走 OpenAI API Key Images API，还是 ChatGPT/Codex OAuth Responses 通道。
- sub2api 的模型映射和账号调度规则。

## 快速复用命令清单

查看当前 Onyx web/nginx 状态：

```bash
docker --context default ps --filter "name=onyx-web_server-1" --filter "name=onyx-nginx-1" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
```

查看运行中的 web 镜像：

```bash
docker --context default inspect onyx-web_server-1 --format '{{.Image}} {{.Config.Image}}'
```

构建前端镜像：

```bash
docker --context default compose \
  --project-directory "e:/Study/AI/claude/onyx/deployment/docker_compose" \
  -f "e:/Study/AI/claude/onyx/deployment/docker_compose/docker-compose.yml" \
  build web_server
```

把 `latest` 标记为 `edge`：

```bash
docker --context default tag onyxdotapp/onyx-web-server:latest onyxdotapp/onyx-web-server:edge
```

重建本地 web/nginx：

```bash
docker --context default compose \
  --project-directory "e:/Study/AI/claude/onyx_data/deployment" \
  -f "e:/Study/AI/claude/onyx_data/deployment/docker-compose.yml" \
  -f "e:/Study/AI/claude/onyx_data/deployment/docker-compose.onyx-lite.yml" \
  -f "e:/Study/AI/claude/onyx_data/deployment/docker-compose.dev.yml" \
  up -d --force-recreate web_server nginx
```

查看 API 日志：

```bash
docker --context default logs --tail 200 onyx-api_server-1
```

打开 Image Generation 页面：

```bash
playwright-cli goto http://localhost:3000/admin/configuration/image-generation
```

## 排错清单

页面没有出现新功能：

- 检查 `onyx-web_server-1` 是否仍使用旧镜像。
- 检查 `onyxdotapp/onyx-web-server:latest` 是否已 tag 成 `onyxdotapp/onyx-web-server:edge`。
- 强制重建 `web_server` 和 `nginx`。

容器无法启动：

- 检查 `3000` 端口是否被其他容器占用。
- 检查是否误启动了临时 compose 项目。
- 优先使用 `onyx_data/deployment` 下的 compose 文件恢复部署。

后端测试连不上服务：

- 检查 Postgres 是否暴露 `5432`。
- 检查 API 是否暴露 `8080`。
- 检查 Redis、Vespa、OpenSearch 对应 profile 是否已启动。
- 从 `onyx/backend` 目录运行测试。

生图报模型不支持：

- 先确认 Onyx Admin Panel → Image Generation 中保存的默认图片模型。
- 检查 sub2api 的账号类型和模型映射。
- 如果错误提到 Codex 或 ChatGPT account，说明请求走到了 OAuth/ChatGPT 通道。
- 如果需要使用特定 `gpt-image-*` 模型，应确认 sub2api 有支持该模型的 OpenAI API Key 账号或正确的上游映射。
