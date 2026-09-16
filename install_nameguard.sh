#!/usr/bin/env bash
#
# Installs the NetBox NameGuard plugin into an existing NetBox dev instance:
#   1. pip installs the plugin (editable mode)
#   2. adds "netbox_nameguard" to PLUGINS in configuration.py (if not already there)
#   3. runs its database migrations
#   4. restarts NetBox (systemd if it's running that way, otherwise tells you
#      how to restart manage.py runserver yourself)
#
# Usage:
#   bash install_nameguard.sh
#
# You can skip the prompts by exporting these first:
#   export NETBOX_REPO_DIR=~/netbox
#   export PLUGIN_DIR=~/netbox-nameguard
#   export VENV_DIR=~/netbox/venv
#   bash install_nameguard.sh

set -euo pipefail

bold() { printf '\033[1m%s\033[0m\n' "$1"; }
info() { printf '  %s\n' "$1"; }
err()  { printf '\033[31m%s\033[0m\n' "$1" >&2; }

# ---------------------------------------------------------------------------
# 1. Gather paths
# ---------------------------------------------------------------------------
bold "== NetBox NameGuard installer =="

if [ -z "${NETBOX_REPO_DIR:-}" ]; then
  read -rp "Path to your NetBox repo root (the folder containing 'netbox/manage.py'), e.g. ~/netbox: " NETBOX_REPO_DIR
fi
NETBOX_REPO_DIR="${NETBOX_REPO_DIR/#\~/$HOME}"

if [ -z "${PLUGIN_DIR:-}" ]; then
  DEFAULT_PLUGIN_DIR="$HOME/netbox-nameguard"
  read -rp "Path to the netbox-nameguard project [$DEFAULT_PLUGIN_DIR]: " PLUGIN_DIR
  PLUGIN_DIR="${PLUGIN_DIR:-$DEFAULT_PLUGIN_DIR}"
fi
PLUGIN_DIR="${PLUGIN_DIR/#\~/$HOME}"

MANAGE_PY="$NETBOX_REPO_DIR/netbox/manage.py"
CONFIG_PY="$NETBOX_REPO_DIR/netbox/netbox/configuration.py"

if [ ! -f "$MANAGE_PY" ]; then
  err "Can't find manage.py at $MANAGE_PY"
  err "Double-check NETBOX_REPO_DIR points at the folder that contains 'netbox/manage.py'."
  exit 1
fi
if [ ! -f "$CONFIG_PY" ]; then
  err "Can't find configuration.py at $CONFIG_PY"
  err "If you only have configuration.example.py, copy it first:"
  err "  cp $NETBOX_REPO_DIR/netbox/netbox/configuration.example.py $CONFIG_PY"
  exit 1
fi
if [ ! -d "$PLUGIN_DIR" ]; then
  err "Can't find the plugin project at $PLUGIN_DIR"
  exit 1
fi

if [ -z "${VENV_DIR:-}" ]; then
  DEFAULT_VENV_DIR="$NETBOX_REPO_DIR/venv"
  read -rp "Path to NetBox's virtualenv [$DEFAULT_VENV_DIR]: " VENV_DIR
  VENV_DIR="${VENV_DIR:-$DEFAULT_VENV_DIR}"
fi
VENV_DIR="${VENV_DIR/#\~/$HOME}"

if [ ! -f "$VENV_DIR/bin/activate" ]; then
  err "Can't find a virtualenv at $VENV_DIR (no bin/activate)."
  err "If NetBox doesn't use a venv, re-run with VENV_DIR set to your Python env, or adapt this script."
  exit 1
fi

echo
info "NetBox repo:  $NETBOX_REPO_DIR"
info "Plugin dir:   $PLUGIN_DIR"
info "Virtualenv:   $VENV_DIR"
info "config file:  $CONFIG_PY"
echo

# ---------------------------------------------------------------------------
# 2. Install the plugin into NetBox's venv
# ---------------------------------------------------------------------------
bold "== Step 1: pip install -e (editable mode) =="
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
pip install -e "$PLUGIN_DIR"
echo

# ---------------------------------------------------------------------------
# 3. Register it in PLUGINS
# ---------------------------------------------------------------------------
bold "== Step 2: registering netbox_nameguard in PLUGINS =="

cp "$CONFIG_PY" "$CONFIG_PY.bak.$(date +%Y%m%d%H%M%S)"
info "Backed up configuration.py before editing."

python3 - "$CONFIG_PY" <<'PYEOF'
import re
import sys

path = sys.argv[1]
with open(path, "r") as f:
    text = f.read()

if "netbox_nameguard" in text:
    print("  'netbox_nameguard' already present in configuration.py, skipping edit.")
else:
    pattern = re.compile(r"(PLUGINS\s*=\s*\[)")
    if pattern.search(text):
        text = pattern.sub(r'\1\n    "netbox_nameguard",', text, count=1)
        print("  Added \"netbox_nameguard\" to the existing PLUGINS list.")
    else:
        text = text.rstrip() + '\n\nPLUGINS = [\n    "netbox_nameguard",\n]\n'
        print("  No PLUGINS list found; appended a new one with netbox_nameguard.")
    with open(path, "w") as f:
        f.write(text)
PYEOF
echo

# ---------------------------------------------------------------------------
# 4. Run migrations
# ---------------------------------------------------------------------------
bold "== Step 3: running migrations =="
python "$MANAGE_PY" migrate netbox_nameguard
echo

# ---------------------------------------------------------------------------
# 5. Restart NetBox
# ---------------------------------------------------------------------------
bold "== Step 4: restart NetBox =="

if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet netbox 2>/dev/null; then
  info "Detected NetBox running as a systemd service. Restarting..."
  sudo systemctl restart netbox netbox-rq
  info "Restarted. Check status with: sudo systemctl status netbox"
else
  info "NetBox doesn't appear to be running as a systemd service on this machine."
  info "If it's running via 'manage.py runserver' in another terminal:"
  info "  1. Go to that terminal and press Ctrl+C to stop it"
  info "  2. Run: source $VENV_DIR/bin/activate && python $MANAGE_PY runserver 0.0.0.0:8000"
fi

echo
bold "Done. Log into NetBox and look for 'NameGuard' in the left-hand nav."
