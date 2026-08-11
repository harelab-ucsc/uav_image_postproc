# uav_image_postproc

Post-processing utilities that turn a raw multi-cam Birdseye payload capture into a COLMAP-ready dataset for sparse/dense reonconstruction.
The pipeline targets a **4-camera birdseye rig** whose cameras are mounted upside down, hardware-sync and calibrated camchain ('birdseye_v2_camchain.yaml'). It corrects the orientation, lays images out in COLMAP's rig convention, convers the calibration into a COLMAP rig_config.json, and builds static occlusion masks for the drone legs that appearin 2 cameras (rgb2 & rgb4).

## Scripts

### 1. 'prepare_colmap_rig.py' - image conditioning + rig layout 
- Rotates every image 180
- Regroups frames into 'camera1/ ... camera4/' 
- Renames frames from the 'rgb_<N>_<timestamp>' to 'image0001.jpeg ... image000N.jpeg (this is what COLMAP expexts)
- Writes 'frame_mapping.txt': 'imageNNNN.jpeg -> original timestamp'

### 2. 'gen_rig_config.py' - calibration -> COLMAP 'rig_config.json'
- Reads 'birdseye_v2_camchain.yaml' and writes 'rig_config.json'

### 3. 'gen_leg_masks.py' - static drone leg occlusion masks
- Finds fixed pixel region covered by UAV's landing gear in every frame
- Writes canonical masks to 'masks/.canonical/camera{1..4}.png
- ('0 = ignore' , '255 = keep')
