#!/usr/bin/env bash
# render.sh <input.svg> <width> <height>  -> writes <input>.png at 2x device scale
set -e
SVG="$1"; W="$2"; H="$3"; BASE="${SVG%.svg}"
CHROME=$(ls /opt/pw-browsers/chromium-*/chrome-linux/chrome | head -1)
{ echo '<!doctype html><html><head><meta charset="utf-8">'
  echo '<style>html,body{margin:0;padding:0;background:#0d1117;overflow:hidden}svg{display:block}</style></head><body>'
  cat "$SVG"; echo '</body></html>'; } > "${BASE}.html"
"$CHROME" --headless --no-sandbox --disable-gpu --hide-scrollbars \
  --force-device-scale-factor=2 --screenshot="${BASE}.png" \
  --window-size="${W},${H}" "${BASE}.html" 2>/dev/null
rm -f "${BASE}.html"
echo "wrote ${BASE}.png"
