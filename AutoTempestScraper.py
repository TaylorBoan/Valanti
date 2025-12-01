import asyncio
import os
import random
import time

import pandas as pd
from playwright.async_api import async_playwright

CAR_MODELS_CSV = "./Car Models/cars.csv"
LISTING_URL_CSV = "./Car Models/listing_urls.csv"
MAX_PAGES_PER_MODEL = 1000
MAX_HARVEST_BUFFER = 15000  # cap for in-memory id buffer
# SAFE_OVERLAP removed; DOM processing is now target-id driven via network responses


# ---- Pretty logging helpers ----
def log_header(title: str):
    print("\n" + "=" * 80)
    print(f"{title}")
    print("=" * 80)


def log_kv(title: str, **kwargs):
    kv = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    print(f"{title} {kv}")


def log_gap(lines: int = 1):
    for _ in range(max(1, lines)):
        print()


async def main():
    # Launch browser
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=100,
        )
        page = await browser.new_page()
        page.set_default_timeout(15000)
        # Attach a network response harvester to collect full records and target ids
        records_by_id = {}
        harvested_buffer = []
        harvest_by_epoch = {}  # epoch -> list of harvested ids
        processed_target_ids = set()  # ids we've already used to process cards
        current_epoch = 0  # incremented before each "More Results" click
        dom_deltas_by_epoch = {}  # epoch -> set of absolute hrefs discovered via DOM diff
        collect_network = False  # do not harvest network data until after Search

        async def _walk_collect(obj):
            try:
                if isinstance(obj, dict):
                    if isinstance(obj.get("id"), str):
                        records_by_id[obj["id"]] = obj
                    for v in obj.values():
                        await _walk_collect(v)
                elif isinstance(obj, list):
                    for v in obj:
                        await _walk_collect(v)
            except Exception:
                pass

        async def _handle_response(resp):
            try:
                ctype = resp.headers.get("content-type", "")
            except Exception:
                ctype = ""
            if ctype and "application/json" in ctype:
                url = getattr(resp, "url", "")
                # Gate network harvesting to trends endpoint only
                if "/api/trends/results" not in url:
                    return
                if not collect_network:
                    return
                try:
                    data = await resp.json()
                except Exception:
                    data = None
                if data is not None:
                    # Extract ids only from this response payload
                    def _collect_ids(obj, out):
                        if isinstance(obj, dict):
                            _id = obj.get("id")
                            if isinstance(_id, str):
                                out.append(_id)
                            for v in obj.values():
                                _collect_ids(v, out)
                        elif isinstance(obj, list):
                            for v in obj:
                                _collect_ids(v, out)

                    resp_ids = []
                    try:
                        # Prefer ids from trends payload shape: data.results[*].id
                        if isinstance(data, dict) and isinstance(
                            data.get("results"), list
                        ):
                            resp_ids = [
                                r.get("id")
                                for r in data["results"]
                                if isinstance(r, dict) and isinstance(r.get("id"), str)
                            ]
                        else:
                            _collect_ids(data, resp_ids)
                    except Exception:
                        resp_ids = []
                    await _walk_collect(data)
                    try:
                        new_ids = resp_ids
                        if new_ids:
                            harvested_buffer.extend(new_ids)
                            if len(harvested_buffer) > MAX_HARVEST_BUFFER:
                                harvested_buffer[:] = harvested_buffer[
                                    -MAX_HARVEST_BUFFER:
                                ]
                            harvest_by_epoch.setdefault(current_epoch, []).extend(
                                new_ids
                            )
                        log_kv(
                            "[Network]",
                            epoch=current_epoch,
                            url=getattr(resp, "url", ""),
                            ctype=ctype,
                            ids_in_resp=len(resp_ids),
                        )
                        print(f"  sample_ids={resp_ids[:5]}")
                        log_gap()
                    except Exception as e:
                        log_kv("[Network error]", error=str(e))
                        log_gap()

        page.on("response", _handle_response)

        # Session-level metrics
        session_start = time.time()
        session_seen_count = 0

        # Load seen URLs from existing CSV if it exists
        seen_urls = set()
        if os.path.exists(LISTING_URL_CSV):
            try:
                existing_df = pd.read_csv(LISTING_URL_CSV)
                if "url" in existing_df.columns:
                    seen_urls = set(existing_df["url"].dropna().tolist())
                else:
                    print("No 'url' column found in CSV")

                # Printing the number of found urls
                print(f"Loaded {len(seen_urls)} seen URLs from {LISTING_URL_CSV}")

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
        total_models = len(car_models_makes)

        for model_index, car in enumerate(car_models_makes, start=1):
            log_header(f"Starting scraping for {car[0]} {car[1]}")
            collect_network = False
            log_kv("[Network Harvest]", state="disabled (pre-search)")
            log_gap()
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

            log_kv("[Action]", action="Search pressed")
            log_gap()
            collect_network = True
            log_kv("[Network Harvest]", state="enabled (post-search)")
            log_gap()

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
            seen_urls_this_model = (
                set()
            )  # Initialize a set to track seen URLs for this model (dedupe key).
            # removed unused last_processed_idx (safe-overlap now driven by network epochs)
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
                    print(f"Failed to load results for {car[0]} {car[1]}")
                    break  # Stop pagination for this model

                # Ensure we are at the top to keep all virtualized items visible
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(150)

                # Select result card elements
                car_elements = page.locator(".ResultItem_cardWrap__tA63Q")
                log_kv("[Results]", selector=".ResultItem_cardWrap__tA63Q")
                log_gap()

                count = await car_elements.count()
                # Index-based window removed; we rely solely on network target ids
                allow_snapshot_all = num_more_results == 0
                # Determine new-only processing set for this iteration (epoch)
                _initial_epoch_ids = (
                    set(harvest_by_epoch.get(current_epoch, [])) - processed_target_ids
                )

                def _trends_url_from_id(_id: str) -> str:
                    return f"https://www.autotempest.com/trends/{_id}"

                # Filter out ids we have already seen (based on constructed trends URL)
                epoch_ids = {
                    eid
                    for eid in _initial_epoch_ids
                    if (_trends_url_from_id(eid) not in seen_urls)
                    and (_trends_url_from_id(eid) not in seen_urls_this_model)
                }

                log_kv(
                    "[Epoch]",
                    epoch=current_epoch,
                    allow_snapshot_all=allow_snapshot_all,
                    epoch_ids=len(epoch_ids),
                    harvested_buffer_len=len(harvested_buffer),
                    processed_target_ids=len(processed_target_ids),
                )
                log_kv(
                    "[Epoch filter]",
                    before=len(_initial_epoch_ids),
                    after=len(epoch_ids),
                    filtered=(len(_initial_epoch_ids) - len(epoch_ids)),
                )
                print(f"  sample_ids={list(epoch_ids)[:5]}")
                log_gap()

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
                    log_kv(
                        "[Snapshot]",
                        cards=len(cards_snapshot),
                        epoch_ids_nonempty=len(epoch_ids) > 0,
                    )
                except Exception:
                    cards_snapshot = None
                if cards_snapshot and len(cards_snapshot) > 0:
                    for entry in cards_snapshot:
                        idx = entry.get("idx")
                        ancestor_id = entry.get("ancestorId")
                        # Only process newly appended indices; after page 1, require membership in epoch_ids
                        if idx is None:
                            continue
                        if ancestor_id:
                            # Skip already processed targets to avoid rework
                            if ancestor_id in processed_target_ids:
                                continue
                            if (epoch_ids and ancestor_id in epoch_ids) or (
                                not epoch_ids and allow_snapshot_all
                            ):
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
                            if allow_snapshot_all:
                                items.append((idx, car_elements.nth(idx), None))
                else:
                    # No snapshot available; build items directly from target ids if present
                    target_source = list(harvested_buffer) if allow_snapshot_all else []
                    if target_source:
                        for ancestor_id in target_source:
                            # Skip already processed targets to avoid rework
                            if ancestor_id in processed_target_ids:
                                continue
                            items.append(
                                (
                                    None,
                                    page.locator(
                                        f'[id="{ancestor_id}"] .ResultItem_cardWrap__tA63Q'
                                    ).first,
                                    ancestor_id,
                                )
                            )
                    else:
                        items = []

                sample_ancestors = [s for _, _, s in items[:5]]
                log_kv(
                    "[Items]",
                    epoch=current_epoch,
                    built=len(items),
                    from_snapshot=(cards_snapshot is not None),
                    epoch_ids=len(epoch_ids),
                )
                print(f"  sample_epoch_ids={list(epoch_ids)[:5]}")
                print(f"  sample_ancestors={sample_ancestors}")
                log_kv(
                    "[Per-card]",
                    skipped=(not allow_snapshot_all),
                    mode=("snapshot" if allow_snapshot_all else "dom-diff"),
                )
                log_gap()
                for i, car_elem, stable_ancestor_id in items:
                    processed_count += 1
                    session_seen_count += 1

                    # Early minimal href extraction for fast duplicate skip (avoid heavy operations)
                    early_href = None
                    try:
                        early_href = await car_elem.evaluate(
                            """(el) => {
                                const a = el.querySelector('h3 a, a[href*="/trends/"], a[href]');
                                return a ? a.getAttribute('href') : null;
                            }"""
                        )
                    except Exception:
                        early_href = None
                    if early_href:
                        early_url = (
                            early_href
                            if early_href.startswith("http")
                            else f"https://www.autotempest.com{early_href}"
                        )
                        if early_url in seen_urls_this_model or early_url in seen_urls:
                            skipped_duplicates += 1
                            print(f"  - duplicate: {early_url}")
                            log_kv(
                                "[Skip]",
                                card=i,
                                in_model=(early_url in seen_urls_this_model),
                                in_session=(early_url in seen_urls),
                                epoch=current_epoch,
                            )
                            if stable_ancestor_id:
                                processed_target_ids.add(stable_ancestor_id)
                            continue

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

                    # Early optional ID extraction (for logging/storage only; URL is the dedupe key)
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
                    # Do not skip based on missing or duplicate ID; dedupe happens by URL below

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
                    if href:
                        if href.startswith("http"):
                            listing_url = href
                        else:
                            listing_url = f"https://www.autotempest.com{href}"
                    else:
                        listing_url = None

                    # listing_id already determined by early duplicate check above

                    # Guard: missing href/url
                    if not href:
                        skipped_no_href += 1
                        print(f"Skipping listing {listing_id}: missing href")
                        if stable_ancestor_id:
                            processed_target_ids.add(stable_ancestor_id)
                        continue

                    # URL-based dedupe (per-model and session)
                    if listing_url in seen_urls_this_model or listing_url in seen_urls:
                        skipped_duplicates += 1
                        in_model = listing_url in seen_urls_this_model
                        in_session = listing_url in seen_urls
                        print(f"  - duplicate: {listing_url}")
                        log_kv(
                            "[Skip]",
                            card=i,
                            in_model=in_model,
                            in_session=in_session,
                            epoch=current_epoch,
                        )
                        if stable_ancestor_id:
                            processed_target_ids.add(stable_ancestor_id)
                        continue
                    seen_urls_this_model.add(listing_url)

                    print(f"Card Index: {i}")
                    print(f"Listing ID (optional): {listing_id}")
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
                    seen_urls.add(listing_url)
                    if stable_ancestor_id:
                        processed_target_ids.add(stable_ancestor_id)
                    log_kv(
                        "[Append: network]",
                        epoch=current_epoch,
                        url=listing_url,
                        id=listing_id,
                        ancestor=stable_ancestor_id,
                    )

                # Write the data to a file (dynamic schema growth)
                if local_results:
                    # Ensure output directory exists
                    os.makedirs(os.path.dirname(LISTING_URL_CSV), exist_ok=True)
                    header = not os.path.exists(LISTING_URL_CSV)
                    pd.DataFrame(local_results).to_csv(
                        LISTING_URL_CSV, mode="a", header=header, index=False
                    )
                    saved_this_model += len(local_results)
                    sample_urls = [r.get("url") for r in local_results[:5]]
                    log_gap()
                    log_kv(
                        "[Save: network]", epoch=current_epoch, count=len(local_results)
                    )
                    print(f"  file={LISTING_URL_CSV}")
                    print(f"  sample={sample_urls}")

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
                # Snapshot pre-click hrefs for DOM-diff fallback
                pre_hrefs = await page.evaluate(
                    """
                    Array.from(document.querySelectorAll('.ResultItem_cardWrap__tA63Q a[href]'))
                        .map(a => a.getAttribute('href'))
                        .filter(Boolean)
                    """
                )
                log_kv(
                    "[More Results click]",
                    prev_count=prev_count,
                    clicks_so_far=num_more_results,
                )
                log_gap()
                # Start a new harvest epoch for responses triggered by this click
                current_epoch += 1
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
                    # Do not break; rely on DOM-diff and network signals below to decide continuation

                # Additional settle loop: wait for card count to stabilize
                try:
                    last_count = await page.locator(sel).count()
                    stable_runs = 0
                    max_polls = 10
                    interval_ms = 150
                    required_stable_runs = 2
                    for _ in range(max_polls):
                        await page.wait_for_timeout(interval_ms)
                        curr = await page.locator(sel).count()
                        if curr == last_count:
                            stable_runs += 1
                            if stable_runs >= required_stable_runs:
                                break
                        else:
                            stable_runs = 0
                            last_count = curr
                    log_kv("[Pagination settled]", count=last_count)
                    log_gap()
                except Exception:
                    pass

                # Compute DOM href delta for this new epoch as a fallback
                try:
                    post_hrefs = await page.evaluate(
                        """
                        Array.from(document.querySelectorAll('.ResultItem_cardWrap__tA63Q a[href]'))
                            .map(a => a.getAttribute('href'))
                            .filter(Boolean)
                        """
                    )

                    def _abs_urls(hrefs):
                        out = []
                        for h in hrefs:
                            if h and h.startswith("http"):
                                out.append(h)
                            elif h:
                                out.append(f"https://www.autotempest.com{h}")
                        return set(out)

                    dom_deltas_by_epoch[current_epoch] = _abs_urls(
                        post_hrefs
                    ) - _abs_urls(pre_hrefs)
                    log_kv(
                        "[DOM-Diff]",
                        epoch=current_epoch,
                        new_urls=len(dom_deltas_by_epoch[current_epoch]),
                    )
                    print(f"  sample={list(dom_deltas_by_epoch[current_epoch])[:5]}")
                    log_gap()
                except Exception as e:
                    dom_deltas_by_epoch[current_epoch] = set()
                    print(f"[DOM-Diff] error: {e}")

                # Process DOM-delta URLs for this epoch without re-walking cards
                dom_delta_urls = dom_deltas_by_epoch.get(current_epoch, set())
                if dom_delta_urls:
                    to_add = [
                        u
                        for u in dom_delta_urls
                        if u not in seen_urls and u not in seen_urls_this_model
                    ]
                    if to_add:
                        log_kv(
                            "[DOM-Diff]",
                            epoch=current_epoch,
                            total_delta=len(dom_delta_urls),
                            to_add=len(to_add),
                            already_seen=(len(dom_delta_urls) - len(to_add)),
                        )
                        dom_only_results = [
                            {"make": car[0], "model": car[1], "id": None, "url": u}
                            for u in to_add
                        ]
                        # Ensure output directory exists
                        os.makedirs(os.path.dirname(LISTING_URL_CSV), exist_ok=True)
                        header = not os.path.exists(LISTING_URL_CSV)
                        pd.DataFrame(dom_only_results).to_csv(
                            LISTING_URL_CSV, mode="a", header=header, index=False
                        )
                        saved_this_model += len(dom_only_results)
                        processed_count += len(dom_only_results)
                        session_seen_count += len(dom_only_results)
                        for u in to_add:
                            seen_urls.add(u)
                            seen_urls_this_model.add(u)
                        sample_dom_urls = [r.get("url") for r in dom_only_results[:5]]
                        log_gap()
                        log_kv(
                            "[Save: dom-delta]",
                            epoch=current_epoch,
                            count=len(dom_only_results),
                        )
                        print(f"  file={LISTING_URL_CSV}")
                        print(f"  sample={sample_dom_urls}")

                # Decide continuation based on progress signals (DOM-diff or new epoch ids)
                dom_delta_count = len(dom_deltas_by_epoch.get(current_epoch, set()))
                epoch_new_ids = len(harvest_by_epoch.get(current_epoch, []))
                progress = dom_delta_count > 0 or epoch_new_ids > 0
                if not progress:
                    try:
                        still_visible = await more_button.is_visible()
                        still_enabled = await more_button.is_enabled()
                    except Exception:
                        still_visible = False
                        still_enabled = False
                    if not still_visible or not still_enabled:
                        print(
                            "[Stop] No progress and button disabled/hidden; ending pagination"
                        )
                        break
                    else:
                        print(
                            "[Warn] No progress but button still enabled; continuing to next iteration"
                        )
                # Proceed to next iteration; targeting is driven by newly harvested ids
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
            # Progress bar for models
            bar_width = 30
            filled = int(bar_width * model_index / total_models) if total_models else 0
            bar = "#" * filled + "-" * (bar_width - filled)
            print(f"[Progress] [{bar}] {model_index}/{total_models} models completed")
            await page.wait_for_timeout(random.randint(6000, 9000))

    # Close browser
    await browser.close()


# Run the async function
asyncio.run(main())
