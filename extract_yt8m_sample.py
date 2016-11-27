import pafy
import json
import requests
import re
import numpy as np
import pandas as pd
import csv 
import urllib
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
from itertools import repeat
import pyes # For documentation around pyes.es : https://pyes.readthedocs.org/en/latest/references/pyes.es.html
import json

#Set API Key
pafy.set_api_key("AIzaSyCnrbLP8V3zdMwG9kaTaCmeq49nNqyEpZ8")

#Download the vocabulary list from the site.
urllib.URLopener().retrieve("http://research.google.com/youtube8m/csv/train-labels-histogram.csv" , "knowledgeGraphList.csv")

#Save only the GraphID with its corresponding LabelName
df1 = pd.read_csv('knowledgeGraphList.csv')
KgraphID = df1[['KnowledgeGraphID','LabelName','FirstVertical','SecondVertical','ThirdVertical']]
series = KgraphID["KnowledgeGraphID"]
series = series.str.replace('/m/','') #Remove '/m/'

#Extract video ID and keywords and make it into a table
series_sample = series[4796:4799]
KgraphIDList_sample = series_sample
total_list = []
total_k = []
empty_frames = []

#Iterate each k-graph entities to get all video IDs
for k in KgraphIDList_sample:
    call_kg_page = requests.get("http://storage.googleapis.com/www.yt8m.org/csv/j/%s.js" % k)
    to_string = str(call_kg_page.text)
    n = to_string.count(";")
    to_list = to_string.split(";", n-1)
    list_filter = [list_filter for list_filter in to_list if len(list_filter) == 11] #Filter out unwanted elements
    total_list.append(list_filter)
    total_list_unnested = sum(total_list, [])
    total_k = list(repeat(k,len(total_list_unnested)))
    subdt1 = pd.DataFrame({
            'vID': total_list_unnested,
            'key': total_k})
    empty_frames.append(subdt1)

#Concatenate all dataFrames
result = pd.concat(empty_frames)

#Turn result into list format "resultList"
resultList = result["vID"].tolist()

#Now insert video ID into youtube API to extract metadata
videoo = resultList
video = videoo
    
vid_ID = []
title = []
thumbnail = []
try:
    for v in video:
        vid_url = "https://www.youtube.com/watch?v=%s" % v
        vid = pafy.new(vid_url)
        title.append(vid.title)
        thumbnail.append(vid.thumb)
        vid_ID.append(v)
except Exception:
    pass
  
t = pd.DataFrame(
    {
    'vID': vid_ID,
    'title': title,
    'thumbnail': thumbnail})

#Merge with result DataFrame on vID
t.merge(result,on='vID',how ='left')


### Push data into Elasticsearch

# Add index to t.
t["index_col"] = range(1,len(t)+1)

# Convert a panda's dataframe to json
tmp = t.reset_index().to_json(orient="records")
#print df

# Load dach record into jon format before bulk
tmp_json = json.loads(tmp)
#print tmp_json[1]

# Create an index into elastic search. if we need to create mapping, we do it here.
index_name = 'yt-8m_to_elastic'
type_name = 'pyelastic'
es = pyes.ES()

# Bulk index
for doc in tmp_json:
    es.index(doc, index_name, type_name, id = doc['index_col'])
