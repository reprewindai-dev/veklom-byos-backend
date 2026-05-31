#!/bin/bash
# Record 15-second demo GIF for Veklom marketplace listing
# Requirements: ffmpeg, gifsicle, terminal recorder (asciinema or similar)

set -e

echo "Veklom Demo Recording Script"
echo "=============================="
echo ""

# Configuration
OUTPUT_DIR="./docs/marketplace"
OUTPUT_FILE="$OUTPUT_DIR/demo.gif"
TEMP_DIR="/tmp/veklom-demo"
RESOLUTION="1280x720"

# Create output directory
mkdir -p "$OUTPUT_DIR"
mkdir -p "$TEMP_DIR"

echo "Step 1: Prepare terminal environment"
echo "--------------------------------------"
# Set terminal to 1280x720
# Clear screen
# Set font size for readability

echo "Step 2: Record demo sequence"
echo "------------------------------"
echo "Timeline:"
echo "  0-3s:   veklom up bringing services online"
echo "  4-7s:   Paste veklom.yaml, hit Validate → Apply"
echo "  8-12s:  Run ops-assistant asking question"
echo "  12-14s: Policy banner pops (blocked PII export)"
echo "  14-15s: Open Audit tab showing enforcement"
echo ""

# Record using asciinema (or alternative)
# asciinema rec -t 15 "$TEMP_DIR/demo.cast"

# Or use terminal recorder with window capture
# Example with ffmpeg + terminal:
# ffmpeg -f x11grab -s $RESOLUTION -r 30 -i :0.0 -c:v libx264 -preset ultrafast "$TEMP_DIR/demo.mp4"

echo "Step 3: Convert to GIF"
echo "----------------------"
# ffmpeg -i "$TEMP_DIR/demo.mp4" -vf "fps=10,scale=$RESOLUTION:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" "$TEMP_DIR/demo.gif"
# gifsicle --optimize=3 --colors 256 "$TEMP_DIR/demo.gif" -o "$OUTPUT_FILE"

echo "Step 4: Add captions (optional)"
echo "-------------------------------"
# Use ffmpeg to burn in captions at key timestamps
# Captions: "Install → Connect → Govern → Prove"

echo "Step 5: Verify output"
echo "---------------------"
# ls -lh "$OUTPUT_FILE"

echo ""
echo "Demo recording complete!"
echo "Output: $OUTPUT_FILE"
echo ""
echo "Tips for best results:"
echo "- Record at 1280x720 resolution"
echo "- Keep cursor visible"
echo "- Use consistent timing"
echo "- Test GIF playback before publishing"
