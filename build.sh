# Nuitka compile script for the black-dvd-archiver. Note hardcoding of paths, will need to be updated if used in another dev env.
#
# 23/03/2023 David Worboys Initial Commit

python -m nuitka --python-flag=-O --python-flag=no_warnings --verbose --verbose-output=./release/verbose.txt --static-libpython=auto --standalone  --onefile --prefer-source-code --include-qt-plugins=sensible,multimedia --follow-imports --assume-yes-for-downloads --static-libpython=yes --show-anti-bloat-changes --enable-plugin=pyside6 --output-filename=black-dvd-archiver --output-dir=./release --linux-icon=/home/david/PycharmProjects/dvdarch/pycode/logo.png --include-data-files=*.svg=./ --include-data-files=*.png=./ --include-data-dir=/home/david/PycharmProjects/dvdarch/pycode/tools=./tools --include-data-dir=/home/david/PycharmProjects/dvdarch/pycode/IBM-Plex-Mono=./IBM-Plex-Mono --include-module=dateparser dvdarchiver.py
