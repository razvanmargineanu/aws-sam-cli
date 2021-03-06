from collections import OrderedDict

from unittest import TestCase

from samcli.commands.deploy.auth_utils import auth_per_resource
from samcli.lib.iac.interface import Stack as IacStack
from samcli.lib.providers.provider import Stack


class TestAuthUtils(TestCase):
    def setUp(self):
        self.template_dict = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Transform": "AWS::Serverless-2016-10-31",
            "Description": "\nSample SAM Template for Tests\n",
            "Globals": OrderedDict([("Function", OrderedDict([("Timeout", 3)]))]),
            "Resources": OrderedDict(
                [
                    (
                        "HelloWorldFunction",
                        OrderedDict(
                            [
                                ("Type", "AWS::Serverless::Function"),
                                (
                                    "Properties",
                                    OrderedDict(
                                        [
                                            ("CodeUri", "HelloWorldFunction"),
                                            ("Handler", "app.lambda_handler"),
                                            ("Runtime", "python3.7"),
                                            (
                                                "Events",
                                                OrderedDict(
                                                    [
                                                        (
                                                            "HelloWorld",
                                                            OrderedDict(
                                                                [
                                                                    ("Type", "Api"),
                                                                    (
                                                                        "Properties",
                                                                        OrderedDict(
                                                                            [("Path", "/hello"), ("Method", "get")]
                                                                        ),
                                                                    ),
                                                                ]
                                                            ),
                                                        )
                                                    ]
                                                ),
                                            ),
                                        ]
                                    ),
                                ),
                            ]
                        ),
                    )
                ]
            ),
        }

    def test_auth_per_resource_no_auth(self):
        iac_stack = IacStack()
        iac_stack.update(self.template_dict)
        _auth_per_resource = auth_per_resource([Stack("", "", "", {}, iac_stack)])
        self.assertEqual(_auth_per_resource, [("HelloWorldFunction", False)])

    def test_auth_per_resource_auth_on_event_properties(self):
        event_properties = self.template_dict["Resources"]["HelloWorldFunction"]["Properties"]["Events"]["HelloWorld"][
            "Properties"
        ]
        # setup authorizer and auth explicitly on the event properties.
        event_properties["Auth"] = {"ApiKeyRequired": True, "Authorizer": None}
        self.template_dict["Resources"]["HelloWorldFunction"]["Properties"]["Events"]["HelloWorld"][
            "Properties"
        ] = event_properties
        iac_stack = IacStack()
        iac_stack.update(self.template_dict)
        _auth_per_resource = auth_per_resource([Stack("", "", "", {}, iac_stack)])
        self.assertEqual(_auth_per_resource, [("HelloWorldFunction", True)])

    def test_auth_per_resource_defined_on_api_resource(self):
        self.template_dict["Resources"]["HelloWorldApi"] = OrderedDict(
            [
                ("Type", "AWS::Serverless::Api"),
                ("Properties", OrderedDict([("StageName", "Prod"), ("Auth", OrderedDict([("ApiKeyRequired", True)]))])),
            ]
        )
        # setup the lambda function with a restapiId which has Auth defined.
        self.template_dict["Resources"]["HelloWorldFunction"]["Properties"]["Events"]["HelloWorld"]["Properties"][
            "RestApiId"
        ] = {"Ref": "HelloWorldApi"}
        iac_stack = IacStack()
        iac_stack.update(self.template_dict)
        _auth_per_resource = auth_per_resource([Stack("", "", "", {}, iac_stack)])
        self.assertEqual(_auth_per_resource, [("HelloWorldFunction", True)])

    def test_auth_supplied_via_definition_body_uri(self):
        self.template_dict["Resources"]["HelloWorldApi"] = OrderedDict(
            [
                ("Type", "AWS::Serverless::Api"),
                (
                    "Properties",
                    OrderedDict(
                        [
                            ("StageName", "Prod"),
                            (
                                "DefinitionBody",
                                {
                                    "swagger": "2.0",
                                    "info": {"version": "1.0", "title": "local"},
                                    "paths": {"/hello": {"get": {"security": ["OAuth2"]}}},
                                },
                            ),
                        ]
                    ),
                ),
            ]
        )
        # setup the lambda function with a restapiId which has definitionBody defined with auth on the route.
        self.template_dict["Resources"]["HelloWorldFunction"]["Properties"]["Events"]["HelloWorld"]["Properties"][
            "RestApiId"
        ] = {"Ref": "HelloWorldApi"}
        iac_stack = IacStack()
        iac_stack.update(self.template_dict)
        _auth_per_resource = auth_per_resource([Stack("", "", "", {}, iac_stack)])

        self.assertEqual(_auth_per_resource, [("HelloWorldFunction", True)])

    def test_auth_supplied_via_definition_body_uri_instrinsics_involved_unable_to_determine(self):
        self.template_dict["Resources"]["HelloWorldApi"] = OrderedDict(
            [
                ("Type", "AWS::Serverless::Api"),
                (
                    "Properties",
                    OrderedDict(
                        [
                            ("StageName", "Prod"),
                            (
                                "DefinitionBody",
                                {
                                    "swagger": "2.0",
                                    "info": {"version": "1.0", "title": "local"},
                                    "paths": {
                                        "/hello": {"Fn::If": ["Condition", {"get": {}}, {"Ref": "AWS::NoValue"}]}
                                    },
                                },
                            ),
                        ]
                    ),
                ),
            ]
        )
        # setup the lambda function with a restapiId which has definitionBody defined with auth on the route.
        self.template_dict["Resources"]["HelloWorldFunction"]["Properties"]["Events"]["HelloWorld"]["Properties"][
            "RestApiId"
        ] = {"Ref": "HelloWorldApi"}
        iac_stack = IacStack()
        iac_stack.update(self.template_dict)
        _auth_per_resource = auth_per_resource([Stack("", "", "", {}, iac_stack)])

        self.assertEqual(_auth_per_resource, [("HelloWorldFunction", False)])
