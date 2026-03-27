import tempfile
import unittest
from pathlib import Path

from app.config import Settings
from app.connectors import RemoteFile
from app.service import IngestRegistryService
from db.repository import RegistryRepository


class FakeGoogleClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def list_files(self, source_url: str):
        self.calls.append(source_url)
        files = [
            RemoteFile(
                external_id=f"gdrive-{index}",
                file_path=f"folder/file-{index}.pdf",
                file_name=f"file-{index}.pdf",
                file_size=1000 + index,
                page_count=1,
                created_at="2026-03-27T10:00:00+00:00",
                modified_at="2026-03-27T10:00:00+00:00",
            )
            for index in range(1, 12)
        ]
        return "ЭОМ", files


class GoogleDriveCabinet111TestCase(unittest.TestCase):
    def test_add_source_auto_sync_and_manual_sync_for_cabinet_111(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            settings = Settings(
                module_name="ingest_registry",
                host="127.0.0.1",
                port=8001,
                base_dir=base_dir,
                data_dir=base_dir / "data",
                storage_dir=base_dir / "data" / "storage",
                upload_dir=base_dir / "data" / "storage" / "uploads",
                bootstrap_dir=base_dir / "data" / "storage" / "bootstrap",
                db_path=base_dir / "data" / "ingest_registry.sqlite3",
                log_path=base_dir / "logs" / "ingest_registry.log",
            )
            repository = RegistryRepository(settings.db_path)
            service = IngestRegistryService(settings, repository)
            fake_google = FakeGoogleClient()
            service.google_client = fake_google

            service.bootstrap()
            source_id = service.add_source(
                "google_drive",
                "https://drive.google.com/drive/folders/test-folder?usp=sharing",
                cabinet_id="111",
            )

            dashboard_111 = service.dashboard(cabinet_id="111")
            dashboard_default = service.dashboard(cabinet_id="default")
            self.assertEqual(len(dashboard_111["sources"]), 1)
            self.assertEqual(dashboard_111["sources"][0]["title"], "Google Drive: ЭОМ")
            self.assertEqual(len(dashboard_111["files"]), 11)
            self.assertEqual(len(dashboard_default["files"]), 0)
            self.assertEqual(fake_google.calls, ["https://drive.google.com/drive/folders/test-folder?usp=sharing"])

            service.sync_source(source_id, cabinet_id="111")

            dashboard_111_after_manual_sync = service.dashboard(cabinet_id="111")
            self.assertEqual(len(dashboard_111_after_manual_sync["files"]), 11)
            self.assertEqual(
                [item["action_type"] for item in dashboard_111_after_manual_sync["recent_logs"]],
                ["sync", "sync", "source_add"],
            )
            self.assertEqual(len(fake_google.calls), 2)


if __name__ == "__main__":
    unittest.main()
