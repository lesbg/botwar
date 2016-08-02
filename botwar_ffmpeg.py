#!/usr/bin/python

import botwar_ui
import sys
import pygame
import os
import subprocess

class VideoClock(object):
    fd = None
    surface = None
    frame = 0
    
    def __init__(self, filename, surface):
        try:
            fd = open(filename, "w")
        except:
            print "Unable to open video file %s for writing" % filename
            sys.exit(1)
        fd.close()
        command = [ 'ffmpeg',
            '-y', # (optional) overwrite output file if it exists
            '-f', 'rawvideo',
            '-vcodec','rawvideo',
            '-s', '1280x536', # size of one frame
            '-pix_fmt', 'rgb24',
            '-r', '60', # frames per second
            '-i', '-', # The imput comes from a pipe
            '-an', # Tells FFMPEG not to expect any audio
            '-c:v', 'libx264', # H264
            '-crf', '21',      # Constant rate factor of 21
            '-vf', 'fps=30',   # 30 FPS
            '-pix_fmt', 'yuv444p',
            filename ]
            
        self.fd = subprocess.Popen( command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        self.surface = surface
            
    def tick(self, frames):
        frames = int(frames*30)
        buf = pygame.image.tostring(self.surface, "RGB")
        self.fd.stdin.write(buf)
        self.frame += 1
        if frames > 1:
            self.fd.stdin.write(buf)
            self.frame += 1
        del buf


video_file = sys.argv[-1]
sys.argv = sys.argv[:-1]
botwar_ui.init()
botwar_ui.screen = botwar_ui.w.set_res(1280, 536)
#botwar_ui.screen = botwar_ui.w.set_res(1920, 804)
botwar_ui.set_clock(VideoClock(video_file, botwar_ui.screen))
botwar_ui.main()


