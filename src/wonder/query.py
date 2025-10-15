#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CDC WONDER Query Parameter Scraper using Playwright

This script uses Playwright to:
1. Navigate to CDC WONDER natality page
2. Click the "I Agree" button to accept data use terms
3. Extract all query parameters from the form (dropdowns, checkboxes, radio buttons, etc.)
4. Save the structured parameter data as JSON

Usage:
    python -m src.wonder.query <url> [--output <path>] [--headless]

Example:
    python -m src.wonder.query https://wonder.cdc.gov/natality-expanded-provisional.html
"""

import json
import logging
import argparse
import csv
import re
from pathlib import Path
from typing import Any, Optional

from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/raw/wonder/query_scrape.log"),
    ],
)
log = logging.getLogger("wonder-query")


def get_dataset_id_and_target_url(
    url: str, dmap_csv_path: str = "data/raw/wonder/dataset_map.csv"
) -> tuple[Optional[str], Optional[str]]:
    """
    Extract dataset ID from URL and get the target URL to scrape.
    If a controller URL is provided, looks up the actual page URL from the dmap CSV.

    Args:
        url: The CDC WONDER page URL (can be controller URL or direct page URL)
        dmap_csv_path: Path to the dmap CSV file

    Returns:
        Tuple of (dataset_id, target_url) where target_url is the actual page to scrape
    """
    dmap_file = Path(dmap_csv_path)
    if not dmap_file.exists():
        log.warning(f"dmap CSV not found at {dmap_csv_path}")
        return None, url

    # Check if this is a controller URL
    controller_match = re.search(r"/controller/datarequest/(D\d+)", url)

    try:
        with open(dmap_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                dataset_id = row.get("id", "")

                # If we have a controller URL, look it up by ID
                if controller_match and dataset_id == controller_match.group(1):
                    final_url = row.get("final_url", "")
                    if final_url and final_url != "":
                        log.info(f"Resolved controller URL to: {final_url}")
                        return dataset_id, final_url
                    else:
                        log.error(f"Dataset {dataset_id} has no final_url in dmap CSV")
                        return dataset_id, None

                # If not a controller URL, look up by final_url or page_name
                if not controller_match:
                    url_path = url.rstrip("/").split("/")[-1]
                    if (
                        row.get("final_url", "").endswith(url_path)
                        or row.get("page_name", "") == url_path
                    ):
                        return dataset_id, url
    except Exception as e:
        log.warning(f"Error reading dmap CSV: {e}")
        return None, url

    # If we got here with a controller URL but no match, that's an error
    if controller_match:
        return controller_match.group(1), None

    return None, url


def click_agree_button(page: Page) -> bool:
    """
    Attempts to find and click the "I Agree" button on CDC WONDER pages.

    Returns:
        bool: True if button was found and clicked, False otherwise
    """
    # Common selectors for the "I Agree" button
    agree_selectors = [
        "input[type='button'][value*='agree' i]",
        "input[type='submit'][value*='agree' i]",
        "button:has-text('I Agree')",
        "input[value='I Agree']",
        "input[name='agree']",
        "input[name='action-I Agree']",
        "#agree-button",
        ".agree-button",
    ]

    for selector in agree_selectors:
        try:
            log.info(f"Trying selector: {selector}")
            element = page.locator(selector).first
            if element.is_visible(timeout=2000):
                log.info(f"Found 'I Agree' button with selector: {selector}")
                element.click()
                # Wait for navigation or form to load (use domcontentloaded for faster response)
                page.wait_for_load_state("domcontentloaded", timeout=15000)
                return True
        except Exception as e:
            log.debug(f"Selector {selector} failed: {e}")
            continue

    log.warning("Could not find 'I Agree' button with any known selector")
    return False


def extract_select_options(page: Page) -> list[dict[str, Any]]:
    """
    Extract all <select> dropdown elements and their options.

    Returns:
        List of dictionaries containing select element info
    """
    selects = []
    select_elements = page.locator("select").all()

    for idx, select in enumerate(select_elements):
        try:
            name = select.get_attribute("name") or f"select_{idx}"
            select_id = select.get_attribute("id") or ""
            multiple = select.get_attribute("multiple") is not None

            # Get associated label if any
            label_text = ""
            if select_id:
                label = page.locator(f"label[for='{select_id}']").first
                try:
                    label_text = label.inner_text() if label.count() > 0 else ""
                except Exception as e:
                    log.error(f"Error extracting label for select {name}: {e}")

            # Extract all options
            options = []
            option_elements = select.locator("option").all()
            for opt in option_elements:
                opt_value = opt.get_attribute("value") or ""
                opt_text = opt.inner_text()
                opt_selected = opt.get_attribute("selected") is not None
                options.append(
                    {"value": opt_value, "text": opt_text, "selected": opt_selected}
                )

            selects.append(
                {
                    "type": "select",
                    "name": name,
                    "id": select_id,
                    "label": label_text.strip(),
                    "multiple": multiple,
                    "options": options,
                    "option_count": len(options),
                }
            )
            log.info(f"Extracted select '{name}' with {len(options)} options")
        except Exception as e:
            log.error(f"Error extracting select element {idx}: {e}")

    return selects


def extract_input_elements(page: Page) -> list[dict[str, Any]]:
    """
    Extract all <input> elements (text, checkbox, radio, hidden, etc.).

    Returns:
        List of dictionaries containing input element info
    """
    inputs = []
    input_elements = page.locator("input").all()

    for idx, inp in enumerate(input_elements):
        try:
            input_type = inp.get_attribute("type") or "text"
            name = inp.get_attribute("name") or f"input_{idx}"
            input_id = inp.get_attribute("id") or ""
            value = inp.get_attribute("value") or ""
            checked = inp.is_checked() if input_type in ["checkbox", "radio"] else None

            # Get associated label
            label_text = ""
            if input_id:
                label = page.locator(f"label[for='{input_id}']").first
                try:
                    label_text = label.inner_text() if label.count() > 0 else ""
                except Exception as e:
                    log.error(f"Error extracting label for input {name}: {e}")

            inputs.append(
                {
                    "type": f"input_{input_type}",
                    "name": name,
                    "id": input_id,
                    "label": label_text.strip(),
                    "value": value,
                    "checked": checked,
                }
            )
        except Exception as e:
            log.error(f"Error extracting input element {idx}: {e}")

    return inputs


def extract_textarea_elements(page: Page) -> list[dict[str, Any]]:
    """
    Extract all <textarea> elements.

    Returns:
        List of dictionaries containing textarea element info
    """
    textareas = []
    textarea_elements = page.locator("textarea").all()

    for idx, textarea in enumerate(textarea_elements):
        try:
            name = textarea.get_attribute("name") or f"textarea_{idx}"
            textarea_id = textarea.get_attribute("id") or ""
            value = textarea.input_value()

            # Get associated label
            label_text = ""
            if textarea_id:
                label = page.locator(f"label[for='{textarea_id}']").first
                try:
                    label_text = label.inner_text() if label.count() > 0 else ""
                except Exception as e:
                    log.error(f"Error extracting label for textarea {name}: {e}")

            textareas.append(
                {
                    "type": "textarea",
                    "name": name,
                    "id": textarea_id,
                    "label": label_text.strip(),
                    "default_value": value,
                }
            )
        except Exception as e:
            log.error(f"Error extracting textarea element {idx}: {e}")

    return textareas


def extract_form_action(page: Page) -> dict[str, str]:
    """
    Extract form action URL and method.

    Returns:
        Dictionary with form action and method
    """
    forms = page.locator("form").all()
    form_info = []

    for idx, form in enumerate(forms):
        try:
            action = form.get_attribute("action") or ""
            method = form.get_attribute("method") or "GET"
            form_id = form.get_attribute("id") or f"form_{idx}"
            form_name = form.get_attribute("name") or ""

            form_info.append(
                {
                    "id": form_id,
                    "name": form_name,
                    "action": action,
                    "method": method.upper(),
                }
            )
        except Exception as e:
            log.error(f"Error extracting form {idx}: {e}")

    return {"forms": form_info}


def scrape_query_parameters(url: str, headless: bool = True) -> dict[str, Any]:
    """
    Main function to scrape query parameters from a CDC WONDER page.
    Handles both direct page URLs and controller redirect URLs.

    Args:
        url: The CDC WONDER page URL (can be controller URL or direct page URL)
        headless: Whether to run browser in headless mode

    Returns:
        Dictionary containing all extracted parameters
    """
    log.info(f"Starting scrape of {url}")

    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            # Navigate to the page
            log.info(f"Navigating to {url}")
            # Use 'domcontentloaded' instead of 'networkidle' as CDC WONDER pages
            # often have persistent connections that prevent networkidle state
            page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # Log the final URL after any redirects
            final_url = page.url
            if final_url != url:
                log.info(f"Redirected to: {final_url}")

            # Try to click "I Agree" button (may appear after redirect)
            agree_clicked = click_agree_button(page)
            if not agree_clicked:
                log.warning("Failed to click 'I Agree' button - proceeding anyway")
            else:
                log.info("Successfully clicked 'I Agree' button")
                # Log final URL after clicking agree in case it navigates again
                final_url = page.url
                log.info(f"Final page URL: {final_url}")

            # Give the page a moment to fully render the form
            page.wait_for_timeout(2000)

            # Extract all form elements
            log.info("Extracting form parameters...")

            form_info = extract_form_action(page)
            selects = extract_select_options(page)
            inputs = extract_input_elements(page)
            textareas = extract_textarea_elements(page)

            # Compile results
            results = {
                "url": url,
                "final_url": final_url,
                "page_title": page.title(),
                "forms": form_info["forms"],
                "parameters": {
                    "selects": selects,
                    "inputs": inputs,
                    "textareas": textareas,
                },
                "summary": {
                    "total_selects": len(selects),
                    "total_inputs": len(inputs),
                    "total_textareas": len(textareas),
                    "total_parameters": len(selects) + len(inputs) + len(textareas),
                },
            }

            log.info(f"Extraction complete: {results['summary']}")
            return results

        except PlaywrightTimeout as e:
            log.error(f"Timeout error: {e}")
            raise
        except Exception as e:
            log.error(f"Error during scraping: {e}")
            raise
        finally:
            browser.close()


def save_results(
    data: dict[str, Any],
    output_path: Optional[str] = None,
    dataset_id: Optional[str] = None,
) -> str:
    """
    Save extracted parameters to JSON file.

    Args:
        data: Dictionary containing extracted parameters
        output_path: Path to save JSON file (if None, will be auto-generated using dataset_id)
        dataset_id: Dataset ID to include in filename (e.g., 'D192'). Required if output_path is None.

    Returns:
        Path where the file was saved
    """
    if output_path is None:
        # Auto-generate filename based on dataset ID
        if not dataset_id:
            raise ValueError("dataset_id is required when output_path is not specified")
        filename = f"query_params_{dataset_id}.json"
        output_path = f"data/raw/wonder/{filename}"

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    log.info(f"Results saved to {output_path}")
    return str(output_path)


def scrape_dataset_range(
    start_id: int,
    end_id: int,
    headless: bool = True,
    dmap_csv_path: str = "data/raw/wonder/dataset_map.csv",
) -> dict[str, Any]:
    """
    Scrape query parameters for a range of dataset IDs.
    Only scrapes datasets that have a valid final_url in the dmap CSV.

    Args:
        start_id: Starting dataset number (e.g., 1 for D1)
        end_id: Ending dataset number (e.g., 250 for D250)
        headless: Whether to run browser in headless mode
        dmap_csv_path: Path to the dmap CSV file

    Returns:
        Dictionary with results for each dataset
    """
    dmap_file = Path(dmap_csv_path)
    if not dmap_file.exists():
        raise FileNotFoundError(f"dmap CSV not found at {dmap_csv_path}")

    # Build list of valid datasets to scrape
    datasets_to_scrape = []
    try:
        with open(dmap_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                dataset_id = row.get("id", "")
                # Extract numeric ID
                match = re.match(r"D(\d+)", dataset_id)
                if match:
                    num_id = int(match.group(1))
                    if start_id <= num_id <= end_id:
                        final_url = row.get("final_url", "").strip()
                        # Only include if there's a valid final_url
                        if final_url and final_url != "":
                            datasets_to_scrape.append(
                                {
                                    "id": dataset_id,
                                    "url": final_url,
                                    "page_name": row.get("page_name", ""),
                                }
                            )
    except Exception as e:
        raise Exception(f"Error reading dmap CSV: {e}")

    log.info(
        f"Found {len(datasets_to_scrape)} datasets to scrape in range D{start_id}-D{end_id}"
    )

    results = {
        "range": f"D{start_id}-D{end_id}",
        "total_attempted": len(datasets_to_scrape),
        "datasets": {},
    }

    for idx, dataset in enumerate(datasets_to_scrape, 1):
        dataset_id = dataset["id"]
        url = dataset["url"]

        log.info(f"[{idx}/{len(datasets_to_scrape)}] Scraping {dataset_id}: {url}")
        print(f"\n[{idx}/{len(datasets_to_scrape)}] Processing {dataset_id}...")

        try:
            dataset_results = scrape_query_parameters(url, headless=headless)
            dataset_results["dataset_id"] = dataset_id

            # Save individual dataset file
            output_path = f"data/raw/wonder/query_params_{dataset_id}.json"
            save_results(
                dataset_results, output_path=output_path, dataset_id=dataset_id
            )

            results["datasets"][dataset_id] = {
                "status": "success",
                "total_parameters": dataset_results["summary"]["total_parameters"],
                "output_file": output_path,
            }

            log.info(
                f"✓ {dataset_id} completed: {dataset_results['summary']['total_parameters']} parameters"
            )

        except Exception as e:
            log.error(f"✗ {dataset_id} failed: {e}")
            results["datasets"][dataset_id] = {"status": "failed", "error": str(e)}

    # Count successes and failures
    successes = sum(1 for d in results["datasets"].values() if d["status"] == "success")
    failures = sum(1 for d in results["datasets"].values() if d["status"] == "failed")

    results["summary"] = {"successful": successes, "failed": failures}

    return results


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Scrape query parameters from CDC WONDER pages"
    )
    parser.add_argument("url", nargs="?", help="CDC WONDER page URL or controller URL")
    parser.add_argument(
        "-o",
        "--output",
        default="data/raw/wonder/query_params.json",
        help="Output JSON file path",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browser in non-headless mode (visible)",
    )
    parser.add_argument(
        "--range",
        metavar="START-END",
        help="Scrape a range of datasets (e.g., '1-250' for D1-D250)",
    )

    args = parser.parse_args()

    try:
        # Handle range mode
        if args.range:
            # Parse range argument
            range_match = re.match(r"(\d+)-(\d+)", args.range)
            if not range_match:
                raise ValueError(
                    f"Invalid range format: {args.range}. Use format like '1-250'"
                )

            start_id = int(range_match.group(1))
            end_id = int(range_match.group(2))

            if start_id > end_id:
                raise ValueError(
                    f"Invalid range: start ({start_id}) must be <= end ({end_id})"
                )

            print(f"\n{'=' * 60}")
            print(f"Scraping datasets D{start_id} to D{end_id}")
            print(f"{'=' * 60}\n")

            results = scrape_dataset_range(
                start_id, end_id, headless=not args.no_headless
            )

            # Save summary
            summary_path = f"data/raw/wonder/scrape_summary_D{start_id}-D{end_id}.json"
            with open(summary_path, "w") as f:
                json.dump(results, f, indent=2)

            print(f"\n{'=' * 60}")
            print("Batch Scraping Summary:")
            print(f"{'=' * 60}")
            print(f"Range: {results['range']}")
            print(f"Total datasets attempted: {results['total_attempted']}")
            print(f"Successful: {results['summary']['successful']}")
            print(f"Failed: {results['summary']['failed']}")
            print(f"\nSummary saved to: {summary_path}")
            print(f"{'=' * 60}\n")

            return

        # Handle single URL mode
        if not args.url:
            error_msg = "ERROR: Either provide a URL or use --range option\n"
            error_msg += "Examples:\n"
            error_msg += "  uv run python -m src.wonder.query https://wonder.cdc.gov/controller/datarequest/D192\n"
            error_msg += "  uv run python -m src.wonder.query --range 1-250\n"
            print(error_msg)
            raise ValueError("No URL or range specified")

        # Extract dataset ID and resolve target URL - FAIL EARLY if not found
        dataset_id, target_url = get_dataset_id_and_target_url(args.url)

        if not dataset_id:
            error_msg = f"ERROR: Could not determine dataset ID from URL: {args.url}\n"
            error_msg += "The URL must either:\n"
            error_msg += "  1. Be a controller URL like https://wonder.cdc.gov/controller/datarequest/D192\n"
            error_msg += "  2. Match an entry in data/raw/wonder/dataset_map.csv\n"
            log.error(error_msg)
            print(f"\n{'=' * 60}")
            print(error_msg)
            print(f"{'=' * 60}\n")
            raise ValueError(f"Could not determine dataset ID from URL: {args.url}")

        if not target_url:
            error_msg = f"ERROR: Dataset {dataset_id} has no final_url in dmap CSV\n"
            error_msg += "Cannot determine which page to scrape.\n"
            log.error(error_msg)
            print(f"\n{'=' * 60}")
            print(error_msg)
            print(f"{'=' * 60}\n")
            raise ValueError(f"No target URL found for dataset {dataset_id}")

        log.info(f"Detected dataset ID: {dataset_id}")
        if target_url != args.url:
            log.info(f"Using target URL: {target_url}")

        results = scrape_query_parameters(target_url, headless=not args.no_headless)

        # Add dataset_id to results
        results["dataset_id"] = dataset_id

        # Save with dataset ID in filename if output not explicitly specified
        output_path_used = (
            args.output if args.output != "data/raw/wonder/query_params.json" else None
        )
        saved_path = save_results(
            results, output_path=output_path_used, dataset_id=dataset_id
        )

        print(f"\n{'=' * 60}")
        print("Extraction Summary:")
        print(f"{'=' * 60}")
        if dataset_id:
            print(f"Dataset ID: {dataset_id}")
        print(f"Page: {results['page_title']}")
        print(f"Total Parameters: {results['summary']['total_parameters']}")
        print(f"  - Select dropdowns: {results['summary']['total_selects']}")
        print(f"  - Input elements: {results['summary']['total_inputs']}")
        print(f"  - Textarea elements: {results['summary']['total_textareas']}")
        print(f"\nResults saved to: {saved_path}")
        print(f"{'=' * 60}\n")

    except Exception as e:
        log.error(f"Script failed: {e}")
        raise


if __name__ == "__main__":
    main()
