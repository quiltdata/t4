import t4
import quilt
b = t4.Bucket('s3://calvin-auth-test-do-not-use')
creds = quilt.tools.command.get_credentials()
t4.update_credentials(creds)
my_prefix = creds['sub']

b.put_file(my_prefix + '/README.md', 'README.md')
