from .box import Box
from .obj import Obj
from .text import Text
import yaml
import re
import os
import fitz as pdf
from operator import itemgetter
from itertools import groupby
import cv2
import json
import numpy as np
from functools import cmp_to_key




class Page(object):
	def __init__(self, page, index):
		self.page_index = index
		self.page       = page
		self.lst_obj    = []
		self.lst_text   = []
		self.fonts   = self.getFont()
		self.width = self.page.MediaBox[2]
		self.height = self.page.MediaBox[3]
		self.config = self.__set_config()
	
	def __set_config(self, path= 'config.yml'):
		try:
			with open('config.yml', 'r') as file:
				config = yaml.safe_load(file)
				return config
		except yaml.YAMLError as exc:
   			print(exc)
		

	def setLstObj(self, lst_obj):
		self.lst_obj = lst_obj

	def getLstObj(self):
		return self.lst_obj

	def setLstText(self, lst_text):
		for obj_t in lst_text:
			text = self.getTextInBox(obj_t.bbox)
			if self.IsCaption(text):
				self.lst_text.append(obj_t)
		self.getLine()

	def getLstText(self):
		return self.lst_text

	def getTextInBox(self, box):
		page_dict = self.page.getText(output = 'dict')
		result = ''
		lst_span = []
		for block in page_dict['blocks']:
			if block['type'] == 0:
				for line in block['lines']:
					for span in line['spans']:
						if Box(span['bbox']).isOverlap(box):
							lst_span.append([Box(span['bbox']), span])
		for i in range(len(lst_span)):
			for j in range(len(lst_span) - 1):
				if lst_span[i][0].ymin - lst_span[j][0].ymin >= 5:
					lst_span[i], lst_span[j] = lst_span[j], lst_span[i]
				elif lst_span[i][0].xmin > lst_span[j][0].xmin:
					lst_span[i], lst_span[j] = lst_span[j], lst_span[i]
		for span in [i[1] for i in lst_span[: : -1]]:
			result += "".join(str(w) for w in span['text'])
		return result.replace('\t', ' ')

	def isHasFigure(self):
		page_dict = self.page.getText(output = 'dict')
		lst_span = []
		for b in page_dict['blocks']:
			if 'lines' in b:
				for line in b['lines']:
					for span in line['spans']:
						if span['text'].find('figure') != -1 or span['text'].find('Figure') != -1 or span['text'].find('Fig') != -1:
							lst_span.append(span)
		return lst_span

	def isHasTable(self):
		page_dict = self.page.getText(output = 'dict')
		lst_span = []
		for b in page_dict['blocks']:
			if 'lines' in b:
				for line in b['lines']:
					for span in line['spans']:
						if span['text'].find('Table') != -1 or span['text'].find('table') != -1:
							lst_span.append(span)
		return lst_span

	def getFont(self):
		fonts = {}
		page_dict = self.page.getText(output = 'dict')
		for block in page_dict['blocks']:
			if block['type'] == 0:
				for line in block['lines']:
					for span in line['spans']:
						if span['font'] not in fonts.keys():
							fonts[span['font']] = {}
							fonts[span['font']]['amount'] = 1
							fonts[span['font']]['span'] = []
							fonts[span['font']]['span'].append(span)
						else:
							fonts[span['font']]['amount'] += 1
							fonts[span['font']]['span'].append(span)
		return fonts

	def sortFont(self) -> list:
		s_font = []
		for font in self.fonts.keys():
			s_font.append([font, self.fonts[font]['amount']])
		s_font = sorted(s_font, key = lambda x : x[1])
		return [i[0] for i in s_font]

	def getImage(self, dpi = 72):
		pix = self.page.getPixmap(alpha = False, matrix = pdf.Matrix( dpi / 72, dpi / 72))
		_name_png = os.path.join(self.config['dir']['image'], str(self.page_index) + '.png')
		pix.writeImage(_name_png)

	def virtualize(self) -> None:
		
		img = cv2.imread(os.path.join(self.config['image'], str(self.page_index) + '.png'))
		for obj in self.lst_obj:
			box = obj.getBox()
			cv2.rectangle(img, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), color = (0, 0, 255), thickness= 1)
		for text in self.lst_text:
			box = text.getBox()
			cv2.rectangle(img, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), color = (0, 255, 0), thickness= 1)
		cv2.imwrite(os.path.join('Image_test', str(self.page_index) + '_copy.png'), img)


	def detectCaptionTT(self) -> None:
		lst_text = self.lst_text.copy()
		for obj in self.lst_obj:
			lst_distance = []
			for text in lst_text:
				distance = obj.bbox.getDistance(text.bbox)
				lst_distance.append([distance, lst_text.index(text)])
			lst_distance = sorted(lst_distance, key= lambda x : x[0])
			caption = ''
			for dis, index in lst_distance:
				caption  = self.getTextInBox(lst_text[index].bbox)
				obj.setBboxCaption(lst_text[index].bbox)
				if lst_text:
					lst_text.pop(index)
				break
			obj.setCaption(caption)


	def sortLst(self, text = False):
		if not text:
			lst_obj = self.lst_obj.copy()
			for i in range(len(lst_obj)):
				for j in range(len(lst_obj)):
					if i != j:
						if lst_obj[i].bbox.ymin > lst_obj[j].bbox.ymin and lst_obj[i].bbox.ymin < lst_obj[j].bbox.ymax:
							if lst_obj[i].bbox.xmin > lst_obj[j].bbox.xmax:
								lst_obj[i], lst_obj[j] = lst_obj[j], lst_obj[i]
						elif lst_obj[j].bbox.ymin > lst_obj[i].bbox.ymin and lst_obj[j].bbox.ymin < lst_obj[i].bbox.ymax:
							if lst_obj[j].bbox.xmin > lst_obj[i].bbox.xmax:
								lst_obj[i], lst_obj[j] = lst_obj[j], lst_obj[i]
						elif lst_obj[i].bbox.ymin > lst_obj[j].bbox.ymin:
							lst_obj[i], lst_obj[j] = lst_obj[j], lst_obj[i]
			return lst_obj
		else:
			lst_text = self.lst_text.copy()
			for i in range(len(lst_text)):
				for j in range(len(lst_text)):
					if i != j:
						if lst_text[i].bbox.ymin > lst_text[j].bbox.ymin and lst_text[i].bbox.ymin < lst_text[j].bbox.ymax:
							if lst_text[i].bbox.xmin > lst_text[j].bbox.xmax:
								lst_text[i], lst_text[j] = lst_text[j], lst_text[i]
						elif lst_text[j].bbox.ymin > lst_text[i].bbox.ymin and lst_text[j].bbox.ymin < lst_text[i].bbox.ymax:
							if lst_text[j].bbox.xmin > lst_text[i].bbox.xmax:
								lst_text[i], lst_text[j] = lst_text[j], lst_text[i]
						elif lst_text[j].bbox.ymin > lst_text[i].bbox.ymin:
							lst_text[i], lst_text[j] = lst_text[j], lst_text[i]
			return lst_text

	def detectCaption(self):
		l_o = len(self.lst_obj)
		l_t = len(self.lst_text)
		if l_o == 0:
			pass
		elif l_o == 1 and l_t == 1:
			caption = self.getTextInBox(self.lst_text[0].bbox)
			self.lst_obj[0].setBboxCaption(self.lst_text[0].bbox)
			self.lst_obj[0].setCaption(caption)
		elif l_o == l_t:
			lst_obj = self.sortLst()
			lst_text = self.sortLst(text = True)
			for i in range(len(lst_obj)):
				caption = self.getTextInBox(lst_text[i].bbox)
				lst_obj[i].setBboxCaption(lst_text[i].bbox)
				lst_obj[i].setCaption(caption)
				self.lst_obj = lst_obj
		else:
			self.detectCaptionTT()

	def extractDict(self):
		result = []
		for obj in self.lst_obj:
			item = {
				"type" : "",
				"page" : self.page_index + 1,
				"page_width" : self.width,
				"page_height" : self.height,
				"reliability" : 0.0,
				"position" : {
					"x-top" : 0.0,
					"y-top" : 0.0,
					"x-bottom" : 0.0,
					"y-bottom" : 0.0,
				},
				"caption" : "",
				"caption-reliability" : 0.0,
				"caption-position" : {
					"x-top" : 0.0,
					"y-top" : 0.0,
					"x-bottom" : 0.0,
					"y-bottom" : 0.0
				}
			}
			caption = obj.getCaption()
			if caption:
				type_ = self.getType(caption)
				if type_ == 1:
					item["type"] = "figure"
				else:
					item["type"] = "table"
				item["reliability"] = obj.getScore().tolist()
				item["position"]["x-top"] = obj.bbox.xmin
				item["position"]["y-top"] = obj.bbox.ymin
				item["position"]["x-bottom"] = obj.bbox.xmax
				item["position"]["y-bottom"] = obj.bbox.ymax
				item["caption"] = caption
				bbox_caption = obj.getBboxCaption()
				item["caption-reliability"] = obj.getScore().tolist()
				item["caption-position"]["x-top"] = bbox_caption[0]
				item["caption-position"]["y-top"] = bbox_caption[1]
				item["caption-position"]["x-bottom"] = bbox_caption[2]
				item["caption-position"]["y-bottom"] = bbox_caption[3]
				result.append(item)
		return result

	def extract(self):
		print(len(self.lst_obj))
		print(len(self.lst_text))
		result = {
			"num_page" : self.page_index + 1, 
			"height" : self.height, 
			"width" : self.width, 
			"detected" : []
		}

		for obj in self.lst_obj:
			item = {
				"type" : None,
				"text" : "",
				"bbox" : [0, 0, 0 ,0],
				"caption" : "",
				"score" : 0.0,
				"bbox_caption" : [0, 0, 0, 0]
			}
			caption = obj.getCaption()
			if caption:
				type_ = self.getType(caption)
				if type_ == 1:
					item['type'] = "Figure"
				else:
					item['type'] = "Table"
				item['bbox'] = [obj.bbox.xmin, obj.bbox.ymin, obj.bbox.xmax, obj.bbox.ymax]
				item['score'] = obj.getScore().tolist()
				bbox_cap = obj.getBboxCaption()
				item['bbox_caption'] = [bbox_cap[0], bbox_cap[1], bbox_cap[2], bbox_cap[3]]
				item['caption'] = caption
				result['detected'].append(item)
			else:
				item['type'] = obj._type
				item['bbox'] = [obj.bbox.xmin, obj.bbox.ymin, obj.bbox.xmax, obj.bbox.ymax]
				item['score'] = obj.getScore().tolist()
				result['detected'].append(item)
		for text in self.lst_text:
			item = {
				"type" : None,
				"text" : "",
				"bbox" : [0, 0, 0 ,0],
				"caption" : "",
				"score" : 0.0,
				"bbox_caption" : [0, 0, 0, 0]
			}
			item['type'] = text.type
			item['text'] = self.getTextInBox(text.bbox)
			item['bbox'] = [text.bbox.xmin, text.bbox.ymin, text.bbox.xmax, text.bbox.ymax]
			item['score'] = text.getScore() if isinstance(text.getScore(), float) else text.getScore().tolist()
			result['detected'].append(item)
		return result

 
	def preprcoess(self, dict_info):
		result = []
		for info in dict_info:
			if info['type'] in ['Text', 'Title']:
				flag = True
				bbox = info['bbox']
				for obj in self.lst_obj:
					bbox_cap = obj.getBboxCaption()
					if len(bbox_cap) > 0 and Box(bbox).iou(Box(bbox_cap)) > 0.7:
						flag = False
						break
				if flag:
					result.append(Text(bbox = bbox, score = info['score'], type = info['type']))
		return result
			
	def run(self,dict_info = None, return_all = False):
		self.detectCaption()
		# for obj in self.lst_obj:
		# 	obj.update()
		if return_all:
			result = self.preprcoess(dict_info)
			self.lst_text = result


	def getType(self, text):
		if len(re.findall(r'^Figure\s+.*', text, re.I)):
			return 1
		if len(re.findall(r'^Fig\s+.*', text, re.I)):
			return 1
		if len(re.findall(r'^Table\s+.*', text, re.I)):
			return 0
		if len(re.findall(r'^Figure.*', text, re.I)):
			return 1
		if len(re.findall(r'^Fig.*', text, re.I)):
			return 1
		if len(re.findall(r'^Table.*', text, re.I)):
			return 0
		if len(re.findall(r'^Figure(:)*\s+.*', text, re.I)):
			return 1
		if len(re.findall(r'^Fig(:)*\s+.*', text, re.I)):
			return 1
		if len(re.findall(r'^Table(:)*\s+.*', text, re.I)):
			return 0

	def IsCaption(self, text):
		if len(re.findall(r'^Figure\s+.*', text, re.I)):
			return True
		if len(re.findall(r'^Fig\s+.*', text, re.I)):
			return True
		if len(re.findall(r'^Table\s+.*', text, re.I)):
			return True
		if len(re.findall(r'^Figure.*', text, re.I)):
			return True
		if len(re.findall(r'^Fig.*', text, re.I)):
			return True
		if len(re.findall(r'^Table.*', text, re.I)):
			return True
		if len(re.findall(r'^Figure(:)*\s+.*', text, re.I)):
			return True
		if len(re.findall(r'^Fig(:)*\s+.*', text, re.I)):
			return True
		if len(re.findall(r'^Table(:)*\s+.*', text, re.I)):
			return True
		return False


	def isShortCaption(self, text):
		if len(re.findall(r'^Figure:?\s*.{0,4}$', text, re.I)):
			return True
		if len(re.findall(r'^Fig:?\s*.{0,4}$', text, re.I)):
			return True
		if len(re.findall(r'^Table:?\s*.{0,4}$', text, re.I)):
			return True
		return False


	def getLine(self):
		page_dict = self.page.getText(output = 'dict')
		lines = []
		for block in page_dict['blocks']:
			if block['type'] == 0:
				for line in block['lines']:
					key = str(int(line['bbox'][1] + 0.99999)).rjust(4, "0") + str(int(line['bbox'][0] + 0.99999)).rjust(4, "0")
					lines.append([line, key])
		lines = sorted(lines, key = lambda x : x[1])
		for i in range(len(lines)):
			line = lines[i][0]
			text = self.getTextInBox(Box(line['bbox']))
			if self.IsCaption(text):
				flag = True
				for obj_t in self.lst_text:
					if Box(line['bbox']).isOverlap(obj_t.bbox):
						flag = False
						break
				if flag:
					if self.isShortCaption(text):
						xmin = min(line['bbox'][0], lines[i + 1][0]['bbox'][0])
						ymin = min(line['bbox'][1], lines[i + 1][0]['bbox'][1])
						xmax = max(line['bbox'][2], lines[i + 1][0]['bbox'][2])
						ymax = max(line['bbox'][3], lines[i + 1][0]['bbox'][3])
						t = Text([xmin, ymin, xmax, ymax])
						self.lst_text.append(t)
					else:
						t = Text(line['bbox'])
						self.lst_text.append(t)











