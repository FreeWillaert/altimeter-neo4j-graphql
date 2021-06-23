
# altimeter-scanner-access role
Attach policies:
* SecurityAudit
* job-function/ViewOnlyAccess
* AWSSupportAccess

# manual run
```
aws events put-events --entries '[{"Source":"altimeter", "DetailType": "start", "Detail":"{}"}]'
```

# Deploying to a Control Tower Audit Account
Control Tower places a guardrail "Guardrail: Disallow Changes to Encryption Configuration for Amazon S3 Buckets" (https://docs.aws.amazon.com/controltower/latest/userguide/elective-guardrails.html#log-archive-encryption-enabled) on the Audit account (via the Core OU) which causes both the CDK Bootstrap and the initial deployment to fail, since in both cases an encrypted S3 bucket needs to be created.

To get around this, assume the 'AWSControlTowerExecution' role from a principal in the master account, and then bootstrap and deploy. 

NOTE: Since CDK uses a CDK deploy role for executing the Cloudformation Stacks, this still fails. Therefore, encryption of the output S3 bucket is disabled (at least for now).


# Welcome to this CDK Python project!

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!
