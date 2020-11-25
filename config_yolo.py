import numpy as np
import tensorflow as tf
import os
from shutil import copyfile

def bootstrap(image_dir, label_dir, dst_dir, probability=0.2):
    for image_file_name in os.listdir(image_dir):
        if np.random.random() < probability:
            image_file_name_without_extension = image_file_name.split('\.')[0]
            image_file = image_file_name_without_extension + '.jpg'
            label_file = image_file_name_without_extension + '.txt'
            image_path = os.join(image_dir, image_file)
            label_path = os.join(label_dir, label_file)
            dst_image_path = os.join(dst_dir, image_file)
            dst_label_path = os.join(dst_dir, label_file)
            copyfile(image_path, dst_image_path)
            copyfile(label_path, dst_label_path)

def get_dataset_for_yolo(image_dir, database_file):
    with open(database_file, 'w') as dbfile:
        for image_file in os.listdir(image_dir):
            full_path = os.path.join(image_dir, image_file)
            dbfile.write(full_path+'\n')