all: publications sync

publications:
	 /opt/jabref/bin/JabRef -n -o publications-feng.html,mylistrefs ../publications-feng.bib

snippets:
	/opt/jabref/bin/JabRef -n -o publications-feng_snippets.html,mylistrefs_snippets -i ../publications-feng.bib

sync:
	rsync -av publications-feng.html ${HOME}/nextcloud/feng.li/cv/publications.html
