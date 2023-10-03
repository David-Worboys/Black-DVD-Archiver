# Nuitka compile script for the black-dvd-archiver. Note hard coding of paths, will need to be updated if used in another
# dev env.
#
# 23/03/2023 David Worboys Initial Commit
# 10/07/2023 David Worboys added --python-flag=isolated
# 29/07/2023 David Worboys added lto, -OO in python-flag and removed data_parser
# 31/08/2023 David Worboys changed folder tools to folder  tool_apps
# 13/09/2023 David Worboys Added --include-module=dbm as Nuitka 1.8 serious did not include thus automatically
#                          Removed a test include that got committed by mistake

python -m nuitka --lto=yes --python-flag=-OO --python-flag=no_warnings --python-flag=isolated  --verbose --verbose-output=./release/verbose.txt --disable-console --static-libpython=yes --standalone  --onefile --prefer-source-code  --include-module=dbm --include-qt-plugins=sensible,multimedia  --assume-yes-for-downloads --show-anti-bloat-changes --enable-plugin=pyside6 --output-filename=black-dvd-archiver --output-dir=./release --linux-icon=/home/david/PycharmProjects/dvdarch/pycode/logo.jpg --include-data-files=*.svg=./ --include-data-files=*.png=./  --include-data-files=*.jpg=./ --include-data-files=*.md=./ --include-data-dir=/home/david/PycharmProjects/dvdarch/pycode/tool_apps=./tool_apps --include-data-dir=/home/david/PycharmProjects/dvdarch/pycode/icons=./icons --include-data-dir=/home/david/PycharmProjects/dvdarch/pycode/IBM-Plex-Mono=./IBM-Plex-Mono  dvdarchiver.py
