from detectron2.data.datasets import register_coco_instances


PUBLAYNET_CATEGORIES = [
    {"color": [220, 20, 60], "isthing": 1, "id": 1, "name": "Background"},
    {"color": [119, 11, 32], "isthing": 1, "id": 2, "name": "Text"},
    {"color": [0, 0, 142], "isthing": 1, "id": 3, "name": "Title"},
    {"color": [0, 0, 230], "isthing": 1, "id": 4, "name": "List"},
    {"color": [106, 0, 228], "isthing": 1, "id": 5, "name": "Table"},
    {"color": [0, 60, 100], "isthing": 1, "id": 6, "name": "Figure"},
]

def _get_publaynet_instances_meta():
    thing_ids = [k["id"] for k in PUBLAYNET_CATEGORIES if k["isthing"] == 1]
    thing_colors = [k["color"] for k in PUBLAYNET_CATEGORIES if k["isthing"] == 1]
    assert len(thing_ids) == 80, len(thing_ids)
    # Mapping from the incontiguous COCO category id to an id in [0, 79]
    thing_dataset_id_to_contiguous_id = {k: i for i, k in enumerate(thing_ids)}
    thing_classes = [k["name"] for k in PUBLAYNET_CATEGORIES if k["isthing"] == 1]
    ret = {
        "thing_dataset_id_to_contiguous_id": thing_dataset_id_to_contiguous_id,
        "thing_classes": thing_classes,
        "thing_colors": thing_colors,
    }
    return ret
def register_publaynet_dataset():
    register_coco_instances("publaynet_train", _get_publaynet_instances_meta(), "../datasets/publaynet/train.json", "../datasets/publaynet/train.json")
    register_coco_instances("publaynet_val", _get_publaynet_instances_meta(), "../datasets/publaynet/val.json", "../datasets/publaynet/val.json")