# AI × Bio Feed

一个面向个人使用的 AI × Bio 新闻 Feed。目标是用极简的阅读流程，帮助用户快速理解美国和欧洲的重要论文、公司、机构与研究者动态。

当前完成的是 Phase 1：基于 mock data 的完整可点击前端，包括 Feed、Story 五段解释、专业解释展开、术语、作者和机构 profile、反馈、Saved、Settings 以及移动端适配。

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
- Phase 2：FastAPI、PostgreSQL、feedback、preference 与 ranking
- Phase 3：arXiv、bioRxiv、PubMed/OpenAlex 真实数据
- Phase 4：OpenAI 快速模型初筛和深度解释
- Phase 5：作者、机构、代表论文与可靠照片
- Phase 6：反馈驱动的个性化排序闭环

最终部署目标仍是单台 Hetzner VPS 上的 Next.js、FastAPI、PostgreSQL/pgvector、Redis/Celery 和 Docker Compose。当前前端脚手架只用于快速验证 Phase 1 交互，后续接入后端时会收敛为标准 Next.js 项目结构。
