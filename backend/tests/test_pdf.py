from __future__ import annotations

import unittest

from bioai_pipeline.sources.pdf import clean_extracted_text


class PdfTextTest(unittest.TestCase):
    def test_removes_postgres_incompatible_nul_characters(self) -> None:
        value = "multimodal sample S(s) =\x00tensor\t value"

        self.assertEqual(
            clean_extracted_text(value),
            "multimodal sample S(s) =tensor value",
        )


if __name__ == "__main__":
    unittest.main()
