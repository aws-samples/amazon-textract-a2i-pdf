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
import uuid
import os
from urllib.parse import unquote, unquote_plus

# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------
# ~ ENTER SAGEMAKER AUGMENTED AI WORKFLOW ARN HERE:
SAGEMAKER_WORKFLOW_AUGMENTED_AI_ARN = os.environ['human_workflow_arn']

# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------

def create_image_keys(data, num_keys):
    keys = []
    for num in range(num_keys):
        keys.append("wip/" + data["id"] + "/" + str(num) + ".png")
    return keys

def upload_id_to_dynamo_db(cur_id, key):
    dynamodb = boto3.client('dynamodb')
    response = dynamodb.put_item(
        TableName='multipagepdfa2i_upload_ids',
        Item={
            'id': {'S': cur_id},
            'key': {'S': key}
        }
    )
    return response

def get_stepfunction_arn(new_token):
    client = boto3.client('stepfunctions')
    if new_token == "meh":
        response = client.list_state_machines(
            maxResults=100
        )
    else:
        response = client.list_state_machines(
            maxResults=100,
            token=new_token
        )
    for machine in response["stateMachines"]:
        if machine["name"] == "multipagepdfa2i_fancy_stepfunction":
            return machine["stateMachineArn"]
    if "nextToken" in response:
        return get_stepfunction_arn(response["newToken"])
    else:
        return "stepfunction_doesnt_exsist"

def start_step_function(payload):
    client = boto3.client('stepfunctions')
    response = client.start_execution(
        stateMachineArn=get_stepfunction_arn("meh"),
        name = payload["id"],
        input = json.dumps(payload, indent=3, default=str),
    )
    return response

def run_pdfbox(data):
    client = boto3.client('lambda')
    image_keys = client.invoke(
        FunctionName='multipagepdfa2i_pngextract',
        Payload=json.dumps({
            "bucket": data["bucket"],
            "original_upload_pdf": data["key"],
            "id": data["id"],
            "cur_page_number": "0"
        })
    )
    return image_keys

def extract_event_data(event):
    s3 = event["Records"][0]["s3"]
    
    id = uuid.uuid4().hex
    bucket = s3["bucket"]["name"]
    key = unquote_plus(unquote(s3["object"]["key"]))
    pdf_name = key[key.rfind("/")+1:key.rfind(".")]
    
    data = {
        "id": id,
        "bucket": bucket,
        "key": key,
        "pdf_name": pdf_name
    }
    
    return data

def lambda_handler(event, context):
    data = extract_event_data(event)
    obj = run_pdfbox(data)["Payload"].read().decode('utf-8')
    num_keys = int(obj.replace("\"", ""))
    if num_keys == 0:
        return 0
    else:
        data["image_keys"] = create_image_keys(data, num_keys)
        payload = {
            "id": data["id"],
            "bucket": data["bucket"],
            "num_files": len(data["image_keys"]),
            "image_keys": data["image_keys"],
            "SAGEMAKER_WORKFLOW_AUGMENTED_AI_ARN": SAGEMAKER_WORKFLOW_AUGMENTED_AI_ARN,
            "original_upload_pdf": data["key"]
        }
        yeah = upload_id_to_dynamo_db(data["id"], data["key"])
        response = start_step_function(payload)

    return json.dumps(payload, indent=3, default=str)

