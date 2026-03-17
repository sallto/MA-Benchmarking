podman run -it --security-opt label=disable \
  -v /opt/CPU2017v1.1.0/:/spec_mount:ro \
  myimage:latest
