# AI × Bio Feed

一个面向个人使用的 AI × Bio 新闻 Feed。目标是用极简的阅读流程，帮助用户快速理解美国和欧洲的重要论文、公司、机构与研究者动态。

当前完成的是 Phase 1 可点击前端，并已开始接入最小云端数据架构：Vercel 承载 Next.js，Supabase 承载 PostgreSQL，GitHub Actions 每天运行 Python pipeline。第一版不需要常驻服务器、Redis 或 Celery。

## 最小云端配置

1. 在 Supabase 创建 Free project。
2. 打开 SQL Editor，执行 `supabase/migrations/001_initial.sql`。
3. 从 **Connect → Session pooler** 复制连接字符串，保留 `sslmode=require`。不要选择 ORM；GitHub Actions 里的 Python batch 是持续连接，更适合 Session pooler（端口 5432）。
4. 在 GitHub 仓库的 **Settings → Secrets and variables → Actions** 添加：
   - `DATABASE_URL`
   - `OPENAI_API_KEY`
   - `OPENALEX_API_KEY`
5. 在 Actions 页面手动运行一次 **Ingest arXiv**。确认无误后，工作流会每天美国东部时间 00:17 自动执行。

所有私钥只放在 GitHub/Vercel Secrets，不要提交到仓库，也不要粘贴到聊天中。完整变量说明见 `.env.example`。

## Pipeline 开发命令

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
PYTHONPATH=backend python -m unittest discover -s backend/tests
PYTHONPATH=backend python -m bioai_pipeline.cli ingest-arxiv --dry-run --lookback-hours 168 --max-results-per-query 30
```

## 在 GitHub Codespaces 中运行

1. 在 GitHub 仓库页面点击 **Code → Codespaces → Create codespace on main**。
2. 首次启动时，Codespaces 会根据 `.devcontainer/devcontainer.json` 自动安装 Node.js 和项目依赖。
3. 如果开发服务器没有自动启动，在 Codespaces 终端运行：

```bash
npm run dev
```

4. 打开 Codespaces 弹出的 **Open in Browser** 通知；也可以在 **Ports** 面板中打开端口 `3000`。
5. 使用完后停止 Codespace，避免继续消耗额度。

## 本地检查命令

```bash
npm run lint
npx tsc --noEmit
npm run build
```

## 产品范围

- Phase 1：可点击的 mock frontend（已完成）
- Phase 2：PostgreSQL、feedback、preference 与 ranking
- Phase 3：arXiv、bioRxiv、PubMed/OpenAlex 真实数据（arXiv adapter 已开始）
- Phase 4：OpenAI Luna 初筛和 GPT-5.6 Sol 深度解释
- Phase 5：作者、机构、代表论文与可靠照片
- Phase 6：反馈驱动的个性化排序闭环

只有在 GitHub Actions 的定时可靠性或处理量不够时，才迁移到一台 Hetzner VPS。FastAPI、pgvector、Redis 和 Celery 都延后到出现明确需求时再增加。
