import os
from flask import Flask, request, abort, Response
from flask_restplus import Resource, Api, Namespace
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

from pht.trainbuilder import Config

__POST = 'POST'
_BAD_REQUEST = 400
_CREATED = 201

app = Flask(__name__)
api = Api(app)
build = Namespace('build', description='Namespace for buiding trains')
api.add_namespace(build)
db = SQLAlchemy(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///build.sqlite"


class Build(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String, unique=False, nullable=False)
    filename = db.Column(db.String, unique=True, nullable=True)


db.create_all()

# TODO How to reconcile this with app.config ?
config = Config.from_env()


def bad_request():
    abort(_BAD_REQUEST)


@build.route('/upload')
class BuildUpload(Resource):
    @build.doc('Upload file to build service')
    @build.response(_BAD_REQUEST, 'If the file could not be uploaded')
    @build.response(_CREATED, 'If the file was uploaded successfully')
    def post(self):
        _file = 'file'
        # check if the post request has the file part
        if _file not in request.files:
            bad_request()
        file = request.files[_file]
        if file.filename == '':
            bad_request()
        if file:
            build = Build(type='file')
            db.session.add(build)
            db.session.commit()
            filename = secure_filename(file.filename + f'_{build.id}')
            build.filename = filename
            db.session.merge(build)
            db.session.commit()
            file.save(os.path.join(config.upload_dir, filename))
            return Response(status=201)
        else:
            bad_request()


@build.route('/')
class BuildPost(Resource):
    @build.doc('Post build request JSON')
    @build.response(_BAD_REQUEST, 'If the build request is invalid')
    @build.response(_CREATED, 'If the POST request was successful')
    @build.header('Accept', 'application/json')
    def post(self):
        if request.data:
            data = request.data
            build = Build(type='post')
            db.session.add(build)
            db.session.commit()
            filename = f'_{build.id}'
            build.filename = filename
            db.session.merge(build)
            db.session.commit()
            with open(os.path.join(config.upload_dir, filename), 'wb') as f:
                f.write(data)
            return Response(status=201)
        else:
            bad_request()


if __name__ == '__main__':
    app.run(host='0.0.0.0')
