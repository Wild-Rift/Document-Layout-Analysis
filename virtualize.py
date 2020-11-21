import streamlit as st 
import cv2
import numpy as np
import matplotlib.pyplot as plt 
from main import App
import json 
import os
import uuid
import re
import fitz
import shutil
# st.set_option('deprecation.showfileUploaderEncoding', False)
st.sidebar.markdown("""<img style=' align:center;  display: block;margin-left: auto;margin-right: auto;width: 75%;' src="https://vinbigdata.org/storage/logothumb.jpg">""",unsafe_allow_html=True)
# st.sidebar.markdown("""<style>body {background-color: #2C3454;color:white;}</style><body></body>""", unsafe_allow_html=True)

st.sidebar.markdown("<h1 style='text-align: center;color: #2C3454;margin-top:30px;margin-bottom:-20px;'>Select File</h1>", unsafe_allow_html=True)

pdf_file = st.sidebar.file_uploader("", type=["pdf"])


def save_file(file_p, stringio):
    with open (file_p, 'wb') as fd:
        stringio.seek(0)
        shutil.copyfileobj(stringio, fd)
        
@st.cache(allow_output_mutation=True)
def predict(pdf_p):
    return App.detectAll(pdf_p = pdf_p)
    
# session_id = uuid.uuid1()

if pdf_file is not None:
    with open('log.json', 'r') as f:
        log = json.load(f)
    if len(log.keys()) == 0 or log['file_name'] != pdf_file.name:
        logs = {
            'file_name' : '',
            'data' : None,
            'toc' : None
        }
        logs['file_name'] = pdf_file.name
        App = App()
        session_id = uuid.uuid1()
        file_p = os.path.join('/home/buithoai/Desktop/VBDI/Fig_Tab_Caption-Detection/UPLOAD', str(session_id) + '.pdf')
        save_file(file_p, pdf_file)
        data, toc = predict(file_p)
        logs['data'] = data 
        logs['toc'] = toc
        with open('log.json', 'w') as l:
            json.dump(logs, l)
    else:
        data = log['data']
        toc = log['toc']
    colors = {
        'Title' : [255, 0, 0], 
        'Table' : [0, 0, 255],
        'Figure' : [0, 255, 0], 
        'Text' : [209, 185, 55]
    }
    # data = json.load(open('sample.json', 'r'))
    st.sidebar.markdown('Select visualize')
    page = ['Page_' + str(i) for i in range(len(data))]
    page_index = st.sidebar.selectbox("Select Page to Visualize", page)
    list_select_label = st.sidebar.multiselect("List Labels show:", ['Title', 'Table', 'Figure', 'Text'])
    types_output = ['Json', 'Table']
    radio = st.sidebar.radio("Select output type: ", ['Json', 'TOC'])
    
    if radio == 'Json':
        col_1, col_2 = st.beta_columns(2)
        idx = int(page_index.split('_')[-1])
        st.header("Output Json:")
        json_result = {
            "detected" : [],
            "num_page" : data[idx]['num_page'], 
            "height" : data[idx]['height'],
            'width' : data[idx]['width']
        }
        for d in data[idx]['detected']:
            if d['type'] in list_select_label:
                json_result['detected'].append(d)
        with col_1:
            st.json(json_result)
        with col_2:
            im = cv2.imread(os.path.join('IMAGE', str(idx) + '.png'))
            # print(im.shape)
            for obj in json_result['detected']:
                bbox = [int(i) for i in obj['bbox']]
                im = cv2.rectangle(im, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color = colors[obj['type']], thickness = 1)
                if obj['type'] in ['Figure', 'Table']:
                    bbox_cap = [int(i) for i in obj['bbox_caption']]
                    im = cv2.rectangle(im, (bbox_cap[0], bbox_cap[1]), (bbox_cap[2], bbox_cap[3]), color = colors[obj['type']], thickness = 1)
            st.image(im)
            
    else:
        col_1, col_2 = st.beta_columns([20, 0.5])
        # toc = [
        #     ["Bilinear Attention Networks", 1],
        #     ["Abstract", 1],
        #     ["1Introduction", 1],
        #     ["2Low-rank bilinear pooling", 2],
        #     ["3Bilinear attention networks", 3],
        #     ["4Related works", 4],
        #     ["5Experiments", 4],
        #     ["5.1Datasets", 4],
        #     ["5.2Preprocessing", 4],
        #     ["5.4Hyperparameters and regularization", 5],
        #     ["6VQA results and discussions", 5],
        #     ["6.1Quantitative results", 5],
        #     ["6.2Residual learning of attention", 6],
        #     ["6.3Qualitative analysis", 7],
        #     ["7Flickr30k entities results and discussions", 7],
        #     ["8Conclusions", 8],
        #     ["Acknowledgments", 9],
        #     ["References", 9],
        #     ["Bilinear Attention Networks \u2014 Appendix", 12],
        #     ["AVariants of BAN", 12],
        #     ["A.1Enhancing glove word embedding", 12],
        #     ["A.2Integrating counting module", 12],
        #     ["A.3Integrating multimodal factorized bilinear (MFB) pooling", 13],
        # ]
        for t in toc:
            text, idx = t
            s = re.sub(r'([0-9])([A-Z])',r'\1. \2', text)
            s = re.sub(r'([A-Z])([A-Z][a-z])', r'\1. \2', s)
            num_tab = len(re.findall(r'([\d\w]((\.)\d)+)', s))
            print(num_tab)
            with col_1:
                st.header(''.join('\t' for i in range(num_tab)) + s)
            with col_2:
                st.header(str(idx))
            
    