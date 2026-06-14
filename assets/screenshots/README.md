# Screenshot Guide

Use the polished dashboard for LinkedIn, portfolio, and GitHub README screenshots. Use `Auth: off` for most
screenshots so the UI clearly shows that no API key is required for the local demo.

Screenshot tips:

- Use the polished dashboard.
- Use Auth: off for most screenshots.
- Do not show API keys.
- Do not show raw restricted context.
- Capture the Ask Assistant page, Evaluation page, and Logs page.
- Keep Screenshot mode enabled when capturing final images.

Before taking screenshots:

1. Start FastAPI backend.
2. Start dashboard.
3. Use screenshot mode.
4. Keep Auth: off unless specifically demonstrating API-key auth.
5. Do not show API keys.
6. Do not show raw debug output.

Expected screenshots:

1. `01-dashboard-home.png` - dashboard landing/health page
2. `02-finance-answer-with-citations.png` - `finance_user` invoice answer with citations
3. `03-intern-safe-abstention.png` - `intern_user` blocked from finance answer
4. `04-gitlab-public-answer.png` - public GitLab-style remote work answer
5. `05-evidence-gate-abstention.png` - unreleased acquisition plan safe abstention
6. `06-evaluation-metrics.png` - eval page showing sample/gitlab metrics
7. `07-sanitized-query-logs.png` - sanitized query logs

Use real screenshots from a local run. Do not include secrets, API keys, private documents, or raw restricted context.

Do not commit screenshots containing real secrets, API keys, private documents, or raw restricted context.
