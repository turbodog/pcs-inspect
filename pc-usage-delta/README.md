# Prisma Cloud Usage Delta Script

## Description

The `pc-usage-delta.py` script queries the Prisma Cloud API for License/Usage data,
saving the data to a historical file, calculating the mean of the historical data,
and comparing that mean to the current usage. 
If the current usage exceeds the mean usage by a (configurable) percentage,
it will output a notification.

This is valuable for detecting a drop or spike in usage,
such as when a cloud account is onboarded or offboarded,
or the number of resources/workloads changes unexpectedly.

### Usage via Cron

* Download the `pc-usage-delta.py` script.
* Customize the `notify` function in the `pc-usage-delta.py` script to meet your notification requirements.
* Execute `pc-usage-delta.py` in the context of a cron job.
* Profit!

Use `./pc-usage-delta.py -h` for a complete list of parameters.

Note that this script requires a Prisma Cloud Access Key with `ACCOUNT GROUP READ ONLY` privileges configured for all accounts, or `SYSTEM ADMIN` privileges.

#### Example

```
vi pc-usage-delta.py
chmod +x pc-usage-delta.py

./pc-usage-delta.py -u "https://api.prismacloud.io" -a "aaaaaaaa-1111-aaaa-1111-aaaaaaaa1111" -s "ssss1111ssss1111ssss1111="

Generating Prisma Cloud API Token
Querying Cloud Accounts
Querying Usage for 150 Cloud Accounts
......................................................................................................................................................
Current (Licensable) Resource Count: 515

Historical (Licensable) Resource Count:

{'Date': '2021-01-26', 'Resources': '1'}
{'Date': '2021-01-27', 'Resources': '104'}

NOTIFY: Spike !!!
NOTIFY: Current resource count (515) is 800 percent greater than the mean resource count (52).
NOTIFY: This notification is triggered by a delta greater than 10 percent, measured over 2 samples.
```

### Usage via AWS Lamdba

* Download the `pc-usage-delta` directory.
* Customize the `notify` function in the `pc-usage-delta.py` script to meet your notification requirements.
* Create a `terraform/terraform.tfvars` file and populate it with the variables defined in `terraform/main.tf`.
* Deploy with Terraform.
* Profit!

#### Example

```
vi pc-usage-delta.py

cd terraform

vi terraform.tfvars

terraform init
terraform validate
terraform plan
terraform apply
```