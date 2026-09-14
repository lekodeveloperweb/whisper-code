#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYPROJECT="$PROJECT_DIR/pyproject.toml"
VERSION_FILE="$PROJECT_DIR/src/whisper_code/__init__.py"

# Parse current version from pyproject.toml
get_version() {
    sed -n 's/^version = "\(.*\)"/\1/p' "$PYPROJECT" | head -1
}

# Bump version semantically
bump_version() {
    local level="$1"
    local current
    current=$(get_version)
    local major minor patch
    major=$(echo "$current" | cut -d. -f1)
    minor=$(echo "$current" | cut -d. -f2)
    patch=$(echo "$current" | cut -d. -f3)

    case "$level" in
        major)   major=$((major + 1)); minor=0; patch=0 ;;
        minor)   minor=$((minor + 1)); patch=0 ;;
        patch)   patch=$((patch + 1)) ;;
    esac

    local new_version="${major}.${minor}.${patch}"

    # Show diff
    echo "📦 Version bump:"
    echo "  Before: $current"
    echo "  After:  $new_version"
    echo ""
    echo "  pyproject.toml: version = \"$new_version\""
    echo "  src/whisper_code/__init__.py: __version__ = \"$new_version\""
    echo ""

    # Prompt for confirmation
    read -p "Proceed? [Y/n] " -n 1 -r
    echo
    if [[ ! "$REPLY" =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi

    # Update pyproject.toml
    sed -i '' "s/^version = \".*\"/version = \"$new_version\"/" "$PYPROJECT"

    # Update src/whisper_code/__init__.py
    if [[ -f "$VERSION_FILE" ]]; then
        sed -i '' "s/^__version__ = \".*\"/__version__ = \"$new_version\"/" "$VERSION_FILE"
    else
        echo "__version__ = \"$new_version\"" > "$VERSION_FILE"
    fi

    echo "✅ Version bumped to $new_version"
}

# Build the macOS .app
build_app() {
    echo "🔨 Building Whisper-Code $(get_version) for macOS..."

    cd "$PROJECT_DIR"

    # Clean previous builds
    rm -rf build dist

    # Run PyInstaller
    echo "🚀 Running PyInstaller..."
    uv run pyinstaller --clean "$SCRIPT_DIR/whisper-code.spec"

    # Detect the built artifact - prefer .app bundle, fall back to plain executable
    local built_artifact=""
    if [[ -d "dist/Whisper-Code.app" ]]; then
        built_artifact="dist/Whisper-Code.app"
    elif [[ -f "dist/Whisper-Code" ]]; then
        built_artifact="dist/Whisper-Code"
    else
        echo "❌ Build failed: no artifact found in dist/"
        ls -la dist/
        exit 1
    fi

    local app_size
    app_size=$(du -sh "$built_artifact" | cut -f1)
    echo "✅ Build complete! $built_artifact ($app_size)"
}

# Parse arguments
VERSION_LEVEL=""
BUILD_ONLY=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --major)   VERSION_LEVEL="major"; shift ;;
        --minor)   VERSION_LEVEL="minor"; shift ;;
        --patch)   VERSION_LEVEL="patch"; shift ;;
        --build)   BUILD_ONLY=true; shift ;;
        --version) echo "$(get_version)"; exit 0 ;;
        *) echo "Usage: $0 [--major|--minor|--patch] [--build]"; exit 1 ;;
    esac
done

# Execute
if [[ -n "$VERSION_LEVEL" ]]; then
    bump_version "$VERSION_LEVEL"
    git add pyproject.toml src/whisper_code/__init__.py
    git commit -m "bump version $(get_version)"
    git tag -a "v$(get_version)" -m "Release v$(get_version)"
fi

if [[ "$BUILD_ONLY" == true ]] || [[ -z "$VERSION_LEVEL" ]]; then
    build_app
fi
