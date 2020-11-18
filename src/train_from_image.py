import docker
import subprocess
import json


class ImageHandler:
    def __init__(self, docker_client: docker.client.DockerClient) -> None:
        self.client = docker_client

    def image_to_train(self, message: dict, img_name: str) -> dict:
        pass

    def validate_image(self, message: dict, img_name: str) -> bool:
        pass

    def compare_image_history(self, base_image:str, image_submission: str) -> dict:
        # Get the history of the images
        base_history = self._get_image(base_image).history()
        submission_history = self._get_image(image_submission).history()

        # TODO do this with sets
        for event in submission_history:
            if event in base_history:
                print("Common event found")
            else:
                print("Found difference")
                print(event)

    def _get_image(self, name) -> docker.client.ImageCollection:
        return self.client.images.get(name)



if __name__ == '__main__':
    client = docker.from_env()
    ih = ImageHandler(client)

    BASE_IMG = "harbor.personalhealthtrain.de/pht_master/master:buster"
    IMG_2 = "harbor.personalhealthtrain.de/pht_train_submission/test"
    ih.compare_image_history(BASE_IMG, IMG_2)

