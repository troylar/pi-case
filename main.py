import click
from haikunator import Haikunator
from botocore.exceptions import ClientError
import boto3
import os
import crypt
import os.path
import socket
import fcntl
import struct
def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])


def get_object(**kwargs):
    bucket_name = kwargs.get('BucketName')
    key = kwargs.get('Key')
    client = boto3.client('s3')
    try:
        resp = client.get_object(
            Bucket=bucket_name,
            Key=key)
        return resp
    except ClientError as e:
        code = e.response['Error']['Code']
        if code == 'AccessDenied':
            return False


def generate_unique_name(**kwargs):
    bucket_name = kwargs.get('BucketName')
    haikunator = Haikunator()
    name = haikunator.haikunate()
    while True:
        obj = get_object(
            BucketName=bucket_name,
            Key=name)
        if not obj:
            break
    return name

@click.group()
@click.version_option()
def cli():
    pass


@cli.command()
@click.argument('bucket')
@click.argument('username', default='root')
@click.option('--name')
@click.option('--profile', default='default')
def register(bucket, username, name, profile):
    if (profile):
        session = boto3.session.Session(profile_name=profile) 
        print 'Profile: ' + profile
        s3 = session.resource('s3')
    else:
        s3 = boto3.resource('s3')

    haikunator = Haikunator()
    if not name:
        if os.path.isfile('/etc/pi-case/key'):
            click.echo('Device already exists . . . re-registering')
            f = open('/etc/pi-case/key', 'r')
            name = f.readline().rstrip()
        else:
            click.echo('Registering device')
            name = generate_unique_name(
                BucketName=bucket)
    print 'Registration Name = {}'.format(name)

    password=haikunator.haikunate(token_length=0)
    ip_address = get_ip_address('wlan0')
    print 'Registering {} with bucket {}'.format(name, bucket)
    os.system('echo "{}:{}" | chpasswd'.format(username, password))
    s3.Object(bucket, name).put(Body='IPAddress: {}\nUsername: {}\nPassword: {}\n'
                                .format(ip_address, username, password))
    os.system("echo {} | sudo tee /etc/pi-case/key".format(name))
     

if __name__ == '__main__':
    cli()
