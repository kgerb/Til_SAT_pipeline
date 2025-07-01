#!/bin/bash

docker run -it --rm --gpus device=1 \
  -v "$(pwd)":/workspace \
  -v /home/kg281/data/dat2_copy:/data \
  til_sat \
  bash -c "bash main.sh /data/test_pc_nopred.las test; exec bash" #exec bash to keep the container running


