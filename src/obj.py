from .items import Items
import numpy as np
from.box import Box


class Obj(Items):
    def __init__(self, bbox, score, type):
        super().__init__(bbox)
        self._type = type
        self._caption = ""
        self._score = score
        self.bbox_caption = []

    def getBox(self):
        return [self.bbox.xmin, self.bbox.ymin, self.bbox.xmax, self.bbox.ymax]

    def getScore(self):
        return self._score

    def setBboxCaption(self, box):
        if isinstance(box, Box):
            for b in box.getBox():
                self.bbox_caption.append(b)
        else:
            for b in box:
                self.bbox_caption.append(b)

    def getBboxCaption(self):
        if self.bbox_caption:
            return [self.bbox_caption[0], self.bbox_caption[1], self.bbox_caption[2], self.bbox_caption[3]]
        else:
            return []

    def getDict(self):
        return {
            "type": self._type,
            "position": self.super().__return_dict(),
            "caption": self._caption,
            "score": self._score
        }

    def setCaption(self, text):
        self._caption = text

    def getCaption(self):
        return self._caption

    def setType(self, type):
        self._type = type

    def update(self):
        if self.bbox_caption:
            if self.bbox.isInside(Box(self.bbox_caption)):
                if self.bbox.ycenter < self.bbox_caption[1]:
                    ymax = self.bbox_caption[1]
                    self.bbox.setBox(
                        [self.bbox.xmin, self.bbox.ymin, self.bbox.xmax, ymax])
                else:
                    ymin = self.bbox_caption[3]
                    self.bbox.setBox(
                        [self.bbox.xmin, ymin, self.bbox.xmax, self.bbox.ymax])
            elif self.bbox.isOverlap(Box(self.bbox_caption)):
                if self.bbox.ycenter < self.bbox_caption[1]:
                    ymax = self.bbox_caption[1]
                    self.bbox.setBox(
                        [self.bbox.xmin, self.bbox.ymin, self.bbox.xmax, ymax])
                else:
                    ymin = self.bbox_caption[3]
                    self.bbox.setBox(
                        [self.bbox.xmin, ymin, self.bbox.xmax, self.bbox.ymax])
            if self.bbox_caption[0] - self.bbox.xmin < 5:
                xmin = self.bbox_caption[0]
                self.bbox.setBox(
                    [xmin, self.bbox.ymin, self.bbox.xmax, self.bbox.ymax])
