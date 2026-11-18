# Getting started

## What you’ll do
- Deploy the NetBox K8s charm.
- Integrate with the Valkey charm.
- Integrate with the PostgreSQL K8s charm.
- Integrate with S3 for storage.
- Expose the NetBox charm with Gateway API Integrator.
- Create a super user.

Through the process, you'll verify the workload state, and log in to
your NetBox instance.

## Requirements
- Juju 3.x installed.
- Juju controller that can create a model of type Kubernetes.
- Read/write access to a S3 compatible server with a bucket created.
- A Kubernetes cluster with a Gateway API controller, a GatewayClass, and
  load-balancer addresses reachable from your browser. The example below uses
  the `ck-gateway` GatewayClass provided by Canonical Kubernetes 1.32 or later.
  See the [Gateway API Integrator tutorial](https://canonical.com/juju/docs/gateway-api-integrator-charm/latest/tutorial/getting-started/)
  for environment setup instructions.

For more information about how to install Juju, see [Get started with Juju](https://documentation.ubuntu.com/juju/3.6/tutorial).


## Setting up a tutorial model

To manage resources effectively and to separate this tutorial's workload from
your usual work, we recommend creating a new model using the following command.

```
juju add-model netbox-tutorial
```

## Deploy

Deploy the NetBox K8s charm, with all its mandatory requirements (PostgreSQL, Valkey and S3).

```
juju deploy netbox-k8s
```

At this point NetBox K8s should be blocked as there is no S3 integration for
storage, Valkey or PostgreSQL.

Set the allowed hosts. In this example every host is allowed. For a production environment
only the used hosts should be allowed.
```
juju config netbox-k8s django-allowed-hosts='*'
```

### Valkey

NetBox K8s requires Valkey to work. Deploy the Valkey charm with:
```
juju deploy valkey --channel=9/edge --trust
```

Integrate Valkey with NetBox K8s with:
```
juju integrate valkey netbox-k8s:valkey
```

### Deploy PostgreSQL

NetBox K8s requires PostgreSQL to work. Deploy and integrate with:
```
juju deploy postgresql-k8s --channel 14/stable --trust
juju integrate postgresql-k8s netbox-k8s
```

### Deploy `s3-integrator`

NetBox requires an S3 integration for the uploaded files. This is because
the NetBox charm is designed to work in a high availability (HA) configuration.
This allows uploaded images to be placed on an S3 compatible server instead of
the local filesystem.

You can configure it with:
```
juju deploy s3-integrator --channel edge
juju config s3-integrator endpoint="<aws_endpoing_url>" bucket=<bucket_name> path=<path_in_bucket> region=<region> s3-uri-style=<path_or_host>
juju wait-for application s3-integrator --query='name=="s3-integrator" && (status=="active" || status=="blocked")'
juju run s3-integrator/leader sync-s3-credentials access-key=<aws_access_key_id> secret-key=<aws_secret_access_key>
juju integrate s3-integrator netbox-k8s
```

See the [s3-integrator charmhub page](https://charmhub.io/s3-integrator) for more information.

### Deploy `gateway-api-integrator`

Gateway API Integrator creates Gateway API resources to route traffic to NetBox.
Deploy it with trust so it can manage these Kubernetes resources:

```
juju deploy gateway-api-integrator --channel=1/edge --trust
juju config gateway-api-integrator gateway-class=ck-gateway external-hostname=<netbox_hostname>
```

Replace `<netbox_hostname>` with the hostname you will use to access NetBox.
If you use a different Gateway API controller, replace `ck-gateway` with the
GatewayClass available in your cluster.

The charm enforces HTTPS by default and will remain blocked until a certificate
provider is integrated. For this tutorial, deploy and integrate
`self-signed-certificates`:

```
juju deploy self-signed-certificates
juju integrate self-signed-certificates:certificates gateway-api-integrator:certificates
```

Self-signed certificates are for testing only. For a production deployment,
use a certificate provider trusted by your clients.

Connect NetBox to the gateway using the `ingress` interface:

```
juju integrate netbox-k8s:ingress gateway-api-integrator:gateway
```

Run `juju status --relations` and wait for the applications to become active.
The Gateway API Integrator status message shows the gateway address. Configure
DNS, or add an entry in your local hosts file, so that `<netbox_hostname>`
resolves to that address.

Check the URL exposed for NetBox:

```
juju run gateway-api-integrator/0 get-proxied-endpoints --format=yaml
```

Open the NetBox URL from the action output in your browser. With the
`netbox-tutorial` model used here, it should be
`https://<netbox_hostname>/netbox-tutorial-netbox-k8s`.
Your browser will show a certificate warning because the tutorial uses a
self-signed certificate.

## Create superuser
To be able to login to NetBox, you can create a super user with the next command:
```
juju run netbox-k8s/0 create-superuser username=<admin_username> email=<admin_email>
```

Congratulations, With the username created and the password provided in the response, 
you have now full access to your own NetBox!
