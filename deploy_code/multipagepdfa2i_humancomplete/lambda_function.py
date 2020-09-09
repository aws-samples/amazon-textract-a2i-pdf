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
from boto3.dynamodb.conditions import Key
from clean_data import create_human_kv_list
import logging
import os

def return_to_stepfunctions(payload):
    client = boto3.client('stepfunctions')
    response = client.send_task_success(
        taskToken = payload['token'],
        output = json.dumps({ 
            "includes_human": "yes",
            "output_dest": payload["final_dest"],
            "bucket": payload["bucket"],
            "id": payload["id"],
            "key": payload["key"]
        })
    )
    return response

def write_to_s3_human_response(payload):
    client = boto3.client('s3')
    response = client.put_object(
        Body = json.dumps(payload["kv_list"]),
        Bucket = payload["bucket"],
        Key = payload["final_dest"]
    )
    return response

def get_s3_data(payload):
    s3 = boto3.resource('s3')
    obj = s3.Object(payload["bucket"], payload["key"])
    body = obj.get()['Body'].read()
    return json.loads(body)

def get_token(payload):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('multia2ipdf_callback')
    response = table.query( KeyConditionExpression=Key('jobid').eq(payload["human_loop_id"]) )
    token = response['Items'][0]['callback_token']
    return token

def create_final_dest(id, key):
    prefix = key[:3].lower()
    if prefix != "wip":
        final_dest = "wip/" + id + "/0.png"
    else:
        final_dest = key
    return final_dest + "/human/output.json"

def create_payload(event):
    payload = {}
    detail = event["detail"]
    cur = detail["humanLoopOutput"]["outputS3Uri"]
    cur = cur.replace("s3://", "")
    payload["bucket"] = cur[:cur.find("/")]
    payload["key"] = cur[len(payload["bucket"])+1:]

    payload["response"] = get_s3_data(payload)
    payload["human_loop_id"] = payload["response"]["humanLoopName"]
    payload["id"] = payload["human_loop_id"][:payload["human_loop_id"].rfind("i")]
    payload["final_dest"] = create_final_dest(payload["id"], payload["response"]["inputContent"]["aiServiceRequest"]["document"]["s3Object"]["name"])
    payload["token"] = get_token(payload)
    return payload

def lambda_handler(event, context):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    try:
        logger.info("INTERNAL_LOGGING: event looks like:" + json.dumps(event, indent=3, default=str))
        logger.info("INTERNAL_LOGGING: context looks like:" + json.dumps(context, indent=3, default=str))

        if event["detail"]["humanLoopStatus"] == "Completed":
            try:
                logger.info("INTERNAL_LOGGING: Attempting create_payload(event)")   
                payload = create_payload(event)
                logger.info("INTERNAL_LOGGING: payload:" + json.dumps(payload, indent=3, default=str))
            except:
                logger.info("INTERNAL_ERROR: Failed on create_payload(event)")
                raise

            try:
                logger.info("INTERNAL_LOGGING: Attempting create_human_kv_list(payload)")   
                payload["kv_list"] = create_human_kv_list(payload)
                logger.info("INTERNAL_LOGGING: payload:" + json.dumps(payload, indent=3, default=str))
            except:
                logger.info("INTERNAL_ERROR: Failed on create_human_kv_list(payload)")
                raise

            try:
                logger.info("INTERNAL_LOGGING: Attempting  write_to_s3_human_response(payload)")   
                response = write_to_s3_human_response(payload)
                logger.info("INTERNAL_LOGGING: response:" + json.dumps(response, indent=3, default=str))
            except:
                logger.info("INTERNAL_ERROR: Failed on  write_to_s3_human_response(payload)")
                raise

            try:
                logger.info("INTERNAL_LOGGING: Attempting  return_to_stepfunctions(payload)")  
                response = return_to_stepfunctions(payload)
                logger.info("INTERNAL_LOGGING: response:" + json.dumps(response, indent=3, default=str))
            except:
                logger.info("INTERNAL_ERROR: Failed on return_to_stepfunctions(payload)")
                raise

            return "all done"
        else:
            return "dont_care"
    except:
        logger.info("INTERNAL_ERROR: Ran into an error. Check logging.")
        return "INTERNAL_ERROR: Ran into an error. Check logging."

