from pathlib import Path
import tempfile,tomllib,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from codex_config import register,fragment

class CodexConfigTests(unittest.TestCase):
    def test_merge_backup_and_idempotence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);config=root/'config.toml';original='# user comment\nmodel = "existing-model"\n[mcp_servers.other]\ncommand = "other-executable"\n'
            config.write_text(original,encoding='utf-8')
            result=register(root,sys.executable,config)
            self.assertEqual(Path(result['backup']).read_text(),original)
            self.assertTrue(config.read_text().startswith(original))
            data=tomllib.loads(config.read_text());self.assertEqual(data['model'],'existing-model');self.assertEqual(data['mcp_servers']['other']['command'],'other-executable')
            self.assertEqual(data['mcp_servers']['wechat-article-export']['tool_timeout_sec'],300)
            self.assertEqual(register(root,sys.executable,config)['status'],'already_configured')
    def test_existing_conflict_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);config=root/'config.toml';text='[mcp_servers.wechat-article-export]\ncommand="existing"\n';config.write_text(text)
            with self.assertRaises(ValueError):register(root,sys.executable,config)
            self.assertEqual(config.read_text(),text)
    def test_paths_with_spaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=tomllib.loads(fragment(Path(tmp)/'中文 有空格',Path(tmp)/'some python.exe'))
            self.assertIn('中文 有空格',data['mcp_servers']['wechat-article-export']['cwd'])

if __name__=='__main__':unittest.main()
