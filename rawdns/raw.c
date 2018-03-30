/**
 *   author       :   丁雪峰
 *   time         :   2018-03-29 20:32:44
 *   email        :   fengidri@yeah.net
 *   version      :   1.0.1
 *   description  :
 */
#include <stdio.h>
#include <stddef.h>
#include <unistd.h>
#include <string.h>
/*
    Raw UDP sockets
*/
#include<stdio.h> //for printf
#include<string.h> //memset
#include<sys/socket.h>    //for socket ofcourse
#include<stdlib.h> //for exit(0);
#include<errno.h> //For errno - the error number
#include<netinet/udp.h>   //Provides declarations for udp header
#include<netinet/ip.h>    //Provides declarations for ip header
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

/*
    96 bit (12 bytes) pseudo header needed for udp header checksum calculation
*/
struct pseudo_header
{
    u_int32_t source_address;
    u_int32_t dest_address;
    u_int8_t placeholder;
    u_int8_t protocol;
    u_int16_t udp_length;
};

/*
    Generic checksum calculation function
*/
unsigned short csum(unsigned short *ptr,int nbytes)
{
    register long sum;
    unsigned short oddbyte;
    register short answer;

    sum=0;
    while(nbytes>1) {
        sum+=*ptr++;
        nbytes-=2;
    }
    if(nbytes==1) {
        oddbyte=0;
        *((u_char*)&oddbyte)=*(u_char*)ptr;
        sum+=oddbyte;
    }

    sum = (sum>>16)+(sum & 0xffff);
    sum = sum + (sum>>16);
    answer=(short)~sum;

    return(answer);
}


char *mk_packet(const char *srcip, const char *dstip, int srcport, int dstport, char *msg, unsigned short *size)
{
    //Datagram to represent the packet
    char *datagram , source_ip[32],  *pseudogram, *data;

    //zero out the packet buffer

    datagram = malloc(4096);
    memset(datagram, 0, 4096);

    //IP header
    struct iphdr *iph = (struct iphdr *) datagram;

    //UDP header
    struct udphdr *udph = (struct udphdr *) (datagram + sizeof (struct ip));

    struct pseudo_header psh;

    //Data part
    data = datagram + sizeof(struct iphdr) + sizeof(struct udphdr);
    memcpy(data, msg, *size);


    //Fill in the IP Header
    iph->ihl      = 5;
    iph->version  = 4;
    iph->tos      = 0;
    iph->tot_len  = sizeof(struct iphdr) + sizeof(struct udphdr) + *size;
    iph->id       = htonl (54321); //Id of this packet
    iph->frag_off = 0;
    iph->ttl      = 255;
    iph->protocol = IPPROTO_UDP;
    iph->check    = 0;      //Set to 0 before calculating checksum
    iph->saddr    = inet_addr(srcip);    //Spoof the source ip address
    iph->daddr    = inet_addr(dstip);

    //Ip checksum
    iph->check = csum ((unsigned short *) datagram, iph->tot_len);

    //UDP header
    udph->source = htons(srcport);
    udph->dest   = htons(dstport);
    udph->len    = htons(8 + *size); //tcp header size
    udph->check  = 0;      //leave checksum 0 now, filled later by pseudo header

    //Now the UDP checksum using the pseudo header
    psh.source_address = inet_addr(srcip);
    psh.dest_address   = inet_addr(dstip);
    psh.placeholder    = 0;
    psh.protocol       = IPPROTO_UDP;
    psh.udp_length     = htons(sizeof(struct udphdr) + *size);

    int psize = sizeof(struct pseudo_header) + sizeof(struct udphdr) + *size;
    pseudogram = malloc(psize);

    memcpy(pseudogram , (char*) &psh , sizeof (struct pseudo_header));
    memcpy(pseudogram + sizeof(struct pseudo_header) , udph , sizeof(struct udphdr) + *size);

    udph->check = csum( (unsigned short*) pseudogram , psize);

    *size = iph->tot_len;
    return datagram;
}

char * ngethostbyname(unsigned char *host , unsigned short *size);
int main (int argc, char **argv)
{
    unsigned short size;
    char *msg, *packet;
    char name[100];
    const char *srcip = argv[3];
    const char *dstip = argv[2];
    int srcport = 3456;
    int dstport = 53;

    strcpy(name, argv[1]);
    msg = ngethostbyname(name, &size);


    packet = mk_packet(srcip, dstip, srcport, dstport, msg, &size);


    struct sockaddr_in sin;





    //Create a raw socket of type IPPROTO
    int s = socket (AF_INET, SOCK_RAW, IPPROTO_RAW);

    if(s == -1)
    {
        //socket creation failed, may be because of non-root privileges
        perror("Failed to create raw socket");
        exit(1);
    }

    sin.sin_family = AF_INET;
    sin.sin_port = htons(dstport);
    sin.sin_addr.s_addr = inet_addr(dstip);

    //Send the packet
    if (sendto (s, packet, size,  0, (struct sockaddr *)&sin, sizeof(sin)) < 0)
    {
        perror("sendto failed");
    }
    //Data send successfully
    else
    {
        printf ("Packet Send. Length : %d \n" , size);
    }

    return 0;
}

//Complete

