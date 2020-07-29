# /*
#  * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  * SPDX-License-Identifier: MIT-0
#  *
#  * Permission is hereby granted, free of charge, to any person obtaining a copy of this
#  * software and associated documentation files (the "Software"), to deal in the Software
#  * without restriction, including without limitation the rights to use, copy, modify,
#  * merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
#  * permit persons to whom the Software is furnished to do so.
#  *
#  * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
#  * INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
#  * PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#  * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
#  * OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
#  * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#  */


import json
import boto3
import botocore
from boto3.dynamodb.conditions import Key
from gather_data import gather_and_combine_data

def write_to_s3(csv, payload, original_uplolad_key):
    client = boto3.client('s3')
    response = client.put_object(
        Body = csv,
        Bucket = payload["bucket"],
        Key = "complete/" + original_uplolad_key + "-" + payload["id"] + "/output.csv"
    )
    return response

def clear_old_s3_data(payload):
    client = boto3.client('s3')
    response = client.list_objects_v2(
        Bucket=payload["bucket"]
    )
    for item in response["Contents"]:
        if payload["id"] in item["Key"]:
            response = client.delete_object(
                Bucket=payload["bucket"],
                Key=item["Key"]
            )
    return "done"

def lambda_handler(event, context):
    # Event looks like this:
    # {
    #     "id": "",
    #     "bucket": "",
    #     "key": "",
    #     "extension": "",
    #     "image_keys": [
    #         ""
    #     ]
    # }

    #gater all of the data into a CSV
    data, payload = gather_and_combine_data(event)

    #clean up old data
    clear_old_s3_data(payload)

    #output to s3
    write_to_s3(data, payload, payload["key"].replace("/", "-"))

    return payload
