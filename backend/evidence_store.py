import os
from .verifier import DATA

def archive(run):
    bucket=os.getenv('EVIDENCE_BUCKET')
    if not bucket:return
    import boto3
    s3=boto3.client('s3',region_name=os.getenv('AWS_REGION','us-east-1'))
    for result in run['results']:
        for evidence in result['evidence']:
            if evidence['type']=='screenshot':
                filename=evidence['name']
                s3.upload_file(str(DATA/filename),bucket,'evidence/'+filename,ExtraArgs={'ContentType':'image/png','ServerSideEncryption':'AES256'})

def fetch(filename):
    bucket=os.getenv('EVIDENCE_BUCKET')
    if not bucket:return None
    import boto3
    s3=boto3.client('s3',region_name=os.getenv('AWS_REGION','us-east-1'))
    # Return through the role-checked API; the bucket itself remains private.
    return s3.get_object(Bucket=bucket,Key='evidence/'+filename)['Body'].read()
