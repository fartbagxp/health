#!/usr/bin/env python3

"""
CDC Wonder Dataset Topic Cataloger

This script catalogs CDC Wonder datasets (D1-D250) into health topics defined
in health-data-topics.json. It uses keyword-based matching to automatically
classify datasets based on their page names and URLs.

Designed for periodic (e.g., weekly) execution to re-catalog as new datasets
become available or existing ones change.

Usage:
    python -m src.wonder.catalog
"""

import csv
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger("wonder-catalog")

# -----------------------------------------------------------------------------
# SEARCH TERM DEFINITIONS
#
# These mappings define which keywords/patterns in dataset URLs or page names
# trigger classification into specific health topics. Each topic has:
#   - patterns: list of regex patterns to match (case-insensitive)
#   - reason_template: explains why a dataset matches this topic
#
# To extend: add new patterns or create new topic entries as needed.
# -----------------------------------------------------------------------------

# Order matters: more specific patterns should come before general ones.
# For example, "Maternal & Child Health" (fetal, lbd) must be checked before
# "Mortality" to prevent fetal-deaths from being classified as general mortality.
TOPIC_SEARCH_TERMS: dict[str, dict[str, Any]] = {
    "Maternal & Child Health": {
        # Check FIRST - fetal/infant deaths are maternal & child health, not general mortality
        "patterns": [
            r"fetal",  # Fetal deaths
            r"lbd",  # Linked Birth/Infant Death
            r"infant",
        ],
        "reason_template": (
            "Dataset '{dataset_id}' maps to 'Maternal & Child Health' because its "
            "page name '{page_name}' contains fetal death or linked birth/infant death "
            "(LBD) patterns. LBD datasets link infant death records to corresponding "
            "birth certificates for analysis of infant mortality risk factors."
        ),
    },
    "Population Estimates": {
        # Check SECOND - birth-death-migration projections are demographics, not mortality
        "patterns": [
            r"bridged-race",  # Bridged-race population estimates
            r"single-race",  # Single-race population estimates
            r"population-projection",  # Population projections
            r"birth-death-migration",  # Birth/death/migration projections (demographics)
        ],
        "reason_template": (
            "Dataset '{dataset_id}' maps to 'Population Estimates' because its page "
            "name '{page_name}' contains population estimation patterns. Bridged-race "
            "and single-race datasets provide demographic population estimates used "
            "as denominators for calculating health rates."
        ),
    },
    "Birth & Natality": {
        "patterns": [
            r"natality",  # Direct natality datasets (birth data)
        ],
        "reason_template": (
            "Dataset '{dataset_id}' maps to 'Birth & Natality' because its page name "
            "'{page_name}' contains natality/birth-related keywords. Natality datasets "
            "provide birth statistics including birth rates, birth weights, maternal "
            "characteristics, and prenatal care information."
        ),
    },
    "Cancer": {
        "patterns": [
            r"cancer",  # Cancer incidence, mortality, survival
            r"cancermort",  # Cancer mortality specifically
            r"cancermir",  # Cancer mortality-incidence ratio
            r"cancernpcr",  # National Program of Cancer Registries
        ],
        "reason_template": (
            "Dataset '{dataset_id}' maps to 'Cancer' because its page name "
            "'{page_name}' contains cancer-related keywords. These datasets cover "
            "cancer incidence rates, cancer mortality, survival statistics, and "
            "data from the National Program of Cancer Registries (NPCR)."
        ),
    },
    "Infectious Diseases": {
        "patterns": [
            r"aids",  # HIV/AIDS data
            r"tb(?:-|$|v)",  # Tuberculosis (tb-v2023, tb.html, etc.)
            r"std",  # Sexually transmitted diseases
            r"tuberculosis",
        ],
        "reason_template": (
            "Dataset '{dataset_id}' maps to 'Infectious Diseases' because its page "
            "name '{page_name}' contains patterns for AIDS, tuberculosis (TB), or "
            "sexually transmitted diseases (STD). These are key infectious disease "
            "surveillance datasets tracking reportable conditions."
        ),
    },
    "Vaccinations & Immunizations": {
        "patterns": [
            r"vaers",  # Vaccine Adverse Event Reporting System
            r"vaccine",
            r"immunization",
        ],
        "reason_template": (
            "Dataset '{dataset_id}' maps to 'Vaccinations & Immunizations' because "
            "its page name '{page_name}' contains VAERS or vaccine-related keywords. "
            "VAERS (Vaccine Adverse Event Reporting System) tracks reported adverse "
            "events following vaccination."
        ),
    },
    "Environmental Health": {
        "patterns": [
            r"nasa",  # NASA environmental data (NLDAS, PM2.5, etc.)
            r"nldas",  # North America Land Data Assimilation System
            r"heatwave",  # Heat wave days
            r"nca",  # National Climate Assessment data
            r"insolar",  # Insolation (sunlight)
            r"precipitation",
            r"pm(?:2\.5|25)?",  # Particulate matter
            r"lst",  # Land Surface Temperature
        ],
        "reason_template": (
            "Dataset '{dataset_id}' maps to 'Environmental Health' because its page "
            "name '{page_name}' contains environmental/climate data patterns. These "
            "datasets from NASA and NCA provide environmental exposure data including "
            "air quality (PM2.5), temperature, precipitation, and heat wave metrics."
        ),
    },
    "Notifiable Conditions": {
        "patterns": [
            r"nndss",  # National Notifiable Diseases Surveillance System
        ],
        "reason_template": (
            "Dataset '{dataset_id}' maps to 'Notifiable Conditions' because its page "
            "name '{page_name}' contains NNDSS (National Notifiable Diseases "
            "Surveillance System). This system tracks diseases required by law to be "
            "reported to public health authorities."
        ),
    },
    "Mortality": {
        # Check LAST - general mortality patterns after specific ones are handled
        "patterns": [
            r"cmf",  # Compressed Mortality File
            r"ucd",  # Underlying Cause of Death
            r"mcd",  # Multiple Cause of Death
            r"mortality",  # General mortality
        ],
        "reason_template": (
            "Dataset '{dataset_id}' maps to 'Mortality' because its page name "
            "'{page_name}' matches mortality-related patterns (CMF=Compressed Mortality "
            "File, UCD=Underlying Cause of Death, MCD=Multiple Cause of Death). These "
            "datasets track death rates and causes of death across populations."
        ),
    },
}


@dataclass
class DatasetMapping:
    """Represents a CDC Wonder dataset mapped to a health topic."""

    dataset_id: str
    page_name: str
    final_url: str
    topic: str
    category: str
    reason: str
    years: str


def load_dataset_map(path: Path) -> list[dict[str, str]]:
    """Load the dataset_map.csv file containing D1-D250 mappings."""
    datasets = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Only include datasets that successfully resolved (have a page_name)
            if row.get("page_name") and row.get("discovery") == "redirect":
                datasets.append(row)
    log.info(f"Loaded {len(datasets)} active datasets from {path}")
    return datasets


def load_topics(path: Path) -> dict[str, Any]:
    """Load the health-data-topics.json file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_topic_to_category_map(topics_data: dict[str, Any]) -> dict[str, str]:
    """Build a mapping from topic name to category name."""
    topic_to_category = {}
    for category_obj in topics_data.get("health", []):
        category_name = category_obj.get("category", "")
        for topic in category_obj.get("topics", []):
            topic_name = topic.get("name", "")
            if topic_name:
                topic_to_category[topic_name] = category_name
    return topic_to_category


def classify_dataset(
    dataset: dict[str, str],
    topic_to_category: dict[str, str],
) -> DatasetMapping | None:
    """
    Classify a dataset into a health topic based on its page name.

    Returns None if no matching topic is found.
    """
    dataset_id = dataset.get("id", "")
    page_name = dataset.get("page_name", "").lower()
    final_url = dataset.get("final_url", "")
    years = dataset.get("years", "")

    # Check each topic's patterns against the page name
    for topic_name, config in TOPIC_SEARCH_TERMS.items():
        for pattern in config["patterns"]:
            if re.search(pattern, page_name, re.IGNORECASE):
                category = topic_to_category.get(topic_name, "Unknown")
                reason = config["reason_template"].format(
                    dataset_id=dataset_id,
                    page_name=dataset.get("page_name", ""),
                )
                return DatasetMapping(
                    dataset_id=dataset_id,
                    page_name=dataset.get("page_name", ""),
                    final_url=final_url,
                    topic=topic_name,
                    category=category,
                    reason=reason,
                    years=years,
                )

    return None


@dataclass
class UnmappedDataset:
    """Represents a CDC Wonder dataset that could not be mapped to any topic."""

    dataset_id: str
    page_name: str
    final_url: str
    reason: str


def catalog_datasets(
    dataset_map_path: Path,
    topics_path: Path,
) -> tuple[list[DatasetMapping], list[UnmappedDataset]]:
    """
    Catalog all CDC Wonder datasets into health topics.

    Returns:
        tuple: (list of DatasetMapping for classified datasets,
                list of UnmappedDataset for datasets that couldn't be classified)
    """
    datasets = load_dataset_map(dataset_map_path)
    topics_data = load_topics(topics_path)
    topic_to_category = build_topic_to_category_map(topics_data)

    mappings = []
    unmapped = []

    for dataset in datasets:
        mapping = classify_dataset(dataset, topic_to_category)
        if mapping:
            mappings.append(mapping)
        else:
            dataset_id = dataset.get("id", "unknown")
            page_name = dataset.get("page_name", "")
            final_url = dataset.get("final_url", "")
            reason = (
                f"Dataset '{dataset_id}' with page '{page_name}' could not be mapped "
                f"to any topic. None of the defined search patterns matched the page name. "
                f"Consider adding a new pattern to TOPIC_SEARCH_TERMS if this dataset "
                f"belongs to an existing topic, or create a new topic category."
            )
            unmapped.append(
                UnmappedDataset(
                    dataset_id=dataset_id,
                    page_name=page_name,
                    final_url=final_url,
                    reason=reason,
                )
            )

    log.info(f"Classified {len(mappings)} datasets into topics")
    if unmapped:
        log.warning(f"Unmapped datasets: {[u.dataset_id for u in unmapped]}")

    return mappings, unmapped


def dataset_id_sort_key(dataset_id: str) -> int:
    """Extract numeric portion of dataset_id for sorting (e.g., 'D27' -> 27)."""
    match = re.match(r"D(\d+)", dataset_id)
    return int(match.group(1)) if match else 0


def write_topics_mapping(
    output_path: Path,
    mappings: list[DatasetMapping],
    unmapped: list[UnmappedDataset],
) -> None:
    """
    Write the topic mappings to a separate JSON file.

    Writes to data/raw/wonder/topics_mapping.json with mappings sorted by dataset_id.
    """
    # Convert mappings to serializable format, sorted by dataset_id numerically
    datasets_list = []
    for m in sorted(mappings, key=lambda x: dataset_id_sort_key(x.dataset_id)):
        datasets_list.append(
            {
                "dataset_id": m.dataset_id,
                "page_name": m.page_name,
                "final_url": m.final_url,
                "topic": m.topic,
                "category": m.category,
                "reason": m.reason,
                "years": m.years,
            }
        )

    # Convert unmapped to serializable format, sorted by dataset_id numerically
    unmapped_list = []
    for u in sorted(unmapped, key=lambda x: dataset_id_sort_key(x.dataset_id)):
        unmapped_list.append(
            {
                "dataset_id": u.dataset_id,
                "page_name": u.page_name,
                "final_url": u.final_url,
                "reason": u.reason,
            }
        )

    output_data = {
        "description": "CDC Wonder dataset to health topic mappings",
        "generated_by": "src/wonder/catalog.py",
        "total_mapped": len(datasets_list),
        "total_unmapped": len(unmapped_list),
        "mappings": datasets_list,
        "unmapped": unmapped_list,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
        f.write("\n")

    log.info(f"Wrote {len(datasets_list)} mappings to {output_path}")


def print_mapping_summary(
    mappings: list[DatasetMapping],
    unmapped: list[UnmappedDataset],
) -> None:
    """Print a summary of dataset classifications by topic."""
    from collections import Counter

    topic_counts = Counter(m.topic for m in mappings)

    print("\n" + "=" * 60)
    print("CDC Wonder Dataset Classification Summary")
    print("=" * 60)

    for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1]):
        print(f"  {topic}: {count} datasets")

    print(f"\nTotal classified: {len(mappings)} datasets")
    print(f"Total unmapped: {len(unmapped)} datasets")
    print("=" * 60)

    # Print detailed explanation for unmapped datasets
    if unmapped:
        print("\n" + "=" * 60)
        print("UNMAPPED DATASETS - Require Manual Review")
        print("=" * 60)
        for u in sorted(unmapped, key=lambda x: dataset_id_sort_key(x.dataset_id)):
            print(f"\n  {u.dataset_id}: {u.page_name}")
            print(f"    URL: {u.final_url}")
            print(f"    Reason: {u.reason}")
        print("\n" + "=" * 60)


def print_example_mapping(mappings: list[DatasetMapping], dataset_id: str) -> None:
    """Print detailed explanation for a specific dataset mapping."""
    for m in mappings:
        if m.dataset_id == dataset_id:
            print(f"\n{'=' * 60}")
            print(f"Dataset: {m.dataset_id}")
            print(f"Page: {m.page_name}")
            print(f"URL: {m.final_url}")
            print(f"Topic: {m.topic}")
            print(f"Category: {m.category}")
            print(f"Years: {m.years}")
            print(f"\nReason:\n{m.reason}")
            print("=" * 60)
            return

    print(f"Dataset {dataset_id} not found in mappings")


def print_datasets_by_topic(mapping_path: Path) -> None:
    """
    Print all datasets grouped by health topic, sorted by dataset_id (D1-D250).

    Reads from data/raw/wonder/topics_mapping.json and displays datasets
    organized by their assigned health topic.
    """
    from collections import defaultdict

    with open(mapping_path, encoding="utf-8") as f:
        data = json.load(f)

    # Group mappings by topic
    by_topic: dict[str, list[dict]] = defaultdict(list)
    for m in data.get("mappings", []):
        by_topic[m["topic"]].append(m)

    # Sort datasets within each topic by dataset_id numerically
    for topic in by_topic:
        by_topic[topic].sort(key=lambda x: dataset_id_sort_key(x["dataset_id"]))

    # Print header
    print("\n" + "=" * 70)
    print("CDC Wonder Datasets by Health Topic (sorted D1-D250)")
    print("=" * 70)

    # Print each topic with its datasets
    for topic in sorted(by_topic.keys()):
        datasets = by_topic[topic]
        print(f"\n### {topic} ({len(datasets)} datasets)")
        print("-" * 50)
        for d in datasets:
            years = f" ({d['years']})" if d.get("years") else ""
            print(f"  {d['dataset_id']}: {d['page_name']}{years}")

    # Print unmapped if any
    unmapped = data.get("unmapped", [])
    if unmapped:
        print(f"\n### UNMAPPED ({len(unmapped)} datasets)")
        print("-" * 50)
        for u in sorted(unmapped, key=lambda x: dataset_id_sort_key(x["dataset_id"])):
            print(f"  {u['dataset_id']}: {u['page_name']}")

    print("\n" + "=" * 70)
    print(
        f"Total: {data.get('total_mapped', 0)} mapped, {data.get('total_unmapped', 0)} unmapped"
    )
    print("=" * 70)


def main() -> None:
    """Main entry point for the cataloger."""
    # Paths relative to project root
    project_root = Path(__file__).parent.parent.parent
    dataset_map_path = project_root / "data" / "raw" / "wonder" / "dataset_map.csv"
    topics_path = project_root / "data" / "raw" / "health-data-topics.json"
    output_path = project_root / "data" / "raw" / "wonder" / "topics_mapping.json"

    # Catalog datasets
    mappings, unmapped = catalog_datasets(dataset_map_path, topics_path)

    # Write to topics_mapping.json (separate file, sorted by dataset_id)
    write_topics_mapping(output_path, mappings, unmapped)

    # Print summary (includes unmapped explanations at the end)
    print_mapping_summary(mappings, unmapped)

    # Print datasets grouped by topic, sorted by dataset_id (D1-D250)
    print_datasets_by_topic(output_path)


if __name__ == "__main__":
    main()
