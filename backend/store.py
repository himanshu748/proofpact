"""Versioned records. Private briefs and sessions never share public project records."""
import json
import os
import sqlite3
from pathlib import Path

class Conflict(Exception):
    pass

class Store:
    def __init__(self, path=None):
        self.path = str(path or os.getenv('DATABASE_PATH', 'backend/data/proofpact.sqlite3'))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS records (key TEXT PRIMARY KEY, version INTEGER NOT NULL, data TEXT NOT NULL)')
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=20)
        conn.execute('PRAGMA journal_mode=WAL')
        return conn
    def get(self, key):
        with self.connect() as conn:
            row = conn.execute('SELECT version,data FROM records WHERE key=?',(key,)).fetchone()
        return ({**json.loads(row[1]), '_rev':row[0]} if row else None)
    def put(self, key, value):
        value = dict(value)
        rev = value.pop('_rev', 0)
        with self.connect() as conn:
            if rev:
                cursor = conn.execute('UPDATE records SET data=?,version=? WHERE key=? AND version=?',(json.dumps(value),rev+1,key,rev))
                if cursor.rowcount != 1: raise Conflict('Record changed. Refresh and retry.')
            else:
                try: conn.execute('INSERT INTO records VALUES (?,?,?)',(key,1,json.dumps(value)))
                except sqlite3.IntegrityError as e: raise Conflict('Record already exists.') from e
        return {**value, '_rev':rev+1}

class DynamoStore:
    def __init__(self, table):
        import boto3
        self.table = boto3.resource('dynamodb',region_name=os.getenv('AWS_REGION','us-east-1')).Table(table)
    def get(self,key):
        item=self.table.get_item(Key={'pk':key},ConsistentRead=True).get('Item')
        return {**json.loads(item['data']),'_rev':int(item['version'])} if item else None
    def put(self,key,value):
        from botocore.exceptions import ClientError
        value=dict(value); rev=value.pop('_rev',0)
        args={'Item':{'pk':key,'version':rev+1,'data':json.dumps(value)}, 'ConditionExpression':'#v = :v' if rev else 'attribute_not_exists(pk)'}
        if rev: args.update(ExpressionAttributeNames={'#v':'version'},ExpressionAttributeValues={':v':rev})
        try: self.table.put_item(**args)
        except ClientError as e:
            if e.response['Error']['Code']=='ConditionalCheckFailedException': raise Conflict('Record changed. Refresh and retry.') from e
            raise
        return {**value,'_rev':rev+1}

def make_store():
    return DynamoStore(os.environ['DYNAMODB_TABLE']) if os.getenv('DYNAMODB_TABLE') else Store()
