# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

import json
import os
import re
import ast
import io
import csv
from time import gmtime, strftime
import boto3
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

s3 = boto3.client('s3')
sm = boto3.client('runtime.sagemaker')

S3_BUCKET = os.environ['S3_BUCKET']
SM_ENDPOINT = os.environ['SM_ENDPOINT']
S3_KEY = "metrics/QUERIES_BY_COUNT/"
S3_OBJ = "QUERIES_BY_COUNT.csv"

def handler(event, context):
    file = S3_KEY + S3_OBJ
    queries = load_s3_file(S3_BUCKET, file)
    new_queries = [[queries[0][0], queries[0][1]]]
    
    for i in range(1, len(queries)):
        res1 = get_inference({"inputs": queries[i][0]})
        is_add = True
        for lst in new_queries:
            res2 = get_inference({"inputs": lst[0]})
            similarity =  get_cos_similarity_vectors(res1, res2)
            if similarity >= 0.6:
                lst[1] += queries[i][1]
                is_add = False
                break
        if is_add:
            new_queries.append([queries[i][0], queries[i][1]])

    return upload_to_s3(new_queries)
    

def load_s3_file(bucket, key):
    response = s3.get_object(Bucket=bucket,Key=key)
    
    file = response["Body"].read()
    df = pd.read_csv(io.BytesIO(file))
    df = df[["query_content", "count"]]

    index = 0
    lst_queries = []
    for q in df["query_content"]:
        lst_queries.append([q, df.at[index, 'count']])
        index +=1
    
    return lst_queries


def get_inference(payload):
    response = sm.invoke_endpoint(EndpointName=SM_ENDPOINT,
                                      ContentType='application/json',
                                      Body=json.dumps(payload))

    sent = response['Body'].read().decode()
    sent_embedding = np.array(ast.literal_eval(sent))
    return sent_embedding


def pad_to_length(x, arraysize):
        return np.pad(x,((0, 0), (0, arraysize - x.shape[1])), mode = 'constant')
   
    
def get_cos_similarity_vectors(vec1, vec2):

    vec1_embed_np = vec1.reshape(1,-1)
    vec2_embed_np = vec2.reshape(1,-1)

    maxsize = max(i.shape[1] for i in [vec1_embed_np,vec2_embed_np])

    padded_vec1 = pad_to_length(vec1_embed_np, maxsize)
    padded_vec2 = pad_to_length(vec2_embed_np, maxsize)

    return cosine_similarity(padded_vec1,padded_vec2)[0][0]


def upload_to_s3(data):

    local_file = "/tmp/my_file.csv"
    object_name = "metrics/HF_QUERIES_BY_COUNT/HF_QUERIES_BY_COUNT.csv"

    df = pd.DataFrame(data)
    df.columns = {"query_content", "count"}
    df.to_csv(local_file, index=False, header=True)

    s3.upload_file(local_file, S3_BUCKET, object_name)    
