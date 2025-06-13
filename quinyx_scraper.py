# quinyx_scraper.py

from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
EMAIL = os.getenv("QUINYX_EMAIL")
PASSWORD = os.getenv("QUINYX_PASSWORD")

async def fetch_user_shifts(target_name=None):
    print(f"Fetching shifts for: {target_name or 'ALL STAFF'}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # --- Login ---
        print("Logging in...")
        await page.goto("https://web.quinyx.com/")
        await page.wait_for_selector('input[name="email"]', timeout=30000)
        await page.fill('input[name="email"]', EMAIL)
        await page.click('button[data-test-id="fetchLoginProvidersButton"]')
        await page.wait_for_selector('input[name="password"]', timeout=30000)
        await page.fill('input[name="password"]', PASSWORD)
        await page.click('button[data-test-id="logInButton"]')
        await page.wait_for_timeout(5000)

        # --- Go to custom schedule URL ---
        from datetime import datetime, timedelta

        today = datetime.now()
        from_date_obj = today - timedelta(days=1)
        from_date = from_date_obj.strftime('%Y-%m-%d')

        days_until_next_thursday = (3 - today.weekday() + 7) % 7
        if days_until_next_thursday == 0:
            days_until_next_thursday = 7
        to_date_obj = today + timedelta(days=days_until_next_thursday)
        to_date = to_date_obj.strftime('%Y-%m-%d')

        url = f"https://web.quinyx.com/staffPortal/schedule?dateOption=week&fromDate={from_date}&toDate={to_date}"
        print(f"Navigating to {url}")
        await page.goto(url)
        await page.wait_for_timeout(3000)


        # --- Filter: Colleague's shift ---
        print("Looking for filter button...")
        await page.wait_for_selector('div.legacyDiv.bold.hidden-sm', timeout=10000)
        filter_divs = await page.query_selector_all('div.legacyDiv.bold.hidden-sm')
        for div in filter_divs:
            text = await div.text_content()
            if text.strip() == "Filter":
                await div.click()
                print("Clicked the Filter button")
                break
        await page.wait_for_selector('div[data-test-id="detail-panel"]', timeout=10000)
        await page.wait_for_selector('div[data-test-id="detail-panel"] div.padding-2-left', timeout=10000)
        checkboxes = await page.query_selector_all('div[data-test-id="detail-panel"] input[type="checkbox"]')
        for cb in checkboxes:
            label = await cb.evaluate_handle('el => el.closest("label")')
            label_text = await label.inner_text()
            if "Colleague's shift" in label_text:
                if not await cb.is_checked():
                    checkbox_icon = await label.query_selector('.styled-checkbox__icon')
                    if checkbox_icon:
                        await checkbox_icon.click()
                        print("Enabled Colleague's shift filter")
                break
        await page.click('div[data-test-id="detail-panel"] button[data-test-id="primaryActionButton"]')
        await page.wait_for_timeout(2000)

        # --- Find scroll container ---
        print("Looking for scrollable schedule container...")
        scroll_container = await page.query_selector("div[style*='overflow: auto']")
        if not scroll_container:
            print("ERROR: Could not find the scroll container! Aborting scroll.")
            await browser.close()
            return []

        # --- SCROLL + SCRAPE LOOP ---
        print("Begin scroll-and-scrape loop for virtualized list")
        seen_shifts = set()
        shifts = []
        last_height = -1
        max_scrolls = 70

        current_date = None  # <--- Move this OUTSIDE the scroll loop

        for scroll_round in range(max_scrolls):
            # Scrape what's currently visible
            all_blocks = await page.query_selector_all('div.legacyDiv')
            for block in all_blocks:
                # Date header?
                date_span = await block.query_selector('span.text-uppercase.padding-1.padding-2-left.padding-2-right.bold.background-transparent-grey.font-small')
                if date_span:
                    date_text = (await date_span.text_content()).strip()
                    try:
                        date_part = date_text.split(",")[1].strip()
                        date_obj = datetime.strptime(date_part, "%d/%m/%Y")
                        current_date = date_obj.strftime("%a %d %b")
                    except Exception as e:
                        current_date = date_text
                    continue

                # Shift row?
                class_attr = await block.get_attribute('class')
                if not class_attr or 'background-white padding-2 staff-portal-schedule__row' not in class_attr:
                    continue

                # Extract shift info
                name_div = await block.query_selector('div.flex-row.overflow-ellipsis.d-block.max-width-100.padding-1-right')
                staff_name = (await name_div.text_content()).strip() if name_div else "Unknown"
                time_span = await block.query_selector('span.bold.display-inline-block')
                shift_time = (await time_span.text_content()).strip() if time_span else "?"
                role_span = await block.query_selector('span.display-inline-block.padding-1-left.max-width-50.overflow-ellipsis')
                role = (await role_span.text_content()).strip() if role_span else "?"

                if shift_time and "-" in shift_time:
                    start_time, end_time = [t.strip() for t in shift_time.split("-")]
                else:
                    start_time, end_time = ("?", "?")

                # Compose a unique key to avoid duplicates (name+date+start+end+role)
                shift_key = f"{staff_name}|{current_date}|{start_time}|{end_time}|{role}"
                if shift_key in seen_shifts:
                    continue

                # Only add if the shift matches the requested name or all
                if (not target_name) or (target_name.lower() in staff_name.lower()):
                    shifts.append({
                        "name": staff_name,
                        "date": current_date if current_date else "Unknown",
                        "start": start_time,
                        "end": end_time,
                        "role": role,
                    })
                    seen_shifts.add(shift_key)
                    print(f"Shift: {staff_name} | {current_date} | {start_time}-{end_time} | {role}")

            # Scroll further
            prev_scroll = await scroll_container.evaluate("(el) => el.scrollTop")
            await scroll_container.evaluate("(el) => el.scrollBy(0, 500)")
            await page.wait_for_timeout(800)
            new_scroll = await scroll_container.evaluate("(el) => el.scrollTop")
            if new_scroll == prev_scroll:
                print(f"End of scroll region reached after {scroll_round+1} scrolls.")
                break

        print(f"Returning {len(shifts)} shifts for {target_name or 'all staff'}")
        await browser.close()
        return shifts
