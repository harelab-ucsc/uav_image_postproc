#!/usr/bin/env bash

# ========================================================================
# Script Name:   postproc.sh
# Description:   Turns a raw 4-camera Birdseye payload capture into a
#                COLMAP-ready project root.
#                Intended to hand off PROJECT_ROOT to
#                payload_camera_ws/scripts/hloc_reconstruct_and_densify.sh
# ========================================================================

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"

usage() {
    echo "Usage:" >&2
    echo "  $0 /path/to/raw/images /path/to/camchain.yaml /path/to/project/root" >&2
    echo "  $0 --finalize-masks /path/to/project/root" >&2
}

if [[ "${1:-}" == "--finalize-masks" ]]; then
    if [[ $# -ne 2 ]]; then
        usage
        exit 2
    fi
    PROJECT_ROOT="$2"

    [[ -d "$PROJECT_ROOT" ]] || {
        echo "Error: project root does not exist: $PROJECT_ROOT" >&2
        exit 1
    }

    "$PYTHON" "$SCRIPT_DIR/gen_leg_masks.py" \
        --colmap-root "$PROJECT_ROOT" \
        --link-frame-masks

    echo
    echo "Done. $PROJECT_ROOT is ready for hloc_reconstruct_and_densify.sh."
    exit 0
fi

if [[ $# -ne 3 ]]; then
    usage
    exit 2
fi

RAW_DIR="$1"
CAMCHAIN="$2"
PROJECT_ROOT="$3"

[[ -d "$RAW_DIR" ]] || {
    echo "Error: raw image directory does not exist: $RAW_DIR" >&2
    exit 1
}

[[ -f "$CAMCHAIN" ]] || {
    echo "Error: camchain YAML file does not exist: $CAMCHAIN" >&2
    exit 1
}

[[ -e "$PROJECT_ROOT/images" ]] && {
    echo "Error: $PROJECT_ROOT/images already exists; refusing to overwrite." >&2
    echo "Remove it or choose a different project root, then re-run." >&2
    exit 1
}

# 1.) rotate, regroup into camera1..4, rename to imageNNNN.jpeg
"$PYTHON" "$SCRIPT_DIR/prepare_colmap_rig.py" \
    --src-dir "$RAW_DIR" \
    --out-dir "$PROJECT_ROOT/images"

# 2.) overwrite the template rig_config.json with the calibrated one
"$PYTHON" "$SCRIPT_DIR/gen_rig_config.py" \
    --src "$CAMCHAIN" \
    --dest "$PROJECT_ROOT/rig_config.json"

# 3.) detect drone-leg occlusion and write canonical masks + overlays
"$PYTHON" "$SCRIPT_DIR/gen_leg_masks.py" \
    --colmap-root "$PROJECT_ROOT" \
    --overlay-dir "$PROJECT_ROOT/masks_overlays"

echo
echo "Canonical masks + overlays written. Review before continuing:"
echo "  $PROJECT_ROOT/masks_overlays/camera2_overlay.png"
echo "  $PROJECT_ROOT/masks_overlays/camera4_overlay.png"
echo
echo "If the masks look correct, finalize with:"
echo "  $0 --finalize-masks $PROJECT_ROOT"
