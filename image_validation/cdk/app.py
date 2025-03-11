from aws_cdk import core
from stack import TwoTierClassificationStack

app = core.App()
TwoTierClassificationStack(app, "TwoTierClassificationStack")
app.synth()
