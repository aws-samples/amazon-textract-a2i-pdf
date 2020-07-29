/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: MIT-0
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this
 * software and associated documentation files (the "Software"), to deal in the Software
 * without restriction, including without limitation the rights to use, copy, modify,
 * merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
 * INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
 * PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 * OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */


import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
// import com.amazonaws.services.lambda.runtime.LambdaLogger;
import java.io.*; 
import java.util.List;
import java.util.Map;
import java.util.ArrayList;
import java.lang.Integer;
import java.lang.String;
import com.google.gson.*;

public class Lambda implements RequestHandler<Map<String,String>, String[]> {

    @Override
    public String[] handleRequest(Map<String,String> event, Context ctx) {
        List<String> image_keys = new ArrayList<String>();
        try {
            String cur_id = event.get("id");
            String cur_bucket = event.get("bucket");
            String cur_key = event.get("key");

            PdfFromS3Pdf s3Pdf = new PdfFromS3Pdf();

            image_keys = s3Pdf.run(cur_id, cur_bucket, cur_key);
            
            String[] return_arr = image_keys.toArray(new String[0]);
            
            // Gson gson = new Gson();

            // return gson.toJson(image_keys);
            return return_arr;
        }
        catch (Exception e) {
            e.printStackTrace();
            System.out.println(e.getMessage());
        }
        return null;
    }
}
