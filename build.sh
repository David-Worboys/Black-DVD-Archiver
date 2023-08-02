# Nuitka compile script for the black-dvd-archiver. Note hardcoding of paths, will need to be updated if used in another dev env.
#
# 23/03/2023 David Worboys Initial Commit
# 10/07/2023 David Worboys added --python-flag=isolated
# 29/07/2023 David Worboys added lto, -OO in python-flag and removed data_parser

python -m nuitka --lto=yes --python-flag=-OO --python-flag=no_warnings --python-flag=isolated  --verbose --verbose-output=./release/verbose.txt --disable-console --static-libpython=yes --standalone  --onefile --prefer-source-code --include-qt-plugins=sensible,multimedia  --assume-yes-for-downloads --show-anti-bloat-changes --enable-plugin=pyside6 --output-filename=black-dvd-archiver --output-dir=./release --linux-icon=/home/david/PycharmProjects/dvdarch/pycode/logo.jpg --include-data-files=*.svg=./ --include-data-files=*.png=./ --include-data-files=*.jpg=./ --include-data-files=*.md=./ --include-data-dir=/home/david/PycharmProjects/dvdarch/pycode/tools=./tools --include-data-dir=/home/david/PycharmProjects/dvdarch/pycode/icons=./icons --include-data-dir=/home/david/PycharmProjects/dvdarch/pycode/IBM-Plex-Mono=./IBM-Plex-Mono  dvdarchiver.py
