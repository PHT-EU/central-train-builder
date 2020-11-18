import docker
import subprocess
import json
from typing import List


class ImageHandler:
    def __init__(self, docker_client: docker.client.DockerClient) -> None:
        self.client = docker_client

    def image_to_train(self, message: dict, img_name: str) -> dict:
        pass

    def validate_image(self, message: dict) -> bool:

        # Extract the image names from the message
        master_img_name = message["master_image"]
        submission_img_name = message["proposal_image"]
        # Get the images
        master_img = self._get_image(master_img_name)
        submission_img = self._get_image(submission_img_name)
        # Compare image histories
        history_diff = self._compare_image_history(master_img, submission_img)

        # compare image file systems
        self._compare_image_file_system(master_img_name, submission_img_name)

    def _compare_image_history(self, master_image: docker.client.ImageCollection,
                               submission_image: docker.client.ImageCollection) -> List[str]:
        """
        Compares the history of the submitted docker image with the master image selected in the ui

        :param master_image: ImageObject representing the selected master image
        :param submission_image: Image object representing the image submitted to pht_train_proposals
        :return: List of difference in the build history between the master image and the proposed train
        :raises: ValueError when the submitted image is not derive from an official master image
        """
        # Get the history of the images
        master_history = master_image.history()
        submission_history = submission_image.history()
        # TODO solve this with set difference maybe
        history_diff = []
        for event in submission_history:
            if event not in master_history:
                history_diff.append(event["CreatedBy"])
        for master_event in master_history:
            if master_event not in submission_history:
                print(master_event)
                if "ENTRYPOINT" in master_event["CreatedBy"]:
                    if not self._validate_entrypoint():
                        # TODO Check entrypoint
                        raise ValueError("The submitted Image is not derived from an accepted base image")
                else:
                    raise ValueError("The submitted Image is not derived from an accepted base image")
        return history_diff

    def _compare_image_file_system(self, master_image_name: str, submission_image_name: str):

        container_diff_args = ["container-diff", "diff", f"daemon://{master_image_name}",
                               f"daemon://{submission_image_name}", "--type=file"]
        output = subprocess.run(container_diff_args, capture_output=True)
        file_system_diff = output.stdout.decode().splitlines()
        self._validate_file_system_changes(file_system_diff)

    def _validate_history_diff(self, history_diff: list):
        pass

    def _validate_entrypoint(self):
        # TODO
        return True

    def _extract_immutable_files(self):
        """
        Extract the files in /opt/pht_train and hash them to get the hash of immutable files

        :return: hex
        """
        # TODO extract tar archive and generate hash

    def _validate_file_system_changes(self, file_system_diff: List[str]) ->bool:
        add_ind = None
        deleted_ind = None
        changed_ind = None
        valid = False
        for ind, content in enumerate(file_system_diff):
            if "These entries have been added" in content:
                add_ind = ind
            elif "These entries have been deleted" in content:
                deleted_ind = ind
            elif "These entries have been changed" in content:
                changed_ind = ind
        # Find the files added to the image file system and make sure they are located exclusively under /opt/pht_train
        if len(file_system_diff[add_ind: deleted_ind]) > 2:
            print("Added files detected.")
            for file in file_system_diff[add_ind + 2: deleted_ind]:
                if not self._validate_added_file(file):
                    valid = False
                else:
                    valid = True
        # If the length of the deleted files section is greater than two, files have been deleted from the master image
        # -> image invalid
        if len(file_system_diff[deleted_ind: changed_ind]) > 2:
            print("Deleted Files detected")
            valid = False
        if len(file_system_diff[changed_ind:]) > 2:
            print("Changed files detected")
            valid = False

        if valid:
            print("Validation success")

        return valid

    @staticmethod
    def _validate_added_file(file: str) -> bool:
        # TODO allow more locations for installed interpreter etc
        path = file.split(" ")[0]
        if len(path) > 1:
            if path.split("/")[1:3] != ["opt", "pht_train"]:
                print(f"Invalid File location found: {path}")
                return False
        return True



    def _get_image(self, name) -> docker.client.ImageCollection:
        return self.client.images.get(name)


if __name__ == '__main__':
    client = docker.from_env()
    ih = ImageHandler(client)
    message = {"master_image": "harbor.personalhealthtrain.de/pht_master/master:buster",
               "proposal_image": "harbor.personalhealthtrain.de/pht_train_submission/test"}

    ih.validate_image(message)
