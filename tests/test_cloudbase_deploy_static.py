import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CloudBaseDeployStaticTest(unittest.TestCase):
    def test_cloudbase_workflow_uses_demo_site_and_secret_names(self):
        workflow = ROOT / ".github" / "workflows" / "deploy-cloudbase.yml"
        text = workflow.read_text(encoding="utf-8")

        self.assertIn("demo-site", text)
        self.assertIn("/storyalbum-geo", text)
        self.assertIn("TCB_SECRET_ID", text)
        self.assertIn("TCB_SECRET_KEY", text)
        self.assertIn("TCB_ENV_ID", text)
        self.assertIn("scripts/check_cloudbase_static.py", text)
        self.assertNotRegex(text, r"(?i)(?<![A-Za-z0-9])[0-9a-f]{32}(?![A-Za-z0-9])")

    def test_cloudbase_deploy_doc_covers_required_setup(self):
        doc = (ROOT / "DEPLOY_CLOUDBASE.md").read_text(encoding="utf-8")

        self.assertIn("TCB_SECRET_ID", doc)
        self.assertIn("TCB_SECRET_KEY", doc)
        self.assertIn("TCB_ENV_ID", doc)
        self.assertIn("/storyalbum-geo", doc)
        self.assertIn("demo-site", doc)
        self.assertIn("python scripts/check_cloudbase_static.py", doc)
        self.assertNotRegex(doc, r"(?i)(?<![A-Za-z0-9])[0-9a-f]{32}(?![A-Za-z0-9])")

    def test_static_site_has_local_album_data_fallback(self):
        html = (ROOT / "demo-site" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "demo-site" / "app.js").read_text(encoding="utf-8")

        self.assertIn('src="data/geo_album.js"', html)
        self.assertIn('const DATA_URL = "data/geo_album.json"', js)
        self.assertIn("window.STORYALBUM_GEO_DATA", js)
        self.assertIn("fallbackSrc", js)
        self.assertIn("img.onerror", js)
        self.assertNotIn("restapi.amap.com", html + js)


if __name__ == "__main__":
    unittest.main()
