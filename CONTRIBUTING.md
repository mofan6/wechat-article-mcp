# Contributing

Designed By MOTAN.

Use Python 3.11+ and a virtual environment. Install requirements.txt; use an installed Edge/Chrome or install Playwright Chromium. Run:

```sh
python -m unittest discover -s tests
python tests/smoke_mcp.py
```

The smoke test speaks real stdio MCP to a subprocess and exports a synthetic article; it does not require a WeChat login or network. Review Windows and Linux CI before merging.

Never commit .state/, .venv/, exports/, real authenticated URLs, credentials, logs, or downloaded articles. Keep stdout reserved for the MCP protocol. Avoid making advertisement removal an automatic destructive guess: preserve explicit Agent review and source data.

Open a focused issue or pull request with the trigger, expected result, implementation, and validation. Bug reports should omit credentials and private content.
