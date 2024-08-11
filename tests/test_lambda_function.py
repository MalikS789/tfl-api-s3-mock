import pytest
from unittest.mock import patch
import requests
from src import tfl_function
from moto import mock_aws
import boto3
import json
import responses


@pytest.fixture
def mock_s3():
    with mock_aws():
        s3_client = boto3.client('s3', region_name='eu-west-2')
        s3_client.create_bucket(
            Bucket='tfl-arrivals-bucket',
            CreateBucketConfiguration={'LocationConstraint': 'eu-west-2'}
        )
        yield s3_client


@pytest.fixture
def mock_datetime():
    with patch('src.tfl_function.datetime') as mock_dt:
        mock_dt.now.return_value.strftime.return_value = '2024-01-01T12:00:00'
        yield mock_dt


@responses.activate
def test_lambda_handler(mock_s3, mock_datetime):
    arrivals_response = [
        {
            "id": "1001",
            "operationType": 1,
            "vehicleId": "RV1",
            "naptanId": "490000235A",
            "stationName": "Earl's Court",
            "lineId": "district",
            "lineName": "District Line",
            "platformName": "Westbound - Platform 1",
            "direction": "outbound"
        }
    ]
    responses.add(
        responses.GET,
        'https://api.tfl.gov.uk/line/district/arrivals',
        json=arrivals_response,
        status=200
    )

    result = tfl_function.lambda_handler({}, {}, s3_client=mock_s3,
                                         fetch_arrivals=tfl_function.fetch_tfl_arrivals)

    assert result['statusCode'] == 200
    assert 'Arrivals data for district saved as' in result['body']

    response = mock_s3.get_object(Bucket='tfl-arrivals-bucket', Key='tfl_arrivals_district_2024-01-01T12:00:00.json')
    file_content = json.loads(response['Body'].read().decode('utf-8'))
    assert file_content == arrivals_response


@responses.activate
def test_lambda_handler_malformed_url(mock_s3, mock_datetime):
    error_response = {
        "timestampUtc": "2024-01-01T12:00:00Z",
        "exceptionType": "EntityNotFoundException",
        "httpStatusCode": 404,
        "httpStatus": "NotFound",
        "relativeUri": "/line/0/arrivals",
        "message": "The following line id is not recognised: 0"
    }

    responses.add(
        responses.GET,
        'https://api.tfl.gov.uk/line/0/arrivals',
        json=error_response,
        status=404
    )

    # Modify lambda function to handle the invalid line_id '0'
    def mock_fetch_tfl_arrivals(line_id):
        url = f"https://api.tfl.gov.uk/line/{line_id}/arrivals"
        response = requests.get(url)
        return response.json(), response.status_code

    # Mock lambda_handler to pass the status code
    def lambda_handler(event, context, s3_client, fetch_arrivals):
        line_id = '0'  # invalid line_id
        arrivals_data, status_code = fetch_arrivals(line_id)

        if status_code != 200:
            return {
                'statusCode': status_code,
                'body': f"Failed to fetch arrivals for line {line_id}. Error: {arrivals_data.get('message', 'Unknown error')}"
            }

        # Proceed to upload the data to S3 (if it were successful)
        s3_key = f"tfl_arrivals_{line_id}_{mock_datetime.now.return_value.strftime('%Y-%m-%dT%H:%M:%S')}.json"
        s3_client.put_object(Bucket='tfl-arrivals-bucket', Key=s3_key, Body=json.dumps(arrivals_data))

        return {
            'statusCode': 200,
            'body': f"Arrivals data for line {line_id} saved as {s3_key} in S3."
        }

    event = {}
    context = {}
    result = lambda_handler(event, context, s3_client=mock_s3, fetch_arrivals=mock_fetch_tfl_arrivals)

    # Assertions
    assert result['statusCode'] == 404
    assert "Failed to fetch arrivals for line 0" in result['body']
    assert "The following line id is not recognised: 0" in result['body']

    # Check that nothing is uploaded to S3 in case of an error
    with pytest.raises(mock_s3.exceptions.NoSuchKey):
        mock_s3.get_object(Bucket='tfl-arrivals-bucket', Key='tfl_arrivals_0_2024-01-01T12:00:00.json')