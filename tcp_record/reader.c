/**
 *   author       :   丁雪峰
 *   time         :   2018-12-03 14:38:55
 *   email        :   fengidri@yeah.net
 *   version      :   1.0.1
 *   description  :
 */
#include <sys/stat.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <string.h>
#include <asm/types.h>
#include <linux/netlink.h>
#include <linux/socket.h>
#include <errno.h>
#include <fcntl.h>
#define NETLINK_TCP_RECORD 25

static int filefd;

int netlink_bind(int tp)
{
    struct sockaddr_nl src_addr;
    int sock_fd, retval;

    sock_fd = socket(AF_NETLINK, SOCK_RAW, tp);
    if(sock_fd == -1){
        printf("error getting socket: %s", strerror(errno));
        return -1;
    }

    // To prepare binding
    memset(&src_addr, 0, sizeof(src_addr));
    src_addr.nl_family = AF_NETLINK;
    src_addr.nl_pid    = 100; //A：设置源端端口号
    src_addr.nl_groups = 0;

    //Bind
    retval = bind(sock_fd, (struct sockaddr*)&src_addr, sizeof(src_addr));
    if(retval < 0){
        printf("bind failed: %s", strerror(errno));
        close(sock_fd);
        return -1;
    }

    return sock_fd;
}


int netlink_send(int sock_fd, const char *str, int src)
{
    struct nlmsghdr *nlh = NULL; //Netlink数据包头
    char buf[NLMSG_SPACE(1024)];
    struct iovec iov;
    struct msghdr msg;
    struct sockaddr_nl dest_addr;

    nlh = (struct nlmsghdr *)buf;


    memset(&dest_addr,0,sizeof(dest_addr));
    dest_addr.nl_family = AF_NETLINK;
    dest_addr.nl_pid    = 0; //B：设置目的端口号
    dest_addr.nl_groups = 0;

    nlh->nlmsg_len   = NLMSG_SPACE(1024);
    nlh->nlmsg_pid   = src; //C：设置源端口
    nlh->nlmsg_flags = 0;

    strcpy(NLMSG_DATA(nlh), str); //设置消息体

    iov.iov_base = (void *)nlh;
    iov.iov_len = NLMSG_SPACE(1024);

    //Create mssage
    memset(&msg, 0, sizeof(msg));
    msg.msg_name = (void *)&dest_addr;
    msg.msg_namelen = sizeof(dest_addr);
    msg.msg_iov = &iov;
    msg.msg_iovlen = 1;

    return sendmsg(sock_fd, &msg,0);
}

typedef  int (netlink_handler)(int rc, struct nlmsghdr *nlh);

int netlink_recv(int sock_fd, netlink_handler *handler)
{
    int rc;
    struct nlmsghdr *nlh = NULL; //Netlink数据包头

    char buf[NLMSG_SPACE(1024)];
    struct iovec iov;
    struct msghdr msg;

    nlh = (struct nlmsghdr *)buf;

    nlh->nlmsg_len   = NLMSG_SPACE(1024);
    nlh->nlmsg_pid   = 0; //C：设置源端口
    nlh->nlmsg_flags = 0;


    iov.iov_base = (void *)nlh;
    iov.iov_len = NLMSG_SPACE(1024);

    //Create mssage
    memset(&msg, 0, sizeof(msg));
    msg.msg_iov = &iov;
    msg.msg_iovlen = 1;

    while(1){
        rc = recvmsg(sock_fd, &msg, 0);
        handler(rc, nlh);
    }
}


int msg_handler(int rc, struct nlmsghdr *nlh)
{
    static int total;
    char *msg;

    if (rc < 0) return -1;

    //printf("recv msglen: %d %ld\n", nlh->nlmsg_len, strlen(msg));

    msg = (char *)NLMSG_DATA(nlh);
    rc = write(filefd, msg, strlen(msg));
    if (rc < 0)
    {
        printf("write file error:%s\n", strerror(errno));
    }

    total += nlh->nlmsg_len;

    if (total > 1024 * 1024 * 1024)
    {
        ftruncate(filefd, 0);
        lseek(filefd, 0, SEEK_SET);
        total = 0;
    }

    return 0;
}



int main(int argc, char* argv[])
{
    int fd;

    if (argc == 2)
    {
        filefd = open(argv[1], O_WRONLY|O_APPEND | O_CREAT, S_IRUSR | S_IWUSR);
        if (filefd < 0)
        {
            printf("open file %s: %s", argv[1], strerror(errno));
            return -1;
        }
    }
    else{
        filefd = 1;
    }


    fd = netlink_bind(NETLINK_TCP_RECORD);

    if(fd == -1){
        printf("error getting socket: %s", strerror(errno));
        return -1;
    }

    int rc;

    rc = netlink_send(fd, "hi", 100);

    if (rc < 0)
    {
        printf("get error sendmsg = %s\n",strerror(errno));
        return -1;
    }

    printf("waiting received!\n");

    netlink_recv(fd, msg_handler);

    close(fd);
    return 0;
}












