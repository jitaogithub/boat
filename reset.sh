#!/bin/sh
num_nodes=3
if [ $# -gt 1 ] ; then
    echo "ERROR: [reset.sh] Incorrect number of arguments. Usage: sh reset.sh [NUM_NODES]"
    exit 1
elif [ $# -eq 1 ] ; then
    num_nodes=$1
fi

echo "INFO: [reset.sh] Cleaning up Clipper"
i=0
while [ $i -lt $num_nodes ] ; do
    containers=`docker network inspect clipper_network_$i --format '{{range .Containers}}{{println .Name}}{{end}}'`
    docker stop $containers >&- 2>&-
    docker rm $containers >&- 2>&-
    docker network rm clipper_network_$i >&- 2>&-
    i=$(($i+1))
done
images=`docker images --format '{{.Repository}}\t{{.ID}}' | grep '<none>' | cut -f 2`
docker image rm $images >&- 2>&-

echo "INFO: [reset.sh] All Clipper containers, networks and outdated images are cleared away."
exit 0