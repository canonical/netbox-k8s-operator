<!-- vale Canonical.007-Headings-sentence-case = NO -->
# Configure OIDC
<!-- vale Canonical.007-Headings-sentence-case = YES -->

The NetBox charm makes use of the OAuth integration for OIDC. You can find
more information in [charmhub](https://charmhub.io/integrations/oauth).

OIDC is configured in NetBox using the library `python-social-core` with the [`OIDC` backend](https://python-social-auth.readthedocs.io/en/latest/backends/oidc.html).

To configure it, you only need to integrate your OIDC provider with NetBox K8s:
```
juju integrate hydra netbox-k8s
```

For NetBox to work, you may need to customise some of the following configuration options:
 - `oidc-scopes`: OIDC scopes are used by an application during authentication to authorize access to a user's details, like name and picture. It must include `openid` to be a valid OIDC.
 - `oidc-redirect-path`: The redirect URL used by the OIDC provider to redirect back to NetBox application after the authorization is done.
 - `oidc-groups-claim`: The OIDC claim containing the user's groups. Setting this option enables group synchronization. Groups from the claim are created in NetBox as needed, and the user's NetBox group memberships are replaced on every login. The claim must contain a list of group names.
 - `oidc-superuser-groups`: A comma-separated list of OIDC groups whose members receive NetBox superuser access. This access is revoked on the next login if the user no longer belongs to one of these groups.
 - `oidc-staff-groups`: A comma-separated list of OIDC groups whose members receive NetBox staff access. This access is revoked on the next login if the user no longer belongs to one of these groups.

NetBox configuration options for OIDC can be configured like:
```
juju config netbox-k8s \
  oidc-scopes="openid profile email groups" \
  oidc-redirect-path="/oauth/complete/oidc/" \
  oidc-groups-claim="groups" \
  oidc-superuser-groups="netbox-admins" \
  oidc-staff-groups="netbox-admins,netbox-operators"
```

Leave `oidc-groups-claim` empty to keep managing NetBox groups and privileges manually.
