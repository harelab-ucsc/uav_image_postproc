#!/usr/bin/env python3
"""Generate COLMAP rig_config.json from birdseye_v2_camchain.yaml

The camchain's "T_cam_ins" matrices are interpreted as the CAMERA POSE IN
THE INS FRAME (T_ins<-cam). Evidence: under this reading the four rgb
cameras form a symmetric cross (+-6.3 cm arms, equal height), each tilted
45 deg off vertical facing four quadrants 90 deg apart -- matching the
actual imagery, which shows four distinct oblique views. Under the
opposite reading (T_cam<-ins) all four cameras would share one optical
axis and center, which the imagery rules out.

COLMAP wants cam_from_rig, with the rig frame defined by the reference
sensor (camera1 = rgb_1). With P_k = T_ins<-camK from the YAML:

    T_camK_rig = inv(P_k) @ P_1

IMPORTANT: the dataset images were rotated 180 deg (upside-down camera
fix), which changes the effective camera frames and intrinsics relative
to the calibration:
  - each camera frame gains a rotation of pi about its optical axis:
    F = Rz(pi) = diag(-1, -1, 1), so T_camK'_ins = F @ T_camK_ins and
    T_camK'_rig' = F @ T_camK_rig @ F   (F is its own inverse)
  - principal point reflects: cx' = W - cx, cy' = H - cy
  - tangential distortion flips sign: p1' = -p1, p2' = -p2
  - fx, fy, k1, k2 are unchanged
"""

import json
from pathlib import Path

import numpy as np
import yaml
from scipy.spatial.transform import Rotation

CAMCHAIN = Path("/home/dkhuttan/dataset/wrp_roof/birdseye_v2_camchain.yaml")
OUT = Path("/home/dkhuttan/dataset/wrp_roof/before_solar_panels/wrp_roof_10Jul2026_rgbs_colmap/rig_config.json")
CAM_NAMES = ["rgb_1", "rgb_2", "rgb_3", "rgb_4"]

F = np.diag([-1.0, -1.0, 1.0, 1.0])  # 180 deg image rotation = Rz(pi) on the camera frame


def nearest_rotation(R):
    """Project onto SO(3); the YAML uses truncated 0.7071068 entries"""
    u, _, vt = np.linalg.svd(R)
    return u @ np.diag([1.0, 1.0, np.linalg.det(u @ vt)]) @ vt


def main():
    chain = yaml.safe_load(CAMCHAIN.read_text())["cameras"]

    T_cam_ins = {}
    for name in CAM_NAMES:
        P = np.array(chain[name]["T_cam_ins"], dtype=float)  # T_ins<-cam (camera pose in INS)
        P[:3, :3] = nearest_rotation(P[:3, :3])
        T_cam_ins[name] = F @ np.linalg.inv(P)  # cam<-ins, in the flipped-image frame

    T_rig_ins = T_cam_ins["rgb_1"]  # rig frame := camera1 (ref sensor)

    cameras = []
    for idx, name in enumerate(CAM_NAMES, start=1):
        cam = chain[name]
        intr, dist, res = cam["intrinsics"], cam["distortion"], cam["resolution"]
        assert dist["model"] == "plumb_bob" and dist["k3"] == 0.0, name
        entry = {
            "image_prefix": f"camera{idx}/",
            "camera_model_name": "OPENCV",
            "camera_params": [
                intr["fx"], intr["fy"],
                res["width"] - intr["cx"], res["height"] - intr["cy"],
                dist["k1"], dist["k2"], -dist["p1"], -dist["p2"],
            ],
        }
        if name == "rgb_1":
            entry["ref_sensor"] = True
        else:
            T = T_cam_ins[name] @ np.linalg.inv(T_rig_ins)
            q = Rotation.from_matrix(T[:3, :3]).as_quat()  # scipy: [x, y, z, w]
            entry["cam_from_rig_rotation"] = [q[3], q[0], q[1], q[2]]  # -> [w, x, y, z]
            entry["cam_from_rig_translation"] = T[:3, 3].tolist()
        cameras.append(entry)

        # sanity: camera center in rig frame
        T = T_cam_ins[name] @ np.linalg.inv(T_rig_ins)
        center = -T[:3, :3].T @ T[:3, 3]
        print(f"{name} -> camera{idx}: center in rig frame = "
              f"[{center[0]:+.4f}, {center[1]:+.4f}, {center[2]:+.4f}] m, "
              f"baseline = {np.linalg.norm(center):.4f} m")

    OUT.write_text(json.dumps([{"cameras": cameras}], indent=4) + "\n")
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
