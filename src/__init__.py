import os
import yaml

path_pro = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open('./config.yml', 'r') as file:
	config = yaml.safe_load(file)


if not os.path.isdir(os.path.join(path_pro, config['dir']['output'])):
    os.mkdir(os.path.join(path_pro, config['dir']['output']))

if not os.path.isdir(os.path.join(path_pro, config['dir']['image'])):
    os.mkdir(os.path.join(path_pro, config['dir']['image']))

if not os.path.isdir(os.path.join(path_pro, config['dir']['upload'])):
    os.mkdir(os.path.join(path_pro, config['dir']['upload']))
