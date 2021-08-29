"""
The module contains schemas for data validation in requests and responses.
"""

from marshmallow import Schema
from marshmallow.fields import Bool, Field, Float, Int, Nested, Str
from marshmallow.validate import Equal, Range


class ParamsSchema(Schema):
    device_id = Int(min=0, strict=True, required=True)
    object_type = Int(validate=Range(min=0, max=33), strict=True, required=True)
    object_id = Int(min=0, strict=True, required=True)
    property = Int(
        validate=Equal(85),  # validate=Range(min=0, max=846), # todo
        strict=True,
        required=True,
    )
    index = Int()
    tag = Int()
    value = Field(required=True)  # validate=OneOf([Int, Float, Str]),

    # device_id = Str(validate=Regexp(regex='\d{1,7}'), required=True)
    # object_type = Str(validate=Regexp(regex='[0-33]'), required=True)
    # object_id = Str(validate=Regexp(regex='\d{1,4}'), required=True)
    # property = Str(validate=Regexp(regex='[0-846]'), required=True)
    # index = Int()
    # tag = Int()
    # value = Field(validate=OneOf([Int, Float, Str]), required=True)


class JsonRPCSchema(Schema):
    jsonrpc = Float(validate=Equal(2.0), required=True)
    method = Str(validate=Equal("writeSetPoint"), required=True)
    params = Nested(ParamsSchema, required=True)
    id = Str()


class JsonRPCPostResponseSchema(Schema):
    success = Bool(required=True)


class ReadResultSchema(Schema):
    value = Field(required=True)
