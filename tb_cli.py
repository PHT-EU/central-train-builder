from TrainBuilder import TrainBuilder
import argparse
from util import post_route_to_vault

route = [1, 2, 3, 4]

tb = TrainBuilder("https://vault.pht.medic.uni-tuebingen.de/")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--entrypoint", help="Path to the entrypoint.py file", required=True)
    parser.add_argument("--train_name", help="Name of the train", required=True)
    parser.add_argument("--route", help="Comma separated list of stations")



    args = parser.parse_args().__dict__
    entrypoint_path = args["entrypoint"]

    if args.get("route", None):
        route = args["route"].split(",")
    print(f"Posting route {route} to vault under name {args['train_name']}\n")
    post_route_to_vault(args["train_name"], route)
    # Build basic train based on one file
    print("Building train..")
    tb.build_minimal_example(name=args["train_name"], file_path=entrypoint_path)
    # Post route to vault


