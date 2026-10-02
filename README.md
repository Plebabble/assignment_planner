# Assignment Planner

A local Python + Streamlit assignment planner that imports an exported Google Calendar `.ics` file.

## Requirements
- Python 3.10 or newer
- Google Calendar exported as an `.ics` file (no Google Cloud setup required)

## Run on Windows
1. Extract this ZIP into a folder.
2. Open Command Prompt or PowerShell in that folder.
3. Install dependencies:

   ```bash
   py -m pip install -r requirements.txt
   ```

4. Start the app:

   ```bash
   py -m streamlit run app.py
   ```

5. A browser tab should open with the planner.

## Export your Google Calendar
1. Open Google Calendar on the web.
2. Select Settings (gear) → Settings.
3. Select **Import & export**.
4. Under Export, click **Export**. Google downloads a ZIP.
5. Extract the ZIP and upload the relevant `.ics` calendar file in the app's sidebar.

You can export one calendar or multiple calendars. Uploading a new `.ics` replaces the previous imported calendar data.

## Data and privacy
- `assignments.json` and `calendar.ics` are stored locally in the same folder where you run the app.
- The app does not send your calendar or assignment data to a server.
- Back up `assignments.json` periodically or use the in-app JSON backup.
- The app reads calendar events; it does not edit your Google Calendar.

## Scheduling behavior
- Gaps between calendar events of 30 minutes or less are treated as unavailable.
- Free time is calculated within the configured waking hours (default 7 AM–11 PM).
- Default fallback availability without an imported calendar is 4 hours on weekdays and 16 hours on weekends.
- Default planned-work limits are 4 hours on weekdays and 5 hours on weekends.
- Logarithmic weighting with an 8-hour effective availability cap reduces the tendency to push all work onto weekends.
- Assignments are allocated in deadline order. If the remaining workload cannot fit before a deadline within the configured limits, the app warns you.

## Important notes
- The first version estimates units using a single average minutes-per-unit value for each assignment.
- A target such as 2.4 questions is an estimated time-equivalent target; use the actual number of questions you complete in the progress input.
- If an assignment is due today and work remains, it is scheduled today if capacity is available. No division by zero is used.
- This is an initial working version; test its schedule against your real week and adjust the daily limits and per-unit estimates.
\n\nQUICK LAUNCH AND BULK IMPORT\n- Double-click 'Launch Assignment Planner.bat' to start the app.\n- Create a shortcut to that BAT file and pin the shortcut to the Windows taskbar.\n- Use 'Import assignments in bulk (JSON)' inside the app to import a JSON list.\n- The included assignments_from_sheet.json contains the three assignments from the supplied sheet image.\n\nCOURSE COLORS\n- Math 131: dark blue\n- Phys 151: light blue\n- CompLit 335: orange\n- FYS 191: purple\n- Engin 112: dark green\n- Other: dark grey\n- For bulk JSON, optionally include a 'course' field with one of those exact names.\n- If omitted, the app tries to infer the course from the assignment name; you can always edit it later.\n