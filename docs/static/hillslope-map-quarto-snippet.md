### Interactive Hillslope Map (Quarto)

```html
<link rel="stylesheet" href="static/css/interactive-hillslope-map.css" />

<div id="hillmap"></div>

<script type="module">
  import {initInteractiveHillslopeMap} from "./static/js/interactive-hillslope-map.js";

  await initInteractiveHillslopeMap({
    containerId: "hillmap",
    csvUrl: "gatecreek_threshold_analysis_results_50.csv",
    hillslopesUrl: "subcatchments.WGS.geojson",
    channelsUrl: "channels.WGS.geojson",
    initialSdyd: 200,
    initialSddc: 200,
    height: 520
  });
</script>
```
