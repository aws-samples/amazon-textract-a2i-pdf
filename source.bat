REM /*
REM  * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
REM  * SPDX-License-Identifier: MIT-0
REM  *
REM  * Permission is hereby granted, free of charge, to any person obtaining a copy of this
REM  * software and associated documentation files (the "Software"), to deal in the Software
REM  * without restriction, including without limitation the rights to use, copy, modify,
REM  * merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
REM  * permit persons to whom the Software is furnished to do so.
REM  *
REM  * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
REM  * INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
REM  * PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
REM  * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
REM  * OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
REM  * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
REM  */


@echo off

rem The sole purpose of this script is to make the command
rem
rem     source .env/bin/activate
rem
rem (which activates a Python virtualenv on Linux or Mac OS X) work on Windows.
rem On Windows, this command just runs this batch file (the argument is ignored).
rem
rem Now we don't need to document a Windows command for activating a virtualenv.

echo Executing .env\Scripts\activate.bat for you
.env\Scripts\activate.bat
