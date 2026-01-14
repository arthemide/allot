#!/usr/bin/env bash
# macOS launchd service installation script
# This script configures the DCA bot to start automatically with macOS

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PLIST_TEMPLATE="$PROJECT_ROOT/bot/dca/com.user.dca-bot.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_DEST="$LAUNCH_AGENTS_DIR/com.user.dca-bot.plist"

log_info "Installing launchd service for DCA bot..."

# Check that template exists
if [ ! -f "$PLIST_TEMPLATE" ]; then
    log_error "Template file not found: $PLIST_TEMPLATE"
    exit 1
fi

# Create LaunchAgents directory if it doesn't exist
if [ ! -d "$LAUNCH_AGENTS_DIR" ]; then
    log_info "Creating directory $LAUNCH_AGENTS_DIR"
    mkdir -p "$LAUNCH_AGENTS_DIR"
fi

# Replace paths in template
log_info "Configuring paths..."
USERNAME=$(whoami)
TEMP_PLIST="/tmp/com.user.dca-bot.plist"

# Detect uv path (homebrew on Apple Silicon or Intel, or standalone install)
if [ -f "/opt/homebrew/bin/uv" ]; then
    UV_PATH="/opt/homebrew/bin/uv"
elif [ -f "/usr/local/bin/uv" ]; then
    UV_PATH="/usr/local/bin/uv"
elif [ -f "$HOME/.local/bin/uv" ]; then
    UV_PATH="$HOME/.local/bin/uv"
else
    log_error "uv is not installed. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

log_info "Using uv: $UV_PATH"

# Use sed to replace paths
sed -e "s|/Users/VOTRE_USERNAME|$HOME|g" \
    -e "s|/opt/homebrew/bin/uv|$UV_PATH|g" \
    "$PLIST_TEMPLATE" > "$TEMP_PLIST"

# Copy to LaunchAgents
log_info "Installing plist file..."
cp "$TEMP_PLIST" "$PLIST_DEST"
rm "$TEMP_PLIST"

# Check that .env file exists
if [ ! -f "$PROJECT_ROOT/bot/dca/.env" ]; then
    log_warning "The .env file does not exist yet"
    log_info "Copying .env.template..."
    if [ -f "$PROJECT_ROOT/bot/dca/.env.template" ]; then
        cp "$PROJECT_ROOT/bot/dca/.env.template" "$PROJECT_ROOT/bot/dca/.env"
        log_warning "⚠️  IMPORTANT: Configure the .env file before loading the service!"
        log_info "Edit: $PROJECT_ROOT/bot/dca/.env"
    fi
fi

# Unload the service if already loaded
if launchctl list | grep -q "com.user.dca-bot"; then
    log_info "Unloading old service..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

# Load the service
log_info "Loading launchd service..."
launchctl load "$PLIST_DEST"

log_success "Service installed successfully!"
echo ""
log_info "Useful commands:"
echo "  • Check status:   launchctl list | grep dca-bot"
echo "  • Stop service:   launchctl unload $PLIST_DEST"
echo "  • Start service:  launchctl load $PLIST_DEST"
echo "  • View logs:      tail -f $PROJECT_ROOT/bot/dca/logs/launchd-dca-bot.log"
echo "  • View errors:    tail -f $PROJECT_ROOT/bot/dca/logs/launchd-dca-bot.log"
echo ""
log_warning "The bot will start automatically at each login!"
log_info "Make sure you have configured the .env file with your Binance API keys."
