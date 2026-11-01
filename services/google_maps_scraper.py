"""
LeadPilot AI — Google Maps Browser Scraper
Uses Playwright to automate Chrome, open Google Maps, search for businesses,
and extract lead information automatically.

This provider opens a real browser window so the user can watch the agent work.
"""
import asyncio
import re
import time
import hashlib
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import quote_plus

from config.logging_config import logger
from services.discovery_provider import DiscoveryProvider, normalize_discovery_record

# CSS selectors for Google Maps (with fallbacks for UI changes)
SELECTORS = {
    # Search
    "search_input": "#searchboxinput",
    "search_button": "#searchbox-searchbutton",

    # Results list
    "results_feed": "div[role='feed']",
    "result_items": "div[role='feed'] > div > div > a",
    "result_links_alt": "a[href*='/maps/place/']",

    # Business detail panel
    "biz_name": "h1.DUwDvf, h1.fontHeadlineLarge, div.qBF1Pd.fontHeadlineSmall",
    "biz_category": "button.DkEaL, span.DkEaL, div.LBgpqf span",
    "biz_address": "button[data-item-id='address'] div.fontBodyMedium, "
                   "div[data-item-id='address'] div.fontBodyMedium, "
                   "button[data-tooltip='Copy address'] div.fontBodyMedium",
    "biz_phone": "button[data-item-id^='phone'] div.fontBodyMedium, "
                 "button[data-tooltip='Copy phone number'] div.fontBodyMedium",
    "biz_website": "a[data-item-id='authority'], "
                   "a[aria-label*='Website'], "
                   "a[data-item-id='authority'] div.fontBodyMedium",
    "biz_rating": "div.F7nice span[aria-hidden='true'], span.ceNzKf[aria-hidden='true']",
    "biz_review_count": "span.UY7F9, div.F7nice span[aria-label]",
    "biz_hours": "div[data-item-id='oh'] div.fontBodyMedium",

    # Navigation
    "back_button": "button[aria-label='Back'], button[jsaction*='back']",

    # Consent / cookie dialog
    "consent_accept": "button[aria-label='Accept all'], form[action*='consent'] button",
}


class GoogleMapsScraper:
    """
    Playwright-based Google Maps scraper that opens a visible Chrome window,
    searches for businesses, and extracts structured lead data.
    """

    ATTRIBUTION = "Data extracted from Google Maps. Google and the Google logo are trademarks of Google LLC."

    def __init__(self):
        self._playwright = None
        self._browser = None

    @property
    def provider_name(self) -> str:
        return "Google Maps (Browser)"

    @property
    def attribution(self) -> str:
        return self.ATTRIBUTION

    async def scrape_leads(
        self,
        query: str,
        location: str,
        max_results: int = 20,
        headless: bool = False,
        progress_callback: Optional[Callable] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Open Google Maps, search for businesses, and extract lead data.

        Args:
            query: Business type (e.g., "dental clinic")
            location: City/area (e.g., "Mumbai")
            max_results: Maximum leads to extract
            headless: If False, opens visible browser window
            progress_callback: fn(step_name, percent, message) for progress updates

        Returns:
            (list_of_leads, error_message_or_None)
        """
        leads = []
        error = None

        def _progress(step: str, pct: int, msg: str):
            if progress_callback:
                try:
                    progress_callback(step, pct, msg)
                except Exception:
                    pass

        try:
            from playwright.async_api import async_playwright

            _progress("init", 5, f"Launching Chrome browser ({'headless' if headless else 'visible'} mode)...")

            search_clean = query.strip()
            if location.strip():
                if location.strip().lower() not in search_clean.lower():
                    search_term = f"{search_clean} in {location.strip()}"
                else:
                    search_term = search_clean
            else:
                search_term = search_clean

            maps_url = f"https://www.google.com/maps/search/{quote_plus(search_term)}"
            _progress("navigate", 10, f"Opening Google Maps: \"{search_term}\"...")

            async with async_playwright() as pw:
                # Add chromium launch fallback arguments to prevent sandboxing or profile lock crashes
                browser = await pw.chromium.launch(
                    headless=headless,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--start-maximized",
                    ]
                )
                context = await browser.new_context(
                    viewport={"width": 1366, "height": 900},
                    locale="en-US",
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                )
                page = await context.new_page()

                # Navigate with domcontentloaded and safe timeout
                try:
                    await page.goto(maps_url, wait_until="domcontentloaded", timeout=45000)
                except Exception as nav_e:
                    logger.warning("Navigation timeout/warning: %s. Continuing with page...", nav_e)
                await page.wait_for_timeout(3500)

                # Handle cookie consent if it appears
                await self._dismiss_consent(page)

                # ── Step 2: Wait for results to load ─────────────────────
                _progress("loading", 15, "Waiting for search results to load...")

                has_feed = False
                try:
                    await page.wait_for_selector(
                        SELECTORS["results_feed"],
                        timeout=10000,
                        state="attached"
                    )
                    has_feed = True
                except Exception:
                    pass

                if not has_feed:
                    # Check if single business directly loaded
                    single_name = await self._safe_text(page, SELECTORS["biz_name"])
                    if single_name:
                        _progress("extract", 50, f"Found business directly: {single_name}")
                        lead = await self._extract_business_details(page, location)
                        if lead:
                            leads.append(lead)
                        await browser.close()
                        return leads, None

                    # Or check if any place links exist even if feed container wasn't matched
                    place_links_count = await page.locator("a[href*='/maps/place/']").count()
                    if place_links_count == 0:
                        await browser.close()
                        return [], f"No business results found on Google Maps for '{search_term}'."

                # ── Step 3: Scroll to load more results ──────────────────
                _progress("scrolling", 20, "Scrolling through results to find businesses...")

                result_links = await self._scroll_and_collect_results(
                    page, max_results, _progress
                )

                total_found = len(result_links)
                _progress("scrolling", 35,
                          f"Found {total_found} businesses on the map. Starting data extraction...")

                if not result_links:
                    await browser.close()
                    return [], "Could not find any business listings on Google Maps."

                # ── Step 4: Click each result and extract details ─────────
                for idx, link_info in enumerate(result_links):
                    if len(leads) >= max_results:
                        break

                    pct = 35 + int(55 * (idx + 1) / len(result_links))
                    biz_label = link_info.get("label", f"Business #{idx+1}")
                    _progress("extract", pct,
                              f"[{idx+1}/{min(len(result_links), max_results)}] Extracting: {biz_label}")

                    try:
                        lead = await self._click_and_extract(
                            page, link_info, location, idx
                        )
                        if lead and lead.get("business_name", "").strip():
                            leads.append(lead)
                            logger.info("Extracted lead #%d: %s", len(leads), lead["business_name"])
                    except Exception as e:
                        logger.warning("Failed to extract business #%d: %s", idx+1, str(e))
                        continue

                _progress("done", 95,
                          f"Extraction complete! Found {len(leads)} business leads.")

                await browser.close()

        except ImportError:
            error = "Playwright is not installed. Run: pip install playwright && python -m playwright install chromium"
        except Exception as e:
            error = f"Google Maps scraper error: {str(e)}"
            logger.error("Google Maps scraper error: %s", str(e), exc_info=True)

        _progress("complete", 100,
                  f"Google Maps scraping finished. {len(leads)} leads extracted."
                  + (f" Error: {error}" if error else ""))

        return leads, error

    async def _dismiss_consent(self, page):
        """Dismiss cookie consent dialogs if they appear."""
        try:
            for selector in SELECTORS["consent_accept"].split(","):
                sel = selector.strip()
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=2000):
                    await btn.click()
                    await page.wait_for_timeout(1000)
                    return
        except Exception:
            pass  # No consent dialog

    async def _scroll_and_collect_results(
        self, page, max_results: int, progress_fn
    ) -> List[Dict[str, str]]:
        """
        Scroll the results panel to load more businesses.
        Returns list of dicts with 'selector_index', 'label', 'href'.
        """
        results = []
        seen_hrefs = set()
        max_scrolls = max(10, max_results // 2)
        scroll_count = 0
        no_new_count = 0

        feed = page.locator(SELECTORS["results_feed"])

        while scroll_count < max_scrolls and len(results) < max_results * 2:
            # Collect all visible result links
            links = page.locator("a[href*='/maps/place/']")
            count = await links.count()

            new_this_round = 0
            for i in range(count):
                try:
                    href = await links.nth(i).get_attribute("href", timeout=2000)
                    label = await links.nth(i).get_attribute("aria-label", timeout=2000) or ""

                    if href and href not in seen_hrefs:
                        seen_hrefs.add(href)
                        results.append({
                            "href": href,
                            "label": label.strip(),
                            "index": len(results)
                        })
                        new_this_round += 1
                except Exception:
                    continue

            if new_this_round == 0:
                no_new_count += 1
                if no_new_count >= 3:
                    break  # No more results loading
            else:
                no_new_count = 0

            # Scroll the feed panel down
            try:
                await feed.evaluate(
                    "el => el.scrollBy(0, el.clientHeight)"
                )
            except Exception:
                # Fallback scroll
                try:
                    await page.evaluate("""
                        () => {
                            const feed = document.querySelector("div[role='feed']");
                            if (feed) feed.scrollBy(0, 600);
                        }
                    """)
                except Exception:
                    break

            await page.wait_for_timeout(1500)
            scroll_count += 1

            pct = 20 + int(15 * scroll_count / max_scrolls)
            progress_fn("scrolling", min(pct, 34),
                        f"Scrolling... found {len(results)} businesses so far")

        return results[:max_results * 2]  # Return up to 2x to account for extraction failures

    async def _click_and_extract(
        self, page, link_info: Dict, location: str, index: int
    ) -> Optional[Dict[str, Any]]:
        """Click a result link and extract business details from the panel."""
        href = link_info.get("href", "")

        try:
            # Navigate to the business detail page
            link = page.locator(f"a[href='{href}']").first
            if not await link.is_visible(timeout=3000):
                # Try navigating directly
                await page.goto(href, wait_until="domcontentloaded", timeout=15000)
            else:
                await link.click(timeout=5000)

            await page.wait_for_timeout(2000)

            # Wait for business name to appear
            try:
                await page.wait_for_selector(SELECTORS["biz_name"], timeout=8000)
            except Exception:
                await page.wait_for_timeout(2000)

            lead = await self._extract_business_details(page, location)

            # Go back to results list
            await page.go_back(wait_until="domcontentloaded", timeout=10000)
            await page.wait_for_timeout(1500)

            # Re-wait for results feed
            try:
                await page.wait_for_selector(SELECTORS["results_feed"], timeout=8000)
            except Exception:
                pass

            return lead

        except Exception as e:
            logger.debug("Click-and-extract failed for %s: %s", href[:80], str(e))
            # Try to navigate back
            try:
                await page.go_back(timeout=5000)
                await page.wait_for_timeout(1000)
            except Exception:
                pass
            return None

    async def _extract_business_details(
        self, page, location: str
    ) -> Optional[Dict[str, Any]]:
        """Extract all business details from the currently visible detail panel."""

        name = await self._safe_text(page, SELECTORS["biz_name"])
        if not name:
            return None

        category = await self._safe_text(page, SELECTORS["biz_category"])
        address = await self._safe_text(page, SELECTORS["biz_address"])
        phone = await self._safe_text(page, SELECTORS["biz_phone"])
        website_url = await self._safe_attr(page, SELECTORS["biz_website"], "href")
        rating_text = await self._safe_text(page, SELECTORS["biz_rating"])
        review_text = await self._safe_text(page, SELECTORS["biz_review_count"])

        # Parse rating
        rating = None
        if rating_text:
            try:
                rating = float(rating_text.replace(",", "."))
            except (ValueError, TypeError):
                pass

        # Parse review count
        review_count = 0
        if review_text:
            # Extract numbers from text like "(1,234)" or "1,234 reviews"
            nums = re.findall(r"[\d,]+", review_text)
            if nums:
                try:
                    review_count = int(nums[0].replace(",", ""))
                except (ValueError, TypeError):
                    pass

        # Clean website URL
        if website_url:
            # Remove Google redirect wrapper if present
            if "google.com/url" in website_url:
                match = re.search(r"[?&]q=([^&]+)", website_url)
                if match:
                    from urllib.parse import unquote
                    website_url = unquote(match.group(1))

        # Generate place_id from name + address hash
        id_source = f"gmaps:{name}:{address or location}"
        place_id = f"gmaps:{hashlib.md5(id_source.encode()).hexdigest()[:12]}"

        # Get Google Maps URL
        maps_url = page.url if "google.com/maps" in page.url else None

        # Parse city from address or use provided location
        city = location
        if address and "," in address:
            # Try to extract city from address parts
            parts = [p.strip() for p in address.split(",")]
            if len(parts) >= 2:
                city = parts[-2] if len(parts) >= 3 else parts[-1]

        return normalize_discovery_record(
            place_id=place_id,
            business_name=name,
            category=category,
            full_address=address,
            city=city,
            country="India",
            phone_number=phone,
            website_url=website_url,
            maps_url=maps_url,
            rating=rating,
            review_count=review_count,
            source="Google Maps (Browser)",
            attribution=self.ATTRIBUTION,
            website_status="UNVERIFIED",
        )

    async def _safe_text(self, page, selector: str) -> Optional[str]:
        """Safely extract text from the first matching element."""
        for sel in selector.split(","):
            sel = sel.strip()
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=1500):
                    text = (await el.inner_text(timeout=2000)).strip()
                    if text:
                        return text
            except Exception:
                continue
        return None

    async def _safe_attr(self, page, selector: str, attr: str) -> Optional[str]:
        """Safely extract an attribute from the first matching element."""
        for sel in selector.split(","):
            sel = sel.strip()
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=1500):
                    val = await el.get_attribute(attr, timeout=2000)
                    if val:
                        return val.strip()
            except Exception:
                continue
        return None


# Singleton
google_maps_scraper = GoogleMapsScraper()

