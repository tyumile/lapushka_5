import unittest

from app.connectors import (
    GoogleDriveFolderParser,
    count_pdf_pages,
    extract_google_file_id,
    extract_google_folder_id,
)


class ConnectorsTestCase(unittest.TestCase):
    def test_extract_google_folder_id(self) -> None:
        self.assertEqual(
            extract_google_folder_id("https://drive.google.com/drive/folders/abc123XYZ?usp=sharing"),
            "abc123XYZ",
        )

    def test_extract_google_file_id(self) -> None:
        self.assertEqual(
            extract_google_file_id("https://drive.google.com/file/d/file123/view?usp=drive_web"),
            "file123",
        )

    def test_google_folder_parser_reads_links_and_title(self) -> None:
        parser = GoogleDriveFolderParser()
        parser.feed(
            """
            <html>
              <head><title>Folder Name - Google Drive</title></head>
              <body>
                <a href="https://drive.google.com/file/d/file123/view?usp=drive_web">Report.pdf</a>
                <a href="https://drive.google.com/drive/folders/folder456">Nested</a>
              </body>
            </html>
            """
        )
        self.assertIn("Folder Name", parser.title)
        self.assertEqual(len(parser.entries), 2)

    def test_count_pdf_pages(self) -> None:
        payload = b"%PDF-1.4\n1 0 obj\n<< /Type /Page >>\nendobj\n2 0 obj\n<< /Type /Page >>\nendobj"
        self.assertEqual(count_pdf_pages(payload), 2)


if __name__ == "__main__":
    unittest.main()
