#!/bin/sh
set -e

# Install script for Kubernetes Manager (km)
# Usage:
#   curl -fsSL https://github.com/<OWNER>/<REPO>/raw/main/kubernetesmanager/install.sh | sh

REPO_RAW_BASE="https://raw.githubusercontent.com/<OWNER>/<REPO>/main/kubernetesmanager"
KM_URL="$REPO_RAW_BASE/km"
INSTALL_PATH="/usr/local/bin/km"
LOCAL_BIN="$HOME/.local/bin"
TMP_KM="$(mktemp /tmp/km.XXXXXX)"

echo "🚀 Kubernetes Manager Installer"

echo "Downloading km from: $KM_URL"
if ! curl -fsSL "$KM_URL" -o "$TMP_KM"; then
  echo "Error: Failed to download km from $KM_URL"
  exit 1
fi

chmod +x "$TMP_KM"

if [ -w "$(dirname "$INSTALL_PATH")" ]; then
  mv "$TMP_KM" "$INSTALL_PATH"
  echo "Installed km to $INSTALL_PATH"
else
  echo "Installing km to $LOCAL_BIN because /usr/local/bin is not writable"
  mkdir -p "$LOCAL_BIN"
  mv "$TMP_KM" "$LOCAL_BIN/km"
  echo "Installed km to $LOCAL_BIN/km"
  if ! echo "$PATH" | grep -q "$LOCAL_BIN"; then
    SHELL_RC="$HOME/.bashrc"
    if [ -n "$ZSH_VERSION" ]; then
      SHELL_RC="$HOME/.zshrc"
    fi
    printf '\n# Kubernetes Manager\nexport PATH="$LOCAL_BIN:$PATH"\n' >> "$SHELL_RC"
    echo "Added $LOCAL_BIN to PATH in $SHELL_RC"
  fi
fi

echo ""
echo "✅ Installation complete. Run 'km' to start the shell."
echo "If the command is not found, open a new terminal or run: source ~/.bashrc"
