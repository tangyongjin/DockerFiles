docker run -d -p 8090:80 --name wiki --rm   \
-v $(pwd)/volumes/dokuwiki/data:/dokuwiki/data:rw \
-v $(pwd)/volumes/dokuwiki/lib/plugins:/dokuwiki/lib/plugins:rw \
-v $(pwd)/volumes/dokuwiki/conf:/dokuwiki/conf:rw \
-v $(pwd)/volumes/dokuwiki/lib/tpl:/dokuwiki/lib/tpl:rw \
mprasil/dokuwiki 
