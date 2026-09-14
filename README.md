# AI × Bio Feed

一个面向个人使用的 AI × Bio 新闻 Feed。目标是用极简的阅读流程，帮助用户快速理解美国和欧洲的重要论文、公司、机构与研究者动态。

当前已完成 Phase 1 可点击前端，并跑通 arXiv + bioRxiv 真实数据链路：Vercel 承载 Next.js 和只读 Feed API，Supabase 承载 PostgreSQL，GitHub Actions 每天运行 Python pipeline。第一版不需要常驻服务器、Redis 或 Celery。

## 最小云端配置

1. 在 Supabase 创建 Free project。
2. 打开 SQL Editor，执行 `supabase/migrations/001_initial.sql`。
3. 从 **Connect → Session pooler** 复制连接字符串，保留 `sslmode=require`。不要选择 ORM；GitHub Actions 里的 Python batch 是持续连接，更适合 Session pooler（端口 5432）。
4. 在 GitHub 仓库的 **Settings → Secrets and variables → Actions** 添加：
   - `DATABASE_URL`
   - `OPENAI_API_KEY`
   - `OPENALEX_API_KEY`
5. 在 Vercel 项目的 **Settings → Environment Variables** 添加同一个 `DATABASE_URL`，勾选 Production、Preview 和 Development，然后重新部署。它只在服务端读取 Supabase，不会发送到浏览器。
6. 在 Actions 页面手动运行一次 **Ingest arXiv**。首次保持 `max_sol_stories=1`，用于低成本验证整条链路。确认无误后，工作流会每天美国东部时间 00:17 自动执行，定时任务最多深度处理 6 篇。每日发现默认使用 arXiv 官方 RSS/Atom 和 bioRxiv 官方 Details API；arXiv 搜索 API 只保留为可选补抓方式，避免 GitHub 共享 IP 的 429 限流。

一条工作流依次完成：arXiv RSS + bioRxiv API 抓取 → 规则初筛 → OpenAlex 作者/机构与 US/Europe hard filter → GPT-5.6 Luna 批量质量筛选 → GPT-5.6 Sol 预生成五段解释、限制与术语 → 写入 `stories` / `explanations`。arXiv 候选读取 PDF；bioRxiv 第一版使用官方摘要并在限制中明确证据范围，避免 PDF 防护导致整批任务不稳定。模型响应不在 OpenAI 侧持久化（`store=false`），token 和估算成本写进数据库供 Debug 使用。

Feed 底部的五个主动反馈会直接写入 `feedback_events`，并由服务端的确定性规则更新 `preference_profile`：解释深度与内容兴趣始终分开；“多来这种 / 少来这种”更新主题、作者、机构和来源 affinity，随后重新计算 Personal Relevance 和 For You 分数。此逻辑不交给 LLM。

所有私钥只放在 GitHub/Vercel Secrets，不要提交到仓库，也不要粘贴到聊天中。完整变量说明见 `.env.example`。

## Pipeline 开发命令

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
PYTHONPATH=backend python -m unittest discover -s backend/tests
PYTHONPATH=backend python -m bioai_pipeline.cli ingest-arxiv --dry-run --lookback-hours 168 --max-results-per-query 30
PYTHONPATH=backend python -m bioai_pipeline.cli ingest-biorxiv --dry-run --lookback-hours 72 --max-results 60
PYTHONPATH=backend python -m bioai_pipeline.cli process-stories --max-papers 20 --max-sol-stories 1
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
- Phase 2：PostgreSQL、主动 feedback、preference 与 ranking（已跑通）
- Phase 3：arXiv、bioRxiv、PubMed/OpenAlex 真实数据（arXiv + bioRxiv 已接入）
- Phase 4：OpenAI Luna 初筛和 GPT-5.6 Sol 深度解释
- Phase 5：作者、机构、代表论文与可靠照片
- Phase 6：反馈驱动的个性化排序闭环

只有在 GitHub Actions 的定时可靠性或处理量不够时，才迁移到一台 Hetzner VPS。FastAPI、pgvector、Redis 和 Celery 都延后到出现明确需求时再增加。
