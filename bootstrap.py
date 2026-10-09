"""Run with Python 3.11+; generates an absolute-path MCP config for this computer."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description='Install WeChat Article MCP into a local venv.')
parser.add_argument('--skip-browser',action='store_true',help='Use installed Edge/Chrome or install Chromium later.')
parser.add_argument('--register-codex',action='store_true',help='Run self-test and merge this server into Codex config.toml, backing it up first.')
parser.add_argument('--codex-config',help='Explicit Codex config path; default CODEX_HOME/config.toml or ~/.codex/config.toml.')
args=parser.parse_args()
if sys.version_info<(3,11):raise SystemExit('Python 3.11+ is required.')
venv=root/'.venv'
python=venv/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
if not python.exists():subprocess.run([sys.executable,'-m','venv',str(venv)],check=True)
subprocess.run([str(python),'-m','pip','install','-r',str(root/'requirements.txt')],check=True)
if not args.skip_browser:
    subprocess.run([str(python),'-m','playwright','install','chromium'],check=True)
config={'mcpServers':{'wechat-article-export':{'command':str(python),'args':[str(root/'server.py')],'env':{'PYTHONUTF8':'1','WECHAT_MCP_OUTPUT_DIR':str(root/'exports')}}}}
(root/'mcp-config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
from codex_config import fragment,register
(root/'codex-config.toml').write_text(fragment(root,python),encoding='utf-8')
if args.register_codex:
    subprocess.run([str(python),str(root/'tests/smoke_mcp.py')],check=True)
    print(json.dumps(register(root,python,args.codex_config),ensure_ascii=False))
print('Setup complete. Codex: use codex-config.toml (not the generic JSON). Restart MCP/desktop app, then call doctor.')
print('Generated config:',root/'mcp-config.json')
print('Generated Codex config:',root/'codex-config.toml')
