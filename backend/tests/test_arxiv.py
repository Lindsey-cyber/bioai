from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET

from bioai_pipeline.sources.arxiv import ArxivClient


ENTRY = """
<entry xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <id>https://arxiv.org/abs/2609.12345v2</id>
  <updated>2026-09-13T20:00:00+00:00</updated>
  <published>2026-09-12T20:00:00+00:00</published>
  <title>A foundation model for brain activity</title>
  <summary>We model neural activity.</summary>
  <author><name>Ada Example</name><arxiv:affiliation>Example University, USA</arxiv:affiliation></author>
  <link href="https://arxiv.org/pdf/2609.12345v2" title="pdf" rel="related" />
  <category term="q-bio.NC" />
  <arxiv:primary_category term="q-bio.NC" />
  <arxiv:doi>10.0000/example</arxiv:doi>
</entry>
"""

RSS_ENTRY = """
<entry xmlns="http://www.w3.org/2005/Atom"
       xmlns:arxiv="http://arxiv.org/schemas/atom"
       xmlns:dc="http://purl.org/dc/elements/1.1/">
  <id>oai:arXiv.org:2609.11937v1</id>
  <updated>2026-09-14T07:33:41+00:00</updated>
  <published>2026-09-14T00:00:00-04:00</published>
  <title>Learning biological representations</title>
  <summary>
    arXiv:2609.11937v1 Announce Type: new
    Abstract: We introduce a machine learning model for proteins.
  </summary>
  <link href="https://arxiv.org/abs/2609.11937" rel="alternate" type="text/html" />
  <category term="cs.LG" />
  <category term="q-bio.BM" />
  <arxiv:announce_type>new</arxiv:announce_type>
  <dc:creator>Ting Xu, Henry Leung</dc:creator>
</entry>
"""


class ArxivParserTest(unittest.TestCase):
    def test_parses_version_and_affiliation(self) -> None:
        parsed = ArxivClient()._parse_entry(ET.fromstring(ENTRY), "test")
        self.assertEqual(parsed.arxiv_id, "2609.12345")
        self.assertEqual(parsed.version, 2)
        self.assertEqual(parsed.authors[0].affiliation, "Example University, USA")
        self.assertEqual(parsed.primary_category, "q-bio.NC")

    def test_parses_daily_rss_entry(self) -> None:
        parsed = ArxivClient()._parse_entry(ET.fromstring(RSS_ENTRY), "rss")
        self.assertEqual(parsed.arxiv_id, "2609.11937")
        self.assertEqual(parsed.version, 1)
        self.assertEqual(parsed.abstract, "We introduce a machine learning model for proteins.")
        self.assertEqual([author.name for author in parsed.authors], ["Ting Xu", "Henry Leung"])
        self.assertEqual(parsed.primary_category, "cs.LG")
        self.assertEqual(parsed.pdf_url, "https://arxiv.org/pdf/2609.11937")
        self.assertEqual(parsed.announce_type, "new")


if __name__ == "__main__":
    unittest.main()
