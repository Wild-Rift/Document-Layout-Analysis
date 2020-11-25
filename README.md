# Document-Layout-Analysis
Tools for extract figure, table, text,... from a pdf document
## Installation
```
$   pip install -r requirements.txt
```
### Install detectron2
Requirment
- CUDA=10.1 
- PyTorch>=1.7.0

How to install CUDA 10.1 can be found here: https://developer.nvidia.com/cuda-10.1-download-archive-base

How to install PyTorch can be found here: https://pytorch.org/

Afer installed above package, follow the instructions below to install detectron2:
```
$   git clone https://github.com/facebookresearch/detectron2.git
$   git checkout 8e3effc
$   python -m pip install -e detectron2
```
### Install Document-Layout-Analysis
Follow the instructions below:
```
$   git clone -b dev https://github.com/Wild-Rift/Document-Layout-Analysis.git
$   cd Document-Layout-Analysis
```

## Train
### Dataset

We use [IBM Publaynet](https://developer.ibm.com/technologies/artificial-intelligence/data/publaynet/) dataset for training and testing.

It includes 358,353 images, 335,703 training images, 11,245 validation images and 11,405 test images. The category-id label mapping of this dataset is: 
| Category id | Label |
| :---: | :--- |
| 1 | Text |
| 2 | Title |
| 3 | List |
| 4 | Table |
| 5 | Figure |

After download and extract dataset, please put it in ```datasets``` directory. The directories should be arranged like this:

    root
    ├── mmdet
    ├── tools
    ├── configs
    ├── output
    │   ├──...
    │
    ├── datasets
    │   ├── publaynet
    │   │   ├── test/
    │   │   ├── train/
    │   │   ├── val/
    │   │   ├── train.json
    │   │   ├── val.json

### Training
Document-Layout-Analysis support training on two models: Faster-RCNN and Mask-RCNN

```
$   CONFIG_FILE='configs/faster_rcnn_R_101_FPN_3x.yaml'      # if use Faster-RCNN model
$   CONFIG_FILE='configs/mask_rcnn_R_101_FPN_3x.yaml'        # if use Mask-RCNN model
```
If you want to inspect model's structures, go to ```configs``` directory

If you want to training on 8 GPU, run:
```
$   python train.py --num-gpus 8 --config-file CONFIG_FILE
```
If you want to training on 1 GPU, you may need to [change some parameters](https://arxiv.org/abs/1706.02677), run:
```
$   python train.py --num-gpus 1 \
    --config-file CONFIG_FILE \
    SOLVER.IMS_PER_BATCH 2 SOLVER.BASE_LR 0.0025
```
Checkpoints of model will be store in ```output``` directory after each epoch.