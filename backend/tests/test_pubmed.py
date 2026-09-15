from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET

from bioai_pipeline.filtering import classify_with_rules
from bioai_pipeline.sources.pubmed import PubmedClient


ARTICLE_XML = """
<PubmedArticle>
  <MedlineCitation>
    <PMID>12345678</PMID>
    <DateCompleted><Year>2026</Year><Month>09</Month><Day>13</Day></DateCompleted>
    <Article>
      <Journal>
        <JournalIssue><PubDate><Year>2026</Year><Month>Sep</Month><Day>12</Day></PubDate></JournalIssue>
        <ISOAbbreviation>Nat Biotechnol</ISOAbbreviation>
      </Journal>
      <ArticleTitle>A foundation model for <i>cellular</i> phenotypes</ArticleTitle>
      <Abstract>
        <AbstractText Label="METHODS">We train a transformer and machine learning model.</AbstractText>
        <AbstractText Label="RESULTS">It predicts gene perturbation responses.</AbstractText>
      </Abstract>
      <AuthorList>
        <Author>
          <ForeName>Ada</ForeName><LastName>Example</LastName>
          <AffiliationInfo><Affiliation>Stanford University, USA.</Affiliation></AffiliationInfo>
        </Author>
      </AuthorList>
      <PublicationTypeList><PublicationType>Journal Article</PublicationType></PublicationTypeList>
    </Article>
    <KeywordList><Keyword>Single-cell</Keyword></KeywordList>
  </MedlineCitation>
  <PubmedData>
    <ArticleIdList>
      <ArticleId IdType="doi">10.1000/example</ArticleId>
      <ArticleId IdType="pmc">PMC1234567</ArticleId>
    </ArticleIdList>
  </PubmedData>
</PubmedArticle>
"""


class PubmedTest(unittest.TestCase):
    def test_parses_pubmed_article(self) -> None:
        paper = PubmedClient._parse_article(ET.fromstring(ARTICLE_XML))

        self.assertEqual(paper.arxiv_id, "pubmed:12345678")
        self.assertEqual(paper.source, "pubmed")
        self.assertEqual(paper.title, "A foundation model for cellular phenotypes")
        self.assertEqual(paper.published_at.date().isoformat(), "2026-09-12")
        self.assertEqual(paper.authors[0].affiliation, "Stanford University, USA.")
        self.assertEqual(paper.source_metadata["journal"], "Nat Biotechnol")
        self.assertEqual(paper.source_metadata["pmcid"], "PMC1234567")

    def test_pubmed_record_counts_as_biological_context(self) -> None:
        paper = PubmedClient._parse_article(ET.fromstring(ARTICLE_XML))

        self.assertTrue(classify_with_rules(paper).accepted)


if __name__ == "__main__":
    unittest.main()
