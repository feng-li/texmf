all: snippets publications sync

publications:
	 /opt/jabref/bin/JabRef -n -o publications-feng.html,mylistrefs ../publications-feng.bib
	 /opt/jabref/bin/JabRef -n -o publications-yanfei.html,mylistrefs ../publications-yanfei.bib
	 /opt/jabref/bin/JabRef -n -o publications-kllab.html,mylistrefs ../publications-kllab.bib

snippets:
	/opt/jabref/bin/JabRef -n -o publications-feng_snippets.html,mylistrefs_snippets -i ../publications-feng.bib
	/opt/jabref/bin/JabRef -n -o publications-yanfei_snippets.html,mylistrefs_snippets -i ../publications-yanfei.bib
	/opt/jabref/bin/JabRef -n -o publications-kllab_snippets.html,mylistrefs_snippets -i ../publications-kllab.bib

sync:
	rsync -av publications-feng.html ${HOME}/nextcloud/feng.li/cv/publications.html
