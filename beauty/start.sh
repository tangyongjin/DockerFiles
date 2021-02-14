docker run -it -d  -p 3001:80  -v ${PWD}/html/:/var/www/html -v ${PWD}/logs:/opt/logs/   --name=beauty   beauty /bin/bash
