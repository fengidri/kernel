/**
 *   author       :   丁雪峰
 *   time         :   2015-11-04 01:11:59
 *   email        :   fengidri@yeah.net
 *   version      :   1.0.1
 *   description  :
 */
#include <stdio.h>
#include <stddef.h>
#include <unistd.h>
#include <string.h>
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
    saddr.sin_port = htons(9065);
    saddr.sin_addr.s_addr = inet_addr("127.0.0.1");
    fd = socket(AF_INET, SOCK_RAW, IPPROTO_TCP);
    char buffer[65535];
    while(1)
    {
        recvfrom(fd, buffer, 65535, 0, (struct sockaddr*)&saddr, &saddr_size);
        printf("recv some.\n");
    }
    return 0;
}
