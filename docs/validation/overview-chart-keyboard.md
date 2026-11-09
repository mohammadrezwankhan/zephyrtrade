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

**Still needed:** a human screen-reader walkthrough with browser and assistive
technology versions, spoken names and states, focus entry and return, and any
status or error announcements. This keyboard/accessibility-tree observation is
not a screen-reader result or a whole-app accessibility certification.
