# The Black DVD Archiver—Developer Notes (Preliminary)
### Author: David Worboys 
* Original 2023-09-01 
* Update 2024-05-16 (Removed apps that are no longer used)

## Introduction
The Black DVD Archiver comprises source code written in python (3.11) and a number of open source applications used for 
specific tasks during the preparation of a DVD image [refer Tool Apps](#tool-apps).

## Contributions
There is still much to be done, and if anyone wants to contribute code or doco, please reach out to me as help is always 
welcome.

## Distribution
The python code is compiled with Nuitka (https://github.com/Nuitka/Nuitka) which produces a standalone 
executable: **black-dvd-archiver**. 

This executable is the only file needed, and it will be over 100MB in size as is normal for standalone python programs, 
as they suck so many libraries and associated files in.  

The **build.sh** script performs this compilation 

**Note:** the folder paths might need updating to work in other dev 
environments

## QTPYGUI
The QTPYGUI package (https://github.com/David-Worboys/QTPYGUI) is used to generate the user interface layer. 

## Tool Apps
To perform a range of tasks in preparing a DVD the following open source software is used (refer to the links as a 
starting point to find the relevant licensing details):

* composite (https://github.com/ImageMagick/ImageMagick6)
* magick (https://imagemagick.org/script/download.php)
* dvdauthor (https://sourceforge.net/projects/dvdauthor/files/)
* ffmpeg  (https://ffmpeg.org/download.html)
* ffprobe (https://ffmpeg.org/download.html)
* * genisoimage (https://www.gnu.org/software/xorriso/)
* identify (https://imagemagick.org/script/download.php)
* mplex (https://www.linuxtv.org/wiki/index.php/Mplex)
* spumux (https://sourceforge.net/projects/dvdauthor/files/)

**Note:** composite is an older version of magick, but it behaves differently and gets the results I want and that is why
it is included. In theory magick alone can be used and this should be tested with future releases.

These binary files are mostly statically compiled where I can get the source. However, they use shared object  
files and will not run standalone on a different computer, with potentially a different linux distro.

### Preparing Standalone Linux Binaries

To make these binary files run standalone, we need to create a separate file structure for them and process them in a way 
that will package the requisite shared object files and modify the shared object file embedded library paths to make them
system independent.

This step requires the linuxdeploy-x86_64.AppImage (https://github.com/linuxdeploy/linuxdeploy/releases/) binary.

**Note** An appimage binary is not being created, I am simply using the linuxdeploy-x86_64.AppImage binary to make a 
standalone file structure that packages the required binaries in a way that will make them platform independent

To prepare the tool_apps folder, a developer needs to copy these binaries into a tools folder with the strucuture below:

```
project folder
│
└───tools
   │ composite
   │ magick
   │ dvdauthor
   │ ffmpeg 
   │ ffprobe
   | genisoimage
   │ identify         
   │ mplex
   │ spumux   
   │
   └───tool_apps
```   

The following command will now be run in the tools folder, and this will populate the tool_apps folder with the linux 
binaries and associated shared object libraries in its own file system.

**Note**: Remove the tool_apps folder before running this command 

The tool_apps folder can now be copied into the root of the Black DVD Archiver source tree.

**Note:**
The paths will need to be changed to reflect the actual tools folder structure above:
```
~/Programs/linuxdeploy-x86_64.AppImage --appdir /home/david/PycharmProjects/dvdarch/tools/tool_apps --executable /home/david/PycharmProjects/dvdarch/tools/composite   --executable /home/david/PycharmProjects/dvdarch/tools/dvdauthor   --executable /home/david/PycharmProjects/dvdarch/tools/ffmpeg --executable /home/david/PycharmProjects/dvdarch/tools/ffprobe --executable /home/david/PycharmProjects/dvdarch/tools/identify  --executable /home/david/PycharmProjects/dvdarch/tools/magick --executable /home/david/PycharmProjects/dvdarch/tools/mplex  --executable /home/david/PycharmProjects/dvdarch/tools/spumux   --executable /home/david/PycharmProjects/dvdarch/tools/genisoimage
```


