# # /*
# #  * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# #  * SPDX-License-Identifier: MIT-0
# #  *
# #  * Permission is hereby granted, free of charge, to any person obtaining a copy of this
# #  * software and associated documentation files (the "Software"), to deal in the Software
# #  * without restriction, including without limitation the rights to use, copy, modify,
# #  * merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# #  * permit persons to whom the Software is furnished to do so.
# #  *
# #  * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# #  * INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# #  * PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# #  * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# #  * OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# #  * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# #  */

import json

def get_child(relation, line, word):
    text = ""
    for id in relation["ids"]:
        if id in line:
            text = line[id]
        else:
            text += " " + word[id]
    if text[0] == " ":
        text = text[1:]
    return text

def extract_value(value, kv, line, word):
    for val in value:
        try:
            text = ""
            for relation in kv[val]["relationships"]:
                if relation["type"] == "CHILD":
                    text = get_child(relation, line, word)
            return text
        except:
            return "UNKNOWN"

def line_up_ids(kv, line, word):
    kv_list = []
    master_values = []
    for cur in kv:
        if kv[cur]["entityTypes"][0] == "KEY":
            value = []
            text = ""
            for relation in kv[cur]["relationships"]:
                if relation["type"] == "VALUE":
                    for id in relation["ids"]:
                        value.append(id)
                if relation["type"] == "CHILD":
                    text = get_child(relation, line, word)
            kv_list.append({
                "value": extract_value(value, kv, line, word),
                "key": text               
            })
    return kv_list

def get_key_value_set(data):
    dict_key_value = {}
    for block in data["blocks"]:
        if block["blockType"] == "KEY_VALUE_SET" and "relationships" in block:
            dict_key_value[block["id"]] = {
                "relationships": block["relationships"],
                "entityTypes": block["entityTypes"]
            }
    return dict_key_value

def get_word_and_line(data):
    dict_word = {}
    dict_line = {}
    for block in data["blocks"]:
        if block["blockType"] == "WORD":
            dict_word[block["id"]] = block["text"]
        if block["blockType"] == "LINE":
            dict_line[block["id"]] = block["text"]
    return dict_word, dict_line

def create_human_kv_list(payload):
    data = payload["response"]["humanAnswers"][0]["answerContent"]["AWS/Textract/AnalyzeDocument/Forms/V1"]
    dict_word, dict_line = get_word_and_line(data)
    dict_key_value = get_key_value_set(data)
    kv_list = line_up_ids(dict_key_value, dict_line, dict_word)
    return kv_list
