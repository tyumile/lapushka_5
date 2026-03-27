import tempfile
import unittest
from pathlib import Path

from app.config import Settings
from app.service import IngestRegistryService
from db.repository import RegistryRepository


class LocalUploadCabinetIsolationTestCase(unittest.TestCase):
    def test_local_uploads_are_isolated_by_cabinet_during_upload_and_sync(self) -> None:
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

            service.bootstrap()
            service.handle_upload("default.txt", b"default-cabinet", cabinet_id="default")
            service.handle_upload("test.txt", b"test-cabinet", cabinet_id="test")

            default_source_id = repository.ensure_local_source("default")
            test_source_id = repository.ensure_local_source("test")
            service.sync_source(default_source_id, cabinet_id="default")
            service.sync_source(test_source_id, cabinet_id="test")

            default_files = repository.list_files(cabinet_id="default")
            test_files = repository.list_files(cabinet_id="test")
            self.assertEqual([item["file_name"] for item in default_files], ["default.txt"])
            self.assertEqual([item["file_name"] for item in test_files], ["test.txt"])
            self.assertTrue(default_files[0]["file_path"].endswith("uploads/default/default.txt"))
            self.assertTrue(test_files[0]["file_path"].endswith("uploads/test/test.txt"))
            self.assertTrue((settings.upload_dir / "default" / "default.txt").exists())
            self.assertTrue((settings.upload_dir / "test" / "test.txt").exists())


if __name__ == "__main__":
    unittest.main()
