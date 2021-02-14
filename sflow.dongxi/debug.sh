docker run -it  -v /ixpdata:/ixpdata -v $PWD/dongxi.php:/dongxi.php     --network=docker_default -p 5501:5501/udp  ixp.sflowdongxi  /bin/bash
