/**
 *   author       :   丁雪峰
 *   time         :   2018-12-03 11:47:55
 *   email        :   fengidri@yeah.net
 *   version      :   1.0.1
 *   description  :
 */

#include <linux/init.h>
#include <linux/module.h>
#include <net/sock.h>
#include <net/netlink.h>
#include <linux/string.h>

#define NETLINK_TCP_RECORD 25
#define MAX_MSGSIZE 64

static struct sock *nl_sock = NULL;
static int pid;

void send_msg(char *msg, int msglen)
{
    struct sk_buff *skb = NULL;
    struct nlmsghdr *nlh = NULL;
    int rc;

    if (msg == NULL || nl_sock == NULL || 0 == pid) {
        return;
    }

    skb = alloc_skb(NLMSG_SPACE(msglen), GFP_KERNEL);
    if (skb == NULL) {
        printk(KERN_ERR "allock skb failed!\n");
        return;
    }

    nlh = nlmsg_put(skb, 0, 0, 0, msglen, 0);
    NETLINK_CB(skb).portid = 0;
    NETLINK_CB(skb).dst_group = 0;
    memcpy(NLMSG_DATA(nlh), msg, msglen);


    rc = netlink_unicast(nl_sock, skb, pid, MSG_DONTWAIT);
    if (rc < 0)
    {
        pid = 0;
        printk("rc: %d set pid to 0\n", rc);
    }
}

static void recv_msg(struct sk_buff *in_skb)
{
    struct sk_buff *skb = NULL;
    struct nlmsghdr *nlh = NULL;

    skb = skb_get(in_skb);
    if (skb->len >= nlmsg_total_size(0)) {
        nlh = nlmsg_hdr(skb);


        pid = nlh->nlmsg_pid;

        printk("receive pid: %d msg: %s.\n", pid, (char *)NLMSG_DATA(nlh));

        kfree_skb(skb);
    }
}

int netlink_init(void)
{
    struct netlink_kernel_cfg netlink_cfg;
    memset(&netlink_cfg, 0, sizeof(struct netlink_kernel_cfg));
    netlink_cfg.input = recv_msg;

    nl_sock = netlink_kernel_create(&init_net,
            NETLINK_TCP_RECORD, &netlink_cfg);
    if (nl_sock == NULL) {
        printk(KERN_ERR "netlink: netlink_kernel_create failed!\n");
        return -1;
    }

    printk("netlink: netlink module init success!\n");
    return 0;
}

void netlink_exit(void)
{
    if (nl_sock != NULL) {
        sock_release(nl_sock->sk_socket);
    }

    printk("netlink: netlink module exit success!\n");
}
