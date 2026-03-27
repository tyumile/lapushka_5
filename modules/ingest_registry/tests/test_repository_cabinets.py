import tempfile
import unittest
from pathlib import Path

from db.repository import RegistryRepository


class RepositoryCabinetIsolationTestCase(unittest.TestCase):
    def test_sources_files_and_events_are_isolated_by_cabinet(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repository = RegistryRepository(Path(tmpdir) / "registry.sqlite3")
            repository.initialize()

            default_source_id = repository.add_source(
                "google_drive",
                "https://example.com/default",
                "Google Drive: Default",
                cabinet_id="default",
            )
            test_source_id = repository.add_source(
                "google_drive",
                "https://example.com/test",
                "Google Drive: Test",
                cabinet_id="test",
            )

            repository.upsert_file(
                {
                    "cabinet_id": "default",
                    "source_id": default_source_id,
                    "source_name": "Google Drive: Default",
                    "source_type": "google_drive",
                    "external_id": "default-1",
                    "file_path": "default/report.pdf",
                    "file_name": "report.pdf",
                    "file_date": "2026-03-27T10:00:00+00:00",
                    "created_at_remote": "2026-03-27T10:00:00+00:00",
                    "modified_at_remote": "2026-03-27T10:00:00+00:00",
                    "page_count": 2,
                    "status": "ready",
                    "file_size": 100,
                }
            )
            repository.upsert_file(
                {
                    "cabinet_id": "test",
                    "source_id": test_source_id,
                    "source_name": "Google Drive: Test",
                    "source_type": "google_drive",
                    "external_id": "test-1",
                    "file_path": "test/spec.pdf",
                    "file_name": "spec.pdf",
                    "file_date": "2026-03-27T11:00:00+00:00",
                    "created_at_remote": "2026-03-27T11:00:00+00:00",
                    "modified_at_remote": "2026-03-27T11:00:00+00:00",
                    "page_count": 5,
                    "status": "ready",
                    "file_size": 200,
                }
            )

            repository.add_event("sync", "done", "default sync", "default artifacts", cabinet_id="default")
            repository.add_event("sync", "done", "test sync", "test artifacts", cabinet_id="test")

            default_sources = repository.list_sources(cabinet_id="default")
            test_sources = repository.list_sources(cabinet_id="test")
            self.assertTrue(any(item["source_url"] == "https://example.com/default" for item in default_sources))
            self.assertFalse(any(item["source_url"] == "https://example.com/test" for item in default_sources))
            self.assertTrue(any(item["source_url"] == "https://example.com/test" for item in test_sources))
            self.assertIsNone(repository.get_source(test_source_id, cabinet_id="default"))

            default_files = repository.list_files(cabinet_id="default")
            test_files = repository.list_files(cabinet_id="test")
            self.assertEqual([item["file_name"] for item in default_files], ["report.pdf"])
            self.assertEqual([item["file_name"] for item in test_files], ["spec.pdf"])

            default_events = repository.list_events(cabinet_id="default")
            test_events = repository.list_events(cabinet_id="test")
            self.assertEqual([item["summary"] for item in default_events], ["default sync"])
            self.assertEqual([item["summary"] for item in test_events], ["test sync"])

    def test_initialize_migrates_legacy_file_registry_without_default_column_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "legacy.sqlite3"
            repository = RegistryRepository(db_path)
            connection = repository._connect()
            connection.executescript(
                """
                CREATE TABLE file_registry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER,
                    source_name TEXT NOT NULL,
                    source_type TEXT NOT NULL DEFAULT '',
                    external_id TEXT NOT NULL UNIQUE,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_date TEXT NOT NULL,
                    created_at_remote TEXT,
                    modified_at_remote TEXT,
                    page_count INTEGER,
                    status TEXT NOT NULL,
                    file_size INTEGER NOT NULL DEFAULT 0,
                    first_seen_at TEXT,
                    last_seen_at TEXT,
                    is_deleted INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                INSERT INTO file_registry (
                    source_id,
                    source_name,
                    source_type,
                    external_id,
                    file_path,
                    file_name,
                    file_date,
                    status,
                    file_size,
                    created_at,
                    updated_at
                )
                VALUES (
                    1,
                    'legacy-source',
                    'local_upload',
                    'legacy-1',
                    'legacy/file.pdf',
                    'file.pdf',
                    '2026-03-27T10:00:00+00:00',
                    'ready',
                    10,
                    '2026-03-27T10:00:00+00:00',
                    '2026-03-27T10:00:00+00:00'
                );
                """
            )
            connection.commit()
            connection.close()

            repository.initialize()

            migrated_files = repository.list_files(cabinet_id="default")
            self.assertEqual(len(migrated_files), 1)
            self.assertEqual(migrated_files[0]["external_id"], "legacy-1")
            self.assertEqual(migrated_files[0]["cabinet_id"], "default")


if __name__ == "__main__":
    unittest.main()
