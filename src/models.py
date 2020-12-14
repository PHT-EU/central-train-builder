from marshmallow import Schema, fields


class Message(Schema):
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
    train_id = fields.Str()
    user_Id = fields.Str()
    session_id = fields.Str()
    rsa_user_public_key = fields.Str()
    encrypted_key = fields.Dict()
    rsa_public_keys = fields.Dict()
    user_encrypted_sym_key = fields.Str()
    e_h = fields.Str()
    e_h_sig = fields.Str()
    e_d = fields.Str()
    e_d_sig = fields.Str()
    digital_signature = fields.List(fields.Dict())


