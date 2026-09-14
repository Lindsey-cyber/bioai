from __future__ import annotations

import re

from bioai_pipeline.models import ArxivPaper, HeuristicResult


AI_KEYWORDS = {
    "machine learning",
    "deep learning",
    "foundation model",
    "language model",
    "transformer",
    "generative",
    "representation learning",
    "artificial intelligence",
    "neural network",
}

BIO_KEYWORDS = {
    "protein",
    "enzyme",
    "molecule",
    "drug",
    "genome",
    "genomic",
    "gene",
    "cell biology",
    "cellular",
    "single cell",
    "single-cell",
    "clinical",
    "biomedical",
    "brain",
    "neuroscience",
    "neuroimaging",
    "connectome",
    "electrophysiology",
    "brain-computer interface",
}

TOPIC_KEYWORDS = {
    "neuroscience": {
        "brain",
        "neuroscience",
        "neural activity",
        "neuron",
        "cognition",
        "electrophysiology",
    },
    "neuroimaging": {"neuroimaging", "fmri", "mri", "eeg", "meg", "connectome"},
    "brain-computer interfaces": {"brain-computer interface", "bci", "neural decoding"},
    "protein design": {"protein design", "protein language model", "enzyme design"},
    "drug discovery": {"drug discovery", "drug design", "molecular generation", "docking"},
    "genomics": {"genome", "genomic", "gene expression", "dna", "rna"},
    "single-cell biology": {"single-cell", "single cell", "spatial transcriptomics"},
    "biomedical ai": {"biomedical", "clinical", "medical"},
}


def _contains(text: str, keyword: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", text) is not None


def classify_with_rules(paper: ArxivPaper) -> HeuristicResult:
    text = f"{paper.title} {paper.abstract}".lower()
    ai_matches = tuple(sorted(term for term in AI_KEYWORDS if _contains(text, term)))
    bio_matches = tuple(sorted(term for term in BIO_KEYWORDS if _contains(text, term)))
    qbio_category = paper.source == "biorxiv" or any(
        category.startswith("q-bio.") for category in paper.categories
    )
    ai_category = any(category in {"cs.AI", "cs.LG", "stat.ML", "cs.CV"} for category in paper.categories)

    accepted = bool((qbio_category and ai_matches) or (ai_category and bio_matches) or (ai_matches and bio_matches))
    topics = tuple(
        topic
        for topic, keywords in TOPIC_KEYWORDS.items()
        if any(_contains(text, keyword) for keyword in keywords)
    )
    evidence = min(len(ai_matches), 3) + min(len(bio_matches), 3)
    relevance = min(1.0, 0.30 + evidence * 0.10 + (0.15 if qbio_category else 0) + (0.10 if topics else 0))

    return HeuristicResult(
        accepted=accepted,
        relevance=round(relevance if accepted else 0.0, 3),
        topics=topics,
        matched_ai_terms=ai_matches,
        matched_bio_terms=bio_matches,
    )
