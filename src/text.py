from .items import Items


class Text(Items):
    def __init__(self, bbox, score = 0.95, type = 'Text'):
        super().__init__(bbox)
        self.type = type
        self._text = ''
        self.score = score

    def setText(self, text):
        self._text = text

    def getText(self):
        return self._text
    
    def getScore(self):
        return self.score

    def getBox(self):
        return [self.bbox.xmin, self.bbox.ymin, self.bbox.xmax, self.bbox.ymax]
