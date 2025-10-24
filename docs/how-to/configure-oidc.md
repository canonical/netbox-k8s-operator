<!-- vale Canonical.007-Headings-sentence-case = NO -->
# Configure OIDC
<!-- vale Canonical.007-Headings-sentence-case = YES -->

The NetBox charm makes use of the oauth integration for OIDC. You can find
more information in [charmhub](https://charmhub.io/integrations/oauth).

OIDC is configured in NetBox using the library `python-social-core` with the [`OIDC` backend](https://python-social-auth.readthedocs.io/en/latest/backends/oidc.html).

To configure it, you only need to integrate your OIDC provider with NetBox K8s:
```
juju integrate hydra netbox-k8s
```

For NetBox to work, you may need to customise some of the following configuration options:
 - `oidc-scopes`: OIDC scopes are used by an application during authentication to authorize access to a user's details, like name and picture. It must include `openid` to be a valid OIDC.
 - `oidc-redirect-path`: The redirect URL used by the OIDC provider to redirect back to NetBox application after the authorization is done.

NetBox configuration options for OIDC can be configured like:
```
juju config netbox-k8s oidc-scopes="openid profile email" oidc-redirect-path="/oauth/complete/oidc/"
```