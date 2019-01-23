Create a Secret in the cluster that holds your authorization token
A Kubernetes cluster uses the Secret of docker-registry type to authenticate with a container registry to pull a private image.

Create this Secret, naming it regcred:

kubectl create secret docker-registry regcred --docker-server=<your-registry-server> --docker-username=<your-name> --docker-password=<your-pword> --docker-email=<your-email>
where:

<your-registry-server> is your Private Docker Registry FQDN. (https://index.docker.io/v1/ for DockerHub)
<your-name> is your Docker username.
<your-pword> is your Docker password.
<your-email> is your Docker email.
You have successfully set your Docker credentials in the cluster as a Secret called regcred.

