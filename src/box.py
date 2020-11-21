import math


class Box(object):
    def __init__(self, box):
        self.xmin = box[0]
        self.ymin = box[1]
        self.xmax = box[2]
        self.ymax = box[3]
        self.width = abs(self.xmax - self.xmin)
        self.height = abs(self.ymax - self.ymin)
        self.xcenter = self.xmin + self.width / 2
        self.ycenter = self.ymin + self.height / 2

    def __str__(self):
        return " ".join(str(i) for i in [self.xmin, self.ymin, self.xmax, self.ymax])

    def area(self):
        return self.width * self.height

    def setBox(self, box):
        self.xmin = box[0]
        self.ymin = box[1]
        self.xmax = box[2]
        self.ymax = box[3]

    def getBox(self):
        return [self.xmin, self.ymin, self.xmax, self.ymax]

    def intersection(self, box):
        xA = max(self.xmin, box.xmin)
        yA = max(self.ymin, box.ymin)
        xB = min(self.xmax, box.xmax)
        yB = min(self.ymax, box.ymax)
        inter_area = max(0, xA - xB + 1) * max(0, yA - yB + 1)
        return inter_area

    def union(self, box):
        area_box = (box.xmax - box.xmin + 1) * (box.ymax - box.ymin + 1)
        return float(self.area() + area_box - self.intersection(box))

    def iou(self, box):
        return self.intersection(box) / self.union(box)

    def isInside(self, box):
        if self.xmin >= box.xmin and self.ymin >= box.ymin and self.xmax <= box.xmax and self.ymax <= box.ymax:
            return True
        return False

    def isOverlap(self, box):
        return not (self.xmax < box.xmin or self.xmin > box.xmax or self.ymin > box.ymax or self.ymax < box.ymin)

    def getCenterDist(self, box):
        return math.sqrt((self.xcenter - box.xcenter) ** 2 + (self.ycenter - box.ycenter) ** 2)

    def getHorizonalDistCenter(self, box):
        return abs(self.xcenter - box.xcenter)

    def getVerticalDistCenter(self, box):
        return abs(self.ycenter - box.ycenter)

    def getDistance(self, box):
        if self.isInside(box):
            return -2
        elif self.isOverlap(box):
            return -1
        else:
            return min(abs(self.ymin - box.ymin), abs(self.ymin - box.ymax), abs(self.ymax - self.ymin), abs(self.ymax - box.ymax))

    def getXX(self, box):
        xmin = max(self.xmin, box.xmin)
        xmax = min(self.xmax, box.xmax)
        if xmin - xmax < 0:
            return -1
        else:
            return max(abs(xmax - xmin) / self.width, abs(xmax - xmin) / box.width)
