# clashbot-nav

A bot for navigating and interacting with Clash-based mobile games via image recognition.

## Tools

### Training Pipeline
1. **annotator.py** - Label screenshots with page types (main, shop, deck, etc.)
2. **pixel_extractor.py** - Click pixels on each page type to create recognition fingerprints
3. **audit.py** - Test pixel recognition accuracy across all labeled images
4. **pixel_debugger.py** - Fix failed pixel matches by removing unreliable pixels

### Navigation Mapping
- **navigation_mapper.py** - Interactive GUI to map page navigation. Select a page, click coordinates on the screenshot where buttons are, specify destination page. Auto-saves to `navigation_graph.json`

### Data Collection
- **recorder.py** - Capture screenshots from emulator at 1 second intervals

## Helper Modules
- `clashbot/google_play.py` - Google Play emulator controller
- `clashbot/image_rec.py` - Image recognition using pixel matching
- `clashbot/image_handler.py` - Image processing utilities
- `clashbot/base.py` - Base bot classes
