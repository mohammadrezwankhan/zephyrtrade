"""Exercise the shipped HTML in Chromium with deterministic document fixtures.

This harness uses set_content and an explicit in-memory Storage test double.
It verifies UI logic, not native durable browser storage or end-to-end
browser-to-server integration. Real local HTTP is tested separately in pytest.
Only the instrumented in-memory document authorizes the exact fixture script;
the shipped HTML and its content security policy remain unchanged.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html as html_tools
import json
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


class _PolicyTags(HTMLParser):
    """Locate exact meta-policy tags without interpreting executable content."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "meta":
            return
        values = dict(attrs)
        if (values.get("http-equiv") or "").casefold() != "content-security-policy":
            return
        original = self.get_starttag_text()
        policy = values.get("content")
        if original is None or policy is None or len(values) != len(attrs):
            raise ValueError("The fixture requires an unambiguous meta policy")
        self.tags.append((original, policy))


def _authorize_fixture(document: str, source: str) -> str:
    """Extend only script directives with the fixture's exact SHA256 source hash."""
    parser = _PolicyTags()
    parser.feed(document)
    if len(parser.tags) != 1:
        raise ValueError(
            "The fixture requires exactly one meta content security policy"
        )
    original, policy = parser.tags[0]
    directives = [part.strip().split() for part in policy.split(";") if part.strip()]
    names = [directive[0] for directive in directives]
    if len(set(names)) != len(names) or "script-src" not in names:
        raise ValueError("The fixture requires a unique explicit script-src policy")
    digest = base64.b64encode(hashlib.sha256(source.encode("utf-8")).digest()).decode()
    token = f"'sha256-{digest}'"
    for directive in directives:
        if directive[0] in {"script-src", "script-src-elem"} and token not in directive:
            directive.append(token)
    updated = "; ".join(" ".join(directive) for directive in directives)
    content = re.search(r"\bcontent\s*=\s*([\"'])(.*?)\1", original, re.DOTALL | re.I)
    if content is None:
        raise ValueError("The fixture requires a quoted content policy")
    replacement = f'content="{html_tools.escape(updated, quote=True)}"'
    meta = original[: content.start()] + replacement + original[content.end() :]
    return document.replace(original, meta, 1)


def instrument(document: str, store: dict[str, str] | None = None) -> str:
    """Add a deterministic storage double and observe actual export payloads."""
    encoded = json.dumps(store or {}).replace("</", "<\\/")
    source = f"""
    (()=>{{
    window.__store={encoded};window.__denyStorage=false;window.__exports=[];
    Object.defineProperty(window,'localStorage',{{configurable:true,value:{{
      getItem:k=>Object.prototype.hasOwnProperty.call(window.__store,k)
        ?window.__store[k]:null,
      setItem:(k,v)=>{{
        if(window.__denyStorage)
          throw new DOMException('Test quota','QuotaExceededError');
        window.__store[k]=String(v);
      }},
      removeItem:k=>{{delete window.__store[k];}},clear:()=>{{window.__store={{}};}}
    }}}});
    const originalCreateURL=URL.createObjectURL.bind(URL);
    URL.createObjectURL=blob=>{{
      window.__exports.push(blob);return originalCreateURL(blob);
    }};
    }})();
    """
    if document.count("</head>") != 1:
        raise ValueError("The fixture requires one explicit document head")
    authorized = _authorize_fixture(document, source)
    return authorized.replace("</head>", f"<script>{source}</script></head>")


def main(argv: list[str] | None = None) -> None:
    """Run the documented browser journeys against an instrumented local document."""
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chromium", default="/usr/bin/chromium")
    parser.add_argument("--output", type=Path, default=root / "docs/champion/evidence")
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    shots = args.output / "screenshots"
    shots.mkdir(exist_ok=True)
    html = (root / "ZephyrTrade-Champion.html").read_text()
    checks: list[dict[str, str]] = []
    errors: list[str] = []

    def record(name: str, details: str = "") -> None:
        """Record a completed browser interaction with its observed details."""
        checks.append({"check": name, "status": "PASS", "details": details})

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=args.chromium,
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000}, device_scale_factor=1
        )
        page = context.new_page()
        page.set_default_timeout(5000)
        page.on("pageerror", lambda e: errors.append(str(e)))
        downloads: list[str] = []
        page.on("download", lambda d: downloads.append(d.suggested_filename))

        def capture(name: str) -> None:
            """Capture the settled application state at the top of the page."""
            # Capture the settled real app state at the top of the page.
            page.locator("#page-title").click()
            page.evaluate("window.scrollTo(0,0)")
            page.wait_for_timeout(120)
            expect(page.locator("#toast")).to_be_hidden(timeout=7000)
            page.screenshot(path=str(shots / name), full_page=True)

        begin = time.perf_counter()
        page.set_content(instrument(html), wait_until="load")
        expect(page.locator("#page-title")).to_have_text("From wind to value.")
        elapsed = time.perf_counter() - begin
        metrics = page.evaluate("ZephyrApp.getVisibleMetrics()")
        if not (metrics["rows"] == 3888):
            raise AssertionError
        if not (abs(metrics["total"] - 18761431.424600992) < 1e-6):
            raise AssertionError
        if not (page.locator("#model-select option").count() == 9):
            raise AssertionError
        record(
            "Initial snapshot and nine strategies",
            (
                f"3888 hours, full-precision revenue agrees; one set_content load "
                f"{elapsed:.3f}s (not network performance)."
            ),
        )
        capture("overview-desktop.png")
        page.get_by_role("button", name="Prices", exact=True).click()
        if not (page.locator('svg[role="img"]').count() > 0):
            raise AssertionError
        page.get_by_role("button", name="Revenue", exact=True).click()
        expect(page.locator("#page-content")).to_contain_text("Perfect foresight")
        page.get_by_role("button", name="Output", exact=True).click()
        record("Three chart modes and benchmark disclosure")
        page.get_by_role("button", name="7 days", exact=True).click()
        ids = page.evaluate("ZephyrApp.getVisibleMetrics().rows")
        if not (0 < ids <= 168):
            raise AssertionError
        page.locator("#model-select").select_option("persistence_24h")
        if not (page.evaluate("ZephyrApp.getState().model") == "persistence_24h"):
            raise AssertionError
        record(
            "Period and strategy changes recompute metrics",
            str(ids) + " retained hours in 7-day window",
        )
        page.get_by_role("button", name="Custom", exact=True).click()
        page.locator("#from-date").fill("2024-12-31")
        page.locator("#to-date").fill("2024-12-01")
        page.get_by_role("button", name="Apply", exact=True).click()
        expect(page.locator("#filter-error")).to_be_visible()
        page.locator("#from-date").fill("2024-07-21")
        page.locator("#to-date").fill("2024-07-21")
        page.get_by_role("button", name="Apply", exact=True).click()
        if not (0 < page.evaluate("ZephyrApp.getVisibleMetrics().rows") <= 24):
            raise AssertionError
        record("Invalid date ordering rejected; one-day window recovers")
        # Dates outside the supplied observations must not replace the valid prior view.
        prior_metrics = page.evaluate("ZephyrApp.getVisibleMetrics()")
        prior_state = page.evaluate("ZephyrApp.getState()")
        page.locator("#from-date").fill("2025-01-01")
        page.locator("#to-date").fill("2025-01-02")
        page.get_by_role("button", name="Apply", exact=True).click()
        expect(page.locator("#filter-error")).to_contain_text("Choose valid dates")
        if page.evaluate("ZephyrApp.getVisibleMetrics()") != prior_metrics:
            raise AssertionError("Rejected dates changed the prior observations")
        if page.evaluate("ZephyrApp.getState()") != prior_state:
            raise AssertionError("Rejected dates changed the prior filter state")
        page.get_by_role("button", name="All data", exact=True).click()
        record("Out-of-range dates retain prior observations and explicit recovery")
        page.get_by_role("link", name="Model arena").click()
        expect(page.locator("#page-title")).to_have_text("Let the evidence lead.")
        if not (page.locator("tbody tr").count() == 9):
            raise AssertionError
        capture("model-arena-desktop.png")
        page.locator("#export-models").click()
        text = page.evaluate("window.__exports.at(-1).text()")
        if not (len(text.strip().splitlines()) == 10 and "capture_pct" in text):
            raise AssertionError
        record("Nine-row model ranking and comparison CSV payload")
        page.get_by_role("link", name="Data explorer").click()
        expect(page.locator("#page-title")).to_have_text("Every number, traceable.")
        if not (page.locator("tbody tr").count() == 25):
            raise AssertionError
        first = page.locator("tbody tr").first.inner_text()
        page.get_by_role("button", name="Next", exact=True).click()
        if not (page.locator("tbody tr").first.inner_text() != first):
            raise AssertionError
        page.locator("#data-search").fill("2024-12-15")
        if not (0 < page.locator("tbody tr").count() <= 24):
            raise AssertionError
        page.locator("#export-filtered").click()
        text = page.evaluate("window.__exports.at(-1).text()")
        if not ("synthetic_research" in text and "2024-12-15" in text):
            raise AssertionError
        if not (len(text.strip().splitlines()) <= 25):
            raise AssertionError
        page.locator("#data-search").fill("not-a-date")
        expect(page.locator("tbody")).to_contain_text("No matching records.")
        page.locator("#data-search").fill("")
        record("Ledger pagination, search, empty state and filtered CSV payload")
        page.get_by_role("link", name="Strategy lab").click()
        expect(page.locator("#optimal-offer")).to_contain_text("9.00")
        page.locator("#da").fill("999")
        expect(page.locator("#lab-stale")).to_be_visible()
        expect(page.locator("#save-scenario")).to_be_disabled()
        page.get_by_role("link", name="Overview").click()
        page.get_by_role("link", name="Strategy lab").click()
        expect(page.locator("#da")).to_have_value("999")
        expect(page.locator("#save-scenario")).to_be_disabled()
        page.get_by_role("button", name="Calculate optimal offer").click()
        expect(page.locator("#lab-error")).to_be_visible()
        page.locator("#da").fill("400")
        page.locator("#up").fill("600")
        page.locator("#down").fill("200")
        page.locator("#scenarios").fill("2,8,20")
        page.locator("#probabilities").fill(".2,.5,.3")
        page.get_by_role("button", name="Calculate optimal offer").click()
        expect(page.locator("#optimal-offer")).to_contain_text("8.00")
        expect(page.locator("#expected-revenue")).to_contain_text("3,200.00")
        expect(page.locator("#lab-stale")).to_be_hidden()
        record(
            "Dirty assumptions, draft navigation retention, invalid prices and recovery"
        )
        capture("strategy-lab-desktop.png")
        page.locator("#hours").fill("0.25")
        page.get_by_role("button", name="Calculate optimal offer").click()
        expect(page.locator("#expected-revenue")).to_contain_text("800.00")
        record("Quarter-hour settlement scaling in UI")
        page.locator("#save-scenario").click()
        expect(page.locator("#save-dialog")).to_be_visible()
        page.locator("#scenario-name").fill("<script>not executable</script>")
        page.locator("#save-form button[type=submit]").click()
        expect(page.locator("#saved-list")).to_contain_text(
            "<script>not executable</script>"
        )
        if not (page.locator("#saved-list script").count() == 0):
            raise AssertionError
        store = page.evaluate("window.__store")
        if "zephyr-scenarios-v1" not in store:
            raise AssertionError
        record(
            "Scenario save and escaped names through Storage test double",
            "Native durable storage NOT verified in this harness.",
        )
        page.locator("#export-scenario").click()
        scenario = json.loads(page.evaluate("window.__exports.at(-1).text()"))
        if not (scenario["calculated"]["expected_revenue_dkk"] == 800):
            raise AssertionError
        page.locator("#export-curve").click()
        if "user_assumptions" not in page.evaluate("window.__exports.at(-1).text()"):
            raise AssertionError
        record("Scenario JSON and revenue-curve CSV payloads")
        page.locator("#scenario-file").set_input_files(
            {"name": "bad.json", "mimeType": "application/json", "buffer": b"{invalid"}
        )
        expect(page.locator("#toast")).to_contain_text("Import failed:")
        scenario["input"]["hours"] = 1
        page.locator("#scenario-file").set_input_files(
            {
                "name": "scenario.json",
                "mimeType": "application/json",
                "buffer": json.dumps(scenario).encode(),
            }
        )
        expect(page.locator("#hours")).to_have_value("1")
        expect(page.locator("#expected-revenue")).to_contain_text("3,200.00")
        record("Invalid import rejected; valid JSON imports and recalculates")
        page.evaluate("window.__denyStorage=true")
        page.locator("#save-scenario").click()
        page.locator("#scenario-name").fill("Quota test")
        page.locator("#save-form button[type=submit]").click()
        expect(page.locator("#toast")).to_contain_text("Could not save")
        expect(page.locator("#save-dialog")).to_be_visible()
        page.get_by_role("button", name="Cancel", exact=True).click()
        page.evaluate("window.__denyStorage=false")
        record(
            "Storage failure is not reported as a successful save",
            "Fault injection into explicit Storage double.",
        )
        page.on("dialog", lambda dialog: dialog.accept())
        page.locator("[data-delete-saved]").click()
        expect(page.locator("#saved-list")).to_contain_text(
            "Your experiments belong here."
        )
        record("Delete confirmation and in-memory storage update")
        # Hydrate an actual saved app record using a fresh DOM and storage fixture.
        page.close()
        page = context.new_page()
        page.set_default_timeout(5000)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("download", lambda d: downloads.append(d.suggested_filename))
        page.set_content(instrument(html, store), wait_until="load")
        page.get_by_role("link", name="Strategy lab").click()
        expect(page.locator("#saved-list")).to_contain_text("not executable")
        page.locator("[data-load-saved]").click()
        expect(page.locator("#hours")).to_have_value("0.25")
        record(
            "Saved-record hydration and loading",
            "Fixture rehydration, not an OS/browser persistence claim.",
        )
        page.locator("#verify-python").click()
        expect(page.locator("#page-title")).to_have_text("Know what you are seeing.")
        record("Unavailable optional solver leads to setup, not fabricated success")
        page.locator("#export-provenance").click()
        provenance = json.loads(page.evaluate("window.__exports.at(-1).text()"))
        if not (
            provenance["quality"]["rows"] == 3888 and len(provenance["sources"]) == 2
        ):
            raise AssertionError
        record("Provenance JSON exposes source hashes and exclusions")
        page.get_by_role("button", name="Open quick guide").click()
        expect(page.locator("#guide-dialog")).to_be_visible()
        if not (
            page.evaluate(
                "document.querySelector('#guide-dialog').contains(document.activeElement)"
            )
        ):
            raise AssertionError
        page.keyboard.press("Escape")
        expect(page.locator("#guide-dialog")).to_be_hidden()
        expect(page.locator("#help-button")).to_be_focused()
        record("Dialog focus entry, Escape and focus return")
        page.get_by_role("link", name="Overview").click()
        page.locator("#model-select").select_option("direct_regression")
        for width, height in [
            (1440, 1000),
            (1024, 900),
            (768, 1024),
            (390, 844),
            (320, 740),
        ]:
            page.set_viewport_size({"width": width, "height": height})
            for name in [
                "Overview",
                "Strategy lab",
                "Model arena",
                "Data explorer",
                "Method & evidence",
            ]:
                page.get_by_role("link", name=name, exact=False).click()
                if not (
                    page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
                ):
                    raise AssertionError((width, name, "overflow"))
            if width == 390:
                page.get_by_role("link", name="Overview").click()
                capture("overview-mobile.png")
                page.get_by_role("link", name="Strategy lab").click()
                capture("strategy-lab-mobile.png")
        record(
            "Responsive overflow check across five pages and five viewports",
            "1440, 1024, 768, 390, 320 CSS px; emulation only.",
        )
        page.locator("#theme-top").click()
        if not (page.locator("html").get_attribute("data-theme") == "light"):
            raise AssertionError
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.get_by_role("link", name="Overview").click()
        capture("overview-light.png")
        record("Light theme and mobile-accessible theme toggle")
        page.emulate_media(reduced_motion="reduce")
        if not (
            page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
        ):
            raise AssertionError
        transition = page.locator(".button").first.evaluate(
            "el=>getComputedStyle(el).transitionDuration"
        )
        if transition not in ["0s", "1e-05s", "0.00001s", "0.01ms"]:
            raise AssertionError(transition)
        record("Reduced-motion preference respected", transition)
        # DOM checks are not a comprehensive accessibility audit.
        missing = page.evaluate(
            "() => [...document.querySelectorAll('button,input:not([type="
            "file]),select,textarea')].filter(el=>el.getClientRects().len"
            "gth && !el.disabled &&"
            " !(el.innerText?.trim()||el.getAttribute('aria-label')||el.l"
            "abels?.length||el.getAttribute('title'))).map(el=>el.outerHT"
            "ML)"
        )
        if missing:
            raise AssertionError(missing)
        record(
            "Visible controls have DOM labels or accessible-name sources",
            "No screen-reader or full WCAG conformance claim.",
        )
        if errors:
            raise AssertionError(errors)
        record("No uncaught JavaScript exceptions across exercised journeys")
        result = {
            "status": "PASS",
            "harness": (
                "Chromium set_content; in-memory Storage double; no file or"
                " localhost browser navigation"
            ),
            "browser": browser.version,
            "checks": checks,
            "javascript_errors": errors,
            "browser_download_events": downloads,
            "limitations": [
                (
                    "Native persistent storage and real file navigation are not"
                    " exercised by this document-fixture harness"
                ),
                (
                    "Browser-to-Python navigation is not exercised here; Python"
                    " HTTP API tested separately"
                ),
                "Screenshots are actual rendered app, not a concept mockup",
                "Human UAT, real devices and assistive-technology tests not performed",
            ],
        }
        (args.output / "browser-checks.json").write_text(json.dumps(result, indent=2))
        sys.stdout.write(str(json.dumps(result, indent=2)) + "\n")
        browser.close()


if __name__ == "__main__":
    main()
