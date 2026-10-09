"""Build a credential-free ZIP using an explicit file set. Designed By MOTAN."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import argparse,hashlib,json,re,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from version import __version__
parser=argparse.ArgumentParser();parser.add_argument('--output',default=str(root/'dist'));args=parser.parse_args()
output=Path(args.output).resolve();output.mkdir(parents=True,exist_ok=True)
name=f'wechat-article-mcp-v{__version__}.zip';archive=output/name
files=[p for p in root.iterdir() if p.is_file() and (p.suffix in {'.py','.md','.txt','.ps1'} or p.name in {'LICENSE','.gitignore','mcp-config.example.json'})]
files+=[p for folder in ['tests','scripts'] for p in (root/folder).glob('*.py')]
files=sorted(set(files))
with ZipFile(archive,'w',ZIP_DEFLATED) as z:
 for p in files:
  text=p.read_text(encoding='utf-8')
  if re.search(r'(?:key|pass_ticket)=[A-Za-z0-9%]{64,}',text):raise ValueError(f'Possible real credentials in {p.name}')
  z.write(p,'wechat-article-mcp/'+p.relative_to(root).as_posix())
with ZipFile(archive) as z:
 assert z.testzip() is None
 assert all(not any(part in {'.state','.venv','exports','__pycache__','.git'} for part in Path(n).parts) for n in z.namelist())
checksum=hashlib.sha256(archive.read_bytes()).hexdigest()
(output/'SHA256SUMS.txt').write_text(f'{checksum}  {name}\n',encoding='utf-8')
print(json.dumps({'archive':str(archive),'sha256':checksum,'files':len(files)},ensure_ascii=False))
