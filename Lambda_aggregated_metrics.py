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
import boto3
import csv
import os

kendra = boto3.client('kendra')
s3 = boto3.client('s3')


def lambda_handler(event, context):
    
    aggregate_metrics = ['QUERIES_BY_COUNT', 'QUERIES_BY_ZERO_CLICK_RATE',
    'QUERIES_BY_ZERO_RESULT_RATE', 'DOCS_BY_CLICK_COUNT', 'AGG_QUERY_DOC_METRICS']
    
    for metric in aggregate_metrics:
        snapshot = get_kendra_analytics_snapshot(metric)
        file = write_to_csv(snapshot)
        upload_to_s3(file, metric)


def get_kendra_analytics_snapshot(metricType):
    
    index_id = os.environ['INDEX_ID']
    interval = 'ONE_MONTH_AGO'

    snapshot = kendra.get_snapshots(
        IndexId= index_id,
        Interval= interval,
        MetricType= metricType
        )
    
    header = snapshot['SnapshotsDataHeader']
    data = snapshot['SnapshotsData']
    data.insert(0, header)
    
    return data

def write_to_csv(data):
    
    tmp_file = '/tmp/snapshot.csv'
        
    with open(tmp_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(data)
    
    return tmp_file
    
def upload_to_s3(local_file, metric_name):
    
    bucket = 'kendra-analytics-bucket'
    object_name = 'snapshot_result/{}/{}.csv'.format(metric_name, metric_name)
    s3.upload_file(local_file, bucket, object_name)