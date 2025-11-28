import asyncio
import os
import random
import time

import pandas as pd
from playwright.async_api import async_playwright

CAR_MODELS_CSV = "./Car Models/cars.csv"
LISTING_URL_CSV = "./Car Models/listing_urls.csv"
MAX_PAGES_PER_MODEL = 1000
SAFE_OVERLAP = 5  # Number of previous indices to reprocess each page for safety


async def main():
    # Launch browser
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=100,
        )
        page = await browser.new_page()
        page.set_default_timeout(15000)

        # Session-level metrics
        session_start = time.time()
        session_seen_count = 0

        # Load seen IDs from existing CSV if it exists
        seen_ids = set()
        if os.path.exists(LISTING_URL_CSV):
            try:
                existing_df = pd.read_csv(LISTING_URL_CSV)
                if "id" in existing_df.columns:
                    seen_ids = set(existing_df["id"].dropna().tolist())
                else:
                    print("No 'id' column found in CSV")

                # Printing the number of found ids
                print(f"Loaded {len(seen_ids)} seen IDs from {LISTING_URL_CSV}")

            except Exception as e:
                print(f"Error loading {LISTING_URL_CSV}: {e}")

        # For each car model we will scrape price trends data
        # Getting each car model from the CSV file
        # Each row has a "Make" and "Model" feature
        df = pd.read_csv(CAR_MODELS_CSV)

        # Creating a list of car models
        car_models = df["Model"].tolist()

        # Creating a list of car makes
        car_makes = df["Make"].tolist()

        # Creating a list of car models and makes
        car_models_makes = list(zip(car_makes, car_models))

        for car in car_models_makes:
            print(f"\n=== Starting scraping for {car[0]} {car[1]} ===")
            # ---------------- Navigate to a car listings for each make and model ----------------
            await page.goto("https://www.autotempest.com/")
            await page.wait_for_timeout(random.randint(700, 1400))

            # Selecting the "Price Trends Option"
            await page.locator('li[data-id="price-trends-main"]').click()
            await page.wait_for_timeout(random.randint(500, 1000))

            # Now we will input the car model and make
            await page.locator("#trends-make-input").fill(car[0])
            await page.locator("#trends-make-input").press("Enter")
            await page.wait_for_timeout(random.randint(400, 900))
            await page.locator("#trends-model-input").fill(car[1])
            await page.locator("#trends-model-input").press("Enter")
            await page.wait_for_timeout(random.randint(400, 900))

            # Clicking the Search button
            await page.get_by_role("button", name="Search").first.click()
            await page.wait_for_timeout(random.randint(1200, 2000))

            print("Search button pressed")

            # Wait for the page to load
            await page.wait_for_timeout(random.randint(2500, 4000))

            # Switching from sample data to all data (if present)
            # The button has text "Sampled Data"
            sampled_btn = page.locator("text=Sampled Data")
            if await sampled_btn.is_visible():
                await sampled_btn.click()
                await page.wait_for_timeout(random.randint(600, 1200))
            else:
                print("Sampled Data toggle not visible; continuing with defaults.")

            # Set the slider to 100%
            slider = page.locator('span[role="slider"]')
            await slider.focus()
            await slider.press("End")
            await page.wait_for_timeout(random.randint(600, 1200))

            # Per-model tracking counters
            num_more_results = 0  # The number of pages processed for each model
            processed_count = 0  # The number of listings processed for each model
            saved_this_model = 0  # The number of listings saved for each model
            skipped_no_id = 0  # The number of listings skipped due to missing ID
            skipped_no_href = 0  # The number of listings skipped due to missing href
            skipped_duplicates = 0  # The number of listings skipped due to duplicates
            seen_dom_ids_this_model = set()  # Initialize a set to track seen DOM IDs for this model. This can include non-saved elements.
            seen_hrefs_this_model = (
                set()
            )  # Initialize a set to track seen hrefs for this model
            last_processed_idx = -1  # Track highest processed index for safe-overlap pagination. It starts at -1 to ensure the first page is processed.
            while num_more_results < MAX_PAGES_PER_MODEL:
                local_results = []
                # ---------------- Getting a list of all listings ----------------
                # Getting a list of car items
                # Wait for results to update (instead of just sleep)
                try:
                    await page.wait_for_selector(
                        ".ResultItem_cardWrap__tA63Q", timeout=8000
                    )  # 8s wait for at least one result
                except:
                    print(f"Initial results failed to load for {car[0]} {car[1]}")
                    break  # Stop pagination for this model
                # Ensure we are at the top to keep all virtualized items visible
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(150)
                # Select result card elements
                try:
                    filtered = page.locator(".ResultItem_cardWrap__tA63Q:has(h3 a)")
                    filtered_count = await filtered.count()
                    if filtered_count > 0:
                        car_elements = filtered
                        print(
                            f"Using filtered result selector (:has(h3 a)). count={filtered_count}"
                        )
                    else:
                        car_elements = page.locator(".ResultItem_cardWrap__tA63Q")
                        print(
                            "Using base result selector (.ResultItem_cardWrap__tA63Q)."
                        )
                except Exception:
                    car_elements = page.locator(".ResultItem_cardWrap__tA63Q")
                    print("Using base result selector due to :has() unsupported.")
                count = await car_elements.count()
                print(f"Found {count} result containers on current page")
                # Compute start index with safe overlap window
                start_index = max(0, last_processed_idx - SAFE_OVERLAP)
                if start_index > 0:
                    print(
                        f"[Pagination] Using start_index={start_index} (last_processed_idx={last_processed_idx}, overlap={SAFE_OVERLAP})"
                    )

                # ---------------- Extract the URL from each listing ----------------
                # Build a stable snapshot of elements to iterate to avoid index drift
                items = []
                cards_snapshot = None
                try:
                    cards_snapshot = await page.evaluate(
                        """Array.from(document.querySelectorAll('.ResultItem_cardWrap__tA63Q')).map((el, idx) => {
                            const withId = el.closest('[id]');
                            return { idx, ancestorId: withId ? withId.id : null };
                        })"""
                    )
                    print(f"Captured card snapshot (len={len(cards_snapshot)})")
                except Exception:
                    cards_snapshot = None
                if cards_snapshot and len(cards_snapshot) > 0:
                    for entry in cards_snapshot:
                        idx = entry.get("idx")
                        ancestor_id = entry.get("ancestorId")
                        # Only process newly appended indices with a small safe overlap
                        if idx is None or idx < start_index:
                            continue
                        if ancestor_id:
                            items.append(
                                (
                                    idx,
                                    page.locator(
                                        f'[id="{ancestor_id}"] .ResultItem_cardWrap__tA63Q'
                                    ).first,
                                    ancestor_id,
                                )
                            )
                        else:
                            items.append((idx, car_elements.nth(idx), None))
                else:
                    for idx in range(start_index, count):
                        items.append((idx, car_elements.nth(idx), None))

                for i, car_elem, stable_ancestor_id in items:
                    processed_count += 1
                    session_seen_count += 1
                    # Detachment guard
                    try:
                        is_detached = await car_elem.count() == 0
                    except Exception as e:
                        print(f"=== Card #{i} count() failed ({e}). Skipping. ===")
                        continue
                    if is_detached:
                        print(f"=== Card #{i} is detached (0 matches). Skipping. ===")
                        continue
                    # Make sure virtualized items are realized
                    try:
                        await car_elem.scroll_into_view_if_needed()
                    except Exception:
                        pass

                    # Early ID extraction and duplicate check to avoid re-processing
                    listing_id = None
                    try:
                        listing_id = await car_elem.get_attribute("id")
                    except Exception:
                        listing_id = None
                    if not listing_id:
                        try:
                            listing_id = await car_elem.locator("..").get_attribute(
                                "id"
                            )
                        except Exception:
                            listing_id = None
                    if not listing_id and stable_ancestor_id:
                        listing_id = stable_ancestor_id
                    # Guard: missing ID (skip early to avoid churn re-processing)
                    if not listing_id:
                        skipped_no_id += 1
                        print(f"[Skip] Card #{i}: missing id")
                        continue
                    # Skip if we've already seen this ID in this model or previously
                    if listing_id in seen_dom_ids_this_model:
                        skipped_duplicates += 1
                        print(
                            f"[Skip] Card #{i} id={listing_id}: duplicate within this model (DOM churn)"
                        )
                        continue
                    if listing_id in seen_ids:
                        skipped_duplicates += 1
                        print(
                            f"[Skip] Card #{i} id={listing_id}: duplicate from previous runs"
                        )
                        continue
                    seen_dom_ids_this_model.add(listing_id)

                    direct_href = None
                    link_elem = car_elem.locator("h3 a")  # Find <a> inside <h3>
                    # Ensure we have a usable link; try fallbacks when missing
                    if await link_elem.count() == 0:
                        # Try fallback selectors before skipping
                        fallback_selector = None
                        for sel in [
                            "a.ResultItem_titleLink__Ty_Xt",
                            "a.ResultItem_thumbnailLink__tl3uL",
                            "a:has-text('View Listing')",
                            "h3 >> a",
                            "a[href*='/trends/']",
                            "a[href]",
                        ]:
                            cand = car_elem.locator(sel)
                            if await cand.count() > 0:
                                link_elem = cand.first
                                fallback_selector = sel
                                print(
                                    f"[card #{i}] primary link missing; using fallback selector: {sel}"
                                )
                                break
                        # Try DOM evaluation to find a likely link if no selector worked
                        if not fallback_selector:
                            try:
                                direct_href = await car_elem.evaluate(
                                    """(el) => {
                                        const anchors = Array.from(el.querySelectorAll('a[href]'));
                                        const prefer = anchors.find(a => (a.getAttribute('href') || '').includes('/trends/'));
                                        const target = prefer || anchors[0];
                                        return target ? target.getAttribute('href') : null;
                                    }"""
                                )
                            except Exception:
                                direct_href = None
                        if not fallback_selector and not direct_href:
                            skipped_no_href += 1
                            # Detailed, digestible debug for cards without a usable link
                            try:
                                cid = await car_elem.get_attribute("id")
                            except Exception:
                                cid = None
                            try:
                                cclass = await car_elem.get_attribute("class")
                            except Exception:
                                cclass = None
                            try:
                                parent_id = await car_elem.evaluate(
                                    "(el) => el.parentElement && el.parentElement.id"
                                )
                                parent_class = await car_elem.evaluate(
                                    "(el) => el.parentElement && el.parentElement.className"
                                )
                            except Exception:
                                parent_id = None
                                parent_class = None
                            try:
                                text_snippet = await car_elem.inner_text()
                                if text_snippet:
                                    text_snippet = text_snippet.strip().replace(
                                        "\n", " "
                                    )[:300]
                            except Exception:
                                text_snippet = None
                            try:
                                child_tags = await car_elem.evaluate(
                                    "(el) => Array.from(new Set(Array.from(el.querySelectorAll('*')).map(e => e.tagName))).slice(0,20)"
                                )
                            except Exception:
                                child_tags = None
                            try:
                                anchors_info = await car_elem.evaluate(
                                    """(el) => Array.from(el.querySelectorAll('a')).slice(0,10).map(a => ({ text: (a.textContent || '').trim().slice(0,80), href: a.getAttribute('href') }))"""
                                )
                            except Exception:
                                anchors_info = None
                            try:
                                outer_snippet = await car_elem.evaluate(
                                    "(el) => el.outerHTML.slice(0, 500)"
                                )
                            except Exception:
                                outer_snippet = None
                            print(
                                "============================================================"
                            )
                            print(f"[Skip] Card #{i}: no usable link")
                            print(f"  id           : {cid}")
                            print(f"  class        : {cclass}")
                            print(f"  parent.id    : {parent_id}")
                            print(f"  parent.class : {parent_class}")
                            print(f"  child_tags   : {child_tags}")
                            if text_snippet:
                                print(f"  text         : {text_snippet}")
                            if anchors_info:
                                for j, a in enumerate(anchors_info):
                                    try:
                                        print(
                                            f"  anchor[{j}]    : text='{a.get('text')}', href='{a.get('href')}'"
                                        )
                                    except Exception:
                                        pass
                            if outer_snippet:
                                print(f"  outer_html   : {outer_snippet}")
                            print(
                                "------------------------------------------------------------"
                            )
                            continue

                    # Get href with a short timeout or use direct href found via evaluation
                    href = direct_href if direct_href else None
                    if href is None:
                        try:
                            href = await link_elem.first.get_attribute(
                                "href", timeout=2000
                            )
                        except Exception:
                            href = None
                    listing_url = f"https://www.autotempest.com{href}" if href else None

                    # listing_id already determined by early duplicate check above

                    # Guard: missing href/url
                    if not href:
                        skipped_no_href += 1
                        print(f"Skipping listing {listing_id}: missing href")
                        continue

                    # Href-based per-model dedupe to mitigate DOM churn
                    if href in seen_hrefs_this_model:
                        skipped_duplicates += 1
                        print(
                            f"[Skip] Card #{i} id={listing_id}: duplicate href on this model page ({href})"
                        )
                        continue
                    seen_hrefs_this_model.add(href)

                    print(f"Listing ID: {listing_id}")
                    print(f"Listing URL: {listing_url}")
                    print("\n")

                    local_results.append(
                        {
                            "make": car[0],
                            "model": car[1],
                            "id": listing_id,
                            "url": listing_url,
                        }
                    )
                    seen_ids.add(listing_id)

                # Update last_processed_idx for next iteration and write the data to a file
                last_processed_idx = count - 1
                if local_results:
                    # Ensure output directory exists
                    os.makedirs(os.path.dirname(LISTING_URL_CSV), exist_ok=True)
                    header = not os.path.exists(LISTING_URL_CSV)
                    pd.DataFrame(local_results).to_csv(
                        LISTING_URL_CSV, mode="a", header=header, index=False
                    )
                    saved_this_model += len(local_results)
                    print(
                        f"Saved {len(local_results)} new listings to {LISTING_URL_CSV}"
                    )

                # Now that we have gotten the listings on this page we will get the listings on the next page
                # by clicking the "More Results" button
                # Check for "More Results" button
                more_button = page.get_by_role("button", name="More Results").first
                if (
                    not await more_button.is_visible()
                    or not await more_button.is_enabled()
                ):
                    current_total = await page.locator(
                        ".ResultItem_cardWrap__tA63Q"
                    ).count()
                    print(
                        f"More Results button not visible/enabled. Stopping at {current_total} total cards."
                    )
                    break  # Exit if button is hidden or missing

                # Click the button and robustly wait for more results to load
                sel = ".ResultItem_cardWrap__tA63Q"
                prev_count = await page.locator(sel).count()
                print(
                    f"Clicking More Results (prev_count={prev_count}, clicks_so_far={num_more_results})"
                )
                await more_button.click()
                await page.wait_for_timeout(
                    random.randint(1200, 2500)
                )  # Short pause for human-like behavior
                try:
                    await page.wait_for_function(
                        "(arg) => document.querySelectorAll(arg.sel).length > arg.prev",
                        arg={"sel": sel, "prev": prev_count},
                        timeout=8000,
                    )
                except Exception as e:
                    print(f"No new results detected after clicking More Results: {e}")
                    break
                new_count = await page.locator(sel).count()
                print(f"After More Results: new_count={new_count}")
                # Next loop will use last_processed_idx computed from the page we just processed
                print(
                    f"[Pagination] last_processed_idx={last_processed_idx} (prior count processed)"
                )
                num_more_results += 1
                # Session pagination logging
                elapsed = time.time() - session_start
                time_per_listing = (
                    (elapsed / session_seen_count)
                    if session_seen_count > 0
                    else float("inf")
                )
                print(
                    f"[Session] Elapsed: {elapsed:.2f}s | Listings seen: {session_seen_count} | Time/listing: {time_per_listing:.2f}s"
                )
            # Per-model summary logging
            print(
                f"Summary for {car[0]} {car[1]} -> processed: {processed_count}, saved: {saved_this_model}, skipped_no_id: {skipped_no_id}, skipped_no_href: {skipped_no_href}, skipped_duplicates: {skipped_duplicates}, more_results_clicks: {num_more_results}"
            )
            await page.wait_for_timeout(random.randint(6000, 9000))

    # Close browser
    await browser.close()


# Run the async function
asyncio.run(main())
