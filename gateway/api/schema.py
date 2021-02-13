"""
The module contains schemas for data validation in requests and responses.
"""

from marshmallow import Schema, ValidationError, validates, validates_schema
from marshmallow.fields import Date, Dict, Float, Int, List, Nested, Str, Field
from marshmallow.validate import Length, OneOf, Range, Equal, Regexp

# POST http://visiobas:7070/json-rpc
# get_properties_example = '{"jsonrpc":"2.0","method":"requestBacnetProperties","params":{"device_id":2099232,"object_type_name":"binary-value","object_id":36,"fields":[87]},"id":""}'



# POST http://visiobas:7070/json-rpc
ex1 = ('{"jsonrpc":"2.0","method":"writeSetPoint",'
       '"params":{'
       '"device_id":"2099232",'
       '"object_type":"5",'
       '"object_id":"36",'
       '"property":"85",'
       '"priority":"10",'
       '"index":"-1",'
       '"tag":"9",'
       '"value":"1"},'
       '"id":""}')

# POST http://visiobas:7070/json-rpc
ex2 = ('{"jsonrpc":"2.0","method":"writeSetPoint",'
       '"params":{'
       '"device_id":"2098185",'
       '"object_type":"5",'
       '"object_id":"3",'
       '"property":"85",'
       '"priority":"10",'
       '"index":"-1",'
       '"tag":"9",'
       '"value":"1"},'
       '"id":""}')


class ParamsSchema(Schema):
    device_id = Int(min=0, strict=True, required=True)
    object_type = Int(validate=Range(min=0, max=33), strict=True, required=True)
    object_id = Int(min=0, strict=True, required=True)
    property = Int(validate=Range(min=0, max=846), strict=True, required=True)
    index = Int()
    tag = Int()
    value = Field(validate=OneOf([Int, Float, Str]), required=True)

    # device_id = Str(validate=Regexp(regex='\d{1,7}'), required=True)
    # object_type = Str(validate=Regexp(regex='[0-33]'), required=True)
    # object_id = Str(validate=Regexp(regex='\d{1,4}'), required=True)
    # property = Str(validate=Regexp(regex='[0-846]'), required=True)
    # index = Int()
    # tag = Int()
    # value = Field(validate=OneOf([Int, Float, Str]), required=True)


class JsonRPCSchema(Schema):
    jsonrpc = Float(validate=Equal(2.0), required=True)
    method = Str(validate=Equal('writeSetPoint'), required=True)
    params = Nested(ParamsSchema, required=True)
    id = Str()


