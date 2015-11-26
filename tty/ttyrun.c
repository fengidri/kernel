/**
 *   author       :   丁雪峰
 *   time         :   2015-11-26 07:08:06
 *   email        :   fengidri@yeah.net
 *   version      :   1.0.1
 *   description  :
 */
#include <stdio.h>
#include <stddef.h>
#include <unistd.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/ioctl.h>
#include <string.h>
#include <unistd.h>
#include <ctype.h>
#include <termios.h>

void print_help(char *prog_name) {
        printf("Usage: %s [-n] DEVNAME COMMAND\n", prog_name);
        printf("Usage: '-n' is an optional argument if you want to push a new line at the end of the text\n");
        printf("Usage: Will require 'sudo' to run if the executable is not setuid root\n");
        exit(1);
}

int openfd(char *path)
{
    int fd;
    char *p;
    char dev[30];
    p = path;
    if ('/' != *p)
    {
        if (isdigit(*p))
        {
            sprintf(dev, "/dev/pts/%s", p);
        }
        else{
            sprintf(dev, "/dev/%s", p);
        }
        p = dev;
    }

    fd = open(p, O_RDWR);
    if(fd == -1) {
        perror("open DEVICE");
        return -1;
    }
    return fd;
}

int sendcmd(int fd, int argc, char **argv)
{
    int i, j;
    for (i = 2; i < argc; i++) {
        for (j = 0; argv[i][j]; j++)
            ioctl(fd, TIOCSTI, argv[i] + j); // the threth arg is pointer to the byte

        ioctl(fd, TIOCSTI, " ");
    }

    ioctl(fd, TIOCSTI, "\n");
    return 0;
}

int sendint(int fd)
{
    struct termios options;
    if (0 != tcgetattr(fd, &options))
    {
        return -1;
    }

    ioctl(fd, TIOCSTI, &options.c_cc[VINTR]);
    printf("Send VINTR\n");
    return 0;
}

int main (int argc, char *argv[]) {
    int fd;
    if (argc < 3) {
        print_help(argv[0]);
    }

    fd = openfd(argv[1]);
    if (-1 == fd) return -1;

    if (argc == 3 && argv[2][0] == '-' && argv[2][1] == 'c') {
        sendint(fd);
    }
    else{
        sendcmd(fd, argc, argv);
    }

    close(fd);
}
