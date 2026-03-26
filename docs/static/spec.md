# deck.gl Spec for PATH Interactive Viz

This spec covers replacing the two matplotlib-based interactive plots in `PATH-figs/Interactive_viz.py` with web-friendly deck.gl components for embedding in a Quarto report.

## Scope
- Tool 1: Interactive hillslope map with treatment categories and channel overlay.
- Tool 2: 3D cost surface with selection indicator tied to the same thresholds.

Both tools share the same data source for thresholds and selections, and the same UI controls for threshold selection.

## Data Sources
- Primary CSV: `gatecreek_threshold_analysis_results_50[19].csv`
  - Required columns:
    - `sddc_threshold` (number)
    - `sdyd_threshold` (number)
    - `total_cost` (number)
    - `selected_hillslopes` (list of `WeppID` values)
    - `treatment_hillslopes` (list of 3 lists of `WeppID` values)
    - `final_Sddc` (number)
    - `untreatable_sdyd` (optional; list of `WeppID` values if available)
  - Columns to ignore for rendering: `sdyd_df`, `hillslopes_sdyd` (pandas string dumps).
- Hillslope geometry: GeoJSON/TopoJSON with polygon features containing `WeppID`.
- Channel geometry: optional GeoJSON with lines/paths.

## Shared UI Controls
- `sdyd_threshold` selector: discrete slider or dropdown driven by unique values in CSV.
- `sddc_threshold` selector: discrete slider or dropdown driven by unique values in CSV.
- Default values: `initial_sdyd=200`, `initial_sddc=200` if present; otherwise first available values.

## Parsing & Normalization
- Parse list-like strings from CSV:
  - `selected_hillslopes`: parse to `number[]`.
  - `treatment_hillslopes`: parse to `number[][]` (up to 3 tiers).
  - `untreatable_sdyd`: list of `[wepp_id, final_Sdyd]` pairs; use `wepp_id` values for the untreatable set.
- Treat missing or invalid parses as empty arrays.
- Build a lookup keyed by `(sdyd_threshold, sddc_threshold)` for fast access to selections and cost.

## Tool 1: Interactive Hillslope Map

### Purpose
Show treatment selections by category, untreated areas, and optional channels for the currently selected thresholds.

### Inputs
- `hillslopesGeojson` (features with `WeppID`)
- `channelsGeojson` (optional)
- `selection` object from CSV (selected/treatment/untreatable lists)

### Output
- 2D map with categorized polygon styling and legend.
- Tooltip for a hovered hillslope (optional): `WeppID`, category, thresholds.

### Rendering (deck.gl)
- `GeoJsonLayer` for hillslopes:
  - Base fill for untreated: light grey.
  - Category fill by membership:
    - Tier 1: `#b2df8a` (0.5 tons/acre)
    - Tier 2: `#33a02c` (1 tons/acre)
    - Tier 3: `#006400` (2 tons/acre)
  - Untreatable outline: red stroke, thicker, no fill.
  - Untreated are all hillslopes not in `selected_hillslopes`.
- `GeoJsonLayer` or `PathLayer` for channels:
  - Stroke color `#50a5d6`.
  - Narrow stroke width.
- Legend items:
  - Untreated
  - 0.5 / 1 / 2 tons/acre
  - Sdyd threshold not met (red outline)
  - Current `total_cost`
  - Current `final_Sddc`

### Interactions
- On threshold change: recompute category membership, update map colors/legend values.
- Optional hover: show `WeppID` and category (untreated, tier 1/2/3, untreatable).

### Notes
- Prefer a fixed view (no basemap required) unless a basemap is already part of the report style.
- Use `COORDINATE_SYSTEM.LNGLAT` for GeoJSON with lon/lat.

### Implementation Plan (Detailed)
1. Inventory inputs and outputs.
   - Confirm paths for hillslope and channel GeoJSON files.
   - Confirm the CSV lives alongside the Quarto report (or is embedded/served).
2. Add data loader and normalizer.
   - Load CSV and parse list-like fields into arrays once at startup.
   - Build `selectionByThreshold` lookup keyed by `${sdyd}_${sddc}`.
   - Build `sdydValues` and `sddcValues` arrays for UI controls.
3. Prepare geometry and join keys.
   - Load hillslope GeoJSON and ensure each feature has `WeppID` as a number.
   - Load channels GeoJSON (optional).
   - Precompute a `weppIdToFeatureIndex` map for quick membership lookups.
4. Implement category resolution.
   - For current thresholds, compute sets:
     - `treatmentTier1`, `treatmentTier2`, `treatmentTier3`
     - `selected`, `untreatable`
   - Derive `untreated` by negating `selected`.
   - Expose a function `getCategory(weppId)` returning:
     - `tier1`, `tier2`, `tier3`, `untreatable`, or `untreated`.
5. Build deck.gl layers.
   - `GeoJsonLayer` for hillslopes with `getFillColor` based on `getCategory`.
   - `GeoJsonLayer` for untreatable outline using `getLineColor` and `getLineWidth`.
   - `GeoJsonLayer` or `PathLayer` for channels.
6. Legend and status readout.
   - Build a legend UI element (HTML), and use `gl-dashboard` legend patterns if available:
     - Untreated, Tier 1/2/3, Sdyd threshold not met.
     - Append current `total_cost` and `final_Sddc` values.
7. UI controls and state wiring.
   - Add `sdyd_threshold` and `sddc_threshold` sliders/dropdowns.
   - On change, update selection state and re-render layers + legend.
8. Embedding in Quarto.
   - Provide a single JS entry (e.g., `interactive-hillslope-map.js`) that mounts into a target div.
   - Include a minimal CSS file for legend and layout.
9. Performance and stability.
   - Avoid rebuilding layers on every tick; update layer props with memoized data.
   - Cache parsed results and feature category sets.
10. QA checklist.
   - Verify categories for a known threshold pair against the old matplotlib output.
   - Confirm legend values match `total_cost` and `final_Sddc` for selection.

## Tool 2: 3D Cost Surface

### Purpose
Visualize the cost landscape over `(sdyd_threshold, sddc_threshold)` with a marker for the current selection.

### Inputs
- All rows from CSV (for full surface grid).

### Output
- 3D surface with color-mapped cost values.
- Marker and guide line at current `(sdyd, sddc, total_cost)` point.

### Rendering (Plotly.js)
- Use Plotly.js WebGL-based 3D surface chart.
- Surface trace:
  - `type: 'surface'`
  - `x`: `sdyd_threshold` values (1D array)
  - `y`: `sddc_threshold` values (1D array)
  - `z`: `total_cost` as 2D grid `[sddc_values.length][sdyd_values.length]`
  - `colorscale`: Viridis
  - `hovertemplate`: show sdyd, sddc, and total_cost
- Selection marker:
  - `type: 'scatter3d'` with `mode: 'markers+lines'`
  - Red marker at current `(sdyd, sddc, total_cost)`
  - Vertical line from `(sdyd, sddc, 0)` to `(sdyd, sddc, total_cost)`

### Interactions
- Built-in orbit/zoom/pan controls via Plotly.
- Hover tooltip showing `(sdyd, sddc, total_cost)`.
- Threshold changes update the selection marker trace only; surface is static.

### Notes
- Load Plotly.js via CDN (`plotly.js-dist-min` or `plotly-basic` for smaller bundle).
- Use `Plotly.react()` for efficient partial updates (marker only).
- Precompute the z-grid once at load time.

### Implementation Plan (Detailed)
1. Data prep and normalization.
   - Load `gatecreek_threshold_analysis_results_50.csv` via fetch + d3-dsv.
   - Parse `sdyd_threshold`, `sddc_threshold`, and `total_cost` as numbers.
   - Build sorted unique arrays: `sdydValues`, `sddcValues`.
   - Create a lookup map keyed by `${sdyd}_${sddc}` for fast cost retrieval.
   - Build 2D z-grid: `zGrid[sddcIdx][sdydIdx] = total_cost`.
2. Plotly surface trace.
   - Create trace with `type: 'surface'`, `x: sdydValues`, `y: sddcValues`, `z: zGrid`.
   - Set `colorscale: 'Viridis'`, `showscale: true`.
   - Configure `hovertemplate` for clean tooltip display.
3. Selection marker trace.
   - Create `scatter3d` trace for the current selection point.
   - Include vertical guide line using two points: `(sdyd, sddc, 0)` and `(sdyd, sddc, cost)`.
   - Style: red color, larger marker size.
4. Layout configuration.
   - Set axis titles: `xaxis: {title: 'Sdyd Threshold'}`, etc.
   - Configure camera position for good initial view.
   - Set `margin` and `height` for consistent sizing.
5. UI controls and coupling.
   - Reuse the slider pattern from the hillslope map.
   - On threshold change, update marker trace via `Plotly.react()` (efficient partial update).
6. Legend/status.
   - Display current `total_cost` and `(sdyd, sddc)` below the plot.
   - Plotly provides built-in colorscale legend.
7. Embedding.
   - Create `static/js/interactive-cost-surface.js` as ES module.
   - Add `cost-surface-demo.html` and Quarto snippet.
   - Load Plotly via `<script src="https://cdn.plot.ly/plotly-2.27.0.min.js">`.
8. Performance.
   - Parse CSV and build z-grid once at initialization.
   - Use `Plotly.react()` instead of `Plotly.newPlot()` for updates.
   - Only update trace 1 (marker) on slider change; trace 0 (surface) stays static.
9. QA checklist.
   - Verify z-grid dimensions: `sddcValues.length × sdydValues.length`.
   - Confirm marker position matches `total_cost` for known threshold pairs.
   - Test orbit/zoom controls work smoothly.

## Data Flow Summary
1. Load CSV.
2. Parse and normalize selection lists.
3. Extract unique `sdyd_threshold` and `sddc_threshold` values.
4. Build:
   - `selectionByThreshold` map for the current selection.
   - `surfaceGrid` for cost visualization.
5. Render:
   - Map layer(s) from geometry + selection.
   - 3D surface layer + selection marker.

## Performance Considerations
- Parse CSV once, cache results in memory.
- Avoid recomputing surface grid on slider change.
- For map updates, recompute category membership using set lookups for `WeppID` lists.

## Open Items / Required Inputs
- Provide the hillslope and channel geometries (GeoJSON with `WeppID`).
- Clarify whether `untreatable_sdyd` should be derived or precomputed as a parseable list in the CSV.
