import os
import io
import boto3
import json
import csv

# grab environment variables
ENDPOINT_NAME = os.environ['ENDPOINT_NAME']
runtime= boto3.client('runtime.sagemaker')

def lambda_handler(event, context):

    # preprocessing
    term = event['term'].lower().replace(' ', '_')
    
    query = {}
    query['topn'] = event['topn']
    query['positive'] = [term]
    query['negative'] = []
    
    for vector in event['vectors']:
        term = vector['term'].lower().replace(' ', '_')
        if vector['positive']:
            query['positive'].append(term)
        else:
            query['negative'].append(term)
    
    payload = json.dumps(query).encode('utf-8')

    # query AWS SageMaker endpoint 
    response = runtime.invoke_endpoint(EndpointName=ENDPOINT_NAME,
                                       ContentType='application/json',
                                       Body=payload)
                                       
    results = json.loads(response['Body'].read().decode())
    
    # postprocessing
    results['query'] = event['term']
    for vector in event['vectors']:
        if vector['positive']:
            results['query'] += ' + ' + vector['term']
        else:
            results['query'] += ' - ' + vector['term']
            
    for result in results['results']:
        result['term'] = result['term'].replace('_-_', '-').replace('_', ' ')
    
    return results