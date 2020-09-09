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
import logging
from urllib.parse import unquote, unquote_plus

def start_step_function(payload):
    client = boto3.client('stepfunctions')
    response = client.start_execution(
        stateMachineArn=os.environ['state_machine_arn'],
        name = payload["id"],
        input = json.dumps(payload, indent=3, default=str),
    )
    return response

def extract_event_data(record):
    s3 = record["s3"]
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
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    try:
        logger.info("INTERNAL_LOGGING: event looks like:" + json.dumps(event, indent=3, default=str))
        logger.info("INTERNAL_LOGGING: context looks like:" + json.dumps(context, indent=3, default=str))

        # this is the sqs payload
        for record in event["Records"]:
            # these are the s3 payload
            for cur_record in json.loads(record["body"])["Records"]:
                logger.info("INTERNAL_LOGGING: here is cur_record from s3 payload:" + json.dumps(cur_record, indent=3, default=str))
                try:
                    # attempting to extract data from cur_record
                    try:
                        data = extract_event_data(cur_record)
                        logger.info("INTERNAL_LOGGING: here is data from extract_event_data:" + json.dumps(data, indent=3, default=str))
                    except:
                        logger.info("INTERNAL_ERROR: Ran into an error with extract_event_data")
                        raise

                        

                    # if the uploaded file has the right extension try to start the step functions
                    extension = data["key"][-3:].lower()
                    if extension == "pdf" or extension == "png" or extension == "jpg":
                        payload = {
                            "id": data["id"],
                            "bucket": data["bucket"],
                            "key": data["key"],
                            "extension": extension
                        }
                        response = start_step_function(payload)
                    try:
                        # delete message from sqs
                        client = boto3.client('sqs')
                        response = client.delete_message(
                            QueueUrl=os.environ['sqs_url'],
                            ReceiptHandle=record["receiptHandle"]
                        )
                    except:
                        logger.info("INTERNAL_ERROR: run into a problem deleting the message from sqs")
                        raise
                except:
                    logger.info("INTERNAL_ERROR: Ran into an error. Check logging.")


        logger.info("INTERNAL_LOGGING_COMPELTE: Didn't run into any errors :)")
        return "INTERNAL_LOGGING_COMPELTE: Didn't run into any errors :)"
    except:
        logger.info("INTERNAL_ERROR: Ran into an error. Check logging.")
        return 0
