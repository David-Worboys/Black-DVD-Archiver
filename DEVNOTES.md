# The Black DVD Archiver - Developer Notes (Preliminary)
## Tool Apps
The perform a range of tasks in preparing a DVD the following open source software is used:

**Note:** composite is an older version of magick, but it behaves differently and gets the results I want and that is why
it is included. In theory magick alone can be used and this should be tested with future releases.
* composite (https://github.com/ImageMagick/ImageMagick6)
* magick (https://imagemagick.org/script/download.php)
* dvdauthor (https://sourceforge.net/projects/dvdauthor/files/)
* ffmpeg  (https://ffmpeg.org/download.html)
* ffprobe (https://ffmpeg.org/download.html)
* identify (https://imagemagick.org/script/download.php)
* mediainfo (https://mediaarea.net/en/MediaInfo/Download) 
* mpeg2enc (https://gstreamer.freedesktop.org/documentation/mpeg2enc/index.html)
* mplex (https://www.linuxtv.org/wiki/index.php/Mplex)
* ppmtoy4m (https://sourceforge.net/projects/mjpeg/)
* spumux (https://sourceforge.net/projects/dvdauthor/files/)
* xorriso (https://www.gnu.org/software/xorriso/)

These are binary files that I have mostly statically compiled from source.

The next step requires the  linuxdeploy-x86_64.AppImage (https://github.com/linuxdeploy/linuxdeploy/releases/)

To prepare the tool_apps folder a developer needs to copy these binaries into a tools folder with the strucuture below:

```
project folder
│
└───tools
   │ composite
   │ magick
   │ dvdauthor
   │ ffmpeg 
   │ ffprobe
   │ identify   
   │ mediainfo
   │ mpeg2enc
   │ mplex
   │ ppmtoy4m
   │ spumux
   │ xorriso
   │
   └───tool_apps
```   

The following command will now be run in the tools folder.

**Note:**
The paths will need to be changed to reflect the actual tools folder structure above:

~/Programs/linuxdeploy-x86_64.AppImage --appdir /home/david/PycharmProjects/dvdarch/tools/tool_apps --executable /home/david/PycharmProjects/dvdarch/tools/composite   --executable /home/david/PycharmProjects/dvdarch/tools/dvdauthor   --executable /home/david/PycharmProjects/dvdarch/tools/ffmpeg --executable /home/david/PycharmProjects/dvdarch/tools/ffprobe --executable /home/david/PycharmProjects/dvdarch/tools/identify  --executable /home/david/PycharmProjects/dvdarch/tools/magick --executable /home/david/PycharmProjects/dvdarch/tools/mediainfo --executable /home/david/PycharmProjects/dvdarch/tools/mp2enc --executable /home/david/PycharmProjects/dvdarch/tools/mp2enc --executable /home/david/PycharmProjects/dvdarch/tools/mpeg2enc --executable /home/david/PycharmProjects/dvdarch/tools/mplex --executable /home/david/PycharmProjects/dvdarch/tools/ppmtoy4m --executable /home/david/PycharmProjects/dvdarch/tools/spumux   --executable /home/david/PycharmProjects/dvdarch/tools/xorriso


