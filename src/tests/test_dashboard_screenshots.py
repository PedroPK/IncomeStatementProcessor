"""
Playwright tests to capture Dashboard screenshots for documentation.

This module takes screenshots of the dashboard in different states:
- Full page view
- Light mode
- Dark mode
- Individual chart views
- Responsive layouts

Screenshots are saved to docs/screenshots/ for use in documentation.
"""

import asyncio
import tempfile
from pathlib import Path
from playwright.async_api import async_playwright
from src.dashboard_generator import generate_dashboard_html
from .test_integration import MOCK_ENTRIES


async def take_dashboard_screenshots():
    """
    Generate dashboard and capture screenshots in multiple states.
    
    Screenshots captured:
    - dashboard_full_light.png - Full page in light mode
    - dashboard_full_dark.png - Full page in dark mode
    - dashboard_charts_light.png - Charts section in light mode
    - dashboard_charts_dark.png - Charts section in dark mode
    - dashboard_table_light.png - Table section in light mode
    - dashboard_responsive.png - Responsive view (mobile width)
    """
    
    print("\n" + "=" * 70)
    print("📸 DASHBOARD SCREENSHOT CAPTURE")
    print("=" * 70 + "\n")
    
    # Create screenshots directory
    screenshots_dir = Path('docs/screenshots')
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate dashboard HTML
    print("🔨 Generating dashboard HTML...")
    dashboard_path = Path(tempfile.gettempdir()) / 'dashboard_temp.html'
    generate_dashboard_html(MOCK_ENTRIES, str(dashboard_path))
    print(f"   ✅ Dashboard generated: {dashboard_path}")
    
    # Convert to file:// URL
    dashboard_url = dashboard_path.as_uri()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        print(f"\n📱 Opening dashboard at {dashboard_url}")
        await page.goto(dashboard_url, wait_until='networkidle')
        
        # Wait for charts to render
        await page.wait_for_selector('#chartInstitution', timeout=5000)
        print("   ✅ Dashboard loaded and charts rendered")
        
        # ── Light Mode Screenshots ──────────────────────────────────────────
        print("\n💡 Capturing light mode screenshots...")
        
        # Ensure light mode is active
        await page.evaluate('() => document.documentElement.classList.remove("dark-mode")')
        await page.wait_for_timeout(500)  # Wait for theme switch animation
        
        # Full page light mode
        screenshot_path = screenshots_dir / 'dashboard_full_light.png'
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"   ✅ Full page (light): {screenshot_path}")
        
        # Charts section light mode
        charts_section = await page.query_selector('.row.mb-4')
        if charts_section:
            screenshot_path = screenshots_dir / 'dashboard_charts_light.png'
            await charts_section.screenshot(path=str(screenshot_path))
            print(f"   ✅ Charts section (light): {screenshot_path}")
        
        # Table section light mode
        table_section = await page.query_selector('.table')
        if table_section:
            screenshot_path = screenshots_dir / 'dashboard_table_light.png'
            await table_section.screenshot(path=str(screenshot_path))
            print(f"   ✅ Table section (light): {screenshot_path}")
        
        # ── Dark Mode Screenshots ───────────────────────────────────────────
        print("\n🌙 Capturing dark mode screenshots...")
        
        # Enable dark mode
        await page.evaluate('() => document.documentElement.classList.add("dark-mode")')
        await page.wait_for_timeout(500)  # Wait for theme switch animation
        
        # Full page dark mode
        screenshot_path = screenshots_dir / 'dashboard_full_dark.png'
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"   ✅ Full page (dark): {screenshot_path}")
        
        # Charts section dark mode
        if charts_section:
            screenshot_path = screenshots_dir / 'dashboard_charts_dark.png'
            await charts_section.screenshot(path=str(screenshot_path))
            print(f"   ✅ Charts section (dark): {screenshot_path}")
        
        # ── Responsive Design ───────────────────────────────────────────────
        print("\n📱 Capturing responsive layout...")
        
        # Set mobile viewport
        await page.set_viewport_size({"width": 375, "height": 667})
        await page.evaluate('() => document.documentElement.classList.remove("dark-mode")')
        await page.wait_for_timeout(500)
        
        screenshot_path = screenshots_dir / 'dashboard_responsive_mobile.png'
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"   ✅ Responsive mobile: {screenshot_path}")
        
        # ── Evolution Chart Detail ──────────────────────────────────────────
        print("\n📊 Capturing evolution chart detail...")
        
        await page.set_viewport_size({"width": 1280, "height": 720})
        evolution_chart = await page.query_selector('#chartEvolution')
        if evolution_chart:
            parent = await evolution_chart.evaluate_handle('el => el.closest(".col-md-6")')
            screenshot_path = screenshots_dir / 'dashboard_chart_evolution.png'
            await parent.screenshot(path=str(screenshot_path))
            print(f"   ✅ Evolution chart detail: {screenshot_path}")
        
        # ── Institution Distribution Chart ─────────────────────────────────
        print("\n🥧 Capturing institution distribution chart...")
        
        institution_chart = await page.query_selector('#chartInstitution')
        if institution_chart:
            parent = await institution_chart.evaluate_handle('el => el.closest(".col-md-6")')
            screenshot_path = screenshots_dir / 'dashboard_chart_institution.png'
            await parent.screenshot(path=str(screenshot_path))
            print(f"   ✅ Institution chart detail: {screenshot_path}")
        
        # ── Tab Navigation ─────────────────────────────────────────────────
        print("\n📋 Capturing tab views...")
        
        tab_names = ['resumo', 'totais']  # Simplified: capture main tabs
        for tab_name in tab_names:
            try:
                # Click tab
                tab_selector = f'a[onclick*="{tab_name}"]'
                tab_button = await page.query_selector(tab_selector)
                if tab_button:
                    await tab_button.click()
                    await page.wait_for_timeout(500)  # Wait for animation and data to render
                    
                    # Capture visible area (not individual element to avoid visibility issues)
                    screenshot_path = screenshots_dir / f'dashboard_tab_{tab_name}.png'
                    await page.screenshot(path=str(screenshot_path), full_page=False)
                    print(f"   ✅ Tab {tab_name}: {screenshot_path}")
            except Exception as e:
                print(f"   ⚠️  Tab {tab_name} capture skipped: {str(e)[:60]}")
        
        await browser.close()
    
    # Print summary
    print("\n" + "=" * 70)
    print("📸 SCREENSHOT CAPTURE COMPLETE")
    print("=" * 70)
    print(f"\n✅ Screenshots saved to: {screenshots_dir.resolve()}")
    print(f"\n📋 Files created:")
    
    for screenshot in sorted(screenshots_dir.glob('*.png')):
        size = screenshot.stat().st_size / 1024  # Size in KB
        print(f"   - {screenshot.name} ({size:.1f}KB)")
    
    print("\n💡 Tip: Add these screenshots to your documentation using:")
    print('   ![Dashboard](./docs/screenshots/dashboard_full_light.png)')
    print("=" * 70 + "\n")


async def take_stepper_screenshots():
    """
    Generate the stepper/initial-screen HTML and capture screenshots showing
    the new About Card feature in both light and dark modes.

    Screenshots captured:
    - stepper_about_light.png  – full initial screen (light mode, about card visible)
    - stepper_about_dark.png   – full initial screen (dark mode, about card visible)
    - stepper_about_card.png   – about card element only (light mode)
    """

    print("\n" + "=" * 70)
    print("📸 STEPPER INITIAL SCREEN – SCREENSHOT CAPTURE")
    print("=" * 70 + "\n")

    screenshots_dir = Path('docs/screenshots')
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    # Render the stepper HTML (no Flask required)
    print("🔨 Generating stepper HTML...")
    from src.main import _stepper_html
    import tempfile

    stepper_path = Path(tempfile.gettempdir()) / 'stepper_temp.html'
    stepper_path.write_text(_stepper_html(), encoding='utf-8')
    stepper_url = stepper_path.as_uri()
    print(f"   ✅ Stepper HTML written: {stepper_path}")

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        print(f"\n📱 Opening stepper at {stepper_url}")
        await page.goto(stepper_url, wait_until='domcontentloaded')
        await page.wait_for_timeout(400)

        # Ensure about card is always visible for the screenshot
        await page.evaluate('() => { localStorage.removeItem("aboutDismissed"); '
                            'const c = document.getElementById("aboutCard"); '
                            'if (c) c.style.display = ""; }')
        await page.wait_for_timeout(200)

        # ── Light mode ──────────────────────────────────────────────────────
        print("\n💡 Light mode...")
        await page.evaluate('() => document.documentElement.classList.remove("dark-mode")')
        await page.wait_for_timeout(300)

        path = screenshots_dir / 'stepper_about_light.png'
        await page.screenshot(path=str(path), full_page=True)
        print(f"   ✅ Full page (light): {path}")

        # About card element only
        about_card = await page.query_selector('#aboutCard')
        if about_card:
            path = screenshots_dir / 'stepper_about_card.png'
            await about_card.screenshot(path=str(path))
            print(f"   ✅ About card only: {path}")

        # ── Dark mode ───────────────────────────────────────────────────────
        print("\n🌙 Dark mode...")
        await page.evaluate('() => document.documentElement.classList.add("dark-mode")')
        await page.wait_for_timeout(300)

        path = screenshots_dir / 'stepper_about_dark.png'
        await page.screenshot(path=str(path), full_page=True)
        print(f"   ✅ Full page (dark): {path}")

        await browser.close()

    print("\n" + "=" * 70)
    print("✅ Stepper screenshots saved to: docs/screenshots")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    asyncio.run(take_dashboard_screenshots())
    asyncio.run(take_stepper_screenshots())
