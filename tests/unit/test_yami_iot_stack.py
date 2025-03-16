import aws_cdk as core
import aws_cdk.assertions as assertions

from yami_iot.yami_iot_stack import YamiIotStack

# example tests. To run these tests, uncomment this file along with the example
# resource in yami_iot/yami_iot_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = YamiIotStack(app, "yami-iot")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
