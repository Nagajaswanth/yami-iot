#!/usr/bin/env python3
import os

import aws_cdk as cdk

from yami_iot.yami_iot_stack import YamiIotStack


app = cdk.App()
YamiIotStack(app, "YamiIotStack",
    )

app.synth()
