import time
import torch
import atexit
import bisect
import yaml
from collections import deque
from tqdm import tqdm
from .text import Text
from .obj import Obj
from .page import Page
from fvcore.common.file_io import PathManager
from PIL import Image, ImageOps
import numpy as np
from statistics import mean
import multiprocessing as mp
from detectron2.config import get_cfg
from detectron2.data import MetadataCatalog
from detectron2.engine.defaults import DefaultPredictor
from detectron2.utils.visualizer import ColorMode, Visualizer
MetadataCatalog.get("dla_val").thing_classes = [
    'text', 'title', 'list', 'table', 'figure']


class Predictor():
    def __init__(self, cfg, instance_mode=ColorMode.IMAGE, parallel=False):
        self.metadata = MetadataCatalog.get(
            cfg.DATASETS.TEST[0] if len(cfg.DATASETS.TEST) else "__unused")
        self.cpu_device = torch.device("cpu")
        self.instance_mode = instance_mode
        self.parallel = parallel
        if parallel:
            num_gpu = torch.cuda.device_count()
            self.predictor = AsyncPredictor(cfg, num_gpus=num_gpu)
        else:
            self.predictor = DefaultPredictor(cfg)

    def predict(self, image):
        predictions = self.predictor(image)
        return predictions


class AsyncPredictor:
    class _StopToken:
        pass

    class _PredictWorker(mp.Process):
        def __init__(self, cfg, task_queue, result_queue):
            self.cfg = cfg
            self.task_queue = task_queue
            self.result_queue = result_queue
            super().__init__()

        def run(self):
            predictor = DefaultPredictor(self.cfg)
            while True:
                task = self.task_queue.get()
                if isinstance(task, AsyncPredictor._StopToken):
                    break
                idx, data = task
                result = predictor(data)
                self.result_queue.put(idx, result)

        def __init__(self, cfg, num_gpus: int = 1):
            num_worker = max(num_gpus, 1)
            self.task_queue = mp.Queue(maxsize=num_worker * 3)
            self.result_queue = mp.Queue(maxsize=num_worker * 3)
            self.procs = []
            for gpuid in range(max(num_gpus, 1)):
                cfg = cfg.clone()
                cfg.defrost()
                cfg.MODEL.DEVICE = "cuda:{}".format(
                    gpuid) if num_gpus > 0 else "cpu"
                self.procs.append(AsyncPredictor._PredictWorker(
                    cfg, self.task_queue, self.result_queue))
            self.put_idx = 0
            self.get_idx = 0
            self.result_rank = []
            self.result_data = []
            for p in self.procs:
                p.start()
            atexit.register(self.shutdown)

        def put(self, image):
            self.put_idx += 1
            self.task_queue.put((self.put_idx, image))

        def get(self):
            self.get_idx += 1
            if len(self.result_rank) and self.result_rank[0] == self.get_idx:
                res = self.result_data[0]
                del self.result_data[0], self.result_rank[0]
                return res
            while True:
                idx, res = self.result_queue.get()
                if idx == self.get_idx:
                    return res
                insert = bisect.bisect(self.result_rank, idx)
                self.result_rank.insert(insert, idx)
                self.result_data.insert(insert, res)

        def __len__(self):
            return self.put_idx - self.get_idx

        def __call__(self, image):
            self.put(image)
            return self.get()

        def shutdown(self):
            for _ in self.procs:
                self.task_queue.put(AsyncPredictor._StopToken())

        @property
        def default_buffer_size(self):
            return len(self.procs) * 5


class Model(object):
    
    CLASSES = ['Text', 'Title', 'List', 'Table', 'Figure']
    def __init__(self, config):
        self.config = config
        self.cfg = self.__set_config()
        self.predictor = Predictor(self.cfg)


    def __set_config(self):
        cfg = get_cfg()
        cfg.merge_from_file(self.config['files']['config'])
        # cfg.merge_from_file('/home/buithoai/Desktop/VBDI/Fig_Tab_Caption-Detection/configs/faster/e2e_faster_rcnn_X-101-64x4d-FPN_1x.yaml')
        cfg.MODEL.RETINANET.SCORE_THRESH_TEST = self.config['models']['score_thresh']
        cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = self.config['models']['score_thresh']
        cfg.MODEL.PANOPTIC_FPN.COMBINE.INSTANCES_CONFIDENCE_THRESH = self.config['models'][
            'instances_confidence_thresh']
        cfg.MODEL.WEIGHTS = self.config['files']['model']
        # cfg.MODEL.WEIGHTS = '/home/buithoai/Desktop/VBDI/Fig_Tab_Caption-Detection/model/faster_rcnn/model_final.pkl'
        cfg.MODEL.DEVICE = self.config['models']['device']
        cfg.freeze()
        return cfg

    def readImage(self, image_path, format=None):
        with PathManager.open(image_path, "rb") as f:
            image = Image.open(f)
            try:
                image = ImageOps.exif_transpose(image)
            except Exception:
                pass
            if format is not None:
                conversion_format = format
                if format == "BGR":
                    conversion_format = "RGB"
                image = image.convert(conversion_format)
            image = np.asarray(image)
            if format == "BGR":
                image = image[:, :, :: -1]
            if format == "L":
                image = np.expand_dims(image, -1)
            return image

    def nms(self, lst_obj, thresh_score=0.75):
        if not lst_obj:
            return []
        result = []
        boxes = [i.getBox() for i in lst_obj]
        scores = [i.getScore() for i in lst_obj]
        boxes = np.array(boxes)
        picked_boxes = []
        picked_score = []
        s_x = boxes[:, 0]
        s_y = boxes[:, 1]
        e_x = boxes[:, 2]
        e_y = boxes[:, 3]
        scores = np.array(scores)
        areas = (e_x - s_x + 1) * (e_y - s_y + 1)
        order = np.argsort(scores)
        while order.size > 0:
            index = order[-1]
            picked_boxes.append(boxes[index])
            picked_score.append(scores[index])
            x1 = np.maximum(s_x[index], s_x[order[:-1]])
            x2 = np.minimum(e_x[index], e_x[order[:-1]])
            y1 = np.maximum(s_y[index], s_y[order[:-1]])
            y2 = np.minimum(e_y[index], e_y[order[:-1]])
            w = np.maximum(0.0, x2 - x1 + 1)
            h = np.maximum(0.0, y2 - y1 + 1)
            intersection = w * h
            ratio = intersection / \
                (areas[index] + areas[order[:-1]] - intersection)
            left = np.where(ratio < thresh_score)
            order = order[left]
        for i in range(len(picked_boxes)):
            obj = Obj(bbox=picked_boxes[i], score=picked_score[i], type='')
            result.append(obj)
        return result

    def softNms(self, lst_obj, Nt = 0.3, sigma = 0.5, thresh = 0.001, method = 2):
        boxes = [i.getBox() for i in lst_obj]
        scores = [i.getScore() for i in lst_obj]
        N     = boxes.shape[0]
        indexes = np.array([np.arange(N)])
        boxes  = np.concatenate((boxes, indexes.T), axis = 1)
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        for i in range(N):
            tBD = boxes[i, :].copy()
            tscore = scores[i].copy()
            tarea = areas[i].copy()
            pos = i + 1
            if i != N - 1:
                maxscore = np.max(scores[pos:], axis=0)
                maxpos = np.argmax(scores[pos:], axis=0)
            else:
                maxscore = scores[-1]
                maxpos   = 0
            if tscore < maxscore:
                dets[i, :] = boxes[maxpos + i + 1, :]
                dets[maxpos + i + 1, :] = tBD
                tBD = boxes[i, :]
                scores[i] = scores[maxpos + i + 1]
                scores[maxpos + i + 1] = tscore
                tscore = scores[i]
                areas[i] = areas[maxpos + i + 1]
                areas[maxpos + i + 1] = tarea
                tarea = areas[i]
            xx1 = np.maximum(boxes[i, 1], boxes[pos:, 1])
            yy1 = np.maximum(boxes[i, 0], boxes[pos:, 0])
            xx2 = np.minimum(boxes[i, 3], boxes[pos:, 3])
            yy2 = np.minimum(boxes[i, 2], boxes[pos:, 2])
            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)
            inter = w * h
            ovr = inter / (areas[i] + areas[pos:] - inter)
            if method == 1:
                weight = np.ones(ovr.shape)
                weight[ovr > Nt] = weight[ovr > Nt] - ovr[ovr > Nt]
            elif method == 2:
                weight = np.exp(-(ovr * ovr) / sigma)
            else: 
                weight = np.ones(ovr.shape)
                weight[ovr > Nt] = 0
            scores[pos:] = weight * scores[pos:]
        inds = boxes[:, 4][scores > thresh]
        keep = inds.astype(int)
        return keep

    def predict(self, image_path, page, nms = False, iou_thresh_max=0.75, iou_thresh_min=0.2):
        import time
        t0 = time.time()
        print("[INFO] Process............................")
        img = self.readImage(image_path, format='BGR')
        page_index = int((image_path.split('/')[-1]).split('.')[0])
        predictions = self.predictor.predict(img)
        lst_text = []
        lst_obj = []
        boxes = predictions["instances"].pred_boxes
        classes = predictions["instances"].pred_classes
        scores = predictions["instances"].scores
        for i in tqdm(range(len(classes))):
            if classes[i] == 0 or classes[i] == 1:
                bbox = boxes[i].tensor.cpu().numpy()[0].astype('float')
                text = Text(bbox)
                lst_text.append(text)
            elif classes[i] == 3:
                bbox = boxes[i].tensor.cpu().numpy()[0].astype('float')
                score = scores[i]
                table = Obj(bbox, score, type='Table')
                lst_obj.append(table)
            elif classes[i] == 4:
                bbox = boxes[i].tensor.cpu().numpy()[0].astype('float')
                score = scores[i]
                figure = Obj(bbox, score, type='Figure')
                lst_obj.append(figure)
        if nms:
            lst_obj = self.nms(lst_obj)
        page.setLstObj(lst_obj)
        page.setLstText(lst_text)
        # page.virtualize()
        print('[INFO] Time to detect: %0.2fs' % (time.time() - t0))
        return page

    def predict_v2(self, image_path, page):
        import time
        t0 = time.time()
        print("[INFO] Process............................")
        img = self.readImage(image_path, format='BGR')
        page_index = int((image_path.split('/')[-1]).split('.')[0])
        predictions = self.predictor.predict(img)
        lst_text = []
        lst_obj = []
        lst_result = []
        boxes = predictions["instances"].pred_boxes
        classes = predictions["instances"].pred_classes
        scores = predictions["instances"].scores
        for i in tqdm(range(len(classes))):
            temp = {
                'type': '',
                'bbox': None,
                'score' : 0.0
            }
            temp['bbox'] = [i for i in boxes[i].tensor.cpu().numpy()[0].astype('float')]
            temp['score'] = scores[i]
            bbox = boxes[i].tensor.cpu().numpy()[0].astype('float')
            if classes[i] == 0 or classes[i] == 1:
                score = scores[i]
                text = Text(bbox, score = score, type = self.CLASSES[classes[i]])
                lst_text.append(text)
                temp['type'] = self.CLASSES[classes[i]]
            elif classes[i] == 3:
                # bbox = boxes[i].tensor.cpu().numpy()[0].astype('float')
                score = scores[i]
                table = Obj(bbox, score, type='Table')
                lst_obj.append(table)
                temp['type'] = self.CLASSES[classes[i]]
            elif classes[i] == 4:
                # bbox = boxes[i].tensor.cpu().numpy()[0].astype('float')
                score = scores[i]
                figure = Obj(bbox, score, type='Figure')
                lst_obj.append(figure)
                temp['type'] = self.CLASSES[classes[i]]
            else:
                score = scores[i]
                text = Text(bbox, score = score)
                lst_text.append(text)
                temp['type'] = self.CLASSES[classes[0]]
            lst_result.append(temp)
        page.setLstObj(lst_obj)
        page.setLstText(lst_text)
        # page.virtualize()
        print('[INFO] Time to detect: %0.2fs' % (time.time() - t0))
        return page, lst_result

    def predictImg(self, image_path):
        import time
        t0 = time.time()
        print("[INFO] Process............................")
        img = self.readImage(image_path, format='BGR')
        page_index = int((image_path.split('/')[-1]).split('.')[0])
        predictions = self.predictor.predict(img)
        lst_result = []
        boxes = predictions["instances"].pred_boxes
        classes = predictions["instances"].pred_classes
        scores = predictions["instances"].scores
        for i in tqdm(range(len(classes))):
            temp = {
                'type': '',
                'bbox': None
            }
            if classes[i] == 0:
                temp['bbox'] = [i for i in boxes[i].tensor.cpu().numpy()[
                    0].astype('float')]
                temp['type'] = 'Text'
                lst_result.append(temp)
            elif classes[i] == 1:
                temp['bbox'] = [i for i in boxes[i].tensor.cpu().numpy()[
                    0].astype('float')]
                temp['type'] = 'Title'
                lst_result.append(temp)
            elif classes[i] == 3 or classes[i] == 4:
                temp['bbox'] = [i for i in boxes[i].tensor.cpu().numpy()[
                    0].astype('float')]
                temp['type'] = 'Object'
                lst_result.append(temp)
        print('[INFO] Time to detect: %0.2fs' % (time.time() - t0))
        return lst_result

    
                
        