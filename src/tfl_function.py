import json

import boto3
import requests
from datetime import datetime


def fetch_tfl_arrivals(line_id: str):
    """
    For a given trainline, return a JSON-string response from the TFL API.
    """
    url = f"https://api.tfl.gov.uk/line/{line_id}/arrivals"
    response = requests.get(url)
    return response.json()


def upload_to_s3(bucket_name: str, file_name: str, data: json, s3_client):
    """
        Helper function that uploads a file to an S3 bucket.

        Parameters:
       ----------
        bucket_name : name of the S3 bucket to upload to.
        file_name : the name to assign to the file to be saved in the S3 bucket.
        data: python object to store on S3.
        s3_client : s3_client object.
    """
    s3_client.put_object(
        Bucket=bucket_name,
        Key=file_name,
        Body=json.dumps(data),
        ContentType='application/json'
    )


def lambda_handler(event: dict, context: object, s3_client=None, fetch_arrivals=None):
    """
       AWS Lambda handler function to fetch arrivals data for a specified TfL line and upload it to an S3 bucket.

       Parameters:
       ----------
       event : The event triggering the Lambda function. This parameter carries the event data from an S3 event,
           API Gateway request or other AWS services.
       context : The runtime information provided by AWS Lambda. This can be used for logging, setting timeouts,
        or accessing metadata about the function's execution.
       s3_client (optional) : A boto3.client object used to interact with Amazon S3.
       fetch_arrivals (optional) : Lambda function to inject. If not provided, the `fetch_tfl_arrivals` function is
       used by default.

       Returns:
       -------
           A dictionary containing the HTTP status code and a message.
       """
    if s3_client is None:
        s3_client = boto3.client('s3', region_name='eu-west-2')
    if fetch_arrivals is None:
        fetch_arrivals = fetch_tfl_arrivals

    line_id = 'district'
    bucket_name = 'tfl-arrivals-bucket'

    arrivals_data = fetch_arrivals(line_id)

    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    file_name = f'tfl_arrivals_{line_id}_{timestamp}.json'

    upload_to_s3(bucket_name, file_name, arrivals_data, s3_client)

    return {
        'statusCode': 200,
        'body': f'Arrivals data for {line_id} saved as {file_name}'
    }
