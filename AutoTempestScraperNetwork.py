import asyncio
import json
import os
import random
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
from playwright.async_api import Response, async_playwright

# Inputs/Outputs
CAR_MODELS_CSV = "./Car Models/cars.csv"
LISTING_URL_CSV = "./Car Models/listing_urls.csv"

# Endpoint to capture (based on prior usage of "/api/trends/results")
TARGET_RESULTS_ENDPOINT_SUBSTRING = "/api/trends/results"

# Browser behavior
HEADLESS = False
SLOW_MO_MS = 100
DEFAULT_TIMEOUT_MS = 15000


def ensure_parent_dir(path: str) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def normalize_value(value: Any) -> Any:
    # Keep scalars, stringify lists/dicts
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)
    return value


def normalize_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return url
    if url.startswith("//"):
        return "https:" + url
    return url


def load_existing_index(path: str) -> Tuple[Set[str], Set[str], Optional[pd.DataFrame]]:
    """Load existing CSV and return sets of seen IDs and URLs and the DataFrame."""
    seen_ids: Set[str] = set()
    seen_urls: Set[str] = set()
    if not os.path.exists(path):
        return seen_ids, seen_urls, None
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        if "id" in df.columns:
            seen_ids = set(df["id"].astype(str).tolist())
        if "url" in df.columns:
            seen_urls = set(df["url"].astype(str).tolist())
        print(
            f"Loaded existing CSV '{path}': {len(df)} rows, {len(seen_ids)} IDs, {len(seen_urls)} URLs"
        )
        return seen_ids, seen_urls, df
    except Exception as e:
        print(f"Warning: could not read existing CSV '{path}': {e}")
        return set(), set(), None


def merge_and_write_csv(
    path: str,
    batch_rows: List[Dict[str, Any]],
    existing_df: Optional[pd.DataFrame],
    dedupe_by: List[str],
) -> pd.DataFrame:
    """Merge batch rows with existing CSV, align dynamic columns, de-duplicate, and write."""
    ensure_parent_dir(path)

    # Create batch DataFrame
    if not batch_rows:
        return existing_df if existing_df is not None else pd.DataFrame()

    batch_df = pd.DataFrame(batch_rows)

    # If existing file exists, union columns and concat, else create new
    if existing_df is not None:
        all_cols = sorted(
            set(existing_df.columns.tolist()) | set(batch_df.columns.tolist())
        )
        existing_df = existing_df.reindex(columns=all_cols, fill_value="")
        batch_df = batch_df.reindex(columns=all_cols, fill_value="")
        merged = pd.concat([existing_df, batch_df], ignore_index=True)
    else:
        merged = batch_df

    # De-duplicate
    dedupe_keys = [k for k in dedupe_by if k in merged.columns]
    if dedupe_keys:
        merged = merged.drop_duplicates(subset=dedupe_keys, keep="first")
    else:
        merged = merged.drop_duplicates(keep="first")

    # Persist
    merged.to_csv(path, index=False)
    print(
        f"Wrote CSV '{path}' with {len(merged)} rows and {len(merged.columns)} columns."
    )
    return merged


async def wait_and_fetch_results_response(
    page, timeout_ms: int = DEFAULT_TIMEOUT_MS
) -> Optional[Dict[str, Any]]:
    """
    Collector-based wait for the next results payload captured via page.on('response').
    Assumes caller clears the collector buffer just before triggering the network action.
    """
    # Ensure collector attributes and listener are initialized
    if not hasattr(page, "_results_queue"):
        page._results_queue = []
    if not hasattr(page, "_results_event"):
        page._results_event = asyncio.Event()
    if not hasattr(page, "_results_on_response"):

        def _on_response(resp: Response):
            if (TARGET_RESULTS_ENDPOINT_SUBSTRING in resp.url) and (resp.status == 200):

                async def _collect():
                    try:
                        payload = await resp.json()
                    except Exception:
                        try:
                            text_body = await resp.text()
                            payload = json.loads(text_body)
                        except Exception:
                            return
                    page._results_queue.append(payload)
                    try:
                        page._results_event.set()
                    except Exception:
                        pass

                asyncio.create_task(_collect())

        page.on("response", _on_response)
        page._results_on_response = _on_response

    # Wait for next payload
    start = time.monotonic()
    while True:
        if getattr(page, "_results_queue", []):
            return page._results_queue.pop(0)
        remaining = timeout_ms / 1000 - (time.monotonic() - start)
        if remaining <= 0:
            print(f"Timed out waiting for {TARGET_RESULTS_ENDPOINT_SUBSTRING}")
            return None
        try:
            page._results_event.clear()
        except Exception:
            pass
        try:
            await asyncio.wait_for(page._results_event.wait(), timeout=remaining)
        except asyncio.TimeoutError:
            print(f"Timed out waiting for {TARGET_RESULTS_ENDPOINT_SUBSTRING}")
            return None


def listings_from_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract a list of listing dicts from the results payload.
    Expected structure: { status: 0, results: [ {...}, {...} ] }
    """
    if not isinstance(payload, dict):
        return []
    results = payload.get("results") or []
    if not isinstance(results, list):
        return []
    rows: List[Dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        flat: Dict[str, Any] = {}
        for k, v in item.items():
            flat[k] = normalize_value(v)
        # Normalize URL
        if "url" in flat:
            flat["url"] = normalize_url(str(flat["url"]))
        rows.append(flat)
    return rows


async def process_batch_and_write(
    make: str,
    model: str,
    page,
    seen_ids: Set[str],
    seen_urls: Set[str],
    existing_df: Optional[pd.DataFrame],
) -> Tuple[Optional[pd.DataFrame], int]:
    """
    Capture next results batch from the network, filter new listings, attach make/model,
    and write to CSV merging columns dynamically. Returns updated df and count saved.
    """
    payload = await wait_and_fetch_results_response(page)
    if payload is None:
        return existing_df, 0

    raw_rows = listings_from_payload(payload)

    # Filter out duplicates and attach make/model
    new_rows: List[Dict[str, Any]] = []
    new_count = 0
    for row in raw_rows:
        row_id = str(row.get("id") or "").strip()
        row_url = str(row.get("url") or "").strip()

        if row_id and row_id in seen_ids:
            continue
        if (not row_id) and row_url and row_url in seen_urls:
            continue

        # Set make/model columns explicitly
        row["make"] = make
        row["model"] = model

        # Track seen
        if row_id:
            seen_ids.add(row_id)
        if row_url:
            seen_urls.add(row_url)

        new_rows.append(row)
        new_count += 1

    if not new_rows:
        print("No new rows in this batch.")
        return existing_df, 0

    # Merge and write (bulk-write this batch)
    updated_df = merge_and_write_csv(
        LISTING_URL_CSV,
        new_rows,
        existing_df=existing_df,
        dedupe_by=["id", "url"],
    )
    return updated_df, new_count


async def run_for_make_model(
    page,
    make: str,
    model: str,
    seen_ids: Set[str],
    seen_urls: Set[str],
    existing_df: Optional[pd.DataFrame],
) -> Optional[pd.DataFrame]:
    """
    Navigate, run the search, capture initial batch and subsequent batches via 'More Results' clicks.
    Bulk-write after each batch with dynamic columns.
    """
    print(f"Starting: {make} {model}")
    await page.goto("https://www.autotempest.com/")
    await page.wait_for_timeout(random.randint(700, 1400))

    # Ensure response collector is attached once per page
    if not hasattr(page, "_results_queue"):
        page._results_queue = []
    if not hasattr(page, "_results_event"):
        page._results_event = asyncio.Event()
    if not hasattr(page, "_results_on_response"):

        def _on_response(resp: Response):
            if (TARGET_RESULTS_ENDPOINT_SUBSTRING in resp.url) and (resp.status == 200):

                async def _collect():
                    try:
                        payload = await resp.json()
                    except Exception:
                        try:
                            text_body = await resp.text()
                            payload = json.loads(text_body)
                        except Exception:
                            return
                    page._results_queue.append(payload)
                    try:
                        page._results_event.set()
                    except Exception:
                        pass

                asyncio.create_task(_collect())

        page.on("response", _on_response)
        page._results_on_response = _on_response

    # Select "Price Trends"
    await page.locator('li[data-id="price-trends-main"]').click()
    await page.wait_for_timeout(random.randint(500, 1000))

    # Fill make and model inputs
    await page.locator("#trends-make-input").fill(make)
    await page.locator("#trends-make-input").press("Enter")
    await page.wait_for_timeout(random.randint(300, 800))

    await page.locator("#trends-model-input").fill(model)
    await page.locator("#trends-model-input").press("Enter")
    await page.wait_for_timeout(random.randint(300, 800))

    # Trigger search: clear collector, click, then await next payload
    if hasattr(page, "_results_queue"):
        page._results_queue.clear()
    if hasattr(page, "_results_event"):
        try:
            page._results_event.clear()
        except Exception:
            pass
    await page.get_by_role("button", name="Search").first.click()

    # Initial results batch
    existing_df, saved_count = await process_batch_and_write(
        make, model, page, seen_ids, seen_urls, existing_df
    )
    print(f"Initial batch saved: {saved_count}")

    # Optional: toggle from "Sampled Data" to "All Data" if present (this often triggers another results call)
    try:
        sampled_btn = page.locator("text=Sampled Data")
        if await sampled_btn.is_visible():
            # Clear collector and click toggle
            if hasattr(page, "_results_queue"):
                page._results_queue.clear()
            if hasattr(page, "_results_event"):
                try:
                    page._results_event.clear()
                except Exception:
                    pass
            await sampled_btn.click()
            existing_df, saved_count = await process_batch_and_write(
                make, model, page, seen_ids, seen_urls, existing_df
            )
            print(f"Post 'Sampled Data' toggle batch saved: {saved_count}")
    except Exception:
        pass

    # Max the slider to 100% (often refines the query; may or may not trigger more results)
    try:
        slider = page.locator('span[role="slider"]')
        await slider.focus()
        # Clear collector and move slider to end
        if hasattr(page, "_results_queue"):
            page._results_queue.clear()
        if hasattr(page, "_results_event"):
            try:
                page._results_event.clear()
            except Exception:
                pass
        await slider.press("End")
        # If the slider triggers another results call, capture it
        try:
            existing_df, saved_count = await process_batch_and_write(
                make, model, page, seen_ids, seen_urls, existing_df
            )
            print(f"Post slider batch saved: {saved_count}")
        except Exception:
            pass
    except Exception:
        pass

    # Loop clicking "More Results" and capture each batch
    total_more_saved = 0
    more_clicks = 0
    while True:
        more_button = page.get_by_role("button", name="More Results").first
        try:
            if not await more_button.is_visible():
                print("No 'More Results' button visible; finishing this model.")
                break
        except Exception:
            print(
                "Could not determine visibility of 'More Results'; finishing this model."
            )
            break

        # Set up wait for the next network response
        try:
            if hasattr(page, "_results_queue"):
                page._results_queue.clear()
            if hasattr(page, "_results_event"):
                try:
                    page._results_event.clear()
                except Exception:
                    pass
            await more_button.click()
        except Exception as e:
            print(f"Failed to click 'More Results': {e}")
            break

        existing_df, saved_count = await process_batch_and_write(
            make, model, page, seen_ids, seen_urls, existing_df
        )
        more_clicks += 1
        total_more_saved += saved_count
        print(
            f"More Results click #{more_clicks}: saved {saved_count} new rows. Total saved so far (more): {total_more_saved}"
        )

        # Human-like small pause
        await page.wait_for_timeout(random.randint(800, 1600))

        # Safety: if no new rows were saved over several clicks, bail out
        if saved_count == 0:
            # Check if button still exists; if it does but yields no new results, stop to avoid infinite loops
            # Wait briefly and re-check; if still no new rows on subsequent click, we'll exit on next loop iteration anyway.
            break

    print(
        f"Completed {make} {model}. Total additional rows from 'More Results': {total_more_saved}"
    )
    return existing_df


async def main():
    ensure_parent_dir(LISTING_URL_CSV)
    # Load global seen sets and existing DF to support dynamic columns across batches
    seen_ids, seen_urls, existing_df = load_existing_index(LISTING_URL_CSV)

    # Load make/model list
    if not os.path.exists(CAR_MODELS_CSV):
        print(f"Car models CSV not found at '{CAR_MODELS_CSV}'. Exiting.")
        return

    models_df = pd.read_csv(CAR_MODELS_CSV, dtype=str, keep_default_na=False)
    if not {"Make", "Model"}.issubset(models_df.columns):
        print(
            f"Input CSV must contain 'Make' and 'Model' columns. Columns found: {models_df.columns.tolist()}"
        )
        return

    pairs: List[Tuple[str, str]] = list(
        zip(models_df["Make"].tolist(), models_df["Model"].tolist())
    )
    total_models = len(pairs)
    print(f"Found {total_models} make/model pairs.")

    start_ts = time.time()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS, slow_mo=SLOW_MO_MS)
        page = await browser.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT_MS)

        for idx, (make, model) in enumerate(pairs, start=1):
            model_start = time.time()
            try:
                existing_df = await run_for_make_model(
                    page, make, model, seen_ids, seen_urls, existing_df
                )
            except Exception as e:
                print(f"Error running for {make} {model}: {e}")

            elapsed = time.time() - model_start
            bar_width = 30
            filled = int(bar_width * idx / max(total_models, 1))
            bar = "#" * filled + "-" * (bar_width - filled)
            print(f"[{bar}] {idx}/{total_models} - {make} {model} in {elapsed:.1f}s")
            # Human-like think time between models
            await page.wait_for_timeout(random.randint(4000, 7000))

        await browser.close()

    total_elapsed = time.time() - start_ts
    print(f"Session done in {total_elapsed / 60:.1f} minutes.")


if __name__ == "__main__":
    asyncio.run(main())
