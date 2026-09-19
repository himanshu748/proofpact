"""Upload an explicit source allowlist and start the existing ProofPact build."""
from pathlib import Path
import json
import zipfile
import boto3
from modal.config import config

root = Path(__file__).resolve().parents[1]
archive = root / 'output' / 'deployment' / 'proofpact.zip'
archive.parent.mkdir(parents=True, exist_ok=True)
files = [root / name for name in ('Dockerfile', '.dockerignore', 'package.json', 'package-lock.json', 'tsconfig.json', 'next.config.ts')]
for folder in ('app', 'components', 'lib', 'backend', 'infra'):
    files.extend(p for p in (root / folder).rglob('*') if p.is_file() and not any(part in ('__pycache__', 'data', 'tests') for part in p.relative_to(root).parts) and p.suffix != '.pyc')
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
    for path in files:
        assert not path.is_symlink()
        z.write(path, path.relative_to(root))

session = boto3.Session(region_name='us-east-1')
stack = session.client('cloudformation').describe_stacks(StackName='proofpact')['Stacks'][0]
outputs = {o['OutputKey']: o['OutputValue'] for o in stack['Outputs']}
secret_client = session.client('secretsmanager')
try:
    secret = secret_client.describe_secret(SecretId='proofpact/modal')['ARN']
except secret_client.exceptions.ResourceNotFoundException:
    credentials = {'token_id': config.get('token_id'), 'token_secret': config.get('token_secret')}
    assert all(credentials.values()), 'Modal credentials are unavailable.'
    secret = secret_client.create_secret(Name='proofpact/modal', SecretString=json.dumps(credentials), Tags=[{'Key': 'Project', 'Value': 'ProofPact'}])['ARN']
session.client('s3').upload_file(str(archive), outputs['Bucket'], 'source/proofpact.zip', ExtraArgs={'ServerSideEncryption': 'AES256'})
build = session.client('codebuild').start_build(projectName='proofpact')['build']
record = {'build_id': build['id'], 'secret_arn': secret, **outputs}
(archive.parent / 'build.json').write_text(json.dumps(record, indent=2))
print(json.dumps({'build_id': build['id'], 'source_files': len(files), 'source_bytes': archive.stat().st_size}))
