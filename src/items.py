from .box import Box

class Items(object):
    def __init__(self, bbox):
        self.bbox = Box(bbox)

    def getDict(self):
        return {
            "xmin": self.bbox.xmin,
            'ymin': self.bbox.ymin,
            'xmax': self.bbox.xmax,
            'ymax': self.bbox.ymax
        }
