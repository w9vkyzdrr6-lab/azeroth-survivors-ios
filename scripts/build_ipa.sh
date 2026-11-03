#!/bin/bash
# Build an unsigned iOS .ipa. Runs on a macOS runner (Codemagic / Bitrise / Actions).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/ios/App"

echo "== toolchain =="
xcodebuild -version
xcrun --sdk iphoneos --show-sdk-version

echo "== xcodebuild =="
xcodebuild \
  -project App.xcodeproj \
  -scheme App \
  -configuration Release \
  -sdk iphoneos \
  -destination "generic/platform=iOS" \
  -derivedDataPath build \
  CODE_SIGNING_ALLOWED=NO \
  CODE_SIGNING_REQUIRED=NO \
  CODE_SIGN_IDENTITY="" \
  CODE_SIGN_ENTITLEMENTS="" \
  ENABLE_BITCODE=NO \
  build

# 记为绝对路径：后面会 cd 到仓库根目录，相对路径会失效
APP_PATH="$PWD/$(find build/Build/Products/Release-iphoneos -maxdepth 1 -name '*.app' | head -1)"
if [ -z "$APP_PATH" ]; then
  echo "ERROR: no .app produced"
  exit 1
fi
echo "built: $APP_PATH"
du -sh "$APP_PATH"

echo "== package payload =="
cd "$ROOT"
rm -rf Payload
mkdir -p Payload
cp -R "$APP_PATH" Payload/
rm -rf "Payload/$(basename "$APP_PATH")/_CodeSignature"

# zip is available on macOS runners; -X keeps Finder metadata out of the bundle
zip -qrX AzerothSurvivors-unsigned.ipa Payload
rm -rf Payload

ls -lh AzerothSurvivors-unsigned.ipa
echo "IPA_READY"
