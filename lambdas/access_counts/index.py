"""
Lambda function that runs Athena queries over CloudTrail logs and .quilt/named_packages/
and creates summaries of object and package access events.
"""

import csv
from collections import defaultdict
import json
import os
import time
from tempfile import TemporaryFile

import boto3

# A saved query that reduces CloudTrail logs event counts per object per day.
OBJECT_ACCESS_COUNTS_QUERY_ID = os.environ['OBJECT_ACCESS_COUNTS_QUERY_ID']
# Named packages
NAMED_PACKAGES_QUERY_ID = os.environ['NAMED_PACKAGES_QUERY_ID']
# Bucket where query results will be stored.
QUERY_RESULT_BUCKET = os.environ['QUERY_RESULT_BUCKET']
# A temporary directory where Athena query results will be written.
QUERY_TEMP_DIR = os.environ['QUERY_TEMP_DIR']
# Directory where the summary files will be stored.
ACCESS_COUNTS_OUTPUT_DIR = os.environ['ACCESS_COUNTS_OUTPUT_DIR']


MAX_RESULTS = 1000


athena = boto3.client('athena')
s3 = boto3.client('s3')


def run_query(named_query_id):
    output = 's3://%s/%s/' % (QUERY_RESULT_BUCKET, QUERY_TEMP_DIR)

    query = athena.get_named_query(NamedQueryId=named_query_id)['NamedQuery']
    response = athena.start_query_execution(
        QueryString=query['QueryString'],
        QueryExecutionContext=dict(Database=query['Database']),
        ResultConfiguration=dict(OutputLocation=output)
    )
    print("Started query:", response)

    execution_id = response['QueryExecutionId']

    return execution_id


def wait_for_query(execution_id):
    while True:
        response = athena.get_query_execution(QueryExecutionId=execution_id)
        print("Query status:", response)
        state = response['QueryExecution']['Status']['State']

        if state == 'RUNNING':
            pass
        elif state == 'SUCCEEDED':
            break
        elif state == 'FAILED':
            raise Exception("Query failed! QueryExecutionId=%r" % execution_id)
        elif state == 'CANCELLED':
            raise Exception("Query cancelled! QueryExecutionId=%r" % execution_id)
        else:
            assert False, "Unexpected state: %s" % state

        time.sleep(5)


def get_query_results(execution_id):
    args = dict(
        QueryExecutionId=execution_id,
        MaxResults=MAX_RESULTS
    )

    header = True

    while True:
        response = athena.get_query_results(**args)
        for row in response['ResultSet']['Rows']:
            if header:
                # Athena returns the header before the actual results. Sigh.
                header = False
            else:
                yield [value['VarCharValue'] for value in row['Data']]

        next_token = response.get('NextToken')
        if next_token is None:
            break
        else:
            args.update(
                NextToken=next_token
            )


def write_counts_csv(fd, data, field_names):
    writer = csv.writer(fd)
    writer.writerow(field_names)
    for key, value in data.items():
        row = list(key)
        row.append(json.dumps(value))
        writer.writerow(row)


def handler(event, context):
    named_packages = defaultdict(list)  # (bucket, hash) -> [(name, version), ...]

    # (eventname, bucket, key) -> {date: count, ...}
    object_access_counts = defaultdict(lambda: defaultdict(int))

    # (eventname, bucket, package_name) -> {date: count, ...}
    package_access_counts = defaultdict(lambda: defaultdict(int))

    # (eventname, bucket, package_name, package_version, package_hash) -> {date: count, ...}
    package_version_access_counts = defaultdict(lambda: defaultdict(int))

    named_packages_execution_id = run_query(NAMED_PACKAGES_QUERY_ID)
    access_counts_execution_id = run_query(OBJECT_ACCESS_COUNTS_QUERY_ID)

    named_packages_key = '%s/%s.csv' % (QUERY_TEMP_DIR, named_packages_execution_id)
    access_counts_key = '%s/%s.csv' % (QUERY_TEMP_DIR, access_counts_execution_id)

    wait_for_query(named_packages_execution_id)

    for bucket, name, version, hash in get_query_results(named_packages_execution_id):
        named_packages[(bucket, hash)].append((name, version))

    wait_for_query(access_counts_execution_id)

    for eventname, date, bucket, key, count_str in get_query_results(access_counts_execution_id):
        count = int(count_str)

        object_access_counts[(eventname, bucket, key)][date] += count

        parts = key.split('/')
        if len(parts) == 3 and parts[0] == '.quilt' and parts[1] == 'packages':
            package_hash = parts[2]
            for package_name, package_version in named_packages.get((bucket, package_hash), []):
                package_access_counts[(eventname, bucket, package_name)][date] += count
                package_version_access_counts[(eventname, bucket, package_name, package_version, package_hash)][date] += count

    for key in [named_packages_key, access_counts_key]:
        s3.delete_object(Bucket=QUERY_RESULT_BUCKET, Key=key)
        s3.delete_object(Bucket=QUERY_RESULT_BUCKET, Key=key + '.metadata')

    outputs = [
        ('Objects.csv', object_access_counts, ['eventname', 'bucket', 'key', 'counts']),
        ('Packages.csv', package_access_counts, ['eventname', 'bucket', 'name', 'counts']),
        ('PackageVersions.csv', package_version_access_counts, ['eventname', 'bucket', 'name', 'version', 'hash', 'counts']),
    ]

    for name, data, header in outputs:
        with TemporaryFile('w+') as file_obj:
            write_counts_csv(file_obj, data, header)
            file_obj.seek(0)
            s3.put_object(
                Body=file_obj.buffer.raw,
                Bucket=QUERY_RESULT_BUCKET,
                Key=ACCESS_COUNTS_OUTPUT_DIR + '/' + name,
                ContentType='text/plain'
            )
