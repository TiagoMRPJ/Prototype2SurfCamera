from google.cloud import storage
from google.oauth2 import service_account

"""
This library exports functions to access Google Cloud Storage (GCS) buckets.
"""


def list_buckets():
    """
    Returns a list of all bucket names.
    """
    credentials = service_account.Credentials.from_service_account_file(
        'credentials.json')
    client = storage.Client(credentials=credentials)
    buckets = client.list_buckets()
    bucket_names = []
    for bucket in buckets:
        bucket_names.append(bucket.name)
    return bucket_names


def get_bucket(bucket_name):
    """
    Returns a bucket object from the given bucket name.
    """
    credentials = service_account.Credentials.from_service_account_file(
        'credentials.json')
    client = storage.Client(credentials=credentials)
    bucket = client.get_bucket(bucket_name)
    return bucket


def create_bucket(bucket_name):
    """
    Creates a bucket with the given name.
    """
    credentials = service_account.Credentials.from_service_account_file(
        'credentials.json')
    client = storage.Client(credentials=credentials)
    bucket = client.create_bucket(bucket_name)
    return bucket


def list_blobs(bucket_name):
    """
    Returns a list of all blob names in the given bucket.
    """
    bucket = get_bucket(bucket_name)
    blobs = bucket.list_blobs()
    blob_names = []
    for blob in blobs:
        blob_names.append(blob.name)
    return blob_names


def download_blob(bucket_name, source_blob_name, destination_file_name):
    """
    Downloads a blob from the bucket to the given file.
    """
    bucket = get_bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)


def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """
    Uploads a file to the bucket.
    """
    bucket = get_bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)

