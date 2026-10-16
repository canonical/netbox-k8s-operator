<!-- vale Canonical.007-Headings-sentence-case = NO -->
# NetBox K8s operator
<!-- vale Canonical.007-Headings-sentence-case = YES -->

A Juju charm deploying and managing
[NetBox](https://github.com/netbox-community/netbox/) on
Kubernetes. NetBox is the go-to solution for modeling and documenting network
infrastructure for thousands of organizations worldwide.

This charm simplifies initial deployment and "day N" operations of
NetBox on Kubernetes, such as integration with SSO, access to S3 for
file storage and more. It allows for deployment on many
different Kubernetes platforms, from [MicroK8s](https://microk8s.io)
to [Charmed Kubernetes](https://ubuntu.com/kubernetes) to public cloud
Kubernetes offerings.

As such, the charm makes it easy for those looking to take control of
their own NetBox server whilst keeping operations simple, and gives them
the freedom to deploy on the Kubernetes platform of their choice.

For DevOps or SRE teams this charm will make operating NetBox simple
and straightforward through Juju's clean interface. It will allow easy
deployment into multiple environments for testing of changes.

## In this documentation

| Topic | Guides and reference |
| --- | --- |
| **Get started** | [Deploy NetBox with Juju](tutorial/getting-started.md) \| [Try NetBox locally with Multipass](tutorial/testing-netbox.md) |
| **Operations** | [Upgrade NetBox](how-to/upgrade.md) \| [Actions](reference/actions.md) |
| **High availability** | [Configure scripts and reports](how-to/configure-scripts-reports.md) |
| **Security** | [Configure OIDC authentication](how-to/configure-oidc.md) |
| **Integrations** | [Relation endpoints](reference/integrations.md) |
| **Design** | [Charm architecture](reference/charm-architecture.md) |

## How this documentation is organised

This documentation uses the
[Diátaxis documentation structure](https://diataxis.fr/).

* **Tutorials** take you step-by-step through
  [deploying NetBox with Juju](tutorial/getting-started.md) or
  [trying NetBox locally with Multipass](tutorial/testing-netbox.md).
* **How-to guides** assume basic familiarity with the charm and cover specific
  tasks, such as [configuring OIDC](how-to/configure-oidc.md),
  [using scripts and reports with high availability](how-to/configure-scripts-reports.md),
  and [upgrading NetBox](how-to/upgrade.md).
* **Reference** provides technical information about
  [actions](reference/actions.md), [integrations](reference/integrations.md),
  and the [charm architecture](reference/charm-architecture.md).

## Limitations

The NetBox charm is designed for a high availability (HA) deployment
and can be scaled to more than one unit.

Do not use file uploads for scripts and reports: the files will be uploaded
to only one unit and will be lost if the pod is rescheduled.

Instead, create scripts and reports from a data source and select
the "Auto sync enabled" checkbox. This synchronises the scripts and reports
every five minutes across all units. See
[Configure scripts and reports for high availability](how-to/configure-scripts-reports.md)
for instructions.

## Project and community

* [NetBox upstream repository](https://github.com/netbox-community/netbox)
* [Code of conduct](https://ubuntu.com/community/ethos/code-of-conduct)
* [Get support](https://discourse.charmhub.io/)
* [Join our online chat](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
* [Contribute](how-to/contribute.md)
* [Juju SDK documentation](https://canonical.com/juju/docs/ops/latest/) for more information about developing and improving charms.

### Contributing to this documentation

Documentation is an important part of this project, and we take the
same open-source approach to the documentation as the code. As such,
we welcome community contributions, suggestions and constructive
feedback on our documentation. Our documentation is hosted on the
[Charmhub forum](https://discourse.charmhub.io/) to enable easy
collaboration. Please use the “Help us improve this documentation”
links on each documentation page to either directly change something
you see that’s wrong, or ask a question, or make a suggestion about a
potential change via the comments section.

If there’s a particular area of documentation that you’d like to see that’s
missing, please [file a bug](https://github.com/canonical/netbox-k8s-operator/issues).

## Contents

1. [Tutorial](tutorial)
  1. [Getting Started](tutorial/getting-started.md)
  1. [Testing NetBox](tutorial/testing-netbox.md)
1. [How To](how-to)
  1. [Contribute](how-to/contribute.md)
  2. [Configure OIDC](how-to/configure-oidc.md)
  3. [Configure Scripts and Reports for HA](how-to/configure-scripts-reports.md)
  4. [Upgrade](how-to/upgrade.md)
1. [Reference](reference)
  1. [Actions](reference/actions.md)
  1. [Charm Architecture](reference/charm-architecture.md)
  2. [Integrations](reference/integrations.md)
