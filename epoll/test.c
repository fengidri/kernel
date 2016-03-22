/**
 *   author       :   丁雪峰
 *   time         :   2016-03-18 02:41:56
 *   email        :   fengidri@yeah.net
 *   version      :   1.0.1
 *   description  :
 */



#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/epoll.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <netdb.h>
#include <stdio.h>
#include <stdlib.h>
#include <signal.h> //  our new library

/*struct addrinfo
{
	int              ai_flags;
	int              ai_family;
	int              ai_socktype;
	int              ai_protocol;
	size_t           ai_addrlen;
	struct sockaddr *ai_addr;
	char            *ai_canonname;
	struct addrinfo *ai_next;
}; */

int sndbuf = 0;



static void write_data(int fd)
{
    size_t total = 0;
    char buf[512];
    int n;

    while(1)
    {
        n = write(fd, buf, 512);
        if (0 > n) break;
        total += n;
    }
    printf("FD: %d Write Data: %lu ", fd, total);
}

static int create_and_bind(char* port)
{
	struct addrinfo hints;
	struct addrinfo*result,*rp;
	int s,sfd;

	memset(&hints,0,sizeof(struct addrinfo));
	hints.ai_family= AF_UNSPEC;/* Return IPv4 and IPv6 */
	hints.ai_socktype= SOCK_STREAM;/* TCP socket */
	hints.ai_flags= AI_PASSIVE;/* All interfaces */

	s = getaddrinfo(NULL, port, &hints,&result); //more info about getaddrinfo() please see:man getaddrinfo!
	if(s != 0)
	{
		fprintf(stderr,"getaddrinfo: %s\n",gai_strerror(s));
		return -1;
	}
	for(rp= result;rp!= NULL;rp=rp->ai_next)
	{
		sfd = socket(rp->ai_family,rp->ai_socktype,rp->ai_protocol);
		if(sfd==-1)
			continue;
		s =bind(sfd,rp->ai_addr,rp->ai_addrlen);
		if(s ==0)
		{
			/* We managed to bind successfully! */
			break;
		}
		close(sfd);
	}

	if(rp== NULL)
	{
		fprintf(stderr,"Could not bind\n");
		return-1;
	}
	freeaddrinfo(result);
	return sfd;
}

static int make_socket_non_blocking(int sfd)
{
	int flags, s;
	flags = fcntl(sfd, F_GETFL,0);
	if(flags == -1)
	{
		perror("fcntl");
		return-1;
	}

	flags|= O_NONBLOCK;
	s =fcntl(sfd, F_SETFL, flags);
	if(s ==-1)
	{
		perror("fcntl");
		return-1;
	}
	return 0;
}

static int listen_to_port(char *port, char **log)
{
    int sfd;
	sfd = create_and_bind(port);
	if(sfd == -1)
    {
        if (log) *log = "bind!";
        return -1;
    }

	if(-1 == make_socket_non_blocking(sfd)){
        if (log) *log = "non_blocking!";
        return -1;
    }

    if (sndbuf)
    {
        printf("Set SO_SNDBUF:%d\n", sndbuf);
        setsockopt(sfd, SOL_SOCKET, SO_SNDBUF, (char *)&sndbuf, sizeof sndbuf);
    }

	if(-1 == listen(sfd, SOMAXCONN)){
        if (log) *log = "listen error!";
        return -1;
    }

    return sfd;
}

int LOOP = 1;

void handle_signal(int sig)
{ // can be called asynchronously
    printf("Recv signal will stop, wait ...\n");
    LOOP = 0;
}


#define MAXEVENTS 64
int main(int argc, char*argv[])
{
	int sfd, s;
	int efd;
	struct epoll_event event;
	struct epoll_event* events;
    char *log;

    signal(SIGINT, handle_signal);

	if(argc!=3)
	{
		fprintf(stderr,"Usage: %s [port] [SNDBUF]\n",argv[0]);
		exit(EXIT_FAILURE);
	}

    sndbuf = atoi(argv[2]);

	efd = epoll_create1(0);
	if(efd==-1)
	{
		perror("epoll_create");
		abort();
	}


    sfd = listen_to_port(argv[1], &log);
    if (-1 == sfd)
    {
        printf("%s\n", log);
        return 0;
    }

	event.data.fd = sfd;
	event.events = EPOLLIN | EPOLLET | EPOLLOUT;
	s =epoll_ctl(efd, EPOLL_CTL_ADD,sfd,&event);
	if(s ==-1)
	{
		perror("epoll_ctl");
		abort();
	}

	/* Buffer where events are returned */
	events=calloc(MAXEVENTS,sizeof event);

	/* The event loop */
	while(LOOP)
	{
		int n,i;
        printf("\n");
		n =epoll_wait(efd, events, MAXEVENTS, 10);
        printf("Wake: %d", n);

		for(i=0;i< n;i++)
		{
			if((events[i].events & EPOLLERR)|| (events[i].events & EPOLLHUP))
			{
				/* An error has occured on this fd, or the socket is not
				   ready for reading (why were we notified then?) */
				fprintf(stderr,"epoll error\n");
				close(events[i].data.fd);
				continue;
			}

			else if(sfd == events[i].data.fd)
			{
				/* We have a notification on the listening socket, which
				   means one or more incoming connections. */
				while(1)
				{
					struct sockaddr in_addr;
					socklen_t in_len;
					int infd;
					char hbuf[NI_MAXHOST],sbuf[NI_MAXSERV];

					in_len = sizeof in_addr;
					infd = accept(sfd,&in_addr,&in_len);
					if(infd==-1)
					{
						if((errno== EAGAIN)||
								(errno== EWOULDBLOCK))
						{
							/* We have processed all incoming
							   connections. */
							break;
						}
						else
						{
							perror("accept");
							break;
						}
					}

					s =getnameinfo(&in_addr,in_len,
							hbuf,sizeof hbuf,
							sbuf,sizeof sbuf,
							NI_NUMERICHOST | NI_NUMERICSERV);
					if(s ==0)
					{
						printf("Accepted connection on descriptor %d "
								"(host=%s, port=%s)\n",infd,hbuf,sbuf);
					}

					/* Make the incoming socket non-blocking and add it to the
					   list of fds to monitor. */
					s = make_socket_non_blocking(infd);
					if(s ==-1)
						abort();

					event.data.fd=infd;
					event.events= EPOLLIN | EPOLLET | EPOLLOUT;
					s = epoll_ctl(efd, EPOLL_CTL_ADD,infd,&event);
					if(s ==-1)
					{
						perror("epoll_ctl");
						abort();
					}
				}
				continue;
			}
			else if (events[i].events & EPOLLIN)
			{
				/* We have data on the fd waiting to be read. Read and
				   display it. We must read whatever data is available
				   completely, as we are running in edge-triggered mode
				   and won't get a notification again for the same
				   data. */
				int done =0;
				while(1)
				{
					ssize_t count;
					char buf[512];
					count = read(events[i].data.fd,buf,sizeof buf);
					if(count == -1)
					{
						/* If errno == EAGAIN, that means we have read all
						   data. So go back to the main loop. */
						if(errno!= EAGAIN)
						{
							perror("read");
							done=1;
						}
						break;
					}
					else if(count ==0)
					{
						/* End of file. The remote has closed the
						   connection. */
						done=1;
						break;
					}
                    write_data(events[i].data.fd);
				}
			}
			else if (events[i].events & EPOLLOUT)
            {
                write_data(events[i].data.fd);

            }
		}
	}
	free(events);
	close(sfd);
    close(efd);
	return EXIT_SUCCESS;
}







