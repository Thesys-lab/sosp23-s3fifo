#!/bin/bash 

set -euo pipefail


if [ ! -d redis ]; then
    echo "Redis not found. Downloading..."
    wget https://download.redis.io/releases/redis-6.2.6.tar.gz 
    tar xvf redis-6.2.6.tar.gz 
    mv redis-6.2.6 redis;
    pushd redis
    make -j
    sed -i "/bind 127.0.0.1 -::1/d" redis.conf
    sed -i "s/port 6379/port 6400/g" redis.conf
    # echo 'user jason on +@all ~* >cloudlab' >> redis.conf 
    sed -i "s/# requirepass foobared/requirepass cloudlab/g" redis.conf
    popd
fi 

screen -S re -dm ./redis/src/redis-server ./redis/redis.conf
sleep 2
./redis/src/redis-cli -p 6400 -a cloudlab



