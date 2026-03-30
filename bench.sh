docker start -ai `cat container_id.txt` << "make all;exit;"
docker cp `cat container_id.txt`:/bench/latex ./latex.`cat container_id.txt`
