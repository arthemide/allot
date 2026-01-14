#!/usr/bin/env bash
# launchd service uninstallation script

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

PLIST_FILE="$HOME/Library/LaunchAgents/com.user.dca-bot.plist"

log_info "Uninstalling launchd service..."

# Check if service is loaded
if launchctl list | grep -q "com.user.dca-bot"; then
    log_info "Stopping service..."
    launchctl unload "$PLIST_FILE" 2>/dev/null || true
    log_success "Service stopped"
fi

# Remove plist file
if [ -f "$PLIST_FILE" ]; then
    log_info "Removing plist file..."
    rm "$PLIST_FILE"
    log_success "Plist file removed"
else
    log_info "No plist file found"
fi

log_success "Service uninstalled successfully!"
