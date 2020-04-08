# mist-rolling-update

Python script for performing FW updates on Mist APs, one at a time

## Requirements

Python libraries:

* [dartmist](https://github.com/bryanward-net/dartmist)

## Environment

You must specify a Mist Org ID and a Mist API Token.  These can be passed in via the command line (see Usage) or, preferably, set as envinronment variables:

    export MIST_ORGID="00000000-0000-0000-0000-000000000000"
    export MIST_TOKEN="12345123451234512345123451234512345"

To get an API Token, refer to the documentation provided by Mist [https://api.mist.com/api/v1/docs/Auth#api-token](https://api.mist.com/api/v1/docs/Auth#api-token)

## Config

Versions to upgrade each model to are specified in the [config.py](config.py) file.

## Usage

    usage: rollingupgrade.py [-h] [--token TOKEN] [--orgid ORGID]
                            (--site SITE | --siteid SITEID) [--delay DELAY]
                            [--debug]

    Upgrade FW of Mist APs, one at a time

    optional arguments:
    -h, --help       show this help message and exit
    --token TOKEN    Mist API Token. Can also use env var MIST_TOKEN
    --orgid ORGID    Organization ID to run against. Can also use env var
                    MIST_ORGID
    --site SITE      Site name to upgrade
    --siteid SITEID  Site ID to upgrade
    --delay DELAY    Additional time to wait between devices
    --debug          Debug Logging Enabled

## Example

`rollingupgrade.py --site "Site Name"`

    2020-04-08 15:54:39,997 INFO    rollingupgrade.<module>:        Connecting to Mist API...
    2020-04-08 15:54:40,458 INFO    rollingupgrade.<module>:        Successfully connected to API.
    2020-04-08 15:54:42,318 INFO    rollingupgrade.rollingupgrade:  Updating firmware on device AP 15-90 [5c5b358e1590] from version 0.5.17230 to version 0.5.17360
    2020-04-08 15:54:47,666 INFO    rollingupgrade.rollingupgrade:  Update of device AP 15-90 [5c5b358e1590] is in progress: 0%
    ...
    2020-04-08 15:55:08,670 INFO    rollingupgrade.rollingupgrade:  Update of device AP 15-90 [5c5b358e1590] is in progress: 100%
    2020-04-08 15:56:18,189 INFO    rollingupgrade.rollingupgrade:  Update of device AP 15-90 [5c5b358e1590] Complete!  Now at version 0.5.17360
    2020-04-08 15:56:18,189 INFO    rollingupgrade.rollingupgrade:  Updating firmware on device AP 46-8C [5c5b358e468c] from version 0.5.17230 to version 0.5.17360
    2020-04-08 15:56:23,553 INFO    rollingupgrade.rollingupgrade:  Update of device AP 46-8C [5c5b358e468c] is in progress: 0%
    ...
    2020-04-08 15:56:42,283 INFO    rollingupgrade.rollingupgrade:  Update of device AP 46-8C [5c5b358e468c] is in progress: 100%
    2020-04-08 15:57:52,788 INFO    rollingupgrade.rollingupgrade:  Update of device AP 46-8C [5c5b358e468c] Complete!  Now at version 0.5.17360
    2020-04-08 15:57:52,788 INFO    rollingupgrade.<module>:        Rolling upgrade complete!
