import fitz 
import os
from time import time
import numpy as np
import json
import cv2
import yaml
from PIL import Image


from src.page import Page
from src.model import Model
from src.box import Box
from src.obj import Obj
from src.text import Text
from src.toc import get_table_of_contents_CV, get_table_of_contents



class App():
	def __init__(self, path_config = './config.yml'):
		self.config = self.__set_config(path_config)
		self.model  = self.__load_model()
		self.color = [(255, 0, 0), (0, 255, 0), (0, 0, 255),
          (224, 199, 255), (96, 96, 96), (0, 0, 0)]

	def getPathUpload(self):
		return self.config['dir']['upload']

	def __set_config(self, path_config):
		try:
			with open('./config.yml', 'r') as file:
				config = yaml.safe_load(file)
				return config
		except yaml.YAMLError as exc:
			print(exc)
	
	def __load_model(self):
		print("[INFO] Load model.......")
		t0 = time()
		model = Model(config = self.config)
		print("[INFO] Time to load model %0.2fs" % (time() - t0))
		return model
	
	def detectToc(self, pdf_p, version = True):
		os.system('rm -rf %s/*' % (self.config['dir']['image']))
		doc = fitz.Document(pdf_p)
		dict_figure = dict.fromkeys([str(i) for i in range(doc.pageCount)], None)
		for page_index in range(doc.pageCount):
			page = doc.loadPage(page_index)
			pix = page.getPixmap()
			img_p = os.path.join(self.config['dir']['image'], str(page_index) + '.png')
			pix.writePNG(img_p)
			temp = self.model.predictImg(img_p)
			dict_figure[str(page_index)] = temp
		if version:
			result = get_table_of_contents_CV(pdf_p, dict_figure)
		else:
			result = get_table_of_contents(pdf_p, dict_figure)
		return result
	
 
	def detectAll(self, pdf_p):
		os.system('rm -rf %s/*' % (self.config['dir']['image']))
		doc = fitz.Document(pdf_p)
		data = []
		dict_figure = dict.fromkeys([str(i) for i in range(doc.pageCount)], None)
		for page_index in range(doc.pageCount):
			page = Page(page=doc.loadPage(page_index), index = page_index)
			page.getImage()
			img_p = os.path.join(self.config['dir']['image'], str(page_index) + '.png')
			lst_result = None
			# if page.isHasFigure() or page.isHasTable():
			page, lst_result = self.model.predict_v2(image_path = img_p, page = page)
			page.run(dict_info = lst_result, return_all = True)
			result = page.extract()
			data.append(result)
			# else:
			# 	lst_result = self.model.predictImg(image_path = img_p)
			dict_figure[str(page_index)] = lst_result
		toc = get_table_of_contents_CV(pdf_p, dict_figure)
		return data, toc
     

	def detectCaption(self, pdf_p):
		os.system('rm -rf %s/*' % (self.config['dir']['image']))
		doc = fitz.Document(pdf_p)
		data = []
		for page_index in range(doc.pageCount):
			page = Page(page=doc.loadPage(page_index), index = page_index)
			page.getImage()
			if page.isHasFigure() or page.isHasTable():
				page = self.model.predict(image_path = os.path.join(self.config['dir']['image'], str(page_index) + '.png'), page = page)
				page.run()
				result = page.extractDict()
				data += result
		return data
	
	def test(self, pdf_p, output = True):
		data = self.detectCaption(pdf_p)
		json_name = pdf_p.split('/')[-1].replace('.pdf', '.json')
		message = {
                    "success": True,
                    "message": 'Successfully',
                    "total": len(data),
                    "detected": data
        }
		with open(os.path.join(self.config['dir']['output'], json_name), 'w') as f:
			f.write(json.dumps(message))
		if output:
			print('[INFO] Draw box')
			c = 0
			for d in data:
				page_index = int(d['page']) - 1
				img_p = os.path.join(self.config['dir']['image'], str(page_index) + '.png')
				img = cv2.imread(img_p)
				xmin_b = int(d['position']['x-top'])
				ymin_b = int(d['position']['y-top'])
				xmax_b = int(d['position']['x-bottom'])
				ymax_b = int(d['position']['y-bottom'])
				xmin_c = int(d['caption-position']['x-top'])
				ymin_c = int(d['caption-position']['y-top'])
				xmax_c = int(d['caption-position']['x-bottom'])
				ymax_c = int(d['caption-position']['y-bottom'])
				cv2.rectangle(img, (xmin_b, ymin_b), (xmax_b, ymax_b), color = self.color[c], thickness=1)
				cv2.rectangle(img, (xmin_c, ymin_c), (xmax_c, ymax_c), color = self.color[c], thickness=1)
				cv2.imwrite(img_p, img)
				if c == len(self.color) - 1:
					c = 0
				else:
					c += 1
			print('[INFO] Convert image to pdf')
			lst_img_p = os.listdir(self.config['dir']['image'])
			lst_img_p = sorted(lst_img_p, key=lambda x: int(x.split('.')[0]))
			im = []
			im1 = Image.open(os.path.join(self.config['dir']['image'], lst_img_p[0]))
			for img_p in lst_img_p[1:]:
				im2 = Image.open(os.path.join(self.config['dir']['image'], img_p))
				im.append(im2)
			im1.save(os.path.join(self.config['dir']['output'], json_name.replace('.json', '.pdf')), "PDF", resolution=100.0, save_all=True, append_images=im)

	def main(self):
		lst_pdf = os.listdir(self.config['dir']['input'])
		for pdf_p in lst_pdf[1:2]:
			print('[INFO] PDF : %s' %(pdf_p))
			pdf_p = os.path.join(self.config['dir']['input'], pdf_p)
			self.test(pdf_p = pdf_p)

if __name__ == '__main__':
	App = App()
	App.main()
