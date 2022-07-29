import json
import urllib.request
import logging
from collections import OrderedDict
import os
import datetime
import calendar
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Maximum number of log data to be extracted
OUTPUT_LIMIT=5
# How many minutes before the extraction target period
TIME_FROM_MIN=5

def lambda_handler(event, context):

    logger.info("Event: " + str(event))
    message = json.loads(event['Records'][0]['Sns']['Message'])

    logs = boto3.client('logs')

    # Get metric filter information using MetricName and Namespace as keys.
    metricfilters = logs.describe_metric_filters(
        metricName = message['Trigger']['MetricName'] ,
        metricNamespace = message['Trigger']['Namespace']
    )

    logger.info("Metricfilters: " + str(metricfilters))
    # Convert log stream extraction target time to UNIX time (acquisition period is TIME_FROM_MIN minutes or later)
    # The end time is 1 minute after the alarm occurs
    timeto = datetime.datetime.strptime(message['StateChangeTime'][:19] ,'%Y-%m-%dT%H:%M:%S') + datetime.timedelta(minutes=1)
    u_to = calendar.timegm(timeto.utctimetuple()) * 1000
    # The start time is TIME_FROM_MIN minutes before the end time
    timefrom = timeto - datetime.timedelta(minutes=TIME_FROM_MIN)
    u_from = calendar.timegm(timefrom.utctimetuple()) * 1000

    # Get log data from log stream
    response = logs.filter_log_events(
        logGroupName = metricfilters['metricFilters'][0]['logGroupName'] ,
        filterPattern = metricfilters['metricFilters'][0]['filterPattern'],
        startTime = u_from,
        endTime = u_to,
        limit = OUTPUT_LIMIT
    )

    # Format messages and notify slack
    for event in response['events']:
        postText = '''
        *・Log Stream Name*
        `{logStreamName}`
        ```{message}```
        '''.format( logStreamName=str(event['logStreamName']),
                    message=str(event['message'])).strip()

        logger.info("Response: " + str(response))

        send_data = {
            "text": postText,
        }

        send_text = json.dumps(send_data)

        request = urllib.request.Request(
            os.environ['SLACK_URL'],
            data=send_text.encode('utf-8'), 
            method="POST"
        )

        with urllib.request.urlopen(request) as response:

            response_body = response.read().decode('utf-8')
