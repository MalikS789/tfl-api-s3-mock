# TfL Arrivals Data Lambda

## Overview

This project contains an AWS Lambda function that fetches live arrivals data from the Transport for London (TfL) API 
for a specified London Underground line. The function stores the retrieved data in an S3 bucket, enabling you to archive
and analyze the transport data.

## Features

Fetch Live Data: The function fetches arrival information for a specified London Underground line using the TfL API.
Storage in S3: Upon successful retrieval, the data is stored in an S3 bucket with a unique key based on the line ID and timestamp.