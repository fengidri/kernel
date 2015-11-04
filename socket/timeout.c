/**
 *   author       :   丁雪峰
 *   time         :   2015-11-04 02:52:17
 *   email        :   fengidri@yeah.net
 *   version      :   1.0.1
 *   description  :
 */
#include <stdio.h>
#include <stddef.h>
#include <unistd.h>
#include <string.h>

#include <sys/socket.h>
#include <sys/types.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <netinet/in.h>

int main(int argc, char **argv)
{
    int fd;
    struct sockaddr_in saddr;
    socklen_t saddr_size = sizeof(saddr);

    saddr.sin_family = AF_INET;
    saddr.sin_port = htons(9090);
    saddr.sin_addr.s_addr = inet_addr("127.0.0.1");

    fd = socket(AF_INET, SOCK_STREAM, 0);

    //struct timeval timeo = {3, 0};
    //socklen_t timelen = sizeof(timeo);

    //setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &timeo, timelen);


    if(-1 == connect(fd,  (struct sockaddr*)&saddr, saddr_size))
    {
        perror("connect");
        return 0;
    }
    printf("connected\n");
    return 0;
}
