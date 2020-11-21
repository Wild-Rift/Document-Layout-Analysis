import sys
import os
from flask import Flask, request, jsonify
import uuid
import cv2
from main import App
import json
try:
	import wget
except:
	os.system('pip install wget')
import base64

app = Flask(__name__)
App = App()
app.config['UPLOAD'] = App.getPathUpload()

@app.route('/caption', methods = ['GET', 'POST'])
def get():
	print('[INFO] API get caption')
	if len(os.listdir(app.config['UPLOAD'])) == 10:
		os.system('rm -rf %s/*' % (app.config['UPLOAD']))
	session_id = uuid.uuid1()
	message = {
		"success" : None, 
		"message" : '',
		"total"   : 0,
		"detected" : []
	}
	file_p = ''
	if request.method == 'GET':
		url = request.args['url']
		file_p = os.path.join(app.config['UPLOAD'], str(session_id) + '.pdf')
		print(file_p)
		try:
			file_name = wget.download(url, out = file_p)
		except: 
			message["success"] = False
			message["message"] = "Url error"
			resp = jsonify({"result" : message })
			return resp
		if not os.path.isfile(file_p):
			message["success"] = False
			message["message"] = "File not downloaded"
			resp = jsonify({"result" : message })
			return resp
	elif request.method == 'POST':
		if request.files['file'].filename == '':
			message["success"] = False
			message["message"] = "Not selected file"
			resp = jsonify({"result" : message })
			return resp
			# url = request.json
			# print(url)
			# if url == '':
			# 	message["success"] = False
			# 	message["message"] = "Url empty or not selected file"
			# 	resp = jsonify({"result" : message })
			# 	return resp
			# else:
			# 	file_p = os.path.join(app.config['UPLOAD'], str(session_id) + '.pdf')
			# 	try:
			# 		file_name = wget.download(url, out=file_p)
			# 	except: 
			# 		message["success"] = False
			# 		message["message"] = "Url error"
			# 		resp = jsonify({"result" : message })
			# 		return resp
			# 	if not os.path.isfile(file_p):
			# 		message["success"] = False
			# 		message["message"] = "File not downloaded"
			# 		resp = jsonify({"result" : message })
			# 		return resp
			# message["success"] = False
			# message["message"] = "No selected file"
			# resp = jsonify({"result" : message })
			# return resp
		else:
			file_p = os.path.join(app.config['UPLOAD'], str(session_id) + '.pdf')
			request.files['file'].save(file_p)
	data = App.detectCaption(file_p)
	message["success"] = True
	message["message"] = "Successfully"
	message["total"]   = len(data)
	message["detected"] = data
	return jsonify(message)
	
	

@app.route('/toc', methods = ['GET', 'POST'])
def getToc():
	print('[INFO] API get TOC')
	if len(os.listdir(app.config['UPLOAD'])) == 10:
		os.system('rm -rf %s/*' % (app.config['UPLOAD']))
	session_id = uuid.uuid1()
	message = {
		"success" : None, 
		"message" : '',
		"detected" : []
	}
	file_p = ''
	if request.method == 'GET':
		url = request.args['url']
		file_p = os.path.join(app.config['UPLOAD'], str(session_id) + '.pdf')
		print(file_p)
		try:
			file_name = wget.download(url, out = file_p)
		except: 
			message["success"] = False
			message["message"] = "Url error"
			resp = jsonify({"result" : message })
			return resp
		if not os.path.isfile(file_p):
			message["success"] = False
			message["message"] = "File not downloaded"
			resp = jsonify({"result" : message })
			return resp
	elif request.method == 'POST':
		if request.files['file'].filename == '':
			message["success"] = False
			message["message"] = "Not selected file"
			resp = jsonify({"result" : message })
			return resp
		else:
			file_p = os.path.join(app.config['UPLOAD'], str(session_id) + '.pdf')
			request.files['file'].save(file_p)
	data = App.detectToc(file_p, version = False)
	message["success"] = True
	message["message"] = "Successfully"
	message["detected"] = data
	return jsonify(message)
	

@app.route('/toc2', methods = ['GET', 'POST'])
def getToc2():
	print('[INFO] API get TOC')
	if len(os.listdir(app.config['UPLOAD'])) == 10:
		os.system('rm -rf %s/*' % (app.config['UPLOAD']))
	session_id = uuid.uuid1()
	message = {
		"success" : None, 
		"message" : '',
		"detected" : []
	}
	file_p = ''
	if request.method == 'GET':
		url = request.args['url']
		file_p = os.path.join(app.config['UPLOAD'], str(session_id) + '.pdf')
		print(file_p)
		try:
			file_name = wget.download(url, out = file_p)
		except: 
			message["success"] = False
			message["message"] = "Url error"
			resp = jsonify({"result" : message })
			return resp
		if not os.path.isfile(file_p):
			message["success"] = False
			message["message"] = "File not downloaded"
			resp = jsonify({"result" : message })
			return resp
	elif request.method == 'POST':
		if request.files['file'].filename == '':
			message["success"] = False
			message["message"] = "Not selected file"
			resp = jsonify({"result" : message })
			return resp
		else:
			file_p = os.path.join(app.config['UPLOAD'], str(session_id) + '.pdf')
			request.files['file'].save(file_p)
	data = App.detectToc(file_p)
	message["success"] = True
	message["message"] = "Successfully"
	message["detected"] = data
	print(message)
	return jsonify(message)


@app.route('/detect', methods = ['POST'])
def getAll():
	print('[INFO] API Document Analysis')
	if len(os.listdir(app.config['UPLOAD'])) == 10:
		os.system('rm -rf %s/*' % (app.config['UPLOAD']))
	session_id = uuid.uuid1()
	message = {
		"status" : None, 
		"message" : '',
		"total"   : 0,
		"pages" : [],
		"ToC" : None
	}
	file_p = ''
	if request.files['file'].filename == '':
		message["status"] = 201
		message["message"] = "Not selected file"
		resp = jsonify({"result" : message })
		return resp
	else:
		file_p = os.path.join(app.config['UPLOAD'], str(session_id) + '.pdf')
		request.files['file'].save(file_p)
	data, toc = App.detectAll(file_p)
	message["status"] = 200
	message["message"] = "Successfully"
	message["total"]   = len(data)
	message["pages"] = data
	message["ToC"] = toc
	# image = open('IMAGE/0.png', 'rb')
	# image_read = image.read()
	# image_64_encode = base64.encodestring(image_read)
	# # print(message)
	# print(image_64_encode)
	# message["image"] = cv2.imread('IMAGE/0.png').tolist()
	return jsonify(message)

if __name__ == '__main__':
	app.run(host= '0.0.0.0', port=9123, debug = False)
