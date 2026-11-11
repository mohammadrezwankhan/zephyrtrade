# Overview chart: keyboard evidence

On 9 November 2026, a keyboard-only automated walkthrough used Chromium
151.0.7922.34 on Windows at 1440 × 900, with the synthetic demo served by
`node scripts/preview-demo.mjs` at `http://127.0.0.1:4173/`.

1. Tab to **Revenue** in the **Chart measure** group and press Enter. The
   button reports `aria-pressed="true"` and retains focus after the redraw.
2. Tab twice to **View chart data table** and press Enter. The disclosure opens.
   Its accessibility tree exposes a named table with UTC interval, perfect
   foresight revenue, and selected strategy revenue columns in DKK. The first
   daily row displayed 20 Jul, 9,573.49 DKK and 9,456.66 DKK respectively.
3. The automated browser regression checks the first daily mean and also
   checks Output, Revenue and Prices against source values for a selected
   hourly interval. It verifies the open disclosure and its focus survive a
   viewport-width change. At 390 px, the
   table remains inside a horizontal scrolling region without page overflow.

The chart uses synthetic observations and does not place trades. The table
matches the chart's aggregation and rounds displayed numbers to two decimal
places; the existing CSV export retains unrounded data. The standalone preview
returns 404 for the optional local-Python health endpoint; the API-backed
browser regression was also run with the local service.

Against the local service, Playwright Firefox 157.0 and WebKit 27.2 also
matched the first hourly row in all three modes and retained the open table
and focus after resizing. Neither produced a page error. WebKit logged one
Content Security Policy inline-style refusal; Firefox logged no console errors.
This existing warning remains under investigation.

On 11 November 2026, a separate bounded check used Linux WebKit 26.5 with
Playwright 1.62.0. Both baseline `c0d7016` and the mobile target-size change
`4723259` skipped the chart table's scroll container in the Tab order. At
320 px, the 320 px table occupied a 246 px scrolling viewport; ArrowRight
could not move it because keyboard focus had moved to **Open strategy lab**.

The container now has an explicit keyboard stop and a region name taken from
its existing table caption. After opening **View chart data table**, Tab enters
that region, ArrowRight scrolls horizontally, and Shift+Tab returns to the
disclosure. The same keyboard sequence moved the table from 0 to 22 px at a
320 px viewport and from 0 to 4 px at 390 px. The region uses the existing
3 px cyan focus outline. This intentionally adds one keyboard stop after the
open disclosure on desktop as well as compact layouts; the table values and
visible copy are unchanged.

That check recorded no application console or page errors before screenshots.
One isolated screenshot call then produced one inline-style CSP refusal:
Playwright's WebKit screenshot preparation temporarily injects `body {}` to
synchronize animations. This capture-only observation does not require a CSP
change and does not establish the cause of every earlier WebKit warning.

**Still needed:** a human screen-reader walkthrough with browser and assistive
technology versions, spoken names and states, focus entry and return, and any
status or error announcements. This keyboard/accessibility-tree observation is
not a screen-reader result or a whole-app accessibility certification.
