"""Generate/merge a single Codex MCP entry; leave other configuration intact."""
from pathlib import Path
import json
import os
import shutil
import tomllib
from datetime import datetime,timezone

SERVER='wechat-article-export'
def entry(root,python):
    return {'command':str(Path(python).resolve()),'args':[str(Path(root).resolve()/'server.py')],
            'cwd':str(Path(root).resolve()),'enabled':True,'startup_timeout_sec':30,'tool_timeout_sec':300,
            'env':{'PYTHONUTF8':'1','WECHAT_MCP_OUTPUT_DIR':str(Path(root).resolve()/'exports')}}

def fragment(root,python):
    data=entry(root,python);quote=lambda value:json.dumps(value,ensure_ascii=False)
    lines=[f'[mcp_servers.{SERVER}]']
    for key in ['command','args','cwd']:lines.append(f'{key} = {quote(data[key])}')
    lines+=['enabled = true','startup_timeout_sec = 30','tool_timeout_sec = 300','',f'[mcp_servers.{SERVER}.env]']
    lines += [key+' = '+quote(value) for key,value in data['env'].items()]
    value='\n'.join(lines)+'\n';assert tomllib.loads(value)['mcp_servers'][SERVER]==data
    return value

def register(root,python,config_path=None):
    base=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex'))).expanduser()
    path=Path(config_path).expanduser().resolve() if config_path else (base/'config.toml').resolve()
    text=path.read_text(encoding='utf-8-sig') if path.exists() else ''
    parsed=tomllib.loads(text)
    existing=parsed.get('mcp_servers',{}).get(SERVER)
    expected=entry(root,python)
    if existing is not None:
        if existing==expected:return {'status':'already_configured','config':str(path)}
        raise ValueError('This Codex config already contains wechat-article-export with different settings. Review/update only that entry using codex-config.toml; do not overwrite the whole config.')
    merged=text.rstrip()+'\n\n'+fragment(root,python)
    new=tomllib.loads(merged)
    assert new['mcp_servers'][SERVER]==expected
    del new['mcp_servers'][SERVER]
    if not new['mcp_servers']:del new['mcp_servers']
    original=dict(parsed)
    if original.get('mcp_servers')=={}:del original['mcp_servers']
    assert new==original,'Configuration merge changed unrelated settings'
    path.parent.mkdir(parents=True,exist_ok=True);backup=None
    if path.exists():
        backup=path.with_name(path.name+'.backup-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        shutil.copy2(path,backup)
    temp=path.with_name(path.name+'.wechat-mcp.tmp');temp.write_text(merged,encoding='utf-8');temp.replace(path)
    return {'status':'registered','config':str(path),'backup':str(backup) if backup else None}
