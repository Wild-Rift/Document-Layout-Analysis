#!/bin/bash

echo'Install..................'
pip install -U torch==1.4+cu100 torchvision==0.5+cu100 -f https://download.pytorch.org/whl/torch_stable.html 
pip install cython pyyaml==5.1
pip install detectron2 -f https://dl.fbaipublicfiles.com/detectron2/wheels/cu100/index.html
pip install -r requirement.txt
echo'.........................'
