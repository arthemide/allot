#!/bin/bash
# Simple status line showing git branch

CLAUDE_INPUT=$(cat 2>/dev/null || echo "{}")

GIT_BRANCH=""
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")
fi

MODEL_NAME=""
if [ "$CLAUDE_INPUT" != "{}" ]; then
  MODEL_NAME=$(echo "$CLAUDE_INPUT" | jq -r '.model.display_name // ""' 2>/dev/null)
fi

OUTPUT="▊ Claude Code"
if [ -n "$GIT_BRANCH" ]; then
  OUTPUT="${OUTPUT}  ⎇ ${GIT_BRANCH}"
fi
if [ -n "$MODEL_NAME" ]; then
  OUTPUT="${OUTPUT}  │  ${MODEL_NAME}"
fi

echo "$OUTPUT"
