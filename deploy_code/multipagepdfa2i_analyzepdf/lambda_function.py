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
import os
from clean_data import extract_data

def invoke_to_get_back_to_stepfunction(event):
    client = boto3.client('stepfunctions')
    response = client.send_task_success(
        taskToken = event['token'],
        output = json.dumps({"all": "done"})
    )
    return response

def dump_task_token_in_dynamodb(event):
    dynamodb = boto3.client('dynamodb')
    response = dynamodb.put_item(
        TableName='multia2ipdf_callback',
        Item={
            'jobid': {'S': event["human_loop_id"]},
            'callback_token': {'S': event["token"]}
        }
    )
    return response

def write_ai_response_to_bucket(event, data):
    client = boto3.client('s3')
    response = client.put_object(
        Body = json.dumps(data),
        Bucket = event["bucket"],
        Key = event["s3_location"]
    )
    return response

def run_analyze_document(event):
    client = boto3.client('textract')
    response = client.analyze_document(
        Document={
            'S3Object': {
                'Bucket': event["bucket"],
                'Name': event["key"]
            }
        },
        FeatureTypes=['FORMS'],
        HumanLoopConfig={
            'HumanLoopName': event["human_loop_id"],
            'FlowDefinitionArn': event["SAGEMAKER_WORKFLOW_AUGMENTED_AI_ARN"],
            'DataAttributes': {
                'ContentClassifiers': [
                    'FreeOfPersonallyIdentifiableInformation',
                    'FreeOfAdultContent'
                ]
            }
        }
    )
    need_to_human_review = False
    if len(response["HumanLoopActivationOutput"]["HumanLoopActivationReasons"]) != 0:
        need_to_human_review = True
    return response, need_to_human_review


def create_png_file(body):
    s3 = boto3.resource('s3')

    try:
        s3.Object(body["bucket"], body["key"]).load()
    except botocore.exceptions.ClientError as e:
        client = boto3.client('lambda')
        image_keys = client.invoke(
            FunctionName='multipagepdfa2i_pngextract',
            Payload=json.dumps({
                "bucket": body["bucket"],
                "original_upload_pdf": body["original_upload_pdf"],
                "id": body["id"],
                "cur_page_number": body["key"][body["key"].rfind("/")+1:-4]
            })
        )
        return "created_new_png"
    else:
        return "already_there"

    

    
def lambda_handler(event, context):

    for record in event["Records"]:
        
        body = json.loads(record["body"])
        body["human_loop_id"] = body["id"] + "i" + (body["key"][body["key"].rfind("/")+1:-4]).replace("_","")
        
        create_png_file(body)

        response, need_to_human_review = run_analyze_document(body)
        kv_list = extract_data(response)

        body["s3_location"] = body["key"] + "/ai/output.json"
        s3_response = write_ai_response_to_bucket(body, kv_list)

        if need_to_human_review is True:
            response = dump_task_token_in_dynamodb(body)
        if need_to_human_review is False:
            response = invoke_to_get_back_to_stepfunction(body)
        
        client = boto3.client('sqs')
        response = client.delete_message(
            QueueUrl=os.environ['sqs_url'],
            ReceiptHandle=record["receiptHandle"]
        )

    return "all_done"
