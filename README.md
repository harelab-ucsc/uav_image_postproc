# uav_image_postproc

Post-processing utilities that turn a raw multi-cam Birdseye payload capture into a COLMAP-ready dataset for sparse/dense reonconstruction.
The pipeline targets a **4-camera birdseye rig** whose cameras are mounted upside down, hardware-sync and calibrated camchain ('birdseye_v2_camchain.yaml'). It corrects the orientation, lays images out in COLMAP's rig convention, convers the calibration into a COLMAP rig_config.json, and builds static occlusion masks for the drone legs that appearin 2 cameras (rgb2 & rgb4).

## Scripts

### 1.
