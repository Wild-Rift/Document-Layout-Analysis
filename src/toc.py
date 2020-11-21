import fitz
import sys
import json
import re
import os
from collections import Counter
from pprint import pprint
import requests
from PIL import Image
from .box import Box


ENCODING = "UTF-8"


def SortBlocks(blocks):
	'''
	Sort the blocks of a TextPage in ascending vertical pixel order,
	then in ascending horizontal pixel order.
	This should sequence the text in a more readable form, at least by
	convention of the Western hemisphere: from top-left to bottom-right.
	If you need something else, change the sortkey variable accordingly ...
	'''

	sblocks = []
	for b in blocks:
		x0 = str(int(b["bbox"][0]+0.99999)).rjust(4,"0") # x coord in pixels
		y0 = str(int(b["bbox"][1]+0.99999)).rjust(4,"0") # y coord in pixels
		sortkey = y0 + x0                                # = "yx"
		sblocks.append([sortkey, b])
	sblocks.sort(key=lambda x: x[0], reverse=False)
	return [b[1] for b in sblocks] # return sorted list of blocks


# Use in get_reading_line
def SortLines(lines):
	''' Sort the lines of a block in ascending vertical direction. See comment
	in SortBlocks function.
	'''
	slines = []
	for l in lines:
		y0 = str(int(l["bbox"][1] + 0.99999)).rjust(4,"0")
		slines.append([y0, l])
	slines.sort(key=lambda x: x[0], reverse=False)
	return [l[1] for l in slines]


def SortSpans(spans):
	''' Sort the spans of a line in ascending horizontal direction. See comment
	in SortBlocks function.
	'''
	sspans = []
	for s in spans:
		x0 = str(int(s["bbox"][0] + 0.99999)).rjust(4,"0")
		sspans.append([x0, s])
	sspans.sort(key=lambda x: x[0], reverse=False)
	return [s[1] for s in sspans]


# Use in remove_header_footer
def get_text_line(line):
	# Use in remove_header_footer
	list_text = []
	# lines = block['lines']
	spans = line['spans']
	for span in spans:
		list_text.append(span['text'].replace(" ", "").lower())
	list_text.sort()
	str_text = ''.join(list_text).strip('0123456789.- ')
	str_text = re.sub(r'[0-9]|\.|\-|\'',"",str_text)
	# print(str_text)
	return str_text


# Use in remove_header_footer
def clear_content_null(page_list):
	list_rm = []
	for page_content in page_list:
		list_block_remove = []
		for block in page_content:
			if 'lines' not in block:
				list_block_remove.append(block)
			else:
				lines = block['lines']

				# Xóa spans rỗng
				for line in lines:
					list_spans_remove = []
					spans = line['spans']
					for span in spans:
						text_spans = span["text"]
						text_spans = re.sub(r'\s+', '', text_spans)
						if not bool(text_spans):
							list_spans_remove.append(span)
					for span in list_spans_remove:
						spans.remove(span)

				# Xóa lines rỗng
				list_line_remove = []
				for line in lines:
					text_spans = ''
					spans = line['spans']
					for span in spans:
						text_spans += span["text"]
					text_spans = re.sub(r'\s+', '', text_spans)
					if not bool(text_spans):
						list_line_remove.append(line)
				for line in list_line_remove:
					lines.remove(line)

				# Xóa block rỗng
				if len(lines) < 1:
					# print(block)
					list_block_remove.append(block)

		list_rm.append(list_block_remove)

	for page_content in page_list:
		list_block_remove = list_rm[page_list.index(page_content)]
		for blk in list_block_remove:
			page_content.remove(blk)
	return page_list


# Use for read_data
def remove_header_footer(page_list):

	clear_content_null(page_list)

	''' Find the blocks appear in all pages (block is supposed header or footer) '''
	dict_line = {}
	list_block_rv = []
	for page_content in page_list:
		for block in page_content:
			for line in block["lines"]:
				is_insert = False
				str_key = str(page_list.index(page_content))+"-" + \
					str(page_content.index(block))+"-" + \
					str(block["lines"].index(line))
				list_update_key = []
				for key, val in dict_line.items():
					key_line = page_list[int(
						key.split("-")[0])][int(key.split("-")[1])]["lines"][int(key.split("-")[2])]
					if (abs(line['bbox'][0] - key_line['bbox'][0]) < 20) and (abs(line['bbox'][1] - key_line['bbox'][1]) < 10) and \
							(abs(line['bbox'][2] - key_line['bbox'][2]) < 20) and (abs(line['bbox'][3] - key_line['bbox'][3]) < 10) and \
							get_text_line(line) == get_text_line(key_line):
						list_update_key.append((key, str_key))
						is_insert = True
				if is_insert:
					for x in list_update_key:
						dict_line[x[0]] = dict_line.get(x[0], 0) + 1
						dict_line[x[1]] = dict_line.get(x[0], 0) + 1
					# dict_line.update({ str_key : 1})
				else:
					dict_line[str_key] = dict_line.get(str_key, 0) + 1
	# print(dict_line)
	for key, val in dict_line.items():
		if len(page_list) > 3:
			if val / len(page_list) > 0.6:
				key_line = page_list[int(
					key.split("-")[0])][int(key.split("-")[1])]["lines"][int(key.split("-")[2])]
				list_block_rv.append(key_line)
		else:
			if val / len(page_list) > 0.5:
				key_line = page_list[int(
					key.split("-")[0])][int(key.split("-")[1])]["lines"][int(key.split("-")[2])]
				list_block_rv.append(key_line)
	# print(list_block_rv)
	for page in page_list:
		for block in page:
			for b in list_block_rv:
				if b in block["lines"]:
					block["lines"].remove(b)

	clear_content_null(page_list)

	for page_content in page_list:
		list_block_remove = []
		for block in page_content:
			if block["bbox"][0] < 0 or block["bbox"][1] < 0 or block["bbox"][2] < 0 or block["bbox"][3] < 0:
				list_block_remove.append(block)
		for blk in list_block_remove:
			page_content.remove(blk)

	return page_list


def read_data(file_path):
	doc = fitz.Document(file_path)
	pages = doc.pageCount
	page_even = []
	page_odd = []
	for x in range(pages):
		if x % 2 == 0:
			page_even.append(json.loads(doc.loadPage(x).getText(output = 'dict')))
		else:
			page_odd.append(json.loads(doc.loadPage(x).getText(output = 'dict')))
	page_odd = remove_header_footer(page_odd)
	page_even = remove_header_footer(page_even)
	page_list = []
	 
	for x in range(min(len(page_odd), len(page_even))):
		page_list.append(page_even[x])
		page_list.append(page_odd[x])

	if len(page_odd) > len(page_even):
		page_list.append(page_odd[-1])
	elif len(page_odd) < len(page_even):
		page_list.append(page_even[-1])

	return page_list


def get_dict_from_api(file_path):
	dict_figure = {}
	url = 'http://118.70.181.44:9123/detect'
	myfiles = {'files': open(file_path ,'rb')}
	figure = requests.post(url, files = myfiles)
	dict_figure = json.loads(figure.json())["result"]
	return dict_figure
		

# Use for get_reading_line
def num_column(list_line):
	list_x0 = []
	for line in list_line:
		list_x0.append(round(line["bbox"][0]))
	list_x1 = []
	for line in list_line:
		list_x1.append(round(line["bbox"][2]))
	freq_x0 = {}
	for items in list_x0:
		freq_x0[items] = list_x0.count(items)
	sorted_freq_x0 = sorted(freq_x0.items(), key = lambda kv:(kv[1], kv[0]))
	result_x0 = []
	freq_x1 = {}
	for items in list_x1:
		freq_x1[items] = list_x0.count(items)
	sorted_freq_x1 = sorted(freq_x1.items(), key = lambda kv:(kv[1], kv[0]))
	result_x1 = []
	if len(sorted_freq_x0) >= 3:
		largest_freq_x0 = sorted_freq_x0[-1][1]
		second_largest_freq_x0 = sorted_freq_x0[-2][1]
		third_largest_freq_x0 = sorted_freq_x0[-3][1]
		if third_largest_freq_x0 > (largest_freq_x0 / 2) and abs(sorted_freq_x0[-1][0] - sorted_freq_x0[-2][0]) > 25 and abs(sorted_freq_x0[-3][0] - sorted_freq_x0[-2][0]) > 25:
			num = 3
			result_x0 = [sorted_freq_x0[-1][0], sorted_freq_x0[-2][0], sorted_freq_x0[-3][0]]
			result_x1 = [sorted_freq_x1[-1][0], sorted_freq_x1[-2][0], sorted_freq_x1[-3][0]]
			return num, result_x0, result_x1
		elif second_largest_freq_x0 > (largest_freq_x0 / 2) and abs(sorted_freq_x0[-1][0] - sorted_freq_x0[-2][0]) > 25:
			num = 2
			result_x0 = [sorted_freq_x0[-1][0], sorted_freq_x0[-2][0]]
			result_x1 = [sorted_freq_x1[-1][0], sorted_freq_x1[-2][0]]
			return num, result_x0, result_x1
		else:
			num = 1
			result_x0 = [sorted_freq_x0[-1][0]]
			result_x1 = [sorted_freq_x1[-1][0]]
			return num, result_x0, result_x1
	elif len(sorted_freq_x0) == 2:
		largest_freq_x0 = sorted_freq_x0[-1][1]
		second_largest_freq_x0 = sorted_freq_x0[-2][1]
		if second_largest_freq_x0 > (largest_freq_x0 / 2) and abs(sorted_freq_x0[-1][0] - sorted_freq_x0[-2][0]) > 25:
			num = 2
			result_x0 = [sorted_freq_x0[-1][0], sorted_freq_x0[-2][0]]
			result_x1 = [sorted_freq_x1[-1][0], sorted_freq_x1[-2][0]]
			return num, result_x0, result_x1
		else:
			num = 1
			result_x0 = [sorted_freq_x0[-1][0]]
			result_x1 = [sorted_freq_x1[-1][0]]
			return num, result_x0, result_x1
	else:
		num = 1
		result_x0 = [sorted_freq_x0[-1][0]]
		result_x1 = [sorted_freq_x1[-1][0]]
		return num, result_x0, result_x1


def get_reading_line(list_line):
	param = 15 # (pixel) Độ thò thụt dòng của mỗi cột
	if num_column(list_line)[0] == 1:
		return list_line
	elif num_column(list_line)[0] == 2:
		result_x0 = num_column(list_line)[1]
		first_col = []
		first_col_x0 = min(result_x0)
		second_col = []
		second_col_x0 = max(result_x0)
		break_page = []
		reading_line = []
		for line in list_line:
			if int(line["bbox"][0]) < (first_col_x0 + param) and int(line["bbox"][0]) > (first_col_x0 - param):
				first_col.append(line)
			elif int(line["bbox"][0]) < (second_col_x0 + param) and int(line["bbox"][0]) > (second_col_x0 - param):
				second_col.append(line)
			else:
				break_page.append(line)
		max_break_point = 0
		last_breakpoint = 0
		for break_line in SortLines(break_page):
			break_point = break_line["bbox"][1]
			if break_point > max_break_point:
				max_break_point = break_point
			for line_col1 in SortLines(first_col):
				if line_col1["bbox"][1] < break_point and line_col1["bbox"][1] > last_breakpoint:
					reading_line.append(line_col1)
			for line_col2 in SortLines(second_col):
				if line_col2["bbox"][1] < break_point and line_col2["bbox"][1] > last_breakpoint:
					reading_line.append(line_col2)
			reading_line.append(break_line)
			last_breakpoint = break_point
		for line_col1 in SortLines(first_col):
			if line_col1["bbox"][1] > max_break_point:
				reading_line.append(line_col1)
		for line_col2 in SortLines(second_col):
			if line_col2["bbox"][1] > max_break_point:
				reading_line.append(line_col2)
		return reading_line
	elif num_column(list_line)[0] == 3:
		result_x0 = num_column(list_line)[1]
		first_col = []
		first_col_x0 = min(result_x0)
		result_x0.remove(first_col_x0)
		third_col = []
		third_col_x0 = max(result_x0)
		second_col = []
		second_col_x0 = min(result_x0)
		break_page = []
		reading_line = []
		for line in list_line:
			if int(line["bbox"][0]) < (first_col_x0 + param) and int(line["bbox"][0]) > (first_col_x0 - param):
				first_col.append(line)
			elif int(line["bbox"][0]) < (second_col_x0 + param) and int(line["bbox"][0]) > (second_col_x0 - param):
				second_col.append(line)
			elif int(line["bbox"][0]) < (third_col_x0 + param) and int(line["bbox"][0]) > (third_col_x0 - param):
				third_col.append(line)
			else:
				break_page.append(line)
		max_break_point = 0
		last_breakpoint = 0
		for break_line in SortLines(break_page):
			break_point = break_line["bbox"][1]
			if break_point > max_break_point:
				max_break_point = break_point
			for line_col1 in first_col:
				if line_col1["bbox"][1] < break_point and line_col1["bbox"][1] > last_breakpoint:
					reading_line.append(line_col1)
			for line_col2 in second_col:
				if line_col2["bbox"][1] < break_point and line_col2["bbox"][1] > last_breakpoint:
					reading_line.append(line_col2)
			for line_col3 in third_col:
				if line_col3["bbox"][1] < break_point and line_col3["bbox"][1] > last_breakpoint:
					reading_line.append(line_col3)
			reading_line.append(break_line)
			last_breakpoint = break_point
		for line_col1 in first_col:
			if line_col1["bbox"][1] > max_break_point:
				reading_line.append(line_col1)
		for line_col2 in second_col:
			if line_col2["bbox"][1] > max_break_point:
				reading_line.append(line_col2)
		for line_col3 in third_col:
			if line_col3["bbox"][1] > max_break_point:
				reading_line.append(line_col3)
		return reading_line


# Get nobody text with 1 column (use for 1 page)
def filter_body_by_distance(reading_line):
	# Get smallest distance y0
	list_y0 = []
	for line in reading_line:
		list_y0.append(round(line["bbox"][1]))
	freq_y0 = {}
	for items in list_y0:
		freq_y0[items] = list_y0.count(items)
	sorted_freq_y0 = sorted(freq_y0.keys())
	distance = []
	for i in range(len(sorted_freq_y0)-1):
		minus = sorted_freq_y0[i+1] - sorted_freq_y0[i]
		distance.append(minus)
	if distance == []:
		return reading_line
	else:
		smallest_distance = min(distance)
	# Get nobody
	sorted_line = SortLines(reading_line)
	i = 0
	tmp = {'bbox': [0,0,0,0],"spans":[]}
	tmp1 = {'bbox': [0,0,0,0],"spans":[]}
	heading_line = []
	next_not_heading = False
	for line in sorted_line:
		if (i % 2) == 0:
			i += 1
			value = line
			if i < 2:
				next_not_heading = False
				pass
			elif (abs(tmp["bbox"][1] - value["bbox"][1]) + abs(tmp["bbox"][1] - tmp1["bbox"][1])) > 2*smallest_distance:
				heading_line.append(tmp)
				next_not_heading = True
			tmp1 = tmp
			tmp = value
		else:
			i += 1
			value = line
			if i < 2:
				next_not_heading = False
				pass
			elif (abs(tmp["bbox"][1] - value["bbox"][1]) + abs(tmp["bbox"][1] - tmp1["bbox"][1])) > 2*smallest_distance:
				heading_line.append(tmp)
				next_not_heading = True
			tm1 = tmp
			tmp = value
	if heading_line == []:
		return reading_line
	else:
		return heading_line


# Get the most common style
def get_pop_freq_style(data):
	dict_style = {}
	index = 0
	pop_freq_style = []
	pop2_freq_style = []
	for page in data:
		for block in page:
			for line in block["lines"]:
				for span in line["spans"]:
					style = []
					style.append(span["flags"])
					style.append(span["font"])
					style.append(span["size"])
					dict_style[index] = str(style)
					index += 1
	list_style = list(dict_style.values())
	freq_style = {}	
	for items in list_style:
		freq_style[items] = list_style.count(items)
	sorted_freq_style = sorted(freq_style.items(), key = lambda kv:(kv[1], kv[0]))
	pop_freq_style = sorted_freq_style[-1][0].replace("[", "").replace("]", "").replace('"', "").replace("'", "").replace(" ", "").split(",")
	if (len(sorted_freq_style) > 1) and sorted_freq_style[-2][1] > (0.5 * sorted_freq_style[-1][1]):
		pop2_freq_style = sorted_freq_style[-2][0].replace("[", "").replace("]", "").replace('"', "").replace("'", "").replace(" ", "").split(",")
	return pop_freq_style, pop2_freq_style


# Remove figrures
def check_heading(heading_line, figures):
	heading_span = []
	del_span = []
	for line in heading_line:
		if len(line["spans"]) == 1:
			for span in line["spans"]:
				heading_span.append(span)
	for span in heading_span:		
		for figure in figures:
			if figure["type"] == "Object":
				if span["bbox"][0] > (figure["bbox"][0] - 15) and span["bbox"][1] > (figure["bbox"][1] - 15) and span["bbox"][2] < (figure["bbox"][2] + 15) and span["bbox"][3] < (figure["bbox"][3] + 15):
					del_span.append(span)
	for span in del_span:
		if span in heading_span:
			heading_span.remove(span)
	return heading_span


def get_heading_by_pop(heading_span, pop_freq_style, pop2_freq_style):
	headings = []
	if pop2_freq_style != []:
		for span in heading_span:
			if ("bold" in str(span["font"]).lower()):
				headings.append(span["text"])
			elif ("italic" in str(span["font"]).lower()):
				pass
			elif span["flags"] > float(pop_freq_style[0]) and span["flags"] > float(pop2_freq_style[0]):
				headings.append(span["text"])
			elif span["size"] > float(pop_freq_style[2]) and span["flags"] > float(pop2_freq_style[2]):
				headings.append(span["text"])
	else:
		for span in heading_span:
			if ("bold" in str(span["font"]).lower()):
				headings.append(span["text"])
			elif ("italic" in str(span["font"]).lower()):
				pass
			elif span["flags"] > float(pop_freq_style[0]):
				headings.append(span["text"])
			elif span["size"] > float(pop_freq_style[2]):
				headings.append(span["text"])
	return headings


# ======================================================================
# Main Program
# ======================================================================


def get_table_of_contents(file_path, dict_figure):
	data = read_data(file_path)
	# dict_figure = get_dict_from_api(file_path)
	pop_freq_style, pop2_freq_style = get_pop_freq_style(data)
	dict_heading = {}
	for index, page in enumerate(data):
		figures = dict_figure[str(index)]
		list_line = []
		for block in page:
			for line in block["lines"]:
				list_line.append(line)
		reading_line = get_reading_line(list_line)
		heading_line = filter_body_by_distance(reading_line)
		heading_span = check_heading(heading_line, figures)
		headings = get_heading_by_pop(heading_span, pop_freq_style, pop2_freq_style)
		for i in headings:
			item = i.replace("[", "").replace("]", "").replace("(", "").replace(")", "").replace(":", "")
			if len(item) > 3 and re.search("[a-z]", item.lower()) and not ("table" in item.lower()) and not ("figure" in item.lower()):
				dict_heading[item] = index + 1
	dict_heading_sorted = sorted(dict_heading.items(), key=lambda x: x[1])
	pprint(dict_heading_sorted)
	heading_json = json.dumps(dict_heading_sorted)
	return heading_json

def getTextInBox(page_dict, box):
	# page_dict = page.getText(output = 'dict')
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
    


def get_table_of_contents_CV(file_path, dict_figure):
	# data = read_data(file_path)
	# dict_figure = get_dict_from_api(file_path)
	doc = fitz.Document(file_path)
	# pop_freq_style, pop2_freq_style = get_pop_freq_style(data)
	acess_letter = [i for i in 'QWERTYUIOPASDFGHJKLZXCVBNM']
	acess_number = [i for i in '1234567890']
	dict_heading = {}
	for index in range(doc.pageCount):
		page = doc.loadPage(index)
		page_dict = page.getText(output = 'dict')
		figures = dict_figure[str(index)]
		list_line = []
		for block in page_dict['blocks']:
			if block['type'] == 0:
				for line in block["lines"]:
					for span in line["spans"]:
						for figure in figures:
							if figure["type"] == "Title":
								if span["bbox"][0] > (figure["bbox"][0] - 15) and span["bbox"][1] > (figure["bbox"][1] - 15) and span["bbox"][2] < (figure["bbox"][2] + 15) and span["bbox"][3] < (figure["bbox"][3] + 15):
									# dict_heading[span["text"]] = index + 1
									# text = getTextInBox(page_dict, Box(figure["bbox"]))
									dict_heading[getTextInBox(page_dict, Box(figure["bbox"]))] = index + 1
	dict_heading_sorted = sorted(dict_heading.items(), key=lambda x: x[1])
	pprint(dict_heading_sorted)
	# heading_json = json.dumps(dict_heading_sorted)
	return dict_heading_sorted


if __name__ == "__main__":
	get_table_of_contents('file-test-1/2.pdf')
	# get_table_of_contents_CV('file-test-1/2.pdf')

