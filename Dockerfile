# syntax=docker/dockerfile-upstream:master-labs
FROM ubuntu:focal
# focal == 20.04

# ______     ______     ______   ______     ______     ______   __  __    
# /\  == \   /\  ___\   /\  == \ /\  == \   /\  __ \   /\  == \ /\ \_\ \   
# \ \  __<   \ \  __\   \ \  _-/ \ \  __<   \ \ \/\ \  \ \  _-/ \ \____ \  
#  \ \_\ \_\  \ \_____\  \ \_\    \ \_\ \_\  \ \_____\  \ \_\    \/\_____\ 
#   \/_/ /_/   \/_____/   \/_/     \/_/ /_/   \/_____/   \/_/     \/_____/ 
# v0.1

# build issues and fixes:
# https://github.com/automl/auto-sklearn/issues/1694
# https://github.com/scikit-learn/scikit-learn/issues/26858
# https://hub.docker.com/r/mfeurer/auto-sklearn
# https://github.com/automl/auto-sklearn/blob/development/Dockerfile

### args
ARG PROJECT="automl_DOE"
ARG PACKAGES="libjpeg-turbo8 build-essential swig python3-dev python3 python3-pip"

### install packages
RUN apt update && apt install -y ${PACKAGES}

### add default container user
RUN groupadd -g 1000 vscode
RUN useradd -rm -d /home/vscode -s /bin/bash -g root -G sudo -u 1000 vscode

### setup default mamba environment for vscode user
USER vscode

# switch back to root
USER root

###############################################################################
# add custom commands here

RUN pip3 install auto-sklearn==0.15.0
RUN pip3 install ipykernel==6.29.3 ipython==8.13.0
RUN pip3 install pandas==2.0.3

# end of custom commands
###############################################################################

# change workdir to make notebooks browseable in jupyter notebooks
WORKDIR /workspaces

### setup volumes

# jupyter notebooks
VOLUME [ "/notebooks" ]

# vscode workspace
VOLUME [ "/workspaces/${PROJECT}" ]

# vscode extensions
VOLUME [ "/home/vscode/.vscode-server"]

# document ports
EXPOSE 8888/tcp
EXPOSE 8889/tcp

### set container entry
# ENTRYPOINT [ "/bin/bash" ]