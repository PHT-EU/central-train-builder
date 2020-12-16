from marshmallow import Schema, fields, post_load


class BuildMessage(Schema):
    """
    Class representing a build command sent from the central UI

    """
    type = fields.Str()
    token = fields.Str()
    trainId = fields.Str()
    proposalId = fields.Str()
    stations = fields.List(fields.Str())
    masterImage = fields.Str()
    entrypointExecutable = fields.Str()
    entrypointPath = fields.Str()
    hash = fields.Str()
    sessionId = fields.Str()


class TrainConfig(Schema):
    train_id = fields.Str(required=True)
    user_Id = fields.Str(required=True)
    session_id = fields.Str(required=True)
    rsa_user_public_key = fields.Str(required=True)
    encrypted_key = fields.Dict(keys=fields.Str(), values=fields.Str(), required=True)
    rsa_public_keys = fields.Dict(required=True)
    user_encrypted_sym_key = fields.Str(required=True)
    e_h = fields.Str(required=True)
    e_h_sig = fields.Str(required=True)
    e_d = fields.Str(required=False)
    e_d_sig = fields.Str(required=False)
    digital_signature = fields.List(fields.Dict(keys=fields.Str(), values=fields.Str()), required=False)


