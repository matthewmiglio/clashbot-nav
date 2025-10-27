# clashbot-nav

A bot for navigating and interacting with Clash-based mobile games via image recognition.

## Structure

- `clashbot/` - Core bot logic (image recognition, Google Play integration, recording)
- `tools/` - Training tools for labeling images and extracting pixel features
- `data/` - Training data, image classes, and pixel recognition models

## Usage

Run training tools from `tools/` to label images and build recognition models. Core bot functionality lives in `clashbot/`.
