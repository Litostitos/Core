
from marshmallow import Schema, fields, validate

class ItemSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1))
    ip = fields.Str(
        required=True,
        validate=validate.Regexp(
            r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$",
            error="Invalid IP address format. Must be a valid IPv4 address."
        )
    )

class StoreSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1))
 