FROM harbor.lukaszimmermann.dev/pht_example_master/master:train
COPY pht_train /opt/pht_train
COPY train_config.json /opt/pht_train/train_config.json
